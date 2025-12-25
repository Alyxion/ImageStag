# ImageStag Filters - Blur & Sharpen
"""
Blur and sharpen filters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from PIL import ImageFilter

from .base import Filter, FilterBackend, FilterContext, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class GaussianBlur(Filter):
    """Gaussian blur filter.

    radius: Blur radius in pixels
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

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

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

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

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

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

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.SHARPEN)
        return Img(result)


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

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'ksize'

    ksize: int = 5

    def __post_init__(self):
        # Ensure ksize is odd
        if self.ksize % 2 == 0:
            self.ksize += 1

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        result = cv2.medianBlur(pixels, self.ksize)
        return ImageClass(result, pixel_format=PixelFormat.RGB)


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
class MedianFilter(Filter):
    """Median filter using PIL.

    Picks the median pixel value in a window of the given size.
    Alternative to MedianBlur for PIL-native processing.

    Parameters:
        size: Window size (default 3)

    Example:
        'medianfilter(5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'size'

    size: int = 3

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.MedianFilter(size=self.size))
        return Img(result)


@register_filter
@dataclass
class MinFilter(Filter):
    """Minimum filter - picks the darkest pixel in a window.

    Useful for removing light noise and expanding dark areas.

    Parameters:
        size: Window size (default 3)

    Example:
        'minfilter(3)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'size'

    size: int = 3

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.MinFilter(size=self.size))
        return Img(result)


@register_filter
@dataclass
class MaxFilter(Filter):
    """Maximum filter - picks the brightest pixel in a window.

    Useful for removing dark noise and expanding bright areas.

    Parameters:
        size: Window size (default 3)

    Example:
        'maxfilter(3)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'size'

    size: int = 3

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.MaxFilter(size=self.size))
        return Img(result)


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
class Smooth(Filter):
    """Smoothing filter using PIL.

    Parameters:
        strength: 'normal' or 'more'

    Example:
        'smooth()' or 'smooth(more)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'strength'

    strength: str = 'normal'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()

        if self.strength == 'more':
            result = pil_img.filter(ImageFilter.SMOOTH_MORE)
        else:
            result = pil_img.filter(ImageFilter.SMOOTH)

        return Img(result)


@register_filter
@dataclass
class Detail(Filter):
    """Detail enhancement filter.

    Enhances fine details in the image.

    Example:
        'detail()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.DETAIL)
        return Img(result)


@register_filter
@dataclass
class Contour(Filter):
    """Contour detection filter.

    Creates an outline/contour effect on the image.

    Example:
        'contour()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.CONTOUR)
        return Img(result)


@register_filter
@dataclass
class Emboss(Filter):
    """Emboss effect filter.

    Creates a raised/3D embossed effect.

    Example:
        'emboss()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.EMBOSS)
        return Img(result)


@register_filter
@dataclass
class FindEdges(Filter):
    """Edge detection filter.

    Simple edge detection using PIL's built-in filter.

    Example:
        'findedges()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.filter(ImageFilter.FIND_EDGES)
        return Img(result)
