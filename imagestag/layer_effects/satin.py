"""
Satin layer effect.

Creates silky interior shading by compositing shifted and blurred copies
of the layer alpha channel.

SVG Export: 0% fidelity (no SVG equivalent).
"""

from typing import Tuple, Union, Dict, Any, Optional, ClassVar
import numpy as np

from pydantic import Field, model_validator

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
        >>> effect = Satin(color='#000000', colorOpacity=0.5, angle=19, distance=11, size=14)
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "satin"
    display_name: ClassVar[str] = "Satin"

    # Effect-specific fields
    color: str = Field(default='#000000')  # Hex string for JS compatibility
    color_opacity: float = Field(default=0.5, alias='colorOpacity', ge=0.0, le=1.0)
    angle: float = Field(default=19.0)
    distance: float = Field(default=11.0)
    size: float = Field(default=14.0)
    invert: bool = Field(default=False)

    # Internal: parsed RGB tuple (not serialized)
    _color_rgb: Optional[Tuple[int, int, int]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Convert color formats and handle legacy parameters."""
        if isinstance(data, dict):
            # Handle legacy 'opacity' parameter for color_opacity
            if 'opacity' in data and 'colorOpacity' not in data and 'color_opacity' not in data:
                opacity_val = data.get('opacity', 1.0)
                if opacity_val != 1.0:
                    data['colorOpacity'] = opacity_val
                    data['opacity'] = 1.0

            # Convert RGB tuple/list to hex string
            color = data.get('color', '#000000')
            if isinstance(color, (list, tuple)):
                r, g, b = color[:3]
                data['color'] = f'#{int(r):02X}{int(g):02X}{int(b):02X}'
        return data

    def model_post_init(self, __context: Any) -> None:
        """Parse color after initialization."""
        super().model_post_init(__context)
        self._color_rgb = self._hex_to_rgb(self.color)

    @staticmethod
    def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        """Convert hex color string to RGB tuple."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) != 6:
            return (0, 0, 0)
        return (
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            int(hex_str[4:6], 16),
        )

    @property
    def color_rgb(self) -> Tuple[int, int, int]:
        """Get color as RGB tuple (0-255)."""
        if self._color_rgb is None:
            self._color_rgb = self._hex_to_rgb(self.color)
        return self._color_rgb

    def get_expansion(self) -> Expansion:
        """Satin effect doesn't expand the canvas."""
        return Expansion()

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

        color = self.color_rgb

        if fmt.is_float:
            color_f32 = (
                color[0] / 255.0,
                color[1] / 255.0,
                color[2] / 255.0,
            )
            result = imagestag_rust.satin_rgba_f32(
                image.astype(np.float32),
                color_f32,
                float(self.color_opacity),
                float(self.angle),
                float(self.distance),
                float(self.size),
                bool(self.invert),
            )
        else:
            result = imagestag_rust.satin_rgba(
                image.astype(np.uint8),
                color,
                float(self.color_opacity),
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

    def __repr__(self) -> str:
        return (
            f"Satin(color={self.color}, colorOpacity={self.color_opacity}, "
            f"angle={self.angle}, distance={self.distance}, "
            f"size={self.size}, invert={self.invert})"
        )
