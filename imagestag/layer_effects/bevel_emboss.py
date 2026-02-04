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

from typing import Tuple, Union, Dict, Any, Optional
import math
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class BevelStyle:
    """Bevel and emboss style options."""
    OUTER_BEVEL = "outer_bevel"
    INNER_BEVEL = "inner_bevel"
    EMBOSS = "emboss"
    PILLOW_EMBOSS = "pillow_emboss"


class BevelEmboss(LayerEffect):
    """
    Bevel and emboss effect.

    Creates a 3D raised or sunken appearance using highlights and shadows.

    Example:
        >>> from imagestag.layer_effects import BevelEmboss
        >>> effect = BevelEmboss(depth=5, angle=120, style="inner_bevel")
        >>> result = effect.apply(image)
    """

    effect_type = "bevelEmboss"
    display_name = "Bevel & Emboss"

    def __init__(
        self,
        depth: float = 3.0,
        angle: float = 120.0,
        altitude: float = 30.0,
        highlight_color: Tuple[int, int, int] = (255, 255, 255),
        highlight_opacity: float = 0.75,
        shadow_color: Tuple[int, int, int] = (0, 0, 0),
        shadow_opacity: float = 0.75,
        style: str = "inner_bevel",
        enabled: bool = True,
        opacity: float = 1.0,
        blend_mode: str = "normal",
    ):
        """
        Initialize bevel and emboss effect.

        Args:
            depth: Depth of the bevel effect in pixels
            angle: Light source angle in degrees (0 = right, 90 = top)
            altitude: Light altitude in degrees (0-90)
            highlight_color: Highlight color as (R, G, B) tuple
            highlight_opacity: Highlight opacity (0.0-1.0)
            shadow_color: Shadow color as (R, G, B) tuple
            shadow_opacity: Shadow opacity (0.0-1.0)
            style: Bevel style ("outer_bevel", "inner_bevel", "emboss", "pillow_emboss")
            enabled: Whether the effect is active
            opacity: Effect opacity (0.0-1.0)
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)
        self.depth = depth
        self.angle = angle
        self.altitude = altitude
        self.highlight_color = highlight_color
        self.highlight_opacity = highlight_opacity
        self.shadow_color = shadow_color
        self.shadow_opacity = shadow_opacity
        self.style = style

    def get_expansion(self) -> Expansion:
        """Calculate expansion needed for outer bevel."""
        if self.style == BevelStyle.OUTER_BEVEL:
            expand = int(self.depth) + 2
            return Expansion(left=expand, top=expand, right=expand, bottom=expand)
        return Expansion()

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

        # Currently only u8 version exists
        if fmt.is_float:
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.bevel_emboss_rgba(
                image_u8,
                float(self.depth),
                float(self.angle),
                float(self.altitude),
                self.highlight_color,
                float(self.highlight_opacity),
                self.shadow_color,
                float(self.shadow_opacity),
                self.style,
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.bevel_emboss_rgba(
                image.astype(np.uint8),
                float(self.depth),
                float(self.angle),
                float(self.altitude),
                self.highlight_color,
                float(self.highlight_opacity),
                self.shadow_color,
                float(self.shadow_opacity),
                self.style,
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

        highlight_hex = self._color_to_hex(self.highlight_color)
        shadow_hex = self._color_to_hex(self.shadow_color)

        # Scale all pixel-based values
        # Note: SVG feMorphology produces ~2x visual effect, and the edge-based
        # approach is inherently different from Rust's gradient-based lighting,
        # so we use more aggressive scaling to produce a subtler effect
        scaled_depth = self.depth * scale / 4.0
        edge_width = max(0.25, scaled_depth)
        blur_std = scaled_depth * 0.5

        # Convert angle to offset direction (scaled)
        import math
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
  <feFlood flood-color="{highlight_hex}" flood-opacity="{self.highlight_opacity}" result="highlightColor"/>
  <feComposite in="highlightColor" in2="highlightMask" operator="in" result="highlight"/>

  <!-- Create shadow (opposite edge) - offset in light direction -->
  <feOffset dx="{dx:.2f}" dy="{dy:.2f}" in="edgeBlur" result="shadowOffset"/>
  <feComposite in="shadowOffset" in2="SourceAlpha" operator="in" result="shadowMask"/>
  <feFlood flood-color="{shadow_hex}" flood-opacity="{self.shadow_opacity}" result="shadowColor"/>
  <feComposite in="shadowColor" in2="shadowMask" operator="in" result="shadow"/>

  <!-- Combine: source + highlight + shadow -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="shadow"/>
    <feMergeNode in="highlight"/>
  </feMerge>
</filter>'''

    def to_dict(self) -> Dict[str, Any]:
        """Serialize bevel/emboss to dict."""
        data = super().to_dict()
        data.update({
            'depth': self.depth,
            'angle': self.angle,
            'altitude': self.altitude,
            'highlight_color': list(self.highlight_color),
            'highlight_opacity': self.highlight_opacity,
            'shadow_color': list(self.shadow_color),
            'shadow_opacity': self.shadow_opacity,
            'style': self.style,
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'BevelEmboss':
        """Create BevelEmboss from dict params."""
        return cls(
            depth=data.get('depth', 3.0),
            angle=data.get('angle', 120.0),
            altitude=data.get('altitude', 30.0),
            highlight_color=tuple(data.get('highlight_color', [255, 255, 255])),
            highlight_opacity=data.get('highlight_opacity', 0.75),
            shadow_color=tuple(data.get('shadow_color', [0, 0, 0])),
            shadow_opacity=data.get('shadow_opacity', 0.75),
            style=data.get('style', 'inner_bevel'),
            **base_params,
        )

    def __repr__(self) -> str:
        return (
            f"BevelEmboss(depth={self.depth}, angle={self.angle}, "
            f"style={self.style})"
        )
