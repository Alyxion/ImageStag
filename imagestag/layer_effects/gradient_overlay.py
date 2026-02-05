"""
Gradient Overlay layer effect.

Fills the layer with a gradient while preserving the alpha channel.
Supports 5 gradient styles: linear, radial, angle, reflected, and diamond.

SVG Export: 80% fidelity for linear/radial (native gradients),
            60% for angle/reflected/diamond (approximation).
"""

from typing import List, Tuple, Union, Dict, Any, Optional, ClassVar
import math
import numpy as np

from pydantic import Field, model_validator

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
        ...         {"position": 0.0, "color": "#FF0000"},  # Red at start
        ...         {"position": 1.0, "color": "#0000FF"},  # Blue at end
        ...     ],
        ...     style="linear",
        ...     angle=90.0,
        ... )
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "gradientOverlay"
    display_name: ClassVar[str] = "Gradient Overlay"

    # Effect-specific fields
    # Gradient stored as list of dicts: [{"position": 0.0, "color": "#RRGGBB"}, ...]
    gradient: List[Dict[str, Any]] = Field(default_factory=lambda: [
        {"position": 0.0, "color": "#000000"},
        {"position": 1.0, "color": "#FFFFFF"},
    ])
    style: str = Field(default="linear")
    angle: float = Field(default=90.0)
    scale: float = Field(default=1.0)
    reverse: bool = Field(default=False)

    @model_validator(mode='before')
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Convert legacy gradient formats."""
        if isinstance(data, dict):
            gradient = data.get('gradient')
            if gradient and isinstance(gradient, list):
                # Convert legacy tuple format: [(pos, r, g, b), ...]
                # to new dict format: [{"position": pos, "color": "#RRGGBB"}, ...]
                normalized = []
                for stop in gradient:
                    if isinstance(stop, dict):
                        # Already in dict format - ensure color is hex
                        stop_dict = dict(stop)
                        color = stop_dict.get('color', '#000000')
                        if isinstance(color, (list, tuple)):
                            r, g, b = color[:3]
                            stop_dict['color'] = f'#{int(r):02X}{int(g):02X}{int(b):02X}'
                        normalized.append(stop_dict)
                    elif isinstance(stop, (list, tuple)) and len(stop) >= 4:
                        # Legacy tuple format: (position, r, g, b)
                        pos, r, g, b = stop[:4]
                        normalized.append({
                            "position": float(pos),
                            "color": f'#{int(r):02X}{int(g):02X}{int(b):02X}',
                        })
                data['gradient'] = normalized
        return data

    def _get_gradient_tuples(self) -> List[Tuple[float, int, int, int]]:
        """Convert gradient stops to tuple format for Rust."""
        result = []
        for stop in self.gradient:
            pos = stop.get('position', 0.0)
            color = stop.get('color', '#000000')
            # Parse hex color
            color = color.lstrip('#')
            if len(color) == 6:
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
            else:
                r, g, b = 0, 0, 0
            result.append((pos, r, g, b))
        return result

    def get_expansion(self) -> Expansion:
        """Gradient overlay doesn't expand the canvas."""
        return Expansion()

    def _stops_to_flat_array(self, is_float: bool) -> List[float]:
        """Convert gradient stops to flat array for Rust."""
        gradient_tuples = self._get_gradient_tuples()
        flat = []
        for pos, r, g, b in gradient_tuples:
            flat.extend([
                float(pos),
                float(r) if not is_float else float(r) / 255.0,
                float(g) if not is_float else float(g) / 255.0,
                float(b) if not is_float else float(b) / 255.0,
            ])
        return flat

    def _resolve_format(self, image: np.ndarray, format: Union[PixelFormat, str, None]) -> PixelFormat:
        """Resolve pixel format from argument or auto-detect."""
        if format is None:
            return PixelFormat.from_array(image)
        if isinstance(format, str):
            return PixelFormat(format)
        return format

    def _ensure_rgba(self, image: np.ndarray) -> np.ndarray:
        """Convert RGB to RGBA if needed."""
        if image.shape[2] == 3:
            alpha = np.ones((*image.shape[:2], 1), dtype=image.dtype)
            if image.dtype == np.uint8:
                alpha = (alpha * 255).astype(np.uint8)
            return np.concatenate([image, alpha], axis=2)
        return image

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
        for stop in gradient:
            pos = stop.get('position', 0.0)
            position = pos if not self.reverse else 1.0 - pos
            color = stop.get('color', '#000000')
            stops.append(f'<stop offset="{position * 100:.1f}%" stop-color="{color}"/>')
        return ''.join(stops)

    def __repr__(self) -> str:
        return (
            f"GradientOverlay(style={self.style!r}, angle={self.angle}, "
            f"scale={self.scale}, reverse={self.reverse}, opacity={self.opacity})"
        )
