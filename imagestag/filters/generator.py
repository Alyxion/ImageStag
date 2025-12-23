# ImageStag Filters - Image Generator
"""
ImageGenerator filter for creating gradient images.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, TYPE_CHECKING

import numpy as np

from .base import Filter, FilterContext, register_filter
from imagestag.pixel_format import PixelFormat

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

    Parameters:
        gradient_type: LINEAR or RADIAL gradient
        angle: Degrees for linear gradient (0=left-to-right, 90=top-to-bottom)
        color_start_*: Start color RGB components
        color_end_*: End color RGB components
        output_format: GRAY, RGB, or RGBA
        width, height: Dimensions when no input image provided
        center_x, center_y: Center point for radial gradient (0-1)
    """

    gradient_type: GradientType = GradientType.LINEAR
    angle: float = 0.0  # Degrees for linear gradient

    # Colors as individual components (dataclass-friendly)
    color_start_r: int = 0
    color_start_g: int = 0
    color_start_b: int = 0
    color_start_a: int = 255
    color_end_r: int = 255
    color_end_g: int = 255
    color_end_b: int = 255
    color_end_a: int = 255

    output_format: PixelFormat = PixelFormat.GRAY
    width: int = 512
    height: int = 512

    # Radial gradient center (0-1 relative position)
    center_x: float = 0.5
    center_y: float = 0.5

    def __post_init__(self):
        """Convert string values to enums."""
        if isinstance(self.gradient_type, str):
            self.gradient_type = GradientType(self.gradient_type.lower())
        if isinstance(self.output_format, str):
            self.output_format = PixelFormat[self.output_format.upper()]

    @property
    def color_start(self) -> tuple[int, ...]:
        """Get start color as tuple."""
        if self.output_format == PixelFormat.GRAY:
            return (self.color_start_r,)
        elif self.output_format == PixelFormat.RGBA:
            return (self.color_start_r, self.color_start_g, self.color_start_b, self.color_start_a)
        return (self.color_start_r, self.color_start_g, self.color_start_b)

    @property
    def color_end(self) -> tuple[int, ...]:
        """Get end color as tuple."""
        if self.output_format == PixelFormat.GRAY:
            return (self.color_end_r,)
        elif self.output_format == PixelFormat.RGBA:
            return (self.color_end_r, self.color_end_g, self.color_end_b, self.color_end_a)
        return (self.color_end_r, self.color_end_g, self.color_end_b)

    def apply(self, image: Image | None = None, context: FilterContext | None = None) -> Image:
        """Generate gradient image.

        Args:
            image: Optional input image to get dimensions from
            context: Filter context (unused)

        Returns:
            Generated gradient image
        """
        # Get dimensions
        if image is not None:
            w, h = image.width, image.height
        else:
            w, h = self.width, self.height

        # Generate based on type
        if self.gradient_type == GradientType.SOLID:
            result = self._generate_solid(w, h)
        elif self.gradient_type == GradientType.LINEAR:
            t = self._generate_linear_t(w, h)
            result = self._interpolate_colors(t)
        else:  # RADIAL
            t = self._generate_radial_t(w, h)
            result = self._interpolate_colors(t)

        # Create image
        from imagestag import Image as Img
        return Img(result, pixel_format=self.output_format)

    def _generate_solid(self, w: int, h: int) -> np.ndarray:
        """Generate solid color image."""
        color = np.array(self.color_start, dtype=np.uint8)

        if self.output_format == PixelFormat.GRAY:
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
        cx = self.center_x * (w - 1) if w > 1 else 0
        cy = self.center_y * (h - 1) if h > 1 else 0

        # Calculate distance from center
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        # Calculate maximum distance (to corners)
        corners = [
            np.sqrt(cx ** 2 + cy ** 2),
            np.sqrt((w - 1 - cx) ** 2 + cy ** 2),
            np.sqrt(cx ** 2 + (h - 1 - cy) ** 2),
            np.sqrt((w - 1 - cx) ** 2 + (h - 1 - cy) ** 2),
        ]
        max_dist = max(corners) if corners else 1

        # Normalize to 0-1
        t = dist / max_dist if max_dist > 1e-10 else np.zeros_like(dist)
        t = np.clip(t, 0, 1)

        return t.astype(np.float32)

    def _interpolate_colors(self, t: np.ndarray) -> np.ndarray:
        """Interpolate between start and end colors."""
        start = np.array(self.color_start, dtype=np.float32)
        end = np.array(self.color_end, dtype=np.float32)

        if self.output_format == PixelFormat.GRAY:
            # Single channel
            result = start[0] + (end[0] - start[0]) * t
            return result.astype(np.uint8)
        else:
            # Multi-channel
            t_expanded = t[..., np.newaxis]
            result = start + (end - start) * t_expanded
            return result.astype(np.uint8)

    def to_dict(self) -> dict:
        return {
            'type': 'ImageGenerator',
            'gradient_type': self.gradient_type.value,
            'angle': self.angle,
            'color_start': self.color_start,
            'color_end': self.color_end,
            'output_format': self.output_format.name,
            'width': self.width,
            'height': self.height,
            'center_x': self.center_x,
            'center_y': self.center_y,
        }
