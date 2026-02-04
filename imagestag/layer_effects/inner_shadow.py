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

from typing import Tuple, Union, Dict, Any, Optional
import numpy as np

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

        color_hex = self._color_to_hex(self.color)
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
  <feFlood flood-color="{color_hex}" result="shadowColor"/>
  <feComposite in="shadowColor" in2="clippedShadow" operator="in" result="coloredShadow"/>
  <!-- Apply opacity to the shadow (boost by 2x to match Rust intensity) -->
  <feComponentTransfer in="coloredShadow" result="opacityShadow">
    <feFuncA type="linear" slope="{min(1.0, self.opacity * 2.0)}" intercept="0"/>
  </feComponentTransfer>
  <!-- Composite shadow ON TOP of source (standard alpha over compositing) -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="opacityShadow"/>
  </feMerge>
</filter>'''

    def to_dict(self) -> Dict[str, Any]:
        """Serialize inner shadow to dict."""
        data = super().to_dict()
        data.update({
            'blur': self.blur,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'choke': self.choke,
            'color': list(self.color),
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'InnerShadow':
        """Create InnerShadow from dict params."""
        return cls(
            blur=data.get('blur', 5.0),
            offset_x=data.get('offset_x', 2.0),
            offset_y=data.get('offset_y', 2.0),
            choke=data.get('choke', 0.0),
            color=tuple(data.get('color', [0, 0, 0])),
            **base_params,
        )

    def __repr__(self) -> str:
        return (
            f"InnerShadow(blur={self.blur}, offset=({self.offset_x}, {self.offset_y}), "
            f"choke={self.choke}, color={self.color}, opacity={self.opacity})"
        )
