"""
Base class for all layer effects.

Layer effects are non-destructive visual effects applied to image layers. Each effect:
- Takes an input image (RGBA)
- Returns an output image (possibly with different dimensions)
- Returns the offset of the output relative to the input

Supported formats:
- RGB8: uint8 (0-255), 3 channels
- RGBA8: uint8 (0-255), 4 channels
- RGBf32: float32 (0.0-1.0), 3 channels
- RGBAf32: float32 (0.0-1.0), 4 channels
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Union
import numpy as np


class PixelFormat(Enum):
    """Pixel format for images."""
    RGB8 = "RGB8"      # uint8, 3 channels
    RGBA8 = "RGBA8"    # uint8, 4 channels
    RGBf32 = "RGBf32"  # float32, 3 channels
    RGBAf32 = "RGBAf32"  # float32, 4 channels

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "PixelFormat":
        """Detect pixel format from numpy array."""
        if arr.ndim != 3:
            raise ValueError(f"Expected 3D array, got {arr.ndim}D")

        channels = arr.shape[2]
        dtype = arr.dtype

        if dtype == np.uint8:
            return cls.RGBA8 if channels == 4 else cls.RGB8
        elif dtype == np.float32 or dtype == np.float64:
            return cls.RGBAf32 if channels == 4 else cls.RGBf32
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")

    @property
    def has_alpha(self) -> bool:
        return self in (PixelFormat.RGBA8, PixelFormat.RGBAf32)

    @property
    def is_float(self) -> bool:
        return self in (PixelFormat.RGBf32, PixelFormat.RGBAf32)


@dataclass
class Expansion:
    """How much an effect expands the canvas."""
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0


@dataclass
class EffectResult:
    """Result of applying a layer effect."""
    image: np.ndarray  # Output image (may be larger than input)
    offset_x: int = 0  # X offset of output relative to input origin
    offset_y: int = 0  # Y offset of output relative to input origin


class LayerEffect(ABC):
    """
    Base class for all layer effects.

    Subclasses must implement:
    - effect_type: Class property returning the effect type string
    - get_expansion(): Returns how much the effect expands the canvas
    - apply(): Applies the effect to an image
    """

    effect_type: str = "base"
    display_name: str = "Layer Effect"

    def __init__(self, enabled: bool = True, opacity: float = 1.0, blend_mode: str = "normal"):
        """
        Initialize effect.

        Args:
            enabled: Whether the effect is active
            opacity: Effect opacity (0.0-1.0)
            blend_mode: Blend mode for compositing
        """
        self.enabled = enabled
        self.opacity = opacity
        self.blend_mode = blend_mode

    @abstractmethod
    def get_expansion(self) -> Expansion:
        """
        Get the canvas expansion needed for this effect.

        Returns:
            Expansion object with left/top/right/bottom pixel counts
        """
        pass

    @abstractmethod
    def apply(self, image: np.ndarray, format: Union[PixelFormat, str, None] = None) -> EffectResult:
        """
        Apply the effect to an image.

        Args:
            image: Input image as numpy array (H, W, C)
            format: Pixel format (auto-detected if None)

        Returns:
            EffectResult with output image and offsets
        """
        pass

    def _ensure_rgba(self, image: np.ndarray) -> np.ndarray:
        """Convert RGB to RGBA if needed."""
        if image.shape[2] == 3:
            # Add alpha channel
            alpha = np.ones((*image.shape[:2], 1), dtype=image.dtype)
            if image.dtype == np.uint8:
                alpha = (alpha * 255).astype(np.uint8)
            return np.concatenate([image, alpha], axis=2)
        return image

    def _resolve_format(self, image: np.ndarray, format: Union[PixelFormat, str, None]) -> PixelFormat:
        """Resolve pixel format from argument or auto-detect."""
        if format is None:
            return PixelFormat.from_array(image)
        if isinstance(format, str):
            return PixelFormat(format)
        return format

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled}, opacity={self.opacity})"
