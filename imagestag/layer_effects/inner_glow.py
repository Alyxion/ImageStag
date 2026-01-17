"""
Inner Glow layer effect.

Creates a glow effect inside the shape edges by:
1. Extracting the alpha channel
2. Eroding based on choke
3. Blurring the eroded alpha
4. Computing glow strength (original - blurred)
5. Compositing glow color with screen blending
"""

from typing import Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class InnerGlow(LayerEffect):
    """
    Inner glow effect.

    Creates a glow effect radiating inward from the layer edges.

    Example:
        >>> from imagestag.layer_effects import InnerGlow
        >>> effect = InnerGlow(radius=10, color=(255, 255, 255))
        >>> result = effect.apply(image)
    """

    effect_type = "innerGlow"
    display_name = "Inner Glow"

    def __init__(
        self,
        radius: float = 10.0,
        color: Tuple[int, int, int] = (255, 255, 0),
        opacity: float = 0.75,
        choke: float = 0.0,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize inner glow effect.

        Args:
            radius: Glow blur radius
            color: Glow color as (R, G, B) tuple (0-255)
            opacity: Glow opacity (0.0-1.0)
            choke: How much to contract the glow (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.radius = radius
        self.color = color
        self.choke = choke

    def get_expansion(self) -> Expansion:
        """Inner glow doesn't expand the canvas."""
        return Expansion()

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply inner glow to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with inner glow applied
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        # Currently only u8 version exists
        if fmt.is_float:
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.inner_glow_rgba(
                image_u8,
                float(self.radius),
                self.color,
                float(self.opacity),
                float(self.choke),
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.inner_glow_rgba(
                image.astype(np.uint8),
                float(self.radius),
                self.color,
                float(self.opacity),
                float(self.choke),
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    def __repr__(self) -> str:
        return (
            f"InnerGlow(radius={self.radius}, color={self.color}, "
            f"choke={self.choke}, opacity={self.opacity})"
        )
