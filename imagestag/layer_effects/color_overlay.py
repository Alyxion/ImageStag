"""
Color Overlay layer effect.

Overlays a solid color on the layer content, preserving the alpha channel.
"""

from typing import Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class ColorOverlay(LayerEffect):
    """
    Color overlay effect.

    Replaces all colors with a solid color while preserving alpha.
    The opacity controls how much of the original color shows through.

    Example:
        >>> from imagestag.layer_effects import ColorOverlay
        >>> effect = ColorOverlay(color=(255, 0, 0), opacity=1.0)
        >>> result = effect.apply(image)
    """

    effect_type = "colorOverlay"
    display_name = "Color Overlay"

    def __init__(
        self,
        color: Tuple[int, int, int] = (255, 0, 0),
        opacity: float = 1.0,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize color overlay effect.

        Args:
            color: Overlay color as (R, G, B) tuple (0-255)
            opacity: How much the overlay replaces original color (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.color = color

    def get_expansion(self) -> Expansion:
        """Color overlay doesn't expand the canvas."""
        return Expansion()

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply color overlay to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with color overlay applied
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        if fmt.is_float:
            color_f32 = (
                self.color[0] / 255.0,
                self.color[1] / 255.0,
                self.color[2] / 255.0,
            )
            result = imagestag_rust.color_overlay_rgba_f32(
                image.astype(np.float32),
                color_f32,
                float(self.opacity),
            )
        else:
            result = imagestag_rust.color_overlay_rgba(
                image.astype(np.uint8),
                self.color,
                float(self.opacity),
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    def __repr__(self) -> str:
        return f"ColorOverlay(color={self.color}, opacity={self.opacity})"
