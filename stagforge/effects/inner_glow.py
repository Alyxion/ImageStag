"""Inner Glow effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class InnerGlowEffect(LayerEffect):
    """Creates a colored glow inside the layer content edges."""

    type: str = field(init=False, default='innerGlow')
    display_name: str = field(init=False, default='Inner Glow')

    blur: int = 10
    choke: int = 0
    color: str = '#FFFF00'
    color_opacity: float = 0.75
    source: str = 'edge'  # 'edge' or 'center'

    def get_expansion(self) -> dict[str, int]:
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def get_params(self) -> dict[str, Any]:
        return {
            'blur': self.blur,
            'choke': self.choke,
            'color': self.color,
            'colorOpacity': self.color_opacity,
            'source': self.source
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'InnerGlowEffect':
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
            blur=data.get('blur', 10),
            choke=data.get('choke', 0),
            color=data.get('color', '#FFFF00'),
            color_opacity=data.get('colorOpacity', 0.75),
            source=data.get('source', 'edge'),
        )
