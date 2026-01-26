"""
ImageStag Layer Effects

Non-destructive visual effects for image layers.

Example:
    >>> from imagestag.layer_effects import DropShadow, Stroke
    >>> shadow = DropShadow(blur=5, offset_x=10, offset_y=10, color=(0, 0, 0))
    >>> result = shadow.apply(image)
    >>> # result.image contains the output, result.offset_x/y contain the position shift

Supported Effects:
    - DropShadow: Shadow cast behind the layer
    - InnerShadow: Shadow inside the layer edges
    - OuterGlow: Glow radiating outward from layer edges
    - InnerGlow: Glow radiating inward from layer edges
    - BevelEmboss: 3D raised/sunken appearance
    - Satin: Silky interior shading
    - Stroke: Outline around layer content
    - ColorOverlay: Solid color overlay preserving alpha
    - GradientOverlay: Gradient fill preserving alpha
    - PatternOverlay: Tiled pattern fill preserving alpha

All effects support:
    - RGB8: uint8 (0-255), 3 channels
    - RGBA8: uint8 (0-255), 4 channels
    - RGBf32: float32 (0.0-1.0), 3 channels
    - RGBAf32: float32 (0.0-1.0), 4 channels
"""

from .base import LayerEffect, PixelFormat, Expansion, EffectResult
from .drop_shadow import DropShadow
from .inner_shadow import InnerShadow
from .outer_glow import OuterGlow
from .inner_glow import InnerGlow
from .bevel_emboss import BevelEmboss, BevelStyle
from .satin import Satin
from .stroke import Stroke, StrokePosition
from .color_overlay import ColorOverlay
from .gradient_overlay import GradientOverlay, GradientStyle
from .pattern_overlay import PatternOverlay

__all__ = [
    # Base classes
    "LayerEffect",
    "PixelFormat",
    "Expansion",
    "EffectResult",
    # Effects
    "DropShadow",
    "InnerShadow",
    "OuterGlow",
    "InnerGlow",
    "BevelEmboss",
    "Satin",
    "Stroke",
    "ColorOverlay",
    "GradientOverlay",
    "PatternOverlay",
    # Constants
    "BevelStyle",
    "StrokePosition",
    "GradientStyle",
]
