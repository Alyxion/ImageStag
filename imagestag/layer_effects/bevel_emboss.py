"""
Bevel and Emboss layer effect.

Creates a 3D raised or sunken appearance using highlights and shadows by:
1. Extracting the alpha channel
2. Computing gradient (bump map) from alpha
3. Calculating lighting based on angle and altitude
4. Applying highlights and shadows
"""

from typing import Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class BevelStyle:
    """Bevel and emboss style options."""
    OUTER_BEVEL = "outer_bevel"
    INNER_BEVEL = "inner_bevel"
    EMBOSS = "emboss"
    PILLOW_EMBOSS = "pillow_emboss"


class BevelEmboss(LayerEffect):
    """
    Bevel and emboss effect.

    Creates a 3D raised or sunken appearance using highlights and shadows.

    Example:
        >>> from imagestag.layer_effects import BevelEmboss
        >>> effect = BevelEmboss(depth=5, angle=120, style="inner_bevel")
        >>> result = effect.apply(image)
    """

    effect_type = "bevelEmboss"
    display_name = "Bevel & Emboss"

    def __init__(
        self,
        depth: float = 3.0,
        angle: float = 120.0,
        altitude: float = 30.0,
        highlight_color: Tuple[int, int, int] = (255, 255, 255),
        highlight_opacity: float = 0.75,
        shadow_color: Tuple[int, int, int] = (0, 0, 0),
        shadow_opacity: float = 0.75,
        style: str = "inner_bevel",
        enabled: bool = True,
        opacity: float = 1.0,
        blend_mode: str = "normal",
    ):
        """
        Initialize bevel and emboss effect.

        Args:
            depth: Depth of the bevel effect in pixels
            angle: Light source angle in degrees (0 = right, 90 = top)
            altitude: Light altitude in degrees (0-90)
            highlight_color: Highlight color as (R, G, B) tuple
            highlight_opacity: Highlight opacity (0.0-1.0)
            shadow_color: Shadow color as (R, G, B) tuple
            shadow_opacity: Shadow opacity (0.0-1.0)
            style: Bevel style ("outer_bevel", "inner_bevel", "emboss", "pillow_emboss")
            enabled: Whether the effect is active
            opacity: Effect opacity (0.0-1.0)
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.depth = depth
        self.angle = angle
        self.altitude = altitude
        self.highlight_color = highlight_color
        self.highlight_opacity = highlight_opacity
        self.shadow_color = shadow_color
        self.shadow_opacity = shadow_opacity
        self.style = style

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for outer bevel."""
        if self.style == BevelStyle.OUTER_BEVEL:
            expand = int(self.depth) + 2
            return Expansion(left=expand, top=expand, right=expand, bottom=expand)
        return Expansion()

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply bevel and emboss to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with beveled/embossed image
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
            result = imagestag_rust.bevel_emboss_rgba(
                image_u8,
                float(self.depth),
                float(self.angle),
                float(self.altitude),
                self.highlight_color,
                float(self.highlight_opacity),
                self.shadow_color,
                float(self.shadow_opacity),
                self.style,
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.bevel_emboss_rgba(
                image.astype(np.uint8),
                float(self.depth),
                float(self.angle),
                float(self.altitude),
                self.highlight_color,
                float(self.highlight_opacity),
                self.shadow_color,
                float(self.shadow_opacity),
                self.style,
            )

        # Handle expansion for outer bevel
        expansion = self.get_expansion()
        offset = -expansion.left if expansion.left > 0 else 0

        return EffectResult(
            image=result,
            offset_x=offset,
            offset_y=offset,
        )

    def __repr__(self) -> str:
        return (
            f"BevelEmboss(depth={self.depth}, angle={self.angle}, "
            f"style={self.style})"
        )
