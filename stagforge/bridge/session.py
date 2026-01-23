"""Bridge session management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from fastapi import WebSocket


@dataclass
class BridgeSession:
    """Represents a connected client session."""

    id: str
    websocket: WebSocket | None = None
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    on_event: Callable[[str, dict], None] | None = None
    on_disconnect: Callable[[], None] | None = None

    # Internal state
    _metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_connected(self) -> bool:
        """Check if session has an active WebSocket connection."""
        return self.websocket is not None

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.now()

    def set_metadata(self, key: str, value: Any) -> None:
        """Set session metadata."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get session metadata."""
        return self._metadata.get(key, default)
