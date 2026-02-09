# ImageStag Filters - Image Generator
"""
ImageGenerator filter for creating gradient images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, TYPE_CHECKING

import numpy as np

from .base import Filter, FilterContext, register_filter
from imagestag.pixel_format import PixelFormat
from imagestag.definitions import ImsFramework
from imagestag.color import Color, Colors

if TYPE_CHECKING:
    from imagestag import Image


class GradientType(Enum):
    """Type of gradient to generate."""
    SOLID = "solid"    # Single solid color (uses start color)
    LINEAR = "linear"  # Linear gradient at specified angle
    RADIAL = "radial"  # Radial gradient from center


@register_filter
@dataclass
class ImageGenerator(Filter):
    """Generate gradient images for masks and effects.

    Creates linear or radial gradients that can be used as blend masks.
    Can take dimensions from an input image or use specified width/height.

    .. deprecated::
        For multi-stop gradients with advanced control (5 styles, separate
        scale X/Y, offset X/Y), use :class:`~imagestag.filters.gradient_generator.GradientGenerator`
        which uses the Rust backend for better performance.

    Parameters:
        gradient_type: "solid", "linear", or "radial"
        angle: Degrees for linear gradient (0=left-to-right, 90=top-to-bottom)
        color_start: Start color as hex string (e.g., "#000000")
        color_end: End color as hex string (e.g., "#FFFFFF")
        format: "gray", "rgb", or "rgba"
        width, height: Dimensions when no input image provided
        cx, cy: Center point for radial gradient (0-1)
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    # Positional parameter (obvious)
    gradient_type: str = "linear"  # solid, linear, radial

    # Keyword-only parameters
    angle: float = 0.0  # Degrees for linear gradient

    # Colors using Color class
    color_start: Color = field(default_factory=lambda: Colors.BLACK)
    color_end: Color = field(default_factory=lambda: Colors.WHITE)

    format: str = "gray"   # gray, rgb, rgba (was: output_format)
    width: int = 512
    height: int = 512

    # Radial gradient center (0-1 relative position)
    cx: float = 0.5  # (was: center_x)
    cy: float = 0.5  # (was: center_y)

    def __post_init__(self):
        """Ensure color parameters are Color objects."""
        if not isinstance(self.color_start, Color):
            self.color_start = Color(self.color_start)
        if not isinstance(self.color_end, Color):
            self.color_end = Color(self.color_end)

    def _get_gradient_type(self) -> GradientType:
        """Convert string to GradientType enum."""
        if isinstance(self.gradient_type, GradientType):
            return self.gradient_type
        return GradientType(self.gradient_type.lower())

    def _get_output_format(self) -> PixelFormat:
        """Convert string to PixelFormat enum."""
        if isinstance(self.format, PixelFormat):
            return self.format
        return PixelFormat[self.format.upper()]

    def _get_color_start_tuple(self) -> tuple[int, ...]:
        """Get start color as int tuple."""
        fmt = self._get_output_format()
        rgb = self.color_start.to_int_rgb()
        if fmt == PixelFormat.GRAY:
            return (int(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]),)
        elif fmt == PixelFormat.RGBA:
            return (*rgb, int(self.color_start.a * 255))
        return rgb

    def _get_color_end_tuple(self) -> tuple[int, ...]:
        """Get end color as int tuple."""
        fmt = self._get_output_format()
        rgb = self.color_end.to_int_rgb()
        if fmt == PixelFormat.GRAY:
            return (int(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]),)
        elif fmt == PixelFormat.RGBA:
            return (*rgb, int(self.color_end.a * 255))
        return rgb

    def apply(self, image: Image | None = None, context: FilterContext | None = None) -> Image:
        """Generate gradient image.

        :param image: Optional input image to get dimensions from
        :param context: Filter context (unused)
        :returns: Generated gradient image
        """
        # Get dimensions
        if image is not None:
            w, h = image.width, image.height
        else:
            w, h = self.width, self.height

        grad_type = self._get_gradient_type()
        out_fmt = self._get_output_format()

        # Generate based on type
        if grad_type == GradientType.SOLID:
            result = self._generate_solid(w, h)
        elif grad_type == GradientType.LINEAR:
            t = self._generate_linear_t(w, h)
            result = self._interpolate_colors(t)
        else:  # RADIAL
            t = self._generate_radial_t(w, h)
            result = self._interpolate_colors(t)

        # Create image
        from imagestag import Image as Img
        return Img(result, pixel_format=out_fmt)

    def _generate_solid(self, w: int, h: int) -> np.ndarray:
        """Generate solid color image."""
        color = np.array(self._get_color_start_tuple(), dtype=np.uint8)
        out_fmt = self._get_output_format()

        if out_fmt == PixelFormat.GRAY:
            return np.full((h, w), color[0], dtype=np.uint8)
        else:
            return np.full((h, w, len(color)), color, dtype=np.uint8)

    def _generate_linear_t(self, w: int, h: int) -> np.ndarray:
        """Generate linear gradient parameter t (0-1)."""
        angle_rad = np.radians(self.angle)

        # Create coordinate grids
        y, x = np.mgrid[0:h, 0:w]

        # Normalize to 0-1
        x_norm = x / (w - 1) if w > 1 else np.zeros_like(x, dtype=np.float32)
        y_norm = y / (h - 1) if h > 1 else np.zeros_like(y, dtype=np.float32)

        # Project onto gradient axis
        t = x_norm * np.cos(angle_rad) + y_norm * np.sin(angle_rad)

        # Normalize t to 0-1 range
        t_min, t_max = t.min(), t.max()
        if t_max - t_min > 1e-10:
            t = (t - t_min) / (t_max - t_min)
        else:
            t = np.zeros_like(t)

        return t.astype(np.float32)

    def _generate_radial_t(self, w: int, h: int) -> np.ndarray:
        """Generate radial gradient parameter t (0-1)."""
        # Create coordinate grids
        y, x = np.mgrid[0:h, 0:w]

        # Calculate center position
        center_x = self.cx * (w - 1) if w > 1 else 0
        center_y = self.cy * (h - 1) if h > 1 else 0

        # Calculate distance from center
        dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

        # Calculate maximum distance (to corners)
        corners = [
            np.sqrt(center_x ** 2 + center_y ** 2),
            np.sqrt((w - 1 - center_x) ** 2 + center_y ** 2),
            np.sqrt(center_x ** 2 + (h - 1 - center_y) ** 2),
            np.sqrt((w - 1 - center_x) ** 2 + (h - 1 - center_y) ** 2),
        ]
        max_dist = max(corners) if corners else 1

        # Normalize to 0-1
        t = dist / max_dist if max_dist > 1e-10 else np.zeros_like(dist)
        t = np.clip(t, 0, 1)

        return t.astype(np.float32)

    def _interpolate_colors(self, t: np.ndarray) -> np.ndarray:
        """Interpolate between start and end colors."""
        start = np.array(self._get_color_start_tuple(), dtype=np.float32)
        end = np.array(self._get_color_end_tuple(), dtype=np.float32)
        out_fmt = self._get_output_format()

        if out_fmt == PixelFormat.GRAY:
            # Single channel
            result = start[0] + (end[0] - start[0]) * t
            return result.astype(np.uint8)
        else:
            # Multi-channel
            t_expanded = t[..., np.newaxis]
            result = start + (end - start) * t_expanded
            return result.astype(np.uint8)
