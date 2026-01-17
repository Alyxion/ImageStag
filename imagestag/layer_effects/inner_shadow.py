"""
Inner Shadow layer effect.

Creates a shadow inside the layer content edges by:
1. Inverting the alpha (shadow comes from outside)
2. Optionally choking (contracting) the shadow
3. Blurring the shadow
4. Offsetting the shadow
5. Masking with original alpha (shadow only visible inside shape)
"""

from typing import Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class InnerShadow(LayerEffect):
    """
    Inner shadow effect.

    Creates a shadow inside the layer content, as if the content were
    cut out and light was shining from a direction.

    Example:
        >>> from imagestag.layer_effects import InnerShadow
        >>> effect = InnerShadow(blur=5, offset_x=3, offset_y=3)
        >>> result = effect.apply(image)
    """

    effect_type = "innerShadow"
    display_name = "Inner Shadow"

    def __init__(
        self,
        blur: float = 5.0,
        offset_x: float = 2.0,
        offset_y: float = 2.0,
        choke: float = 0.0,
        color: Tuple[int, int, int] = (0, 0, 0),
        opacity: float = 0.75,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize inner shadow effect.

        Args:
            blur: Shadow blur radius
            offset_x: Horizontal shadow offset
            offset_y: Vertical shadow offset
            choke: How much to contract before blur (0.0-1.0)
            color: Shadow color as (R, G, B) tuple (0-255)
            opacity: Shadow opacity (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.blur = blur
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.choke = choke
        self.color = color

    def get_expansion(self) -> Expansion:
        """Inner shadow doesn't expand the canvas."""
        return Expansion()

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply inner shadow to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with inner shadow applied
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
            result = imagestag_rust.inner_shadow_rgba_f32(
                image.astype(np.float32),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                float(self.choke),
                color_f32,
                float(self.opacity),
            )
        else:
            result = imagestag_rust.inner_shadow_rgba(
                image.astype(np.uint8),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                float(self.choke),
                self.color,
                float(self.opacity),
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    def __repr__(self) -> str:
        return (
            f"InnerShadow(blur={self.blur}, offset=({self.offset_x}, {self.offset_y}), "
            f"choke={self.choke}, color={self.color}, opacity={self.opacity})"
        )
