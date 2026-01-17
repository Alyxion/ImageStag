"""Stroke effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class StrokeEffect(LayerEffect):
    """Adds an outline stroke around the layer content."""

    type: str = field(init=False, default='stroke')
    display_name: str = field(init=False, default='Stroke')

    size: int = 3
    position: str = 'outside'  # inside, outside, center
    color: str = '#000000'
    color_opacity: float = 1.0

    def get_expansion(self) -> dict[str, int]:
        if self.position == 'outside':
            return {'left': self.size, 'top': self.size, 'right': self.size, 'bottom': self.size}
        elif self.position == 'center':
            half = int(self.size / 2) + 1
            return {'left': half, 'top': half, 'right': half, 'bottom': half}
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def get_params(self) -> dict[str, Any]:
        return {
            'size': self.size,
            'position': self.position,
            'color': self.color,
            'colorOpacity': self.color_opacity
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'StrokeEffect':
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
            size=data.get('size', 3),
            position=data.get('position', 'outside'),
            color=data.get('color', '#000000'),
            color_opacity=data.get('colorOpacity', 1.0),
        )
