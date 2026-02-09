"""
Layer Effects Module

Provides layer effects for server-side rendering.
Each effect is in its own file for clean architecture.
"""

from .base import LayerEffect
from .drop_shadow import DropShadowEffect
from .inner_shadow import InnerShadowEffect
from .outer_glow import OuterGlowEffect
from .inner_glow import InnerGlowEffect
from .bevel_emboss import BevelEmbossEffect
from .stroke import StrokeEffect
from .color_overlay import ColorOverlayEffect
from .gradient_overlay import GradientOverlayEffect

# Registry for deserialization
effect_registry = {
    'dropShadow': DropShadowEffect,
    'innerShadow': InnerShadowEffect,
    'outerGlow': OuterGlowEffect,
    'innerGlow': InnerGlowEffect,
    'bevelEmboss': BevelEmbossEffect,
    'stroke': StrokeEffect,
    'colorOverlay': ColorOverlayEffect,
    'gradientOverlay': GradientOverlayEffect,
}

# Render order (Affinity-style, bottom to top)
effect_render_order = [
    'dropShadow',      # Behind layer
    'outerGlow',       # Behind layer
    'colorOverlay',    # Fill overlay
    'gradientOverlay', # Fill overlay
    'patternOverlay',  # Fill overlay
    'satin',           # Surface shading
    'bevelEmboss',     # 3D lighting (on top of overlays)
    'innerShadow',     # Inner edges
    'innerGlow',       # Inner edges
    'stroke',          # Topmost
]


def deserialize_effect(data: dict) -> LayerEffect | None:
    """Create effect from serialized data."""
    effect_type = data.get('type')
    if effect_type not in effect_registry:
        return None
    return effect_registry[effect_type].from_dict(data)


def get_available_effects() -> list[dict]:
    """Get list of all available effect types."""
    return [
        {'type': name, 'displayName': cls.display_name}
        for name, cls in effect_registry.items()
    ]


__all__ = [
    'LayerEffect',
    'DropShadowEffect',
    'InnerShadowEffect',
    'OuterGlowEffect',
    'InnerGlowEffect',
    'BevelEmbossEffect',
    'StrokeEffect',
    'ColorOverlayEffect',
    'GradientOverlayEffect',
    'effect_registry',
    'effect_render_order',
    'deserialize_effect',
    'get_available_effects',
]
