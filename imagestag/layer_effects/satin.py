"""
Satin layer effect.

Creates silky interior shading by compositing shifted and blurred copies
of the layer alpha channel.

SVG Export: 0% fidelity (no SVG equivalent).
"""

from typing import Tuple, Union, Dict, Any, Optional
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class Satin(LayerEffect):
    """
    Satin effect.

    Creates a silky, satiny interior shading effect by:
    1. Creating two offset copies of the alpha at opposite angles
    2. Blurring both copies
    3. Computing the absolute difference
    4. Optionally inverting the result
    5. Blending with the specified color

    Example:
        >>> from imagestag.layer_effects import Satin
        >>> effect = Satin(color=(0, 0, 0), opacity=0.5, angle=19, distance=11, size=14)
        >>> result = effect.apply(image)
    """

    effect_type = "satin"
    display_name = "Satin"

    def __init__(
        self,
        color: Tuple[int, int, int] = (0, 0, 0),
        opacity: float = 0.5,
        angle: float = 19.0,
        distance: float = 11.0,
        size: float = 14.0,
        invert: bool = False,
        enabled: bool = True,
        blend_mode: str = "multiply",
    ):
        """
        Initialize satin effect.

        Args:
            color: Satin color as (R, G, B) tuple (0-255)
            opacity: Effect opacity (0.0-1.0)
            angle: Direction angle in degrees
            distance: Offset distance in pixels
            size: Blur radius
            invert: Whether to invert the effect
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.color = color
        self.angle = angle
        self.distance = distance
        self.size = size
        self.invert = invert

    def get_expansion(self) -> Expansion:
        """Satin effect doesn't expand the canvas."""
        return Expansion()

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply satin effect to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with satin effect applied
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
            result = imagestag_rust.satin_rgba_f32(
                image.astype(np.float32),
                color_f32,
                float(self.opacity),
                float(self.angle),
                float(self.distance),
                float(self.size),
                bool(self.invert),
            )
        else:
            result = imagestag_rust.satin_rgba(
                image.astype(np.uint8),
                self.color,
                float(self.opacity),
                float(self.angle),
                float(self.distance),
                float(self.size),
                bool(self.invert),
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
        """Satin has no SVG equivalent."""
        return 0

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """Satin cannot be represented in SVG filters."""
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize satin to dict."""
        data = super().to_dict()
        data.update({
            'color': list(self.color),
            'angle': self.angle,
            'distance': self.distance,
            'size': self.size,
            'invert': self.invert,
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'Satin':
        """Create Satin from dict params."""
        return cls(
            color=tuple(data.get('color', [0, 0, 0])),
            angle=data.get('angle', 19.0),
            distance=data.get('distance', 11.0),
            size=data.get('size', 14.0),
            invert=data.get('invert', False),
            **base_params,
        )

    def __repr__(self) -> str:
        return (
            f"Satin(color={self.color}, opacity={self.opacity}, "
            f"angle={self.angle}, distance={self.distance}, "
            f"size={self.size}, invert={self.invert})"
        )
