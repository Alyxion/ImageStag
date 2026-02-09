"""Inner Shadow effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class InnerShadowEffect(LayerEffect):
    """Creates a shadow inside the layer content edges."""

    type: str = field(init=False, default='innerShadow')
    display_name: str = field(init=False, default='Inner Shadow')

    offset_x: int = 2
    offset_y: int = 2
    blur: int = 5
    choke: int = 0
    color: str = '#000000'

    def get_expansion(self) -> dict[str, int]:
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def get_params(self) -> dict[str, Any]:
        return {
            'offsetX': self.offset_x,
            'offsetY': self.offset_y,
            'blur': self.blur,
            'choke': self.choke,
            'color': self.color,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'InnerShadowEffect':
        # Migrate legacy colorOpacity → base opacity
        opacity = data.get('colorOpacity', data.get('opacity', 0.75))
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=opacity,
            offset_x=data.get('offsetX', 2),
            offset_y=data.get('offsetY', 2),
            blur=data.get('blur', 5),
            choke=data.get('choke', 0),
            color=data.get('color', '#000000'),
        )
