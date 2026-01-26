"""
Pattern Overlay layer effect.

Fills the layer with a repeating pattern while preserving the alpha channel.
"""

from typing import Union
import numpy as np

from .base import LayerEffect, PixelFormat, Expansion, EffectResult

try:
    from imagestag import imagestag_rust
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
            )

        return EffectResult(
            image=result,
            offset_x=0,
            offset_y=0,
        )

    def __repr__(self) -> str:
        pattern_shape = self.pattern.shape if self.pattern is not None else None
        return (
            f"PatternOverlay(pattern_shape={pattern_shape}, scale={self.scale}, "
            f"offset=({self.offset_x}, {self.offset_y}), opacity={self.opacity})"
        )
