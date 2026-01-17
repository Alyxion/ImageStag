"""Bevel & Emboss effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class BevelEmbossEffect(LayerEffect):
    """Creates beveled/embossed 3D-like edges on the layer."""

    type: str = field(init=False, default='bevelEmboss')
    display_name: str = field(init=False, default='Bevel & Emboss')

    style: str = 'innerBevel'  # innerBevel, outerBevel, emboss, pillowEmboss
    depth: int = 3
    direction: str = 'up'  # up, down
    size: int = 5
    soften: int = 0
    angle: int = 120
    altitude: int = 30
    highlight_color: str = '#FFFFFF'
    highlight_opacity: float = 0.75
    shadow_color: str = '#000000'
    shadow_opacity: float = 0.75

    def get_expansion(self) -> dict[str, int]:
        if self.style == 'outerBevel':
            expand = int(self.size)
            return {'left': expand, 'top': expand, 'right': expand, 'bottom': expand}
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def get_params(self) -> dict[str, Any]:
        return {
            'style': self.style,
            'depth': self.depth,
            'direction': self.direction,
            'size': self.size,
            'soften': self.soften,
            'angle': self.angle,
            'altitude': self.altitude,
            'highlightColor': self.highlight_color,
            'highlightOpacity': self.highlight_opacity,
            'shadowColor': self.shadow_color,
            'shadowOpacity': self.shadow_opacity
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BevelEmbossEffect':
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=data.get('opacity', 1.0),
            style=data.get('style', 'innerBevel'),
            depth=data.get('depth', 3),
            direction=data.get('direction', 'up'),
            size=data.get('size', 5),
            soften=data.get('soften', 0),
            angle=data.get('angle', 120),
            altitude=data.get('altitude', 30),
            highlight_color=data.get('highlightColor', '#FFFFFF'),
            highlight_opacity=data.get('highlightOpacity', 0.75),
            shadow_color=data.get('shadowColor', '#000000'),
            shadow_opacity=data.get('shadowOpacity', 0.75),
        )
