"""
Pattern Overlay layer effect.

Fills the layer with a repeating pattern while preserving the alpha channel.

SVG Export: 80% fidelity via embedded pattern image in SVG <pattern> element.
"""

from typing import Union, Dict, Any, Optional
import base64
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


class PatternOverlay(LayerEffect):
    """
    Pattern overlay effect.

    Fills the layer content with a tiled pattern while preserving transparency.
    The pattern is repeated (tiled) across the entire layer.

    Example:
        >>> from imagestag.layer_effects import PatternOverlay
        >>> import numpy as np
        >>> # Create a simple checkerboard pattern
        >>> pattern = np.zeros((16, 16, 4), dtype=np.uint8)
        >>> pattern[::2, ::2] = [255, 255, 255, 255]
        >>> pattern[1::2, 1::2] = [255, 255, 255, 255]
        >>> effect = PatternOverlay(pattern=pattern, scale=1.0)
        >>> result = effect.apply(image)
    """

    effect_type = "patternOverlay"
    display_name = "Pattern Overlay"

    def __init__(
        self,
        pattern: np.ndarray = None,
        scale: float = 1.0,
        offset_x: int = 0,
        offset_y: int = 0,
        opacity: float = 1.0,
        enabled: bool = True,
        blend_mode: str = "normal",
    ):
        """
        Initialize pattern overlay effect.

        Args:
            pattern: Pattern image as numpy array (H, W, 3 or 4).
                    If None, a default 2x2 checkerboard is created.
            scale: Pattern scale factor (1.0 = 100%)
            offset_x: Horizontal offset for pattern origin
            offset_y: Vertical offset for pattern origin
            opacity: Effect opacity (0.0-1.0)
            enabled: Whether the effect is active
            blend_mode: Blend mode for compositing
        """
        super().__init__(enabled=enabled, opacity=opacity, blend_mode=blend_mode)

        # Default pattern: simple 2x2 checkerboard
        if pattern is None:
            pattern = np.array([
                [[255, 255, 255, 255], [0, 0, 0, 255]],
                [[0, 0, 0, 255], [255, 255, 255, 255]],
            ], dtype=np.uint8)
        self.pattern = pattern
        self.scale = scale
        self.offset_x = offset_x
        self.offset_y = offset_y

    def get_expansion(self) -> Expansion:
        """Pattern overlay doesn't expand the canvas."""
        return Expansion()

    def _ensure_pattern_rgba(self, pattern: np.ndarray) -> np.ndarray:
        """Ensure pattern has 4 channels."""
        if pattern.ndim != 3:
            raise ValueError(f"Pattern must be 3D array, got {pattern.ndim}D")

        if pattern.shape[2] == 3:
            # Add alpha channel
            alpha = np.ones((*pattern.shape[:2], 1), dtype=pattern.dtype)
            if pattern.dtype == np.uint8:
                alpha = (alpha * 255).astype(np.uint8)
            return np.concatenate([pattern, alpha], axis=2)
        return pattern

    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply pattern overlay to image.

        Args:
            image: Input RGBA image as numpy array (H, W, 4)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with pattern overlay applied
        """
        if not self.enabled:
            return EffectResult(image=image.copy(), offset_x=0, offset_y=0)

        fmt = self._resolve_format(image, format)

        if not fmt.has_alpha:
            image = self._ensure_rgba(image)
            fmt = PixelFormat.RGBAf32 if fmt.is_float else PixelFormat.RGBA8

        if not HAS_RUST:
            raise RuntimeError("Rust extension not available.")

        # Ensure pattern is RGBA
        pattern = self._ensure_pattern_rgba(self.pattern)

        # Match pattern dtype to image
        if fmt.is_float:
            if pattern.dtype == np.uint8:
                pattern = pattern.astype(np.float32) / 255.0
            result = imagestag_rust.pattern_overlay_rgba_f32(
                image.astype(np.float32),
                pattern.astype(np.float32),
                float(self.scale),
                int(self.offset_x),
                int(self.offset_y),
                float(self.opacity),
                self.blend_mode,  # Pass blend mode to Rust
            )
        else:
            if pattern.dtype != np.uint8:
                pattern = (pattern * 255).astype(np.uint8)
            result = imagestag_rust.pattern_overlay_rgba(
                image.astype(np.uint8),
                pattern.astype(np.uint8),
                float(self.scale),
                int(self.offset_x),
                int(self.offset_y),
                float(self.opacity),
                self.blend_mode,  # Pass blend mode to Rust
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
        """Pattern overlay has 80% fidelity via embedded pattern image."""
        return 80

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter for pattern overlay.

        Returns None - pattern overlay cannot be implemented as a pure SVG filter.
        Use to_svg_defs() instead to get pattern definitions that can be applied
        via fill on the target element.
        """
        # feImage with data URLs has poor browser/resvg support
        # Pattern overlays must be implemented via SVG defs + element fills
        return None

    def to_svg_defs(self, pattern_id: str, viewbox_scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG pattern definition for use in defs section.

        The pattern can be applied to elements via fill="url(#pattern_id)".

        Args:
            pattern_id: ID for the pattern definition
            viewbox_scale: Scale factor to convert pixel dimensions to viewBox units
                          (viewBox_size / render_size). This ensures the pattern
                          appears at the same visual size regardless of viewBox.

        Returns:
            SVG pattern definition string, or None if disabled
        """
        if not self.enabled or self.pattern is None:
            return None

        # Ensure pattern is RGBA and encode as base64 PNG
        pattern = self._ensure_pattern_rgba(self.pattern)
        pattern_data_url = self._pattern_to_data_url(pattern)

        if pattern_data_url is None:
            return None

        # Calculate scaled pattern dimensions
        # Apply viewbox_scale to convert pixel dimensions to viewBox units
        pattern_h, pattern_w = pattern.shape[:2]
        scaled_w = pattern_w * self.scale * viewbox_scale
        scaled_h = pattern_h * self.scale * viewbox_scale
        scaled_offset_x = self.offset_x * viewbox_scale
        scaled_offset_y = self.offset_y * viewbox_scale

        # Use image-rendering: pixelated to prevent interpolation blur when scaling
        return (
            f'<pattern id="{pattern_id}" patternUnits="userSpaceOnUse" '
            f'width="{scaled_w}" height="{scaled_h}" x="{scaled_offset_x}" y="{scaled_offset_y}">'
            f'<image href="{pattern_data_url}" width="{scaled_w}" height="{scaled_h}" '
            f'style="image-rendering: pixelated; image-rendering: crisp-edges;"/>'
            f'</pattern>'
        )

    def _pattern_to_data_url(self, pattern: np.ndarray) -> Optional[str]:
        """Convert pattern array to base64 data URL."""
        try:
            from PIL import Image
            import io
            img = Image.fromarray(pattern)
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{b64_data}"
        except Exception:
            return None

    def to_svg_rect(self, width: int, height: int, rect_id: str = "pattern_rect") -> Optional[str]:
        """
        Generate SVG rect element filled with the pattern.

        This is an alternative to filter-based approach that directly creates
        a patterned rect that can be clipped to the source shape.

        Args:
            width: Target width
            height: Target height
            rect_id: ID for the SVG rect element

        Returns:
            SVG defs + rect elements with pattern fill, or None if disabled
        """
        if not self.enabled or self.pattern is None:
            return None

        pattern = self._ensure_pattern_rgba(self.pattern)
        pattern_data_url = self._pattern_to_data_url(pattern)

        if pattern_data_url is None:
            return None

        pattern_h, pattern_w = pattern.shape[:2]
        scaled_w = pattern_w * self.scale
        scaled_h = pattern_h * self.scale

        pattern_id = f"{rect_id}_pattern"

        return f'''<defs>
  <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{scaled_w}" height="{scaled_h}" x="{self.offset_x}" y="{self.offset_y}">
    <image href="{pattern_data_url}" width="{scaled_w}" height="{scaled_h}" preserveAspectRatio="none"/>
  </pattern>
</defs>
<rect id="{rect_id}" x="0" y="0" width="{width}" height="{height}" fill="url(#{pattern_id})" opacity="{self.opacity}"/>'''

    def to_dict(self) -> Dict[str, Any]:
        """Serialize pattern overlay to dict."""
        data = super().to_dict()
        # Encode pattern as base64 PNG for storage
        pattern_data = None
        if self.pattern is not None:
            try:
                from PIL import Image
                import io
                img = Image.fromarray(self._ensure_pattern_rgba(self.pattern))
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                pattern_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            except ImportError:
                # Fall back to raw array if PIL not available
                pattern_data = self.pattern.tolist()

        data.update({
            'pattern': pattern_data,
            'scale': self.scale,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
        })
        return data

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'PatternOverlay':
        """Create PatternOverlay from dict params."""
        pattern = None
        pattern_data = data.get('pattern')
        if pattern_data:
            if isinstance(pattern_data, str):
                # Base64 PNG
                try:
                    from PIL import Image
                    import io
                    img_data = base64.b64decode(pattern_data)
                    img = Image.open(io.BytesIO(img_data))
                    pattern = np.array(img)
                except Exception:
                    pattern = None
            elif isinstance(pattern_data, list):
                # Raw array
                pattern = np.array(pattern_data, dtype=np.uint8)

        return cls(
            pattern=pattern,
            scale=data.get('scale', 1.0),
            offset_x=data.get('offset_x', 0),
            offset_y=data.get('offset_y', 0),
            **base_params,
        )

    def __repr__(self) -> str:
        pattern_shape = self.pattern.shape if self.pattern is not None else None
        return (
            f"PatternOverlay(pattern_shape={pattern_shape}, scale={self.scale}, "
            f"offset=({self.offset_x}, {self.offset_y}), opacity={self.opacity})"
        )
