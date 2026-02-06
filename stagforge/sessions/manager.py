"""Session manager for tracking active editor sessions."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

from stagforge.api.data_cache import data_cache
from stagforge.bridge import editor_bridge, BridgeSessionError, BridgeTimeoutError

from .models import DocumentInfo, EditorSession, LayerInfo, SessionState


class SessionManager:
    """Manages all active editor sessions."""

    # Session timeout - sessions without heartbeat are removed after this
    SESSION_TIMEOUT_SECONDS = 6
    # Cleanup interval - how often to check for dead sessions
    CLEANUP_INTERVAL_SECONDS = 1

    def __init__(self):
        self._sessions: dict[str, EditorSession] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._session_timeout = timedelta(seconds=self.SESSION_TIMEOUT_SECONDS)
        self._running = False
        self._bridge_hooks_registered = False

    def register(
        self,
        session_id: str,
        client: Any = None,
        editor: Any = None,
    ) -> EditorSession:
        """Register a new session or return existing one."""
        # Start cleanup task if not running (lazy start since lifespan
        # events don't work for mounted sub-apps in NiceGUI)
        if not self._running:
            try:
                self.start_cleanup_task()
            except RuntimeError:
                # No event loop yet - will start on next register
                pass

        # Register bridge hooks lazily
        self._register_bridge_hooks()

        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.client = client
            session.editor = editor
            session.update_activity()
            print(f"[SessionManager] Updated existing session: {session_id}")
            # Try to set up bridge events if bridge session now exists
            self._setup_bridge_events(session_id)
            return session

        session = EditorSession(
            id=session_id,
            client=client,
            editor=editor,
        )
        self._sessions[session_id] = session

        # Set up bridge event handler for this session (if bridge session exists)
        self._setup_bridge_events(session_id)

        print(f"[SessionManager] Registered new session: {session_id}, total sessions: {len(self._sessions)}")
        return session

    def _register_bridge_hooks(self) -> None:
        """Register hooks with the editor bridge to sync sessions."""
        if self._bridge_hooks_registered:
            return

        self._bridge_hooks_registered = True

        # When a bridge session is created, ensure SessionManager knows about it
        def on_bridge_session_created(bridge_session):
            session_id = bridge_session.id
            print(f"[SessionManager] Bridge session created: {session_id}")

            # Create or update the session
            if session_id not in self._sessions:
                session = EditorSession(id=session_id)
                self._sessions[session_id] = session
                print(f"[SessionManager] Auto-registered session from bridge: {session_id}")

            # Set up event handler
            bridge_session.on_event = lambda event, data: self._handle_bridge_event(
                session_id, event, data
            )

        editor_bridge.on_session_created(on_bridge_session_created)
        print("[SessionManager] Registered bridge hooks")

        # Sync any existing bridge sessions that were created before hooks were registered
        for bridge_session in editor_bridge.get_all_sessions():
            if bridge_session.id not in self._sessions:
                session = EditorSession(id=bridge_session.id)
                self._sessions[bridge_session.id] = session
                print(f"[SessionManager] Synced existing bridge session: {bridge_session.id}")
                # Set up event handler for existing sessions too
                bridge_session.on_event = lambda event, data, sid=bridge_session.id: self._handle_bridge_event(
                    sid, event, data
                )

    def _setup_bridge_events(self, session_id: str) -> None:
        """Set up event handlers for bridge communication.

        Args:
            session_id: The session ID to set up events for.
        """
        bridge_session = editor_bridge.get_session(session_id)
        if bridge_session:
            # Set the event handler to route events to session manager
            bridge_session.on_event = lambda event, data: self._handle_bridge_event(
                session_id, event, data
            )

    def _handle_bridge_event(
        self, session_id: str, event: str, data: dict[str, Any]
    ) -> None:
        """Handle events from the bridge.

        Args:
            session_id: The session ID that sent the event.
            event: The event name.
            data: The event data.
        """
        if event == "state-update":
            self.update_state(session_id, data)

    def unregister(self, session_id: str) -> None:
        """Remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get(self, session_id: str) -> EditorSession | None:
        """Get a session by ID.

        If session doesn't exist locally but exists in the bridge,
        auto-register it (handles reconnection after server restart).
        """
        session = self._sessions.get(session_id)
        if session:
            return session

        # Check if bridge has this session (reconnected after restart)
        bridge_session = editor_bridge.get_session(session_id)
        if bridge_session and bridge_session.is_connected:
            # Auto-register from bridge
            session = EditorSession(id=session_id)
            self._sessions[session_id] = session
            print(f"[SessionManager] Auto-registered session from bridge on get(): {session_id}")
            # Set up event handler
            bridge_session.on_event = lambda event, data: self._handle_bridge_event(
                session_id, event, data
            )
            return session

        return None

    def get_all(self) -> list[EditorSession]:
        """Get all active sessions, sorted by most recent activity first.

        Syncs with bridge to catch any sessions that reconnected after restart.
        """
        # Sync any connected bridge sessions not in our list
        for bridge_session in editor_bridge.get_all_sessions():
            if bridge_session.is_connected and bridge_session.id not in self._sessions:
                session = EditorSession(id=bridge_session.id)
                self._sessions[bridge_session.id] = session
                print(f"[SessionManager] Auto-registered session from bridge on get_all(): {bridge_session.id}")
                # Set up event handler
                bridge_session.on_event = lambda event, data, sid=bridge_session.id: self._handle_bridge_event(
                    sid, event, data
                )

        sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.last_activity, reverse=True)
        return sessions

    def get_most_recent(self) -> EditorSession | None:
        """Get the most recently active session."""
        sessions = self.get_all()
        return sessions[0] if sessions else None

    def get_or_default(self, session_id: str | None) -> EditorSession | None:
        """Get session by ID, or the most recent session if ID is None."""
        if session_id:
            return self.get(session_id)
        return self.get_most_recent()

    def update_state(
        self,
        session_id: str,
        state_update: dict[str, Any],
    ) -> None:
        """Update session state from JavaScript.

        Expected state_update format:
        {
            "active_tool": "brush",
            "tool_properties": {...},
            "foreground_color": "#000000",
            "background_color": "#FFFFFF",
            "zoom": 1.0,
            "recent_colors": [...],
            "active_document_id": "doc-id",
            "documents": [
                {
                    "id": "doc-id",
                    "name": "Document 1",
                    "width": 800,
                    "height": 600,
                    "active_layer_id": "layer-id",
                    "is_modified": false,
                    "created_at": "2024-01-01T00:00:00",
                    "modified_at": "2024-01-01T00:00:00",
                    "layers": [
                        {
                            "id": "layer-id",
                            "name": "Layer 1",
                            "type": "raster",
                            ...
                        }
                    ]
                }
            ]
        }
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        session.update_activity()
        state = session.state

        # Update session-level properties
        if "active_tool" in state_update:
            state.active_tool = state_update["active_tool"]
        if "tool_properties" in state_update:
            state.tool_properties = state_update["tool_properties"]
        if "foreground_color" in state_update:
            state.foreground_color = state_update["foreground_color"]
        if "background_color" in state_update:
            state.background_color = state_update["background_color"]
        if "zoom" in state_update:
            state.zoom = state_update["zoom"]
        if "recent_colors" in state_update:
            state.recent_colors = state_update["recent_colors"]
        if "active_document_id" in state_update:
            state.active_document_id = state_update["active_document_id"]

        # Update documents
        if "documents" in state_update:
            state.documents = []
            for doc_data in state_update["documents"]:
                layers = []
                for layer_data in doc_data.get("layers", []):
                    layers.append(
                        LayerInfo(
                            id=layer_data["id"],
                            name=layer_data["name"],
                            visible=layer_data.get("visible", True),
                            locked=layer_data.get("locked", False),
                            opacity=layer_data.get("opacity", 1.0),
                            blend_mode=layer_data.get(
                                "blendMode", layer_data.get("blend_mode", "normal")
                            ),
                            type=layer_data.get("type", "raster"),
                            width=layer_data.get("width", 0),
                            height=layer_data.get("height", 0),
                            offset_x=layer_data.get("offsetX", layer_data.get("offset_x", 0)),
                            offset_y=layer_data.get("offsetY", layer_data.get("offset_y", 0)),
                            parent_id=layer_data.get("parentId", layer_data.get("parent_id")),
                            # Transform properties
                            rotation=layer_data.get("rotation", 0.0),
                            scale_x=layer_data.get("scaleX", layer_data.get("scale_x", 1.0)),
                            scale_y=layer_data.get("scaleY", layer_data.get("scale_y", 1.0)),
                        )
                    )

                # Parse datetime strings if provided
                created_at = datetime.now()
                modified_at = datetime.now()
                if "created_at" in doc_data:
                    try:
                        created_at = datetime.fromisoformat(doc_data["created_at"].replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass
                if "modified_at" in doc_data:
                    try:
                        modified_at = datetime.fromisoformat(doc_data["modified_at"].replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

                state.documents.append(
                    DocumentInfo(
                        id=doc_data["id"],
                        name=doc_data.get("name", "Untitled"),
                        width=doc_data.get("width", 800),
                        height=doc_data.get("height", 600),
                        layers=layers,
                        active_layer_id=doc_data.get("active_layer_id"),
                        created_at=created_at,
                        modified_at=modified_at,
                        is_modified=doc_data.get("is_modified", False),
                    )
                )

    async def execute_tool(
        self,
        session_id: str,
        tool_id: str,
        action: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool action on a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "executeToolAction",
                {"toolId": tool_id, "action": action, "params": params},
            )
            return {"success": True, "result": result}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_command(
        self,
        session_id: str,
        command: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an editor command on a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "executeCommand",
                {"command": command, "params": params or {}},
            )
            return {"success": True, "result": result}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_data(
        self,
        session_id: str,
        layer_id: str | int | None = None,
        document_id: str | int | None = None,
        format: str = "webp",
        bg: str | None = None,
        timeout: float = 10.0,
    ) -> tuple[bytes | None, dict[str, Any]]:
        """Get data from a session using push-based transfer.

        Uses push-based transfer to avoid WebSocket payload limits:
        1. Generates unique request_id
        2. Tells JS to push data to /api/upload/{request_id}
        3. Waits for data to arrive in cache

        Args:
            session_id: The session ID.
            layer_id: Layer selector - can be UUID, name, or index. None for composite.
            document_id: Document selector - can be UUID, name, or index. None for active.
            format: Output format - 'webp', 'avif', 'png', 'svg', 'json'.
                    For raster layers/composite: webp, avif, png
                    For vector layers: svg, json, or raster formats
            bg: Background color (e.g., '#FFFFFF') or None for transparent.
            timeout: Maximum time to wait for data (seconds). Default 10s.

        Returns (data_bytes, metadata) or (None, error_dict).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, {"error": "Session not found"}

        session.update_activity()

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        try:
            # Create pending request in cache
            data_cache.create_request(request_id)

            # Tell JS to push data to upload endpoint via WebSocket bridge
            editor_bridge.fire(
                session_id,
                "pushData",
                {
                    "requestId": request_id,
                    "layerId": layer_id,
                    "documentId": document_id,
                    "format": format,
                    "bg": bg,
                },
            )

            # Brief yield to let the event loop process the WebSocket send
            await asyncio.sleep(0.005)

            # Wait for data to arrive
            entry, error = await data_cache.wait_for_data(request_id, timeout=timeout)

            if error:
                return None, {"error": error}

            if entry:
                return entry.data, {
                    "content_type": entry.content_type,
                    **entry.metadata,
                }

            return None, {"error": "No data received"}

        except BridgeSessionError as e:
            data_cache.remove_entry(request_id)
            return None, {"error": str(e)}
        except Exception as e:
            # Clean up pending request on error
            data_cache.remove_entry(request_id)
            print(f"[get_data] ERROR: {e}")
            return None, {"error": str(e)}

    # Legacy method for backwards compatibility
    async def get_image(
        self,
        session_id: str,
        layer_id: str | int | None = None,
        document_id: str | int | None = None,
        format: str = "webp",
        bg: str | None = None,
    ) -> tuple[bytes | None, dict[str, Any]]:
        """Get image data from a session.

        This is a convenience wrapper around get_data() for image formats.

        Args:
            session_id: The session ID.
            layer_id: Layer selector - can be UUID, name, or index. None for composite.
            document_id: Document selector - can be UUID, name, or index. None for active.
            format: Image format - 'webp', 'avif', 'png'. Default: 'webp'.
            bg: Background color (e.g., '#FFFFFF') or None for transparent.

        Returns (image_bytes, metadata) or (None, error_dict).
        """
        return await self.get_data(
            session_id=session_id,
            layer_id=layer_id,
            document_id=document_id,
            format=format,
            bg=bg,
        )

    async def export_document(
        self,
        session_id: str,
        document_id: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Export a document as JSON.

        Args:
            session_id: The session ID
            document_id: Optional document ID. If None, exports active document.

        Returns (document_data, metadata) or (None, error_dict).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, {"error": "Session not found"}

        session.update_activity()

        try:
            # Request serialized document from JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "exportDocument",
                {"documentId": document_id},
                timeout=30.0,  # Longer timeout for complex documents
            )
            if result and "document" in result:
                return result["document"], {"success": True}
            return None, {"error": "No document data returned"}
        except BridgeSessionError as e:
            return None, {"error": str(e)}
        except BridgeTimeoutError as e:
            return None, {"error": f"Timeout: {e}"}
        except Exception as e:
            return None, {"error": str(e)}

    async def import_document(
        self,
        session_id: str,
        document_data: dict[str, Any],
        document_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Import a full document from JSON.

        Args:
            session_id: The session ID
            document_data: The document data to import
            document_id: Optional document selector to replace. If None, creates new.

        Returns success/error dict.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Send document to JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "importDocument",
                {"documentData": document_data, "documentId": document_id},
                timeout=30.0,  # Longer timeout for complex documents
            )
            return {"success": True, "result": result}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_config(
        self,
        session_id: str,
        path: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Get UIConfig settings from a session.

        Args:
            session_id: The session ID
            path: Optional dot-separated path (e.g., 'rendering.vectorSVGRendering')
                  If None, returns full config.

        Returns (config_data, metadata) or (None, error_dict).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, {"error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "getConfig",
                {"path": path},
            )
            return result, {"success": True}
        except BridgeSessionError as e:
            return None, {"error": str(e)}
        except BridgeTimeoutError as e:
            return None, {"error": f"Timeout: {e}"}
        except Exception as e:
            return None, {"error": str(e)}

    async def set_config(
        self,
        session_id: str,
        path: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set a UIConfig setting on a session.

        Args:
            session_id: The session ID
            path: Dot-separated path (e.g., 'rendering.vectorSupersampleLevel')
            value: The value to set

        Returns success/error dict.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "setConfig",
                {"path": path, "value": value},
            )
            return {"success": True, "result": result}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            # Register bridge hooks when starting
            self._register_bridge_hooks()

    def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Background loop that periodically cleans up dead sessions."""
        while self._running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                self.cleanup_inactive()
            except asyncio.CancelledError:
                break
            except Exception:
                # Don't let cleanup errors crash the loop
                pass

    def heartbeat(self, session_id: str) -> bool:
        """Update session heartbeat timestamp.

        Args:
            session_id: The session ID

        Returns:
            True if session exists, False otherwise
        """
        # Ensure cleanup task is running
        if not self._running:
            try:
                self.start_cleanup_task()
            except RuntimeError:
                pass

        # Run cleanup synchronously on each heartbeat to remove stale sessions
        self.cleanup_inactive()

        session = self._sessions.get(session_id)
        if session:
            session.update_activity()
            return True
        return False

    def cleanup_inactive(self) -> int:
        """Remove sessions that have been inactive too long.

        Sessions are considered dead if:
        - Their last_activity is older than SESSION_TIMEOUT_SECONDS AND
          no active bridge connection with recent heartbeats

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        inactive = []

        for sid, session in self._sessions.items():
            time_since_activity = now - session.last_activity

            # Check if bridge session has recent activity
            bridge_session = editor_bridge.get_session(sid)
            bridge_active = False
            if bridge_session:
                # Consider bridge active if connected OR if session is new (grace period)
                if bridge_session.is_connected:
                    time_since_bridge = now - bridge_session.last_heartbeat
                    if time_since_bridge < self._session_timeout:
                        bridge_active = True
                        # Sync bridge heartbeat to session activity
                        session.update_activity()

            # Only remove if timed out AND no active bridge
            # This gives new sessions a grace period before removal
            if time_since_activity > self._session_timeout and not bridge_active:
                inactive.append(sid)

        for sid in inactive:
            print(f"[SessionManager] Removing inactive session: {sid}")
            del self._sessions[sid]

        if inactive:
            print(f"[SessionManager] Removed {len(inactive)} sessions, remaining: {len(self._sessions)}")

        return len(inactive)

    # Layer Effects Methods

    async def get_layer_effects(
        self,
        session_id: str,
        layer_id: str | int,
        document_id: str | int | None = None,
    ) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
        """Get all effects for a layer.

        Args:
            session_id: The session ID
            layer_id: Layer selector (ID, name, or index)
            document_id: Optional document selector. If None, uses active document.

        Returns (effects_list, metadata) or (None, error_dict).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, {"error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "getLayerEffects",
                {"layerId": layer_id, "documentId": document_id},
            )
            if result is not None:
                return result, {"success": True}
            return None, {"error": "No effects data returned"}
        except BridgeSessionError as e:
            return None, {"error": str(e)}
        except BridgeTimeoutError as e:
            return None, {"error": f"Timeout: {e}"}
        except Exception as e:
            return None, {"error": str(e)}

    async def add_layer_effect(
        self,
        session_id: str,
        layer_id: str | int,
        effect_type: str,
        params: dict[str, Any],
        document_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Add an effect to a layer.

        Args:
            session_id: The session ID
            layer_id: Layer selector (ID, name, or index)
            effect_type: Type of effect to add
            params: Effect parameters
            document_id: Optional document selector. If None, uses active document.

        Returns success/error dict with effect_id if successful.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "addLayerEffect",
                {
                    "layerId": layer_id,
                    "effectType": effect_type,
                    "params": params,
                    "documentId": document_id,
                },
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to add effect")}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_layer_effect(
        self,
        session_id: str,
        layer_id: str | int,
        effect_id: str,
        params: dict[str, Any],
        document_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Update an effect's parameters.

        Args:
            session_id: The session ID
            layer_id: Layer selector (ID, name, or index)
            effect_id: The effect ID to update
            params: New effect parameters
            document_id: Optional document selector. If None, uses active document.

        Returns success/error dict.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "updateLayerEffect",
                {
                    "layerId": layer_id,
                    "effectId": effect_id,
                    "params": params,
                    "documentId": document_id,
                },
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to update effect")}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def remove_layer_effect(
        self,
        session_id: str,
        layer_id: str | int,
        effect_id: str,
        document_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Remove an effect from a layer.

        Args:
            session_id: The session ID
            layer_id: Layer selector (ID, name, or index)
            effect_id: The effect ID to remove
            document_id: Optional document selector. If None, uses active document.

        Returns success/error dict.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.update_activity()

        try:
            # Call JavaScript via WebSocket bridge (async version)
            result = await editor_bridge.call_async(
                session_id,
                "removeLayerEffect",
                {
                    "layerId": layer_id,
                    "effectId": effect_id,
                    "documentId": document_id,
                },
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to remove effect")}
        except BridgeSessionError as e:
            return {"success": False, "error": str(e)}
        except BridgeTimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global singleton instance
session_manager = SessionManager()
