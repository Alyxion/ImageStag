"""Slopstag Canvas Editor - NiceGUI Custom Component."""

from typing import Any

from nicegui import context
from nicegui.element import Element

from .sessions import session_manager


class CanvasEditor(Element, component='canvas_editor.js'):
    """Full-featured image editor component.

    This is a NiceGUI custom component that wraps the JavaScript-based
    canvas editor. The editor works completely autonomously in the browser;
    Python just provides the envelope and optional backend filters.
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        api_base: str = '/api',
    ) -> None:
        """Initialize the canvas editor.

        Args:
            width: Default canvas width in pixels.
            height: Default canvas height in pixels.
            api_base: Base URL for the backend API.
        """
        super().__init__()
        self._props['canvasWidth'] = width
        self._props['canvasHeight'] = height
        self._props['apiBase'] = api_base

        # Get session ID from NiceGUI client
        self._session_id = context.client.id
        self._props['sessionId'] = self._session_id

        # Register with session manager
        session_manager.register(
            self._session_id,
            client=context.client,
            editor=self,
        )

        # Register event handler for state updates from JS
        self.on('state-update', self._handle_state_update)

        # Unregister on disconnect
        context.client.on_disconnect(self._on_disconnect)

    def _on_disconnect(self) -> None:
        """Handle client disconnect."""
        # Keep session for a while (cleanup will remove it later)
        session = session_manager.get(self._session_id)
        if session:
            session.client = None
            session.editor = None

    def _handle_state_update(self, e: Any) -> None:
        """Handle state updates from JavaScript."""
        if hasattr(e, 'args') and e.args:
            session_manager.update_state(self._session_id, e.args)

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    def new_document(self, width: int, height: int) -> None:
        """Create a new document with the specified dimensions."""
        self.run_method('newDocument', width, height)

    def undo(self) -> None:
        """Undo the last action."""
        self.run_method('undo')

    def redo(self) -> None:
        """Redo the last undone action."""
        self.run_method('redo')

    def select_tool(self, tool_id: str) -> None:
        """Select a tool by its ID."""
        self.run_method('selectTool', tool_id)

    def set_foreground_color(self, color: str) -> None:
        """Set the foreground color."""
        self._props['foregroundColor'] = color
        self.update()

    def set_background_color(self, color: str) -> None:
        """Set the background color."""
        self._props['backgroundColor'] = color
        self.update()

    async def apply_filter(self, filter_id: str, params: dict | None = None) -> None:
        """Apply a backend filter to the current layer."""
        self.run_method('applyFilter', filter_id, params or {})
