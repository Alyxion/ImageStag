"""Session manager for tracking active editor sessions."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

from stagforge.api.data_cache import data_cache

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

        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.client = client
            session.editor = editor
            session.update_activity()
            return session

        session = EditorSession(
            id=session_id,
            client=client,
            editor=editor,
        )
        self._sessions[session_id] = session
        return session

    def unregister(self, session_id: str) -> None:
        """Remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get(self, session_id: str) -> EditorSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_all(self) -> list[EditorSession]:
        """Get all active sessions, sorted by most recent activity first."""
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            # Call JavaScript via NiceGUI
            result = await session.editor.run_method(
                "executeToolAction",
                tool_id,
                action,
                params,
            )
            return {"success": True, "result": result}
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method(
                "executeCommand",
                command,
                params or {},
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_data(
        self,
        session_id: str,
        layer_id: str | int | None = None,
        document_id: str | int | None = None,
        format: str = "webp",
        bg: str | None = None,
        timeout: float = 30.0,
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
            timeout: Maximum time to wait for data (seconds).

        Returns (data_bytes, metadata) or (None, error_dict).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, {"error": "Session not found"}

        if not session.editor:
            return None, {"error": "Editor not connected"}

        session.update_activity()

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        try:
            # Create pending request in cache
            data_cache.create_request(request_id)

            # Tell JS to push data to upload endpoint
            # This call returns immediately (fire-and-forget)
            session.editor.run_method(
                "pushData",
                request_id,
                layer_id,
                document_id,
                format,
                bg,
            )

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

        except Exception as e:
            # Clean up pending request on error
            data_cache.remove_entry(request_id)
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

        if not session.editor:
            return None, {"error": "Editor not connected"}

        session.update_activity()

        try:
            # Request serialized document from JavaScript
            # Use longer timeout (30s) for complex documents
            result = await session.editor.run_method(
                "exportDocument", document_id, timeout=30.0
            )
            if result and "document" in result:
                return result["document"], {"success": True}
            return None, {"error": "No document data returned"}
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            # Send document to JavaScript for import
            # Use longer timeout (30s) for complex documents
            result = await session.editor.run_method(
                "importDocument",
                document_data,
                document_id,
                timeout=30.0,
            )
            return {"success": True, "result": result}
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

        if not session.editor:
            return None, {"error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method("getConfig", path)
            return result, {"success": True}
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method("setConfig", path, value)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

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
        - Their last_activity is older than SESSION_TIMEOUT_SECONDS, OR
        - They have no client AND no editor (disconnected)

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        inactive = []

        for sid, session in self._sessions.items():
            time_since_activity = now - session.last_activity

            # Remove if timed out (no heartbeat for too long)
            if time_since_activity > self._session_timeout:
                inactive.append(sid)
            # Also remove if both client and editor are gone (immediate cleanup)
            elif session.client is None and session.editor is None:
                inactive.append(sid)

        for sid in inactive:
            del self._sessions[sid]

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

        if not session.editor:
            return None, {"error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method(
                "getLayerEffects",
                layer_id,
                document_id,
            )
            if result is not None:
                return result, {"success": True}
            return None, {"error": "No effects data returned"}
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method(
                "addLayerEffect",
                layer_id,
                effect_type,
                params,
                document_id,
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to add effect")}
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method(
                "updateLayerEffect",
                layer_id,
                effect_id,
                params,
                document_id,
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to update effect")}
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

        if not session.editor:
            return {"success": False, "error": "Editor not connected"}

        session.update_activity()

        try:
            result = await session.editor.run_method(
                "removeLayerEffect",
                layer_id,
                effect_id,
                document_id,
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to remove effect")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global singleton instance
session_manager = SessionManager()
