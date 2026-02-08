"""
SVGBaseLayer - Abstract base for SVG-based layers.

Mirrors the JS SVGBaseLayer class, providing shared SVG transform state
for StaticSVGLayer and TextLayer.

The Python model is for serialization only. Rendering happens in JS/resvg.
"""

from typing import Any, Optional

from pydantic import Field

from .base import BaseLayer


class SVGBaseLayer(BaseLayer):
    """
    Abstract base for SVG-based layers (StaticSVGLayer, TextLayer).

    Provides shared transform state tracking for SVG content:
    - Content rotation (0, 90, 180, 270)
    - Mirror state (horizontal, vertical)
    - Original SVG content before transforms
    """

    # Transform state tracking
    original_svg_content: Optional[str] = Field(
        default=None, alias='_originalSvgContent'
    )
    original_natural_width: float = Field(
        default=0, alias='_originalNaturalWidth'
    )
    original_natural_height: float = Field(
        default=0, alias='_originalNaturalHeight'
    )
    content_rotation: int = Field(default=0, alias='_contentRotation')
    mirror_x: bool = Field(default=False, alias='_mirrorX')
    mirror_y: bool = Field(default=False, alias='_mirrorY')

    def has_transform(self) -> bool:
        """Check if layer has any baked-in SVG transforms."""
        return (
            self.content_rotation != 0
            or self.mirror_x
            or self.mirror_y
            or super().has_transform()
        )
