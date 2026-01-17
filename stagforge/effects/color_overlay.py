"""Color Overlay effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class ColorOverlayEffect(LayerEffect):
    """Overlays a solid color on the layer content."""

    type: str = field(init=False, default='colorOverlay')
    display_name: str = field(init=False, default='Color Overlay')

    color: str = '#FF0000'

    def get_expansion(self) -> dict[str, int]:
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def get_params(self) -> dict[str, Any]:
        return {'color': self.color}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ColorOverlayEffect':
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
            color=data.get('color', '#FF0000'),
        )
