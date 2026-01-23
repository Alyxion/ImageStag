"""Stagforge Canvas Editor - NiceGUI Custom Component."""

from nicegui import context
from nicegui.element import Element

from .sessions import session_manager


class CanvasEditor(Element, component='canvas_editor.js'):
    """Full-featured image editor component.

    This is a NiceGUI custom component that wraps the JavaScript-based
    canvas editor. The editor works completely autonomously in the browser.

    All communication happens via the WebSocket bridge and REST API.
    This Python class only provides the session ID for API calls.
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

        # Clean up references on disconnect (session stays for reconnect)
        context.client.on_disconnect(self._on_disconnect)

    def _on_disconnect(self) -> None:
        """Handle client disconnect."""
        session = session_manager.get(self._session_id)
        if session:
            session.client = None
            session.editor = None

    @property
    def session_id(self) -> str:
        """Get the session ID for API calls."""
        return self._session_id
