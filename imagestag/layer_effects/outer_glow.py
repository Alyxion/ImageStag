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

from typing import Tuple, Union, Dict, Any, Optional, ClassVar
import numpy as np

from pydantic import Field, model_validator

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
        >>> effect = OuterGlow(blur=15, color='#FFFF00')
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "outerGlow"
    display_name: ClassVar[str] = "Outer Glow"

    # Effect-specific fields
    blur: float = Field(default=10.0)
    color: str = Field(default='#FFFF00')  # Hex string for JS compatibility
    color_opacity: float = Field(default=0.75, alias='colorOpacity', ge=0.0, le=1.0)
    spread: float = Field(default=0.0)

    # Internal: parsed RGB tuple (not serialized)
    _color_rgb: Optional[Tuple[int, int, int]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Convert color formats and handle legacy parameters."""
        if isinstance(data, dict):
            # Handle legacy 'radius' parameter for blur
            if 'radius' in data and 'blur' not in data:
                data['blur'] = data.pop('radius')

            # Handle legacy 'opacity' parameter for color_opacity
            if 'opacity' in data and 'colorOpacity' not in data and 'color_opacity' not in data:
                opacity_val = data.get('opacity', 1.0)
                if opacity_val != 1.0:
                    data['colorOpacity'] = opacity_val
                    data['opacity'] = 1.0

            # Convert RGB tuple/list to hex string
            color = data.get('color', '#FFFF00')
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
            return (255, 255, 0)
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

    # Legacy property for backwards compatibility
    @property
    def radius(self) -> float:
        return self.blur

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for the glow."""
        expand = int(self.blur * 3) + 2 + abs(int(self.spread))
        return Expansion(left=expand, top=expand, right=expand, bottom=expand)

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

        color = self.color_rgb

        # Currently only u8 version exists
        if fmt.is_float:
            # Convert to u8, apply, convert back
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.outer_glow_rgba(
                image_u8,
                float(self.blur),
                color,
                float(self.color_opacity),
                float(self.spread),
                expand,
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.outer_glow_rgba(
                image.astype(np.uint8),
                float(self.blur),
                color,
                float(self.color_opacity),
                float(self.spread),
                expand,
            )

        return EffectResult(
            image=result,
            offset_x=-expand,
            offset_y=-expand,
        )

    def apply_glow_only(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Get glow-only layer without compositing the original image.

        Returns the FULL glow area (including what would be "under" the original
        shape). Unlike the regular apply() which subtracts the original alpha,
        this returns the complete glow. Useful for baked SVG export where the
        glow is rendered as a separate layer underneath vector content.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with ONLY the glow (original NOT composited on top)
        """
        if not self.enabled:
            expansion = self.get_expansion()
            expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)
            h, w = image.shape[:2]
            new_h, new_w = h + 2 * expand, w + 2 * expand
            empty = np.zeros((new_h, new_w, 4), dtype=image.dtype)
            return EffectResult(image=empty, offset_x=-expand, offset_y=-expand)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        expansion = self.get_expansion()
        expand = max(expansion.left, expansion.right, expansion.top, expansion.bottom)

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        color = self.color_rgb

        # Call glow-only Rust functions
        if fmt.is_float:
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.outer_glow_only_rgba(
                image_u8,
                float(self.blur),
                color,
                float(self.color_opacity),
                float(self.spread),
                expand,
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.outer_glow_only_rgba(
                image.astype(np.uint8),
                float(self.blur),
                color,
                float(self.color_opacity),
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

        # Scale pixel-based values
        svg_blur = self.blur * scale

        # Build spread element if needed
        spread_elem = ""
        blur_input = "SourceAlpha"
        if self.spread > 0:
            spread_radius = self.spread * scale
            spread_elem = f'  <feMorphology operator="dilate" radius="{spread_radius:.2f}" in="SourceAlpha" result="spread"/>\n'
            blur_input = "spread"

        # primitiveUnits="userSpaceOnUse" ensures values are in viewBox units
        return f'''<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%" primitiveUnits="userSpaceOnUse">
{spread_elem}  <feGaussianBlur stdDeviation="{svg_blur:.2f}" in="{blur_input}" result="blurred"/>
  <!-- Subtract original alpha from blurred to get outer-only glow -->
  <feComposite in="blurred" in2="SourceAlpha" operator="out" result="outerOnly"/>
  <feFlood flood-color="{self.color}" flood-opacity="{self.color_opacity}" result="color"/>
  <feComposite in="color" in2="outerOnly" operator="in" result="glow"/>
  <feMerge>
    <feMergeNode in="glow"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>'''

    def __repr__(self) -> str:
        return (
            f"OuterGlow(blur={self.blur}, color={self.color}, "
            f"spread={self.spread}, colorOpacity={self.color_opacity})"
        )
