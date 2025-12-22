# ImageStag Filters - Geometric Transforms
"""
Geometric transform filters: Resize, Crop, Rotate, Flip, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from PIL import ImageOps

from .base import Filter, register_filter

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class Resize(Filter):
    """Resize image.

    Either specify size (width, height) or scale factor.
    """
    size: tuple[int, int] | None = None
    scale: float | None = None
    _primary_param = 'scale'

    def apply(self, image: Image) -> Image:
        from imagestag.interpolation import InterpolationMethod

        if self.scale is not None:
            new_width = int(image.width * self.scale)
            new_height = int(image.height * self.scale)
            return image.resized((new_width, new_height), InterpolationMethod.LANCZOS)
        elif self.size is not None:
            return image.resized(self.size, InterpolationMethod.LANCZOS)
        else:
            return image

    def to_dict(self) -> dict[str, Any]:
        data = {'type': self.type}
        if self.scale is not None:
            data['scale'] = self.scale
        if self.size is not None:
            data['size'] = list(self.size)
        return data


@register_filter
@dataclass
class Crop(Filter):
    """Crop image region.

    x, y: Top-left corner
    width, height: Size of crop region
    """
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def apply(self, image: Image) -> Image:
        from imagestag import Image as Img
        if self.width <= 0 or self.height <= 0:
            return image
        # PIL crop uses (left, upper, right, lower) where right/lower are exclusive
        pil_img = image.to_pil()
        x2 = min(self.x + self.width, image.width)
        y2 = min(self.y + self.height, image.height)
        result = pil_img.crop((self.x, self.y, x2, y2))
        return Img(result)


@register_filter
@dataclass
class CenterCrop(Filter):
    """Crop from center of image."""
    width: int = 0
    height: int = 0

    def apply(self, image: Image) -> Image:
        from imagestag import Image as Img
        if self.width <= 0 or self.height <= 0:
            return image

        x = (image.width - self.width) // 2
        y = (image.height - self.height) // 2
        x = max(0, x)
        y = max(0, y)
        # PIL crop uses (left, upper, right, lower) where right/lower are exclusive
        pil_img = image.to_pil()
        x2 = min(x + self.width, image.width)
        y2 = min(y + self.height, image.height)
        result = pil_img.crop((x, y, x2, y2))
        return Img(result)


@register_filter
@dataclass
class Rotate(Filter):
    """Rotate image.

    angle: Rotation in degrees, counter-clockwise
    expand: If True, expand canvas to fit rotated image
    fill_color: Background color for empty areas
    """
    angle: float = 0.0
    expand: bool = False
    fill_color: tuple[int, int, int] = (0, 0, 0)
    _primary_param = 'angle'

    def apply(self, image: Image) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.rotate(
            self.angle,
            expand=self.expand,
            fillcolor=self.fill_color
        )
        return Img(result)


@register_filter
@dataclass
class Flip(Filter):
    """Flip image horizontally and/or vertically."""
    horizontal: bool = False
    vertical: bool = False

    def apply(self, image: Image) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()

        if self.horizontal:
            pil_img = ImageOps.mirror(pil_img)
        if self.vertical:
            pil_img = ImageOps.flip(pil_img)

        return Img(pil_img)
