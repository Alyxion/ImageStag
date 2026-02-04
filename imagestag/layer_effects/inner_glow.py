"""
Inner Glow layer effect.

Creates a glow effect inside the shape edges by:
1. Extracting the alpha channel
2. Eroding based on choke
3. Blurring the eroded alpha
4. Computing glow strength (original - blurred)
5. Compositing glow color with screen blending

SVG Export: 85% fidelity via composite filter chain.
"""

from typing import Tuple, Union, Dict, Any, Optional
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
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

    # =========================================================================
    # SVG Export
    # =========================================================================

    @property
    def svg_fidelity(self) -> int:
        """Inner glow has 85% fidelity via composite filter chain."""
        return 85

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for inner glow.

        Matches Rust algorithm:
        1. Optionally erode alpha (choke)
        2. Blur the eroded alpha
        3. Compute glow intensity = original alpha - blurred (edge detection)
        4. Clip to original alpha
        5. Apply screen blending with glow color

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor for viewBox units (viewBox_size / render_size)
        """
        if not self.enabled:
            return None

        color_hex = self._color_to_hex(self.color)

        # Rust: choke_radius = radius * choke
        # Rust: blur_radius = radius * (1.0 - choke * 0.5)
        # Scale all pixel-based values
        # Note: SVG filter effects appear 2x larger than Rust, so halve values
        choke_radius = self.radius * self.choke * scale / 2.0
        svg_blur = self.radius * (1.0 - self.choke * 0.5) * scale / 2.0

        # Build choke (erode) element if needed
        choke_elem = ""
        blur_input = "SourceAlpha"
        if self.choke > 0 and choke_radius >= 1:
            choke_elem = f'  <feMorphology operator="erode" radius="{choke_radius:.2f}" in="SourceAlpha" result="eroded"/>\n'
            blur_input = "eroded"

        # primitiveUnits="userSpaceOnUse" ensures values are in viewBox units
        return f'''<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%" primitiveUnits="userSpaceOnUse">
{choke_elem}  <!-- Blur the (possibly eroded) alpha -->
  <feGaussianBlur stdDeviation="{svg_blur:.2f}" in="{blur_input}" result="blurred"/>
  <!-- Edge detection: original - blurred = glow intensity at edges -->
  <feComposite in="SourceAlpha" in2="blurred" operator="arithmetic" k1="0" k2="1" k3="-1" k4="0" result="edgeGlow"/>
  <!-- Clip to original shape -->
  <feComposite in="edgeGlow" in2="SourceAlpha" operator="in" result="clippedGlow"/>
  <!-- Colorize -->
  <feFlood flood-color="{color_hex}" flood-opacity="{self.opacity}" result="color"/>
  <feComposite in="color" in2="clippedGlow" operator="in" result="glow"/>
  <!-- Screen blend over source (Rust uses screen blending for inner glow) -->
  <feBlend in="glow" in2="SourceGraphic" mode="screen" result="blended"/>
  <!-- Ensure we keep original alpha -->
  <feComposite in="blended" in2="SourceAlpha" operator="in"/>
</filter>'''

    def to_dict(self) -> Dict[str, Any]:
        """Serialize inner glow to dict."""
        data = super().to_dict()
        data.update({
            'radius': self.radius,
            'color': list(self.color),
            'choke': self.choke,
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'InnerGlow':
        """Create InnerGlow from dict params."""
        return cls(
            radius=data.get('radius', 10.0),
            color=tuple(data.get('color', [255, 255, 0])),
            choke=data.get('choke', 0.0),
            **base_params,
        )

    def __repr__(self) -> str:
        return (
            f"InnerGlow(radius={self.radius}, color={self.color}, "
            f"choke={self.choke}, opacity={self.opacity})"
        )
