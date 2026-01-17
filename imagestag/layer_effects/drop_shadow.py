"""
Drop Shadow layer effect.

Creates a shadow behind the layer content by:
1. Extracting the alpha channel
2. Blurring it with Gaussian kernel
3. Offsetting the shadow
4. Colorizing with shadow color
5. Compositing original on top
"""

from typing import Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

# Import Rust implementation
try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class DropShadow(LayerEffect):
    """
    Drop shadow effect.

    Creates a shadow cast by the layer content, offset and blurred.

    Example:
        >>> from imagestag.layer_effects import DropShadow
        >>> effect = DropShadow(blur=5, offset_x=10, offset_y=10, color=(0, 0, 0))
        >>> result = effect.apply(image)
        >>> output_image = result.image
        >>> offset_x, offset_y = result.offset_x, result.offset_y
    """

    effect_type = "dropShadow"
    display_name = "Drop Shadow"

    def __init__(
        self,
        blur: float = 5.0,
        offset_x: float = 4.0,
        offset_y: float = 4.0,
        color: Tuple[int, int, int] = (0, 0, 0),
        opacity: float = 0.75,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize drop shadow effect.

        Args:
            blur: Shadow blur radius (sigma for Gaussian)
            offset_x: Horizontal shadow offset (positive = right)
            offset_y: Vertical shadow offset (positive = down)
            color: Shadow color as (R, G, B) tuple (0-255)
            opacity: Shadow opacity (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.blur = blur
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.color = color

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for the shadow."""
        # Blur expands by ~3 sigma in each direction
        blur_expand = int(self.blur * 3) + 2

        # Account for offset
        left = blur_expand + max(0, -int(self.offset_x))
        right = blur_expand + max(0, int(self.offset_x))
        top = blur_expand + max(0, -int(self.offset_y))
        bottom = blur_expand + max(0, int(self.offset_y))

        return Expansion(left=left, top=top, right=right, bottom=bottom)

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply drop shadow to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with shadowed image and offset
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
            raise RuntimeError("Rust extension not available. Install imagestag with Rust support.")

        # Call appropriate Rust function based on format
        if fmt.is_float:
            # Normalize color to 0.0-1.0 for f32
            color_f32 = (
                self.color[0] / 255.0,
                self.color[1] / 255.0,
                self.color[2] / 255.0,
            )
            result = imagestag_rust.drop_shadow_rgba_f32(
                image.astype(np.float32),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                color_f32,
                float(self.opacity),
                expand,
            )
        else:
            result = imagestag_rust.drop_shadow_rgba(
                image.astype(np.uint8),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                self.color,
                float(self.opacity),
                expand,
            )

        # The result is expanded, offset is negative of expansion
        return EffectResult(
            image=result,
            offset_x=-expand,
            offset_y=-expand,
        )

    def __repr__(self) -> str:
        return (
            f"DropShadow(blur={self.blur}, offset=({self.offset_x}, {self.offset_y}), "
            f"color={self.color}, opacity={self.opacity})"
        )
