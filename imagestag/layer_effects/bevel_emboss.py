"""
Bevel and Emboss layer effect.

Creates a 3D raised or sunken appearance using highlights and shadows by:
1. Extracting the alpha channel
2. Computing gradient (bump map) from alpha
3. Calculating lighting based on angle and altitude
4. Applying highlights and shadows

SVG Export: ~70% fidelity (approximation).

NOTE: SVG cannot achieve 100% parity with the Rust implementation because:
- Rust computes a proper gradient/bump map from the alpha channel
- Rust calculates precise lighting based on the light direction (angle/altitude)
- SVG's feSpecularLighting and feDiffuseLighting produce fundamentally different results
- The SVG approximation uses edge detection with offset highlights/shadows instead

This is a visual approximation that captures the general "bevel" look but will not
match the Rust output pixel-for-pixel. For 100% fidelity, render via Rust.
"""

from typing import Tuple, Union, Dict, Any, Optional, ClassVar
import math
import numpy as np

from pydantic import Field, model_validator

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class BevelStyle:
    """Bevel and emboss style options."""
    # JS-compatible camelCase values
    OUTER_BEVEL = "outerBevel"
    INNER_BEVEL = "innerBevel"
    EMBOSS = "emboss"
    PILLOW_EMBOSS = "pillowEmboss"

    # Style conversion: Python snake_case to JS camelCase
    _TO_JS = {
        "outer_bevel": "outerBevel",
        "inner_bevel": "innerBevel",
        "pillow_emboss": "pillowEmboss",
    }
    _FROM_JS = {v: k for k, v in _TO_JS.items()}

    @classmethod
    def to_js(cls, style: str) -> str:
        """Convert Python style to JS format."""
        return cls._TO_JS.get(style, style)

    @classmethod
    def from_js(cls, style: str) -> str:
        """Convert JS style to Python format (for Rust API)."""
        return cls._FROM_JS.get(style, style)


