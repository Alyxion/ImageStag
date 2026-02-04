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

SVG Export:
- Effects can be exported to SVG filters with varying fidelity
- Use `svg_fidelity` property to check how well an effect maps to SVG (0-100%)
- Use `to_svg_filter()` to generate SVG filter definition
- Use `to_dict()`/`from_dict()` for serialization (debaking support)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Union, Optional, Dict, Any, Type
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

    Subclasses should override for SVG export:
    - svg_fidelity: Property returning SVG conversion fidelity (0-100)
    - to_svg_filter(): Returns SVG filter definition
    """

    effect_type: str = "base"
    display_name: str = "Layer Effect"

    # Registry of effect classes by effect_type
    _registry: Dict[str, Type['LayerEffect']] = {}

    def __init_subclass__(cls, **kwargs):
        """Register effect subclass in registry."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'effect_type') and cls.effect_type != "base":
            LayerEffect._registry[cls.effect_type] = cls

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

    # =========================================================================
    # SVG Export Support
    # =========================================================================

    @property
    def svg_fidelity(self) -> int:
        """
        How well this effect can be represented in SVG (0-100%).

        Returns:
            0 = No SVG equivalent
            1-69 = Poor approximation
            70-89 = Good approximation
            90-99 = Near-perfect
            100 = Exact match
        """
        return 0  # Override in subclasses

    def can_convert_to_svg(self) -> bool:
        """Check if this effect can be converted to SVG filter."""
        return self.svg_fidelity > 0

    def to_svg_filter(self, filter_id: str, scale: float = 1.0) -> Optional[str]:
        """
        Generate SVG filter definition for this effect.

        Args:
            filter_id: Unique ID for the filter element
            scale: Scale factor for converting pixel values to viewBox units.
                   Use viewBox_size / render_size when rendering the SVG
                   to a specific pixel size. Default 1.0 means values are
                   already in the target coordinate system.

        Returns:
            SVG filter element as string, or None if not supported
        """
        return None  # Override in subclasses

    # =========================================================================
    # Serialization (Debaking Support)
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize effect to dictionary for storage in SVG metadata.

        Returns:
            Dict with effect_type and all parameters
        """
        # Base properties
        data = {
            'effect_type': self.effect_type,
            'enabled': self.enabled,
            'opacity': self.opacity,
            'blend_mode': self.blend_mode,
        }
        # Add effect-specific properties (subclasses add their own)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayerEffect':
        """
        Reconstruct effect from dictionary.

        Args:
            data: Dictionary from to_dict()

        Returns:
            LayerEffect instance
        """
        effect_type = data.get('effect_type', 'base')

        # Look up the correct class
        effect_class = cls._registry.get(effect_type)
        if effect_class is None:
            raise ValueError(f"Unknown effect type: {effect_type}")

        # Extract base parameters
        base_params = {
            'enabled': data.get('enabled', True),
            'opacity': data.get('opacity', 1.0),
            'blend_mode': data.get('blend_mode', 'normal'),
        }

        # Let the subclass handle its own parameters
        return effect_class._from_dict_params(data, base_params)

    @classmethod
    def _from_dict_params(cls, data: Dict[str, Any], base_params: Dict[str, Any]) -> 'LayerEffect':
        """
        Create instance from dict params. Override in subclasses.

        Args:
            data: Full data dict
            base_params: Pre-extracted base parameters

        Returns:
            LayerEffect instance
        """
        return cls(**base_params)

    # =========================================================================
    # Utility Methods
    # =========================================================================

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

    @staticmethod
    def _color_to_hex(color: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color string."""
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled}, opacity={self.opacity})"
