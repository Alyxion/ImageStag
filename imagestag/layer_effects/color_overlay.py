"""
Color Overlay layer effect.

Overlays a solid color on the layer content, preserving the alpha channel.

SVG Export: 100% fidelity via feFlood + feComposite.
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


class ColorOverlay(LayerEffect):
    """
    Color overlay effect.

    Replaces all colors with a solid color while preserving alpha.
    The opacity controls how much of the original color shows through.

    Example:
        >>> from imagestag.layer_effects import ColorOverlay
        >>> effect = ColorOverlay(color='#FF0000', opacity=1.0)
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "colorOverlay"
    display_name: ClassVar[str] = "Color Overlay"

    # Effect-specific fields
    color: str = Field(default='#FF0000')  # Hex string for JS compatibility

    # Internal: parsed RGB tuple (not serialized)
    _color_rgb: Optional[Tuple[int, int, int]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_color(cls, data: Any) -> Any:
        """Convert color formats."""
        if isinstance(data, dict):
            # Convert RGB tuple/list to hex string
            color = data.get('color', '#FF0000')
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
            return (255, 0, 0)
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
        """Color overlay doesn't expand the canvas."""
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

        color = self.color_rgb

        if fmt.is_float:
            color_f32 = (
                color[0] / 255.0,
                color[1] / 255.0,
                color[2] / 255.0,
            )
            result = imagestag_rust.color_overlay_rgba_f32(
                image.astype(np.float32),
                color_f32,
                float(self.opacity),
            )
        else:
            result = imagestag_rust.color_overlay_rgba(
                image.astype(np.uint8),
                color,
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

        # Color overlay: blend solid color over source with given opacity
        # 1. Create color flood with effect opacity
        # 2. Clip to source alpha
        # 3. Composite over source graphic
        return f'''<filter id="{filter_id}" x="0%" y="0%" width="100%" height="100%">
  <feFlood flood-color="{self.color}" flood-opacity="{self.opacity}" result="color"/>
  <feComposite in="color" in2="SourceAlpha" operator="in" result="overlay"/>
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="overlay"/>
  </feMerge>
</filter>'''

    def __repr__(self) -> str:
        return f"ColorOverlay(color={self.color}, opacity={self.opacity})"
