# ImageStag Filters - Blur & Sharpen
"""
Blur and sharpen filters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import ImageFilter

from .base import Filter, FilterBackend, FilterContext, register_filter

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class GaussianBlur(Filter):
    """Gaussian blur filter.

    radius: Blur radius in pixels
    """
    radius: float = 2.0
    _primary_param = 'radius'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.PIL

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.GaussianBlur(radius=self.radius))
        return Img(result)


@register_filter
@dataclass
class BoxBlur(Filter):
    """Box (average) blur filter.

    radius: Blur radius in pixels
    """
    radius: int = 2
    _primary_param = 'radius'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.BoxBlur(radius=self.radius))
        return Img(result)


@register_filter
@dataclass
class UnsharpMask(Filter):
    """Unsharp mask sharpening.

    radius: Blur radius
    percent: Sharpening strength (0-500)
    threshold: Minimum brightness change to sharpen
    """
    radius: float = 2.0
    percent: int = 150
    threshold: int = 3
    _primary_param = 'radius'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.UnsharpMask(
            radius=self.radius,
            percent=self.percent,
            threshold=self.threshold
        ))
        return Img(result)


@register_filter
@dataclass
class Sharpen(Filter):
    """Simple sharpen filter using PIL's built-in SHARPEN kernel."""

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.SHARPEN)
        return Img(result)
