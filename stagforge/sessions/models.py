"""Session data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LayerInfo:
    """Information about a layer."""

    id: str
    name: str
    visible: bool = True
    locked: bool = False
    opacity: float = 1.0
    blend_mode: str = "normal"
    type: str = "raster"  # 'raster', 'vector', 'text'
    width: int = 0
    height: int = 0
    offset_x: int = 0
    offset_y: int = 0


@dataclass
class SessionState:
    """Current state of an editor session."""

    document_width: int = 800
    document_height: int = 600
    layers: list[LayerInfo] = field(default_factory=list)
    active_layer_id: str | None = None
    active_tool: str = "brush"
    tool_properties: dict[str, Any] = field(default_factory=dict)
    foreground_color: str = "#000000"
    background_color: str = "#FFFFFF"
    zoom: float = 1.0
    recent_colors: list[str] = field(default_factory=list)


@dataclass
class EditorSession:
    """Represents an active editor session."""

    id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    state: SessionState = field(default_factory=SessionState)
    # Reference to NiceGUI client for communication
    client: Any = None
    # Reference to the CanvasEditor component
    editor: Any = None

    def to_summary(self) -> dict:
        """Get summary dict for API response."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "document_width": self.state.document_width,
            "document_height": self.state.document_height,
            "layer_count": len(self.state.layers),
            "active_tool": self.state.active_tool,
            "foreground_color": self.state.foreground_color,
            "background_color": self.state.background_color,
        }

    def to_detail(self) -> dict:
        """Get detailed dict for API response."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "document": {
                "width": self.state.document_width,
                "height": self.state.document_height,
            },
            "layers": [
                {
                    "id": layer.id,
                    "name": layer.name,
                    "visible": layer.visible,
                    "locked": layer.locked,
                    "opacity": layer.opacity,
                    "blend_mode": layer.blend_mode,
                    "type": layer.type,
                    "width": layer.width,
                    "height": layer.height,
                    "offset_x": layer.offset_x,
                    "offset_y": layer.offset_y,
                }
                for layer in self.state.layers
            ],
            "active_layer_id": self.state.active_layer_id,
            "active_tool": self.state.active_tool,
            "tool_properties": self.state.tool_properties,
            "colors": {
                "foreground": self.state.foreground_color,
                "background": self.state.background_color,
            },
            "zoom": self.state.zoom,
            "recent_colors": self.state.recent_colors,
        }

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
