"""Drop Shadow effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class DropShadowEffect(LayerEffect):
    """Creates a shadow behind the layer content."""

    type: str = field(init=False, default='dropShadow')
    display_name: str = field(init=False, default='Drop Shadow')

    offset_x: int = 4
    offset_y: int = 4
    blur: int = 5
    spread: int = 0
    color: str = '#000000'
    color_opacity: float = 0.75

    def get_expansion(self) -> dict[str, int]:
        expand = int(self.blur * 3) + abs(self.spread)
        return {
            'left': max(0, expand - self.offset_x),
            'top': max(0, expand - self.offset_y),
            'right': max(0, expand + self.offset_x),
            'bottom': max(0, expand + self.offset_y)
        }

    def get_params(self) -> dict[str, Any]:
        return {
            'offsetX': self.offset_x,
            'offsetY': self.offset_y,
            'blur': self.blur,
            'spread': self.spread,
            'color': self.color,
            'colorOpacity': self.color_opacity
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'DropShadowEffect':
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
            offset_x=data.get('offsetX', 4),
            offset_y=data.get('offsetY', 4),
            blur=data.get('blur', 5),
            spread=data.get('spread', 0),
            color=data.get('color', '#000000'),
            color_opacity=data.get('colorOpacity', 0.75),
        )
