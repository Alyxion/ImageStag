# ImageStag Filters - Size Matcher
"""
SizeMatcher filter for matching dimensions of two images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, TYPE_CHECKING

import numpy as np

from .base import register_filter, FilterContext
from .graph import CombinerFilter
from imagestag.interpolation import InterpolationMethod

if TYPE_CHECKING:
    from imagestag import Image


class SizeMatchMode(Enum):
    """Mode for determining target dimensions."""
    SMALLER_WINS = "smaller_wins"  # Resize to min(width), min(height)
    BIGGER_WINS = "bigger_wins"    # Resize to max(width), max(height)
    FIRST_WINS = "first_wins"      # Resize second to match first
    SECOND_WINS = "second_wins"    # Resize first to match second


class AspectMode(Enum):
    """Mode for handling aspect ratio mismatches."""
    STRETCH = "stretch"   # Stretch to exact dimensions (may distort)
    FIT = "fit"           # Fit within bounds, add borders
    FILL = "fill"         # Fill bounds, crop excess


class CropPosition(Enum):
    """Position for cropping when using FILL mode."""
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@register_filter
@dataclass
class SizeMatcher(CombinerFilter):
    """Match dimensions of two images.

    Takes two images and resizes them to matching dimensions based on
    the selected mode. Handles aspect ratio mismatches with fit/fill/stretch.

    Returns a dict with 'output_a' and 'output_b' keys.
    """

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'image_a', 'description': 'First image'},
        {'name': 'image_b', 'description': 'Second image'},
    ]
    _output_ports: ClassVar[list[dict]] = [
        {'name': 'output_a', 'description': 'Resized first image'},
        {'name': 'output_b', 'description': 'Resized second image'},
    ]

    size_mode: SizeMatchMode = SizeMatchMode.SMALLER_WINS
    aspect_mode: AspectMode = AspectMode.FILL
    crop_position: CropPosition = CropPosition.CENTER
    interpolation: InterpolationMethod = InterpolationMethod.LINEAR
    fill_color_r: int = 0
    fill_color_g: int = 0
    fill_color_b: int = 0

    def __post_init__(self):
        """Convert string values to enums."""
        if isinstance(self.size_mode, str):
            self.size_mode = SizeMatchMode(self.size_mode.lower())
        if isinstance(self.aspect_mode, str):
            self.aspect_mode = AspectMode(self.aspect_mode.lower())
        if isinstance(self.crop_position, str):
            self.crop_position = CropPosition(self.crop_position.lower())
        if isinstance(self.interpolation, str):
            self.interpolation = InterpolationMethod[self.interpolation.upper()]

    @property
    def fill_color(self) -> tuple[int, int, int]:
        """Get fill color as tuple."""
        return (self.fill_color_r, self.fill_color_g, self.fill_color_b)

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> dict[str, Image]:
        if len(self.inputs) < 2:
            raise ValueError("SizeMatcher requires 2 inputs")

        img_a = images[self.inputs[0]]
        img_b = images[self.inputs[1]]

        # Determine target dimensions
        target_w, target_h = self._compute_target_size(img_a, img_b)

        # Resize both images
        out_a = self._resize_image(img_a, target_w, target_h)
        out_b = self._resize_image(img_b, target_w, target_h)

        return {'output_a': out_a, 'output_b': out_b}

    def _compute_target_size(self, img_a: Image, img_b: Image) -> tuple[int, int]:
        """Compute target dimensions based on size_mode."""
        w1, h1 = img_a.width, img_a.height
        w2, h2 = img_b.width, img_b.height

        if self.size_mode == SizeMatchMode.SMALLER_WINS:
            return (min(w1, w2), min(h1, h2))
        elif self.size_mode == SizeMatchMode.BIGGER_WINS:
            return (max(w1, w2), max(h1, h2))
        elif self.size_mode == SizeMatchMode.FIRST_WINS:
            return (w1, h1)
        elif self.size_mode == SizeMatchMode.SECOND_WINS:
            return (w2, h2)
        else:
            return (min(w1, w2), min(h1, h2))

    def _resize_image(self, img: Image, target_w: int, target_h: int) -> Image:
        """Resize image to target dimensions with aspect handling."""
        from imagestag import Image as Img

        # Already correct size
        if img.width == target_w and img.height == target_h:
            return img

        if self.aspect_mode == AspectMode.STRETCH:
            return img.resized((target_w, target_h), interpolation=self.interpolation)

        elif self.aspect_mode == AspectMode.FIT:
            return self._resize_fit(img, target_w, target_h)

        elif self.aspect_mode == AspectMode.FILL:
            return self._resize_fill(img, target_w, target_h)

        return img.resized((target_w, target_h), interpolation=self.interpolation)

    def _resize_fit(self, img: Image, target_w: int, target_h: int) -> Image:
        """Resize to fit within bounds, adding borders."""
        from imagestag import Image as Img

        # Calculate scale to fit
        scale_w = target_w / img.width
        scale_h = target_h / img.height
        scale = min(scale_w, scale_h)

        # Resize maintaining aspect ratio
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        resized = img.resized((new_w, new_h), interpolation=self.interpolation)

        # If already target size, return
        if new_w == target_w and new_h == target_h:
            return resized

        # Create canvas with fill color
        num_channels = len(img.get_pixels().shape)
        if num_channels == 2:
            # Grayscale
            canvas = np.full((target_h, target_w), self.fill_color_r, dtype=np.uint8)
        else:
            channels = img.get_pixels().shape[2] if num_channels == 3 else 3
            if channels == 4:
                canvas = np.full((target_h, target_w, 4),
                               [self.fill_color_r, self.fill_color_g, self.fill_color_b, 255],
                               dtype=np.uint8)
            else:
                canvas = np.full((target_h, target_w, 3),
                               [self.fill_color_r, self.fill_color_g, self.fill_color_b],
                               dtype=np.uint8)

        # Calculate position based on crop_position (used for alignment)
        x, y = self._get_position(target_w, target_h, new_w, new_h)

        # Place resized image on canvas
        resized_px = resized.get_pixels()
        if len(resized_px.shape) == 2 and len(canvas.shape) == 3:
            resized_px = np.stack([resized_px] * canvas.shape[2], axis=2)
        elif len(resized_px.shape) == 3 and len(canvas.shape) == 2:
            resized_px = np.mean(resized_px, axis=2).astype(np.uint8)

        canvas[y:y+new_h, x:x+new_w] = resized_px[:canvas.shape[0]-y, :canvas.shape[1]-x]

        return Img(canvas, pixel_format=img.pixel_format)

    def _resize_fill(self, img: Image, target_w: int, target_h: int) -> Image:
        """Resize to fill bounds, cropping excess."""
        from imagestag import Image as Img

        # Calculate scale to fill
        scale_w = target_w / img.width
        scale_h = target_h / img.height
        scale = max(scale_w, scale_h)

        # Resize maintaining aspect ratio
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        resized = img.resized((new_w, new_h), interpolation=self.interpolation)

        # If already target size, return
        if new_w == target_w and new_h == target_h:
            return resized

        # Calculate crop position
        x, y = self._get_position(new_w, new_h, target_w, target_h)

        # Crop to target size
        resized_px = resized.get_pixels()
        cropped = resized_px[y:y+target_h, x:x+target_w]

        return Img(cropped, pixel_format=img.pixel_format)

    def _get_position(self, outer_w: int, outer_h: int, inner_w: int, inner_h: int) -> tuple[int, int]:
        """Get position for placing inner within outer based on crop_position."""
        if self.crop_position == CropPosition.CENTER:
            x = (outer_w - inner_w) // 2
            y = (outer_h - inner_h) // 2
        elif self.crop_position == CropPosition.TOP_LEFT:
            x, y = 0, 0
        elif self.crop_position == CropPosition.TOP_RIGHT:
            x = outer_w - inner_w
            y = 0
        elif self.crop_position == CropPosition.BOTTOM_LEFT:
            x = 0
            y = outer_h - inner_h
        elif self.crop_position == CropPosition.BOTTOM_RIGHT:
            x = outer_w - inner_w
            y = outer_h - inner_h
        else:
            x = (outer_w - inner_w) // 2
            y = (outer_h - inner_h) // 2

        return (max(0, x), max(0, y))

    @classmethod
    def is_multi_output(cls) -> bool:
        return True

    def to_dict(self) -> dict:
        return {
            'type': 'SizeMatcher',
            'inputs': self.inputs,
            'size_mode': self.size_mode.value,
            'aspect_mode': self.aspect_mode.value,
            'crop_position': self.crop_position.value,
            'interpolation': self.interpolation.name,
            'fill_color': self.fill_color,
        }
