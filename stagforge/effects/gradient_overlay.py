"""Gradient Overlay effect."""
from dataclasses import dataclass, field
from typing import Any
from .base import LayerEffect


@dataclass
class GradientOverlayEffect(LayerEffect):
    """Overlays a gradient on the layer content."""

    type: str = field(init=False, default='gradientOverlay')
    display_name: str = field(init=False, default='Gradient Overlay')

    gradient: list = field(default_factory=lambda: [
        {'position': 0.0, 'color': '#000000'},
        {'position': 1.0, 'color': '#FFFFFF'},
    ])
    style: str = 'linear'
    angle: float = 90.0
    scale_x: float = 100.0
    scale_y: float = 100.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    reverse: bool = False

    def get_expansion(self) -> dict[str, int]:
        return {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}

    def get_params(self) -> dict[str, Any]:
        return {
            'gradient': self.gradient,
            'style': self.style,
            'angle': self.angle,
            'scaleX': self.scale_x,
            'scaleY': self.scale_y,
            'offsetX': self.offset_x,
            'offsetY': self.offset_y,
            'reverse': self.reverse,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'GradientOverlayEffect':
        # Migrate legacy fillOpacity → base opacity
        opacity = data.get('fillOpacity', data.get('opacity', 1.0))
        return cls(
            id=data.get('id'),
            enabled=data.get('enabled', True),
            blend_mode=data.get('blendMode', 'normal'),
            opacity=opacity,
            gradient=data.get('gradient', [
                {'position': 0.0, 'color': '#000000'},
                {'position': 1.0, 'color': '#FFFFFF'},
            ]),
            style=data.get('style', 'linear'),
            angle=data.get('angle', 90.0),
            scale_x=data.get('scaleX', 100.0),
            scale_y=data.get('scaleY', 100.0),
            offset_x=data.get('offsetX', 0.0),
            offset_y=data.get('offsetY', 0.0),
            reverse=data.get('reverse', False),
        )
