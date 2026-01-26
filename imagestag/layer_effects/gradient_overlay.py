"""
Gradient Overlay layer effect.

Fills the layer with a gradient while preserving the alpha channel.
Supports 5 gradient styles: linear, radial, angle, reflected, and diamond.
"""

from typing import List, Tuple, Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class GradientStyle:
    """Gradient style options."""
    LINEAR = "linear"
    RADIAL = "radial"
    ANGLE = "angle"
    REFLECTED = "reflected"
    DIAMOND = "diamond"


class GradientOverlay(LayerEffect):
    """
    Gradient overlay effect.

    Fills the layer content with a gradient while preserving transparency.
    Supports 5 gradient styles matching Photoshop's options.

    Example:
        >>> from imagestag.layer_effects import GradientOverlay
        >>> # Gradient from red to blue
        >>> effect = GradientOverlay(
        ...     gradient=[
        ...         (0.0, 255, 0, 0),    # Red at start
        ...         (1.0, 0, 0, 255),    # Blue at end
        ...     ],
        ...     style="linear",
        ...     angle=90.0,
        ... )
        >>> result = effect.apply(image)
    """

    effect_type = "gradientOverlay"
    display_name = "Gradient Overlay"

    def __init__(
        self,
        gradient: List[Tuple[float, int, int, int]] = None,
        style: str = "linear",
        angle: float = 90.0,
        scale: float = 1.0,
        reverse: bool = False,
        opacity: float = 1.0,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize gradient overlay effect.

        Args:
            gradient: List of color stops as (position, r, g, b) tuples.
                     Position is 0.0-1.0, colors are 0-255.
                     Default is black to white gradient.
            style: Gradient style - "linear", "radial", "angle", "reflected", "diamond"
            angle: Angle in degrees (for linear/reflected styles)
            scale: Scale factor (1.0 = 100%)
            reverse: Whether to reverse the gradient direction
            opacity: Effect opacity (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)

        # Default gradient: black to white
        if gradient is None:
            gradient = [
                (0.0, 0, 0, 0),      # Black at start
                (1.0, 255, 255, 255), # White at end
            ]
        self.gradient = gradient
        self.style = style
        self.angle = angle
        self.scale = scale
        self.reverse = reverse

    def get_expansion(self) -> Expansion:
        """Gradient overlay doesn't expand the canvas."""
        return Expansion()

    def _stops_to_flat_array(self, is_float: bool) -> List[float]:
        """Convert gradient stops to flat array for Rust."""
        flat = []
        for pos, r, g, b in self.gradient:
            flat.extend([
                float(pos),
                float(r) if not is_float else float(r) / 255.0,
                float(g) if not is_float else float(g) / 255.0,
                float(b) if not is_float else float(b) / 255.0,
            ])
        return flat

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply gradient overlay to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with gradient overlay applied
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        # Convert stops to flat array
        stops = self._stops_to_flat_array(fmt.is_float)

        if fmt.is_float:
            result = imagestag_rust.gradient_overlay_rgba_f32(
                image.astype(np.float32),
                stops,
                self.style,
                float(self.angle),
                float(self.scale),
                bool(self.reverse),
                float(self.opacity),
            )
        else:
            result = imagestag_rust.gradient_overlay_rgba(
                image.astype(np.uint8),
                stops,
                self.style,
                float(self.angle),
                float(self.scale),
                bool(self.reverse),
                float(self.opacity),
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    def __repr__(self) -> str:
        return (
            f"GradientOverlay(style={self.style!r}, angle={self.angle}, "
            f"scale={self.scale}, reverse={self.reverse}, opacity={self.opacity})"
        )
