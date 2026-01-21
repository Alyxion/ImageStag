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
    type: str = "raster"  # 'raster', 'vector', 'text', 'group'
    width: int = 0
    height: int = 0
    offset_x: int = 0
    offset_y: int = 0
    parent_id: str | None = None  # For layer groups

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "opacity": self.opacity,
            "blend_mode": self.blend_mode,
            "type": self.type,
            "width": self.width,
            "height": self.height,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "parent_id": self.parent_id,
        }


@dataclass
class DocumentInfo:
    """Information about an open document."""

    id: str
    name: str
    width: int = 800
    height: int = 600
    layers: list[LayerInfo] = field(default_factory=list)
    active_layer_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    is_modified: bool = False

    def to_summary(self) -> dict:
        """Get summary dict for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "layer_count": len(self.layers),
            "active_layer_id": self.active_layer_id,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "is_modified": self.is_modified,
        }

    def to_detail(self) -> dict:
        """Get detailed dict for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "layers": [layer.to_dict() for layer in self.layers],
            "active_layer_id": self.active_layer_id,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "is_modified": self.is_modified,
        }


@dataclass
class SessionState:
    """Current state of an editor session."""

    # Multi-document support
    documents: list[DocumentInfo] = field(default_factory=list)
    active_document_id: str | None = None

    # Tools and colors (session-wide)
    active_tool: str = "brush"
    tool_properties: dict[str, Any] = field(default_factory=dict)
    foreground_color: str = "#000000"
    background_color: str = "#FFFFFF"
    zoom: float = 1.0
    recent_colors: list[str] = field(default_factory=list)

    def get_active_document(self) -> DocumentInfo | None:
        """Get the currently active document."""
        if not self.active_document_id:
            return None
        for doc in self.documents:
            if doc.id == self.active_document_id:
                return doc
        return None


@dataclass
class EditorSession:
    """Represents an active editor session (browser tab)."""

    id: str  # Tab/session ID
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    state: SessionState = field(default_factory=SessionState)
    # Reference to NiceGUI client for communication
    client: Any = None
    # Reference to the CanvasEditor component
    editor: Any = None

    def to_summary(self) -> dict:
        """Get summary dict for API response."""
        active_doc = self.state.get_active_document()
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "document_count": len(self.state.documents),
            "active_document_id": self.state.active_document_id,
            "active_document_name": active_doc.name if active_doc else None,
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
            "documents": [doc.to_detail() for doc in self.state.documents],
            "active_document_id": self.state.active_document_id,
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
