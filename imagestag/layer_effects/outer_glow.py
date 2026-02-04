"""
Outer Glow layer effect.

Creates a glow effect outside the shape edges by:
1. Extracting the alpha channel
2. Optionally spreading (dilating) the alpha
3. Blurring the alpha
4. Colorizing with glow color
5. Compositing original on top

SVG Export: 90% fidelity via composite filter chain.
"""

from typing import Tuple, Union, Dict, Any, Optional
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class OuterGlow(LayerEffect):
    """
    Outer glow effect.

    Creates a glow effect radiating outward from the layer content.

    Example:
        >>> from imagestag.layer_effects import OuterGlow
        >>> effect = OuterGlow(radius=15, color=(255, 255, 0))
        >>> result = effect.apply(image)
    """

    effect_type = "outerGlow"
    display_name = "Outer Glow"

    def __init__(
        self,
        radius: float = 10.0,
        color: Tuple[int, int, int] = (255, 255, 0),
        opacity: float = 0.75,
        spread: float = 0.0,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize outer glow effect.

        Args:
            radius: Glow blur radius
            color: Glow color as (R, G, B) tuple (0-255)
            opacity: Glow opacity (0.0-1.0)
            spread: How much to expand the glow before blur (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.radius = radius
        self.color = color
        self.spread = spread

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for the glow."""
        expand = int(self.radius * 3) + 2
        return Expansion(left=expand, top=expand, right=expand, bottom=expand)

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply outer glow to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with glowing image and offset
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        expansion = self.get_expansion()
        expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        # Currently only u8 version exists
        if fmt.is_float:
            # Convert to u8, apply, convert back
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.outer_glow_rgba(
                image_u8,
                float(self.radius),
                self.color,
                float(self.opacity),
                float(self.spread),
                expand,
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.outer_glow_rgba(
                image.astype(np.uint8),
                float(self.radius),
                self.color,
                float(self.opacity),
                float(self.spread),
                expand,
            )

        return EffectResult(
            image=result,
            offset_x=-expand,
            offset_y=-expand,
        )

    # =========================================================================
    # SVG Export
    # =========================================================================

    @property
    def svg_fidelity(self) -> int:
        """Outer glow has 90% fidelity via composite filter chain."""
        return 90

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for outer glow.

        Matches Rust algorithm:
        1. Extract alpha
        2. Optionally dilate (spread)
        3. Blur
        4. Subtract original alpha to get outer-only glow
        5. Colorize and composite source over glow

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor for viewBox units (viewBox_size / render_size)
        """
        if not self.enabled:
            return None

        color_hex = self._color_to_hex(self.color)

        # Scale pixel-based values
        svg_blur = self.radius * scale

        # Build spread element if needed
        # Rust: spread_radius = radius * spread
        spread_elem = ""
        blur_input = "SourceAlpha"
        if self.spread > 0:
            spread_radius = self.radius * self.spread * scale
            spread_elem = f'  <feMorphology operator="dilate" radius="{spread_radius:.2f}" in="SourceAlpha" result="spread"/>\n'
            blur_input = "spread"

        # primitiveUnits="userSpaceOnUse" ensures values are in viewBox units
        return f'''<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%" primitiveUnits="userSpaceOnUse">
{spread_elem}  <feGaussianBlur stdDeviation="{svg_blur:.2f}" in="{blur_input}" result="blurred"/>
  <!-- Subtract original alpha from blurred to get outer-only glow -->
  <feComposite in="blurred" in2="SourceAlpha" operator="out" result="outerOnly"/>
  <feFlood flood-color="{color_hex}" flood-opacity="{self.opacity}" result="color"/>
  <feComposite in="color" in2="outerOnly" operator="in" result="glow"/>
  <feMerge>
    <feMergeNode in="glow"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>'''

    def to_dict(self) -> Dict[str, Any]:
        """Serialize outer glow to dict."""
        data = super().to_dict()
        data.update({
            'radius': self.radius,
            'color': list(self.color),
            'spread': self.spread,
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'OuterGlow':
        """Create OuterGlow from dict params."""
        return cls(
            radius=data.get('radius', 10.0),
            color=tuple(data.get('color', [255, 255, 0])),
            spread=data.get('spread', 0.0),
            **base_params,
        )

    def __repr__(self) -> str:
        return (
            f"OuterGlow(radius={self.radius}, color={self.color}, "
            f"spread={self.spread}, opacity={self.opacity})"
        )
