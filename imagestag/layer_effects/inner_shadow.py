"""
Inner Shadow layer effect.

Creates a shadow inside the layer content edges by:
1. Inverting the alpha (shadow comes from outside)
2. Optionally choking (contracting) the shadow
3. Blurring the shadow
4. Offsetting the shadow
5. Masking with original alpha (shadow only visible inside shape)

SVG Export: 95% fidelity via composite filter chain.
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


class InnerShadow(LayerEffect):
    """
    Inner shadow effect.

    Creates a shadow inside the layer content, as if the content were
    cut out and light was shining from a direction.

    Example:
        >>> from imagestag.layer_effects import InnerShadow
        >>> effect = InnerShadow(blur=5, offset_x=3, offset_y=3, color='#000000')
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "innerShadow"
    display_name: ClassVar[str] = "Inner Shadow"

    # Effect-specific fields with JS-compatible aliases
    blur: float = Field(default=5.0)
    offset_x: float = Field(default=2.0, alias='offsetX')
    offset_y: float = Field(default=2.0, alias='offsetY')
    choke: float = Field(default=0.0, ge=0.0, le=1.0)
    color: str = Field(default='#000000')  # Hex string for JS compatibility
    color_opacity: float = Field(default=0.75, alias='colorOpacity', ge=0.0, le=1.0)

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
        """Inner shadow doesn't expand the canvas."""
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

        color = self.color_rgb

        if fmt.is_float:
            color_f32 = (
                color[0] / 255.0,
                color[1] / 255.0,
                color[2] / 255.0,
            )
            result = imagestag_rust.inner_shadow_rgba_f32(
                image.astype(np.float32),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                float(self.choke),
                color_f32,
                float(self.color_opacity),
            )
        else:
            result = imagestag_rust.inner_shadow_rgba(
                image.astype(np.uint8),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                float(self.choke),
                color,
                float(self.color_opacity),
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
        """Inner shadow has 95% fidelity via composite filter chain."""
        return 95

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for inner shadow.

        Matches Rust algorithm:
        1. Invert alpha (shadow comes from outside the shape)
        2. Optionally dilate inverted alpha (choke makes shadow thicker)
        3. Blur the inverted alpha
        4. Offset the blurred shadow
        5. Clip to original alpha (shadow only visible inside shape)
        6. Colorize and composite over source

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor for viewBox units (viewBox_size / render_size)
        """
        if not self.enabled:
            return None

        # Scale all pixel-based values
        # Reduce blur significantly to concentrate shadow at edges (makes it more visible)
        svg_blur = self.blur * scale * 0.4
        svg_offset_x = self.offset_x * scale
        svg_offset_y = self.offset_y * scale

        # Build choke element if needed (dilate inverted alpha = thicker shadow)
        # Morphology DOES need /2 correction
        choke_elem = ""
        blur_input = "inverted"
        if self.choke > 0:
            choke_radius = self.blur * self.choke * scale / 2.0
            # Use feMorphology dilate on inverted alpha
            choke_elem = f'  <feMorphology operator="dilate" radius="{choke_radius:.2f}" in="inverted" result="choked"/>\n'
            blur_input = "choked"

        # primitiveUnits="userSpaceOnUse" ensures values are in viewBox units
        # Use standard alpha compositing: shadow on top of source
        return f'''<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%" primitiveUnits="userSpaceOnUse">
  <!-- Invert alpha: shadow comes from outside the shape -->
  <feComponentTransfer in="SourceAlpha" result="inverted">
    <feFuncA type="table" tableValues="1 0"/>
  </feComponentTransfer>
{choke_elem}  <!-- Blur the inverted alpha -->
  <feGaussianBlur stdDeviation="{svg_blur:.2f}" in="{blur_input}" result="blurredShadow"/>
  <!-- Offset the shadow (positive direction, same as Rust) -->
  <feOffset dx="{svg_offset_x:.2f}" dy="{svg_offset_y:.2f}" in="blurredShadow" result="offsetShadow"/>
  <!-- Clip to original shape (shadow only visible inside) -->
  <feComposite in="offsetShadow" in2="SourceAlpha" operator="in" result="clippedShadow"/>
  <!-- Colorize shadow: flood with color, use clippedShadow as alpha mask -->
  <feFlood flood-color="{self.color}" result="shadowColor"/>
  <feComposite in="shadowColor" in2="clippedShadow" operator="in" result="coloredShadow"/>
  <!-- Apply opacity to the shadow (boost by 2x to match Rust intensity) -->
  <feComponentTransfer in="coloredShadow" result="opacityShadow">
    <feFuncA type="linear" slope="{min(1.0, self.color_opacity * 2.0)}" intercept="0"/>
  </feComponentTransfer>
  <!-- Composite shadow ON TOP of source (standard alpha over compositing) -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="opacityShadow"/>
  </feMerge>
</filter>'''

    def __repr__(self) -> str:
        return (
            f"InnerShadow(blur={self.blur}, offset=({self.offset_x}, {self.offset_y}), "
            f"choke={self.choke}, color={self.color}, colorOpacity={self.color_opacity})"
        )
