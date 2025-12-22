# ImageStag Filters - Color Adjustments
"""
Color adjustment filters: Brightness, Contrast, Saturation, Grayscale, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import ImageEnhance, ImageOps
from PIL import Image as PILImage

from .base import Filter, FilterContext, register_filter

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class Brightness(Filter):
    """Adjust image brightness.

    factor: 0.0 = black, 1.0 = original, 2.0 = 2x bright
    """
    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Brightness(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Contrast(Filter):
    """Adjust image contrast.

    factor: 0.0 = gray, 1.0 = original, 2.0 = high contrast
    """
    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Contrast(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Saturation(Filter):
    """Adjust color saturation.

    factor: 0.0 = grayscale, 1.0 = original, 2.0 = vivid
    """
    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Color(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Sharpness(Filter):
    """Adjust image sharpness.

    factor: 0.0 = blurry, 1.0 = original, 2.0 = sharper
    """
    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Sharpness(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Grayscale(Filter):
    """Convert to grayscale."""
    method: str = 'luminosity'  # 'luminosity', 'average', 'lightness'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.convert('L').convert('RGB')
        return Img(result)


@register_filter
@dataclass
class Invert(Filter):
    """Invert colors (negative)."""

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        # Handle RGBA by inverting only RGB channels
        if pil_img.mode == 'RGBA':
            r, g, b, a = pil_img.split()
            rgb = PILImage.merge('RGB', (r, g, b))
            inverted = ImageOps.invert(rgb)
            r, g, b = inverted.split()
            result = PILImage.merge('RGBA', (r, g, b, a))
        else:
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            result = ImageOps.invert(pil_img)
        return Img(result)


@register_filter
@dataclass
class Threshold(Filter):
    """Binary threshold filter.

    Pixels above threshold become white, below become black.
    """
    value: int = 128  # 0-255
    _primary_param = 'value'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        import numpy as np

        pil_img = image.to_pil()
        # Convert to grayscale first
        gray = pil_img.convert('L')
        # Apply threshold
        pixels = np.array(gray)
        binary = np.where(pixels > self.value, 255, 0).astype(np.uint8)
        # Convert back to RGB
        result = PILImage.fromarray(binary, mode='L').convert('RGB')
        return Img(result)
