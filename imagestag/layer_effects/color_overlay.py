"""
Color Overlay layer effect.

Overlays a solid color on the layer content, preserving the alpha channel.

SVG Export: 100% fidelity via feFlood + feComposite.
"""

from typing import Tuple, Union, Dict, Any, Optional
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class ColorOverlay(LayerEffect):
    """
    Color overlay effect.

    Replaces all colors with a solid color while preserving alpha.
    The opacity controls how much of the original color shows through.

    Example:
        >>> from imagestag.layer_effects import ColorOverlay
        >>> effect = ColorOverlay(color=(255, 0, 0), opacity=1.0)
        >>> result = effect.apply(image)
    """

    effect_type = "colorOverlay"
    display_name = "Color Overlay"

    def __init__(
        self,
        color: Tuple[int, int, int] = (255, 0, 0),
        opacity: float = 1.0,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize color overlay effect.

        Args:
            color: Overlay color as (R, G, B) tuple (0-255)
            opacity: How much the overlay replaces original color (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.color = color

    def get_expansion(self) -> Expansion:
        """Color overlay doesn't expand the canvas."""
        return Expansion()

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply color overlay to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with color overlay applied
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
            result = imagestag_rust.color_overlay_rgba_f32(
                image.astype(np.float32),
                color_f32,
                float(self.opacity),
            )
        else:
            result = imagestag_rust.color_overlay_rgba(
                image.astype(np.uint8),
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
        """Color overlay has 100% fidelity via feFlood + feComposite."""
        return 100

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for color overlay.

        Uses feFlood and feComposite to overlay color with opacity.

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor (not used for color overlay as it has no dimensions)
        """
        if not self.enabled:
            return None

        color_hex = self._color_to_hex(self.color)

        # Color overlay: blend solid color over source with given opacity
        # 1. Create color flood with effect opacity
        # 2. Clip to source alpha
        # 3. Composite over source graphic
        return f'''<filter id="{filter_id}" x="0%" y="0%" width="100%" height="100%">
  <feFlood flood-color="{color_hex}" flood-opacity="{self.opacity}" result="color"/>
  <feComposite in="color" in2="SourceAlpha" operator="in" result="overlay"/>
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="overlay"/>
  </feMerge>
</filter>'''

    def to_dict(self) -> Dict[str, Any]:
        """Serialize color overlay to dict."""
        data = super().to_dict()
        data.update({
            'color': list(self.color),
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'ColorOverlay':
        """Create ColorOverlay from dict params."""
        return cls(
            color=tuple(data.get('color', [255, 0, 0])),
            **base_params,
        )

    def __repr__(self) -> str:
        return f"ColorOverlay(color={self.color}, opacity={self.opacity})"
