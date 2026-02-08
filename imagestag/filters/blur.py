# ImageStag Filters - Blur & Sharpen
"""
Blur and sharpen filters.

Uses Rust backend via imagestag_rust for filters with cross-platform implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from PIL import ImageFilter

from .base import Filter, FilterContext, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


def _apply_blur_rust(image: 'Image', rust_fn, *args) -> 'Image':
    """Apply a Rust function that operates on numpy arrays.

    Preserves the input image's pixel format (RGB or RGBA).
    """
    from imagestag import Image as Img
    from imagestag.pixel_format import PixelFormat
    has_alpha = image.pixel_format in (PixelFormat.RGBA, PixelFormat.BGRA)
    pf = PixelFormat.RGBA if has_alpha else PixelFormat.RGB
    pixels = image.get_pixels(pf)
    result = rust_fn(pixels, *args)
    return Img(result, pixel_format=pf)


@register_filter
@dataclass
class GaussianBlur(Filter):
    """Gaussian blur filter.

    radius: Blur radius in pixels
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    radius: float = 2.0
    _primary_param = 'radius'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img, imagestag_rust
        from imagestag.pixel_format import PixelFormat
        has_alpha = image.pixel_format in (PixelFormat.RGBA, PixelFormat.BGRA)
        pf = PixelFormat.RGBA if has_alpha else PixelFormat.RGB
        pixels = image.get_pixels(pf)
        result = imagestag_rust.gaussian_blur_rgba(pixels, float(self.radius))
        return Img(result, pixel_format=pf)


@register_filter
@dataclass
class BoxBlur(Filter):
    """Box (average) blur filter.

    radius: Blur radius in pixels
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    radius: int = 2
    _primary_param = 'radius'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img, imagestag_rust
        from imagestag.pixel_format import PixelFormat
        has_alpha = image.pixel_format in (PixelFormat.RGBA, PixelFormat.BGRA)
        pf = PixelFormat.RGBA if has_alpha else PixelFormat.RGB
        pixels = image.get_pixels(pf)
        result = imagestag_rust.box_blur_rgba(pixels, self.radius)
        return Img(result, pixel_format=pf)


@register_filter
@dataclass
class UnsharpMask(Filter):
    """Unsharp mask sharpening.

    radius: Blur radius
    percent: Sharpening strength (0-500)
    threshold: Minimum brightness change to sharpen
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    radius: float = 2.0
    percent: int = 150
    threshold: int = 3
    _primary_param = 'radius'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag.filters.sharpen import unsharp_mask
        # Rust amount: 0-5 (1.0=100%). PIL percent: 0-500 (150=150%).
        amount = self.percent / 100.0
        return _apply_blur_rust(image, unsharp_mask, amount, self.radius, self.threshold)


@register_filter
@dataclass
class Sharpen(Filter):
    """Simple sharpen filter."""

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag.filters.sharpen import sharpen
        return _apply_blur_rust(image, sharpen, 1.0)


@register_filter
@dataclass
class MedianBlur(Filter):
    """Median blur filter for noise removal.

    Replaces each pixel with the median of neighboring pixels.
    Effective for salt-and-pepper noise while preserving edges.

    Parameters:
        ksize: Kernel size (must be odd, e.g., 3, 5, 7)

    Example:
        'medianblur(5)' or 'medianblur(ksize=3)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'ksize'

    ksize: int = 5

    def __post_init__(self):
        # Ensure ksize is odd
        if self.ksize % 2 == 0:
            self.ksize += 1

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag.filters.noise import median
        # Rust median takes radius (1=3x3, 2=5x5), ksize = 2*radius+1
        radius = (self.ksize - 1) // 2
        return _apply_blur_rust(image, median, radius)


@register_filter
@dataclass
class BilateralFilter(Filter):
    """Bilateral filter for edge-preserving smoothing.

    Smooths images while keeping edges sharp by considering both
    spatial distance and color similarity.

    Parameters:
        d: Diameter of pixel neighborhood (use -1 for auto based on sigma)
        sigma_color: Filter sigma in color space (larger = more colors mixed)
        sigma_space: Filter sigma in coordinate space (larger = more distant pixels influence)

    Example:
        'bilateralfilter(9,75,75)' - typical settings
        'bilateralfilter(d=-1,sigma_color=50,sigma_space=50)' - auto diameter
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'd'

    d: int = 9
    sigma_color: float = 75.0
    sigma_space: float = 75.0

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        result = cv2.bilateralFilter(pixels, self.d, self.sigma_color, self.sigma_space)
        return ImageClass(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class ModeFilter(Filter):
    """Mode filter - picks the most common pixel in a window.

    Useful for removing isolated pixels and creating a posterized effect.

    Parameters:
        size: Window size (default 3)

    Example:
        'modefilter(5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'size'

    size: int = 3

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.ModeFilter(size=self.size))
        return Img(result)


@register_filter
@dataclass
class Emboss(Filter):
    """Emboss effect filter.

    Creates a raised/3D embossed effect.

    Example:
        'emboss()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag.filters.stylize import emboss
        return _apply_blur_rust(image, emboss)


@register_filter
@dataclass
class FindEdges(Filter):
    """Edge detection filter.

    Example:
        'findedges()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag.filters.edge_detect import find_edges
        return _apply_blur_rust(image, find_edges)
