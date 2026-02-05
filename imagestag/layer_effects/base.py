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

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Union, Optional, Dict, Any, Type, ClassVar
import uuid
import numpy as np

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class LayerEffect(BaseModel):
    """
    Base class for all layer effects.

    Uses Pydantic for serialization with camelCase aliases matching JS format.

    Subclasses must implement:
    - effect_type: Class variable with the effect type string
    - get_expansion(): Returns how much the effect expands the canvas
    - apply(): Applies the effect to an image

    Subclasses should override for SVG export:
    - svg_fidelity: Property returning SVG conversion fidelity (0-100)
    - to_svg_filter(): Returns SVG filter definition
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=False,
        extra='ignore',
        arbitrary_types_allowed=True,
    )

    # Class variables (not serialized)
    effect_type: ClassVar[str] = "base"
    display_name: ClassVar[str] = "Layer Effect"
    VERSION: ClassVar[int] = 1

    # Registry of effect classes by effect_type
    _registry: ClassVar[Dict[str, Type['LayerEffect']]] = {}

    # Instance fields with JS-compatible aliases
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    enabled: bool = Field(default=True)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    blend_mode: str = Field(default='normal', alias='blendMode')

    # Serialization metadata
    version: int = Field(default=1, alias='_version')
    type_name: str = Field(default='LayerEffect', alias='_type')

    def __init_subclass__(cls, **kwargs):
        """Register effect subclass in registry."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'effect_type') and cls.effect_type != "base":
            LayerEffect._registry[cls.effect_type] = cls

    def model_post_init(self, __context: Any) -> None:
        """Set type_name after initialization."""
        self.type_name = 'LayerEffect'

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
    # Serialization (JS-Compatible Format)
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize effect to dictionary matching JS LayerEffect.serialize() format.

        Output format matches JS exactly for SFR file interoperability:
        - _version: Serialization version for migration
        - _type: Class name for debugging
        - id: Unique identifier
        - type: Effect type string (e.g., 'dropShadow')
        - enabled, blendMode, opacity: Base properties (camelCase)
        - ...effect-specific params (camelCase)

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.VERSION
        data = self.model_dump(by_alias=True, mode='json')
        # Add effect type (not a field, it's a class variable)
        data['type'] = self.effect_type
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayerEffect':
        """
        Reconstruct effect from dictionary.

        Accepts both JS format (from SFR files) and legacy Python format:
        - JS format: type, blendMode, id, _version, _type
        - Legacy format: effect_type, blend_mode

        Args:
            data: Dictionary from to_dict() or JS serialize()

        Returns:
            LayerEffect instance
        """
        # Handle both 'type' (JS) and 'effect_type' (legacy Python)
        effect_type = data.get('type') or data.get('effect_type', 'base')

        # Look up the correct class
        effect_class = cls._registry.get(effect_type)
        if effect_class is None:
            raise ValueError(f"Unknown effect type: {effect_type}")

        # Handle legacy snake_case keys by converting to camelCase
        if 'blend_mode' in data and 'blendMode' not in data:
            data['blendMode'] = data.pop('blend_mode')

        return effect_class.model_validate(data)

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
        """Convert RGB tuple (0-255) to hex color string (#RRGGBB)."""
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    @staticmethod
    def _hex_to_color(hex_str: str) -> Tuple[int, int, int]:
        """Convert hex color string (#RRGGBB or RRGGBB) to RGB tuple (0-255)."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) != 6:
            raise ValueError(f"Invalid hex color: {hex_str}")
        return (
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            int(hex_str[4:6], 16),
        )

    @staticmethod
    def _parse_color(color: Any) -> Tuple[int, int, int]:
        """
        Parse color from various formats to RGB tuple.

        Accepts:
        - RGB tuple/list: (255, 0, 0) or [255, 0, 0]
        - Hex string: '#FF0000' or 'FF0000'

        Returns:
            RGB tuple (0-255)
        """
        if isinstance(color, str):
            return LayerEffect._hex_to_color(color)
        elif isinstance(color, (list, tuple)):
            return tuple(color[:3])
        else:
            raise ValueError(f"Invalid color format: {color}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled}, opacity={self.opacity})"
