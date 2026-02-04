"""
Gradient Overlay layer effect.

Fills the layer with a gradient while preserving the alpha channel.
Supports 5 gradient styles: linear, radial, angle, reflected, and diamond.

SVG Export: 80% fidelity for linear/radial (native gradients),
            60% for angle/reflected/diamond (approximation).
"""

from typing import List, Tuple, Union, Dict, Any, Optional
import math
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
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
                self.blend_mode,  # Pass blend mode to Rust
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
                self.blend_mode,  # Pass blend mode to Rust
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    # =========================================================================
    # SVG Export
    # =========================================================================

    @property
    def svg_fidelity(self) -> int:
        """Gradient overlay fidelity varies by style."""
        if self.style in (GradientStyle.LINEAR, GradientStyle.RADIAL):
            return 80
        return 60  # angle, reflected, diamond are approximations

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for gradient overlay.

        Returns None - gradient overlay cannot be implemented as a pure SVG filter.
        Use to_svg_defs() instead to get gradient definitions that can be applied
        via fill or mask on the target element.
        """
        # feImage with data URLs has poor browser/resvg support
        # Gradient overlays must be implemented via SVG defs + element fills
        return None

    def to_svg_defs(self, gradient_id: str) -> Optional[str]:
        """
        Generate SVG gradient definition for use in defs section.

        The gradient can be applied to elements via fill="url(#gradient_id)".
        For overlay effect, apply to a rect/path clipped to the source shape.

        Args:
            gradient_id: ID for the gradient definition

        Returns:
            SVG gradient definition string, or None if disabled
        """
        if not self.enabled:
            return None

        stops = self._generate_svg_stops()

        if self.style == GradientStyle.RADIAL:
            return f'<radialGradient id="{gradient_id}" cx="50%" cy="50%" r="50%">{stops}</radialGradient>'
        else:
            # Linear gradient (also used as approximation for angle/reflected/diamond)
            # Photoshop angle convention: 0° = up, 90° = right, increases clockwise
            # SVG convention: x1,y1 = start point, x2,y2 = end point
            # Convert PS angle to SVG coordinates
            angle_rad = math.radians(self.angle)
            # Start point (position 0.0)
            x1 = 50 + 50 * math.sin(angle_rad)
            y1 = 50 - 50 * math.cos(angle_rad)
            # End point (position 1.0)
            x2 = 50 - 50 * math.sin(angle_rad)
            y2 = 50 + 50 * math.cos(angle_rad)
            return f'<linearGradient id="{gradient_id}" x1="{x1:.1f}%" y1="{y1:.1f}%" x2="{x2:.1f}%" y2="{y2:.1f}%">{stops}</linearGradient>'

    def _generate_svg_stops(self) -> str:
        """Generate SVG gradient stop elements (compact, no newlines for data URL embedding)."""
        stops = []
        gradient = self.gradient if not self.reverse else list(reversed(self.gradient))
        for pos, r, g, b in gradient:
            position = pos if not self.reverse else 1.0 - pos
            color = f"#{r:02X}{g:02X}{b:02X}"
            stops.append(f'<stop offset="{position * 100:.1f}%" stop-color="{color}"/>')
        return ''.join(stops)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize gradient overlay to dict."""
        data = super().to_dict()
        data.update({
            'gradient': self.gradient,
            'style': self.style,
            'angle': self.angle,
            'scale': self.scale,
            'reverse': self.reverse,
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'GradientOverlay':
        """Create GradientOverlay from dict params."""
        gradient = data.get('gradient')
        if gradient:
            gradient = [tuple(stop) for stop in gradient]
        return cls(
            gradient=gradient,
            style=data.get('style', 'linear'),
            angle=data.get('angle', 90.0),
            scale=data.get('scale', 1.0),
            reverse=data.get('reverse', False),
            **base_params,
        )

    def __repr__(self) -> str:
        return (
            f"GradientOverlay(style={self.style!r}, angle={self.angle}, "
            f"scale={self.scale}, reverse={self.reverse}, opacity={self.opacity})"
        )
