"""WebSocket bridge for Python-JavaScript communication.

This module provides a reusable WebSocket-based communication system
for bidirectional Python-JavaScript messaging.

Classes:
    EditorBridge: Main bridge class with thread-safe synchronous API.
    BridgeSession: Represents a connected client session.

Exceptions:
    BridgeError: Base exception for bridge errors.
    BridgeTimeoutError: Command timed out waiting for response.
    BridgeSessionError: Session-related errors.
    BridgeProtocolError: Protocol/message format errors.

Example:
    from stagforge.bridge import editor_bridge

    # Start the bridge
    editor_bridge.start()

    # In FastAPI route:
    @app.websocket("/ws/editor/{session_id}")
    async def ws_endpoint(websocket: WebSocket, session_id: str):
        await editor_bridge.websocket_endpoint(websocket, session_id)

    # From any Python code (thread-safe):
    result = editor_bridge.call(session_id, "executeCommand", {"command": "undo"})
"""

from .editor_bridge import EditorBridge, editor_bridge
from .exceptions import (
    BridgeError,
    BridgeProtocolError,
    BridgeSessionError,
    BridgeTimeoutError,
)
from .session import BridgeSession

__all__ = [
    "EditorBridge",
    "editor_bridge",
    "BridgeSession",
    "BridgeError",
    "BridgeTimeoutError",
    "BridgeSessionError",
    "BridgeProtocolError",
]
