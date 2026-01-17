"""Outer Glow effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class OuterGlowEffect(LayerEffect):
    """Creates a colored glow around the layer content."""

    type: str = field(init=False, default='outerGlow')
    display_name: str = field(init=False, default='Outer Glow')

    blur: int = 10
    spread: int = 0
    color: str = '#FFFF00'
    color_opacity: float = 0.75

    def get_expansion(self) -> dict[str, int]:
        expand = int(self.blur * 3) + self.spread
        return {'left': expand, 'top': expand, 'right': expand, 'bottom': expand}

    def get_params(self) -> dict[str, Any]:
        return {
            'blur': self.blur,
            'spread': self.spread,
            'color': self.color,
            'colorOpacity': self.color_opacity
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'OuterGlowEffect':
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
            blur=data.get('blur', 10),
            spread=data.get('spread', 0),
            color=data.get('color', '#FFFF00'),
            color_opacity=data.get('colorOpacity', 0.75),
        )
