"""
Drop Shadow layer effect.

Creates a shadow behind the layer content by:
1. Extracting the alpha channel
2. Blurring it with Gaussian kernel
3. Offsetting the shadow
4. Colorizing with shadow color
5. Compositing original on top

SVG Export: 100% fidelity via native <feDropShadow> element.
"""

from typing import Tuple, Union, Dict, Any, Optional, ClassVar
import numpy as np

from pydantic import Field, model_validator

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

# Import Rust implementation
try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class DropShadow(LayerEffect):
    """
    Drop shadow effect.

    Creates a shadow cast by the layer content, offset and blurred.

    Example:
        >>> from imagestag.layer_effects import DropShadow
        >>> effect = DropShadow(blur=5, offset_x=10, offset_y=10, color='#000000')
        >>> result = effect.apply(image)
        >>> output_image = result.image
        >>> offset_x, offset_y = result.offset_x, result.offset_y
    """

    effect_type: ClassVar[str] = "dropShadow"
    display_name: ClassVar[str] = "Drop Shadow"

    # Effect-specific fields with JS-compatible aliases
    blur: float = Field(default=5.0)
    offset_x: float = Field(default=4.0, alias='offsetX')
    offset_y: float = Field(default=4.0, alias='offsetY')
    color: str = Field(default='#000000')  # Hex string for JS compatibility
    color_opacity: float = Field(default=0.75, alias='colorOpacity', ge=0.0, le=1.0)
    spread: float = Field(default=0.0)

    # Internal: parsed RGB tuple (not serialized)
    _color_rgb: Optional[Tuple[int, int, int]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_color(cls, data: Any) -> Any:
        """Convert color formats and handle legacy parameters."""
        if isinstance(data, dict):
            # Handle legacy 'opacity' parameter for color_opacity
            if 'opacity' in data and 'colorOpacity' not in data and 'color_opacity' not in data:
                # Only use opacity for color_opacity if it looks like a shadow opacity
                opacity_val = data.get('opacity', 1.0)
                if opacity_val != 1.0:
                    data['colorOpacity'] = opacity_val
                    data['opacity'] = 1.0  # Base effect opacity stays 1.0

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
        """Calculate expansion needed for the shadow."""
        # Blur expands by ~3 sigma in each direction
        blur_expand = int(self.blur * 3) + 2 + abs(int(self.spread))

        # Account for offset
        left = blur_expand + max(0, -int(self.offset_x))
        right = blur_expand + max(0, int(self.offset_x))
        top = blur_expand + max(0, -int(self.offset_y))
        bottom = blur_expand + max(0, int(self.offset_y))

        return Expansion(left=left, top=top, right=right, bottom=bottom)

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
        Apply drop shadow to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with shadowed image and offset
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        # Ensure RGBA
        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        # Calculate expansion
        expansion = self.get_expansion()
        expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available. Install imagestag with Rust support.")

        color = self.color_rgb

        # Call appropriate Rust function based on format
        if fmt.is_float:
            # Normalize color to 0.0-1.0 for f32
            color_f32 = (
                color[0] / 255.0,
                color[1] / 255.0,
                color[2] / 255.0,
            )
            result = imagestag_rust.drop_shadow_rgba_f32(
                image.astype(np.float32),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                color_f32,
                float(self.color_opacity),
                expand,
            )
        else:
            result = imagestag_rust.drop_shadow_rgba(
                image.astype(np.uint8),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                color,
                float(self.color_opacity),
                expand,
            )

        # The result is expanded, offset is negative of expansion
        return EffectResult(
            image=result,
            offset_x=-expand,
            offset_y=-expand,
        )

    def apply_shadow_only(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Get shadow-only layer without compositing the original image.

        Returns the FULL shadow area (including what would be "under" the original
        shape). Useful for baked SVG export where the shadow is rendered as a
        separate layer underneath vector content.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with ONLY the shadow (original NOT composited on top)
        """
        if not self.enabled:
            # Return transparent image with same dimensions
            expansion = self.get_expansion()
            expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)
            h, w = image.shape[:2]
            new_h, new_w = h + 2 * expand, w + 2 * expand
            empty = np.zeros((new_h, new_w, 4), dtype=image.dtype)
            return EffectResult(image=empty, offset_x=-expand, offset_y=-expand)

        fmt = self._resolve_format(image, format)

        # Ensure RGBA
        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        # Calculate expansion
        expansion = self.get_expansion()
        expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available. Install imagestag with Rust support.")

        color = self.color_rgb

        # Call shadow-only Rust functions
        if fmt.is_float:
            color_f32 = (
                color[0] / 255.0,
                color[1] / 255.0,
                color[2] / 255.0,
            )
            result = imagestag_rust.drop_shadow_only_rgba_f32(
                image.astype(np.float32),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                color_f32,
                float(self.color_opacity),
                expand,
            )
        else:
            result = imagestag_rust.drop_shadow_only_rgba(
                image.astype(np.uint8),
                float(self.offset_x),
                float(self.offset_y),
                float(self.blur),
                color,
                float(self.color_opacity),
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
        """Drop shadow has 100% SVG fidelity via native <feDropShadow>."""
        return 100

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for drop shadow.

        Uses native <feDropShadow> element.
        SVG stdDeviation is sigma (standard deviation) which matches Rust's blur_radius directly.

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor for viewBox units (viewBox_size / render_size)
        """
        if not self.enabled:
            return None

        # Scale all pixel-based values for viewBox coordinate system
        svg_blur = self.blur * scale
        svg_offset_x = self.offset_x * scale
        svg_offset_y = self.offset_y * scale

        # primitiveUnits="userSpaceOnUse" ensures values are in viewBox units
        return f'''<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%" primitiveUnits="userSpaceOnUse">
  <feDropShadow dx="{svg_offset_x:.2f}" dy="{svg_offset_y:.2f}" stdDeviation="{svg_blur:.2f}" flood-color="{self.color}" flood-opacity="{self.color_opacity}"/>
</filter>'''

    def __repr__(self) -> str:
        return (
            f"DropShadow(blur={self.blur}, offset=({self.offset_x}, {self.offset_y}), "
            f"spread={self.spread}, color={self.color}, colorOpacity={self.color_opacity})"
        )
