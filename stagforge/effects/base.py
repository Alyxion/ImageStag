"""
Base class for layer effects.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayerEffect:
    """Base class for all layer effects."""

    type: str = field(init=False)
    display_name: str = field(init=False, default='Effect')
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    enabled: bool = True
    blend_mode: str = 'normal'
    opacity: float = 1.0

    def get_expansion(self) -> dict[str, int]:
        """Get expansion needed beyond layer bounds."""
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def to_dict(self) -> dict[str, Any]:
        """Serialize effect to dictionary."""
        return {
            'id': self.id,
            'type': self.type,
            'enabled': self.enabled,
            'blendMode': self.blend_mode,
            'opacity': self.opacity,
            **self.get_params()
        }

    def get_params(self) -> dict[str, Any]:
        """Get effect-specific parameters."""
        return {}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'LayerEffect':
        """Create effect from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
        )
