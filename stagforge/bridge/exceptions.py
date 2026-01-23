"""Exception classes for the WebSocket bridge."""


class BridgeError(Exception):
    """Base exception for bridge errors."""

    pass


class BridgeTimeoutError(BridgeError):
    """Raised when a command times out waiting for response."""

    pass


class BridgeSessionError(BridgeError):
    """Raised for session-related errors (not found, disconnected)."""

    pass


class BridgeProtocolError(BridgeError):
    """Raised for protocol/message format errors."""

    pass
