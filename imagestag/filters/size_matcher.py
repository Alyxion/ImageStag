# ImageStag Filters - Size Matcher
"""
SizeMatcher filter for matching dimensions of two images.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, TYPE_CHECKING

import numpy as np

from pydantic import field_validator
from .base import register_filter, FilterContext
from .graph import CombinerFilter
from imagestag.interpolation import InterpolationMethod
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


class SizeMatchMode(Enum):
    """Mode for determining target dimensions."""
    SMALLER = "smaller"      # Resize to min(width), min(height)
    BIGGER = "bigger"        # Resize to max(width), max(height)
    SOURCE = "source"        # Resize other to match source (first image)
    OTHER = "other"          # Resize source to match other (second image)
    # Legacy aliases
    SMALLER_WINS = "smaller"
    BIGGER_WINS = "bigger"
    FIRST_WINS = "source"
    SECOND_WINS = "other"


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
class SizeMatcher(CombinerFilter):
    """Match dimensions of two images.

    Takes two images and resizes them to matching dimensions based on
    the selected mode. Handles aspect ratio mismatches with fit/fill/stretch.

    Returns a dict with 'a' and 'b' keys containing the resized images.
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL, ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'First image'},
        {'name': 'b', 'description': 'Second image'},
    ]
    _output_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'Resized first image'},
        {'name': 'b', 'description': 'Resized second image'},
    ]

    # Positional parameter (obvious)
    mode: SizeMatchMode = SizeMatchMode.SMALLER

    # Keyword-only parameters (non-obvious)
    aspect: AspectMode = AspectMode.FILL
    crop: CropPosition = CropPosition.CENTER
    interp: InterpolationMethod = InterpolationMethod.LINEAR
    fill: str = '#000000'  # Fill color as hex string

    @field_validator('mode', mode='before')
    @classmethod
    def _coerce_mode(cls, v):
        if isinstance(v, str):
            return SizeMatchMode(v.lower())
        return v

    @field_validator('aspect', mode='before')
    @classmethod
    def _coerce_aspect(cls, v):
        if isinstance(v, str):
            return AspectMode(v.lower())
        return v

    @field_validator('crop', mode='before')
    @classmethod
    def _coerce_crop(cls, v):
        if isinstance(v, str):
            return CropPosition(v.lower())
        return v

    @field_validator('interp', mode='before')
    @classmethod
    def _coerce_interp(cls, v):
        if isinstance(v, str):
            return InterpolationMethod[v.upper()]
        return v

    @property
    def fill_color(self) -> tuple[int, int, int]:
        """Get fill color as RGB tuple from hex string."""
        # Parse hex color string
        color = self.fill.lstrip('#')
        if len(color) == 6:
            return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))
        elif len(color) == 3:
            return (int(color[0]*2, 16), int(color[1]*2, 16), int(color[2]*2, 16))
        return (0, 0, 0)

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> dict[str, Image]:
        # Get images by port names (a, b)
        img_a = images.get('a')
        img_b = images.get('b')

        # Fallback to legacy port names for backwards compatibility
        if img_a is None:
            img_a = images.get('source') or images.get('image_a')
        if img_b is None:
            img_b = images.get('other') or images.get('image_b')

        # Fallback to self.inputs if port names don't match (legacy support)
        if img_a is None and len(self.inputs) > 0:
            img_a = images.get(self.inputs[0])
        if img_b is None and len(self.inputs) > 1:
            img_b = images.get(self.inputs[1])

        if img_a is None or img_b is None:
            raise ValueError(f"SizeMatcher requires 2 inputs. Got keys: {list(images.keys())}")

        # Determine target dimensions
        target_w, target_h = self._compute_target_size(img_a, img_b)

        # Resize both images
        out_a = self._resize_image(img_a, target_w, target_h)
        out_b = self._resize_image(img_b, target_w, target_h)

        return {'a': out_a, 'b': out_b}

    def _compute_target_size(self, img_a: Image, img_b: Image) -> tuple[int, int]:
        """Compute target dimensions based on mode."""
        w1, h1 = img_a.width, img_a.height
        w2, h2 = img_b.width, img_b.height

        # Handle both new and legacy enum values
        mode_value = self.mode.value if isinstance(self.mode, SizeMatchMode) else self.mode
        if mode_value in ('smaller', 'smaller_wins'):
            return (min(w1, w2), min(h1, h2))
        elif mode_value in ('bigger', 'bigger_wins'):
            return (max(w1, w2), max(h1, h2))
        elif mode_value in ('source', 'first_wins'):
            return (w1, h1)
        elif mode_value in ('other', 'second_wins'):
            return (w2, h2)
        else:
            return (min(w1, w2), min(h1, h2))

    def _resize_image(self, img: Image, target_w: int, target_h: int) -> Image:
        """Resize image to target dimensions with aspect handling."""
        from imagestag import Image as Img

        # Already correct size
        if img.width == target_w and img.height == target_h:
            return img

        if self.aspect == AspectMode.STRETCH:
            return img.resized((target_w, target_h), interpolation=self.interp)

        elif self.aspect == AspectMode.FIT:
            return self._resize_fit(img, target_w, target_h)

        elif self.aspect == AspectMode.FILL:
            return self._resize_fill(img, target_w, target_h)

        return img.resized((target_w, target_h), interpolation=self.interp)

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
        resized = img.resized((new_w, new_h), interpolation=self.interp)

        # If already target size, return
        if new_w == target_w and new_h == target_h:
            return resized

        # Create canvas with fill color
        fill_r, fill_g, fill_b = self.fill_color
        num_channels = len(img.get_pixels().shape)
        if num_channels == 2:
            # Grayscale
            canvas = np.full((target_h, target_w), fill_r, dtype=np.uint8)
        else:
            channels = img.get_pixels().shape[2] if num_channels == 3 else 3
            if channels == 4:
                canvas = np.full((target_h, target_w, 4),
                               [fill_r, fill_g, fill_b, 255],
                               dtype=np.uint8)
            else:
                canvas = np.full((target_h, target_w, 3),
                               [fill_r, fill_g, fill_b],
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
        resized = img.resized((new_w, new_h), interpolation=self.interp)

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
        """Get position for placing inner within outer based on crop."""
        if self.crop == CropPosition.CENTER:
            x = (outer_w - inner_w) // 2
            y = (outer_h - inner_h) // 2
        elif self.crop == CropPosition.TOP_LEFT:
            x, y = 0, 0
        elif self.crop == CropPosition.TOP_RIGHT:
            x = outer_w - inner_w
            y = 0
        elif self.crop == CropPosition.BOTTOM_LEFT:
            x = 0
            y = outer_h - inner_h
        elif self.crop == CropPosition.BOTTOM_RIGHT:
            x = outer_w - inner_w
            y = outer_h - inner_h
        else:
            x = (outer_w - inner_w) // 2
            y = (outer_h - inner_h) // 2

        return (max(0, x), max(0, y))

    @classmethod
    def is_multi_output(cls) -> bool:
        return True
