"""Session manager for tracking active editor sessions."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from .models import EditorSession, LayerInfo, SessionState


class SessionManager:
    """Manages all active editor sessions."""

    def __init__(self):
        self._sessions: dict[str, EditorSession] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._session_timeout = timedelta(minutes=5)

    def register(
        self,
        session_id: str,
        client: Any = None,
        editor: Any = None,
    ) -> EditorSession:
        """Register a new session or return existing one."""
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
        """Get all active sessions."""
        return list(self._sessions.values())

    def update_state(
        self,
        session_id: str,
        state_update: dict[str, Any],
    ) -> None:
        """Update session state from JavaScript."""
        session = self._sessions.get(session_id)
        if not session:
            return

        session.update_activity()
        state = session.state

        # Update basic properties
        if "document_width" in state_update:
            state.document_width = state_update["document_width"]
        if "document_height" in state_update:
            state.document_height = state_update["document_height"]
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
        if "active_layer_id" in state_update:
            state.active_layer_id = state_update["active_layer_id"]

        # Update layers
        if "layers" in state_update:
            state.layers = [
                LayerInfo(
                    id=layer["id"],
                    name=layer["name"],
                    visible=layer.get("visible", True),
                    locked=layer.get("locked", False),
                    opacity=layer.get("opacity", 1.0),
                    blend_mode=layer.get("blendMode", layer.get("blend_mode", "normal")),
                    type=layer.get("type", "raster"),
                    width=layer.get("width", 0),
                    height=layer.get("height", 0),
                    offset_x=layer.get("offsetX", 0),
                    offset_y=layer.get("offsetY", 0),
                )
                for layer in state_update["layers"]
            ]

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

    async def get_image(
        self,
        session_id: str,
        layer_id: str | None = None,
    ) -> tuple[bytes | None, dict[str, Any]]:
        """Get image data from a session.

        Returns (rgba_bytes, metadata) or (None, error_dict).
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, {"error": "Session not found"}

        if not session.editor:
            return None, {"error": "Editor not connected"}

        session.update_activity()

        try:
            # Request image data from JavaScript
            result = await session.editor.run_method(
                "getImageData",
                layer_id,
            )
            if result and "data" in result:
                # Data comes as base64, decode it
                import base64
                rgba_bytes = base64.b64decode(result["data"])
                metadata = {
                    "width": result.get("width", session.state.document_width),
                    "height": result.get("height", session.state.document_height),
                }
                if layer_id:
                    metadata["layer_id"] = layer_id
                    metadata["layer_name"] = result.get("name", "")
                    metadata["layer_opacity"] = result.get("opacity", 1.0)
                    metadata["layer_blend_mode"] = result.get("blend_mode", "normal")
                return rgba_bytes, metadata
            return None, {"error": "No image data returned"}
        except Exception as e:
            return None, {"error": str(e)}

    async def export_document(
        self,
        session_id: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Export the full document as JSON.

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
            result = await session.editor.run_method("exportDocument")
            if result and "document" in result:
                return result["document"], {"success": True}
            return None, {"error": "No document data returned"}
        except Exception as e:
            return None, {"error": str(e)}

    async def import_document(
        self,
        session_id: str,
        document_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Import a full document from JSON.

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
            result = await session.editor.run_method(
                "importDocument",
                document_data,
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

    def cleanup_inactive(self) -> None:
        """Remove sessions that have been inactive too long."""
        now = datetime.now()
        inactive = [
            sid
            for sid, session in self._sessions.items()
            if now - session.last_activity > self._session_timeout
            and session.client is None
        ]
        for sid in inactive:
            del self._sessions[sid]

    # Layer Effects Methods

    async def get_layer_effects(
        self,
        session_id: str,
        layer_id: str,
    ) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
        """Get all effects for a layer.

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
            )
            if result is not None:
                return result, {"success": True}
            return None, {"error": "No effects data returned"}
        except Exception as e:
            return None, {"error": str(e)}

    async def add_layer_effect(
        self,
        session_id: str,
        layer_id: str,
        effect_type: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Add an effect to a layer.

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
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to add effect")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_layer_effect(
        self,
        session_id: str,
        layer_id: str,
        effect_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an effect's parameters.

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
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to update effect")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def remove_layer_effect(
        self,
        session_id: str,
        layer_id: str,
        effect_id: str,
    ) -> dict[str, Any]:
        """Remove an effect from a layer.

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
            )
            if result and result.get("success"):
                return result
            return {"success": False, "error": result.get("error", "Failed to remove effect")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global singleton instance
session_manager = SessionManager()
