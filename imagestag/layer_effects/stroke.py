"""
Stroke layer effect.

Creates an outline around non-transparent areas by:
1. Extracting the alpha channel
2. Dilating/eroding to create the stroke area
3. Colorizing with stroke color
"""

from typing import Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class StrokePosition:
    """Stroke position relative to the shape edge."""
    OUTSIDE = "outside"
    INSIDE = "inside"
    CENTER = "center"


class Stroke(LayerEffect):
    """
    Stroke/outline effect.

    Creates an outline around non-transparent areas of the layer.

    Example:
        >>> from imagestag.layer_effects import Stroke
        >>> effect = Stroke(width=3, color=(255, 0, 0), position="outside")
        >>> result = effect.apply(image)
    """

    effect_type = "stroke"
    display_name = "Stroke"

    def __init__(
        self,
        width: float = 2.0,
        color: Tuple[int, int, int] = (0, 0, 0),
        opacity: float = 1.0,
        position: str = "outside",
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize stroke effect.

        Args:
            width: Stroke width in pixels
            color: Stroke color as (R, G, B) tuple (0-255)
            opacity: Stroke opacity (0.0-1.0)
            position: Stroke position: "outside", "inside", or "center"
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.width = width
        self.color = color
        self.position = position

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for the stroke."""
        if self.position == StrokePosition.INSIDE:
            return Expansion()  # No expansion for inside stroke

        # Outside or center stroke needs expansion
        expand = int(self.width) + 2
        if self.position == StrokePosition.CENTER:
            expand = int(self.width / 2) + 2

        return Expansion(left=expand, top=expand, right=expand, bottom=expand)

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply stroke to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with stroked image and offset
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        # Ensure RGBA
        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        # Calculate expansion
        expansion = self.get_expansion()
        expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        # Call appropriate Rust function based on format
        if fmt.is_float:
            color_f32 = (
                self.color[0] / 255.0,
                self.color[1] / 255.0,
                self.color[2] / 255.0,
            )
            result = imagestag_rust.stroke_rgba_f32(
                image.astype(np.float32),
                float(self.width),
                color_f32,
                float(self.opacity),
                self.position,
                expand,
            )
        else:
            result = imagestag_rust.stroke_rgba(
                image.astype(np.uint8),
                float(self.width),
                self.color,
                float(self.opacity),
                self.position,
                expand,
            )

        return EffectResult(
            image=result,
            offset_x=-expand if expand > 0 else 0,
            offset_y=-expand if expand > 0 else 0,
        )

    def __repr__(self) -> str:
        return (
            f"Stroke(width={self.width}, color={self.color}, "
            f"position={self.position}, opacity={self.opacity})"
        )
