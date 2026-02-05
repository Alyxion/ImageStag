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

from typing import Tuple, Union, Dict, Any, Optional, ClassVar
import numpy as np

from pydantic import Field, model_validator

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
        >>> effect = InnerGlow(blur=10, color='#FFFF00')
        >>> result = effect.apply(image)
    """

    effect_type: ClassVar[str] = "innerGlow"
    display_name: ClassVar[str] = "Inner Glow"

    # Effect-specific fields
    blur: float = Field(default=10.0)
    color: str = Field(default='#FFFF00')  # Hex string for JS compatibility
    color_opacity: float = Field(default=0.75, alias='colorOpacity', ge=0.0, le=1.0)
    choke: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(default="edge")  # 'edge' or 'center'

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
        """Inner glow doesn't expand the canvas."""
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

        color = self.color_rgb

        # Currently only u8 version exists
        if fmt.is_float:
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.inner_glow_rgba(
                image_u8,
                float(self.blur),
                color,
                float(self.color_opacity),
                float(self.choke),
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.inner_glow_rgba(
                image.astype(np.uint8),
                float(self.blur),
                color,
                float(self.color_opacity),
                float(self.choke),
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    def apply_glow_only(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Get inner glow-only layer without the original content composited.

        Returns just the inner glow effect as a separate layer. The glow is
        clipped to the original alpha (only visible inside the shape).
        Useful for baked SVG export where the glow is rendered as a separate
        overlay layer on top of the vector content.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with ONLY the inner glow (original NOT composited)
        """
        if not self.enabled:
            h, w = image.shape[:2]
            empty = np.zeros((h, w, 4), dtype=image.dtype)
            return EffectResult(image=empty, offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        color = self.color_rgb

        # Call glow-only Rust functions
        if fmt.is_float:
            image_u8 = (image * 255).astype(np.uint8)
            result = imagestag_rust.inner_glow_only_rgba(
                image_u8,
                float(self.blur),
                color,
                float(self.color_opacity),
                float(self.choke),
            )
            result = result.astype(np.float32) / 255.0
        else:
            result = imagestag_rust.inner_glow_only_rgba(
                image.astype(np.uint8),
                float(self.blur),
                color,
                float(self.color_opacity),
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

        # Rust: choke_radius = radius * choke
        # Rust: blur_radius = radius * (1.0 - choke * 0.5)
        # Scale all pixel-based values
        # Note: SVG filter effects appear 2x larger than Rust, so halve values
        choke_radius = self.blur * self.choke * scale / 2.0
        svg_blur = self.blur * (1.0 - self.choke * 0.5) * scale / 2.0

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
  <feFlood flood-color="{self.color}" flood-opacity="{self.color_opacity}" result="color"/>
  <feComposite in="color" in2="clippedGlow" operator="in" result="glow"/>
  <!-- Screen blend over source (Rust uses screen blending for inner glow) -->
  <feBlend in="glow" in2="SourceGraphic" mode="screen" result="blended"/>
  <!-- Ensure we keep original alpha -->
  <feComposite in="blended" in2="SourceAlpha" operator="in"/>
</filter>'''

    def __repr__(self) -> str:
        return (
            f"InnerGlow(blur={self.blur}, color={self.color}, "
            f"choke={self.choke}, colorOpacity={self.color_opacity}, source={self.source})"
        )