class BevelEmboss(LayerEffect):
    """
    Bevel and emboss effect.

    Creates a 3D raised or sunken appearance using highlights and shadows.

    Example:
        >>> from imagestag.layer_effects import BevelEmboss
        >>> effect = BevelEmboss(depth=5, angle=120, style="innerBevel")
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "bevelEmboss"
    display_name: ClassVar[str] = "Bevel & Emboss"

    # Effect-specific fields
    style: str = Field(default="innerBevel")
    depth: float = Field(default=3.0)
    direction: str = Field(default="up")  # 'up' or 'down'
    size: float = Field(default=5.0)
    soften: float = Field(default=0.0, ge=0.0, le=1.0)
    angle: float = Field(default=120.0)
    altitude: float = Field(default=30.0)
    highlight_color: str = Field(default='#FFFFFF', alias='highlightColor')
    highlight_opacity: float = Field(default=0.75, alias='highlightOpacity', ge=0.0, le=1.0)
    shadow_color: str = Field(default='#000000', alias='shadowColor')
    shadow_opacity: float = Field(default=0.75, alias='shadowOpacity', ge=0.0, le=1.0)

    # Internal: parsed RGB tuples (not serialized)
    _highlight_rgb: Optional[Tuple[int, int, int]] = None
    _shadow_rgb: Optional[Tuple[int, int, int]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Convert color formats and handle legacy parameters."""
        if isinstance(data, dict):
            # Convert RGB tuple/list to hex string for highlight
            for key in ['highlightColor', 'highlight_color']:
                if key in data:
                    color = data[key]
                    if isinstance(color, (list, tuple)):
                        r, g, b = color[:3]
                        data[key] = f'#{int(r):02X}{int(g):02X}{int(b):02X}'

            # Convert RGB tuple/list to hex string for shadow
            for key in ['shadowColor', 'shadow_color']:
                if key in data:
                    color = data[key]
                    if isinstance(color, (list, tuple)):
                        r, g, b = color[:3]
                        data[key] = f'#{int(r):02X}{int(g):02X}{int(b):02X}'

            # Handle legacy snake_case color keys
            if 'highlight_color' in data and 'highlightColor' not in data:
                data['highlightColor'] = data.pop('highlight_color')
            if 'shadow_color' in data and 'shadowColor' not in data:
                data['shadowColor'] = data.pop('shadow_color')
            if 'highlight_opacity' in data and 'highlightOpacity' not in data:
                data['highlightOpacity'] = data.pop('highlight_opacity')
            if 'shadow_opacity' in data and 'shadowOpacity' not in data:
                data['shadowOpacity'] = data.pop('shadow_opacity')

            # Convert legacy snake_case style to JS camelCase
            if 'style' in data:
                data['style'] = BevelStyle.to_js(data['style'])
        return data

    def model_post_init(self, __context: Any) -> None:
        """Parse colors after initialization."""
        super().model_post_init(__context)
        self._highlight_rgb = self._hex_to_rgb(self.highlight_color)
        self._shadow_rgb = self._hex_to_rgb(self.shadow_color)

    @staticmethod
    def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        """Convert hex color string to RGB tuple."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) != 6:
            return (128, 128, 128)
        return (
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            int(hex_str[4:6], 16),
        )

    @property
    def highlight_rgb(self) -> Tuple[int, int, int]:
        """Get highlight color as RGB tuple (0-255)."""
        if self._highlight_rgb is None:
            self._highlight_rgb = self._hex_to_rgb(self.highlight_color)
        return self._highlight_rgb

    @property
    def shadow_rgb(self) -> Tuple[int, int, int]:
        """Get shadow color as RGB tuple (0-255)."""
        if self._shadow_rgb is None:
            self._shadow_rgb = self._hex_to_rgb(self.shadow_color)
        return self._shadow_rgb

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for outer bevel."""
        if self.style == BevelStyle.OUTER_BEVEL or self.style == "outer_bevel":
            expand = int(self.size) + 2
            return Expansion(left=expand, top=expand, right=expand, bottom=expand)
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
        Apply bevel and emboss to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with beveled/embossed image
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        # Convert JS-style camelCase to snake_case for Rust API
        rust_style = BevelStyle.from_js(self.style)

        highlight = self.highlight_rgb
        shadow = self.shadow_rgb

        # Currently only u8 version exists
        if fmt.is_float:
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.bevel_emboss_rgba(
                image_u8,
                float(self.depth),
                float(self.angle),
                float(self.altitude),
                highlight,
                float(self.highlight_opacity),
                shadow,
                float(self.shadow_opacity),
                rust_style,
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.bevel_emboss_rgba(
                image.astype(np.uint8),
                float(self.depth),
                float(self.angle),
                float(self.altitude),
                highlight,
                float(self.highlight_opacity),
                shadow,
                float(self.shadow_opacity),
                rust_style,
            )

        # Handle expansion for outer bevel
        expansion = self.get_expansion()
        offset = -expansion.left if expansion.left > 0 else 0

        return EffectResult(
            image=result,
            offset_x=offset,
            offset_y=offset,
        )

    # =========================================================================
    # SVG Export
    # =========================================================================

    @property
    def svg_fidelity(self) -> int:
        """Bevel/emboss has 70% fidelity (approximation via SVG lighting)."""
        return 70

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for bevel/emboss.

        This is a visual approximation (~70% fidelity) using edge detection and
        offset highlights/shadows. SVG's feSpecularLighting produces fundamentally
        different results than the Rust gradient-based lighting algorithm, so we
        use a simpler approach that captures the general "bevel" look.

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor for viewBox units (viewBox_size / render_size)
        """
        if not self.enabled:
            return None

        # Scale all pixel-based values
        # Note: SVG feMorphology produces ~2x visual effect, and the edge-based
        # approach is inherently different from Rust's gradient-based lighting,
        # so we use more aggressive scaling to produce a subtler effect
        scaled_depth = self.depth * scale / 4.0
        edge_width = max(0.25, scaled_depth)
        blur_std = scaled_depth * 0.5

        # Convert angle to offset direction (scaled)
        angle_rad = math.radians(self.angle)
        dx = math.cos(angle_rad) * scaled_depth * 0.5
        dy = -math.sin(angle_rad) * scaled_depth * 0.5

        # primitiveUnits="userSpaceOnUse" ensures values are in viewBox units
        # Highlight appears on edges facing the light, shadow on edges facing away
        # Offsetting edge by light direction then masking gives the opposite-facing edge
        return f'''<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%" primitiveUnits="userSpaceOnUse">
  <!-- Extract edge by eroding and subtracting -->
  <feMorphology operator="erode" radius="{edge_width:.2f}" in="SourceAlpha" result="eroded"/>
  <feComposite in="SourceAlpha" in2="eroded" operator="out" result="edge"/>
  <feGaussianBlur in="edge" stdDeviation="{blur_std:.2f}" result="edgeBlur"/>

  <!-- Create highlight (light-facing edge) - offset opposite to light direction -->
  <feOffset dx="{-dx:.2f}" dy="{-dy:.2f}" in="edgeBlur" result="highlightOffset"/>
  <feComposite in="highlightOffset" in2="SourceAlpha" operator="in" result="highlightMask"/>
  <feFlood flood-color="{self.highlight_color}" flood-opacity="{self.highlight_opacity}" result="highlightColor"/>
  <feComposite in="highlightColor" in2="highlightMask" operator="in" result="highlight"/>

  <!-- Create shadow (opposite edge) - offset in light direction -->
  <feOffset dx="{dx:.2f}" dy="{dy:.2f}" in="edgeBlur" result="shadowOffset"/>
  <feComposite in="shadowOffset" in2="SourceAlpha" operator="in" result="shadowMask"/>
  <feFlood flood-color="{self.shadow_color}" flood-opacity="{self.shadow_opacity}" result="shadowColor"/>
  <feComposite in="shadowColor" in2="shadowMask" operator="in" result="shadow"/>

  <!-- Combine: source + highlight + shadow -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="shadow"/>
    <feMergeNode in="highlight"/>
  </feMerge>
</filter>'''

    def __repr__(self) -> str:
        return (
            f"BevelEmboss(style={self.style}, depth={self.depth}, "
            f"size={self.size}, angle={self.angle})"
        )
