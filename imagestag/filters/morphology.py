# ImageStag Filters - Morphological Operations
"""
Morphological image operations.

Uses Rust backend for Erode and Dilate.
OpenCV used for compound operations (MorphOpen, MorphClose, etc.) that
don't have Rust implementations yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, FilterBackend, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


class MorphShape(Enum):
    """Structuring element shape for morphological operations."""
    RECT = auto()      # Rectangular
    ELLIPSE = auto()   # Elliptical
    CROSS = auto()     # Cross-shaped


def _get_kernel(shape: MorphShape, size: int):
    """Create structuring element kernel."""
    import cv2
    shape_map = {
        MorphShape.RECT: cv2.MORPH_RECT,
        MorphShape.ELLIPSE: cv2.MORPH_ELLIPSE,
        MorphShape.CROSS: cv2.MORPH_CROSS,
    }
    return cv2.getStructuringElement(shape_map[shape], (size, size))


def _apply_morph_rust(image: 'Image', rust_fn, *args) -> 'Image':
    """Apply a Rust morphology function, preserving pixel format."""
    from imagestag import Image as Img
    from imagestag.pixel_format import PixelFormat
    has_alpha = image.pixel_format in (PixelFormat.RGBA, PixelFormat.BGRA)
    pf = PixelFormat.RGBA if has_alpha else PixelFormat.RGB
    pixels = image.get_pixels(pf)
    result = rust_fn(pixels, *args)
    return Img(result, pixel_format=pf)


@register_filter
@dataclass
class Erode(Filter):
    """Morphological erosion.

    Erodes away boundaries of foreground objects. Useful for removing
    small white noise and detaching connected objects.

    Parameters:
        kernel_size: Size of structuring element (default 3)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')
        iterations: Number of times to apply erosion

    Example:
        'erode(3)' or 'erode(kernel_size=5,iterations=2)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    kernel_size: int = 3
    shape: str = 'rect'
    iterations: int = 1

    _primary_param: ClassVar[str] = 'kernel_size'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag.filters.morphology_filters import erode
        # Rust erode takes radius (float), kernel_size = 2*radius+1
        radius = float((self.kernel_size - 1) // 2) or 1.0
        result = image
        for _ in range(self.iterations):
            result = _apply_morph_rust(result, erode, radius)
        return result


@register_filter
@dataclass
class Dilate(Filter):
    """Morphological dilation.

    Expands boundaries of foreground objects. Useful for filling small
    holes and connecting nearby objects.

    Parameters:
        kernel_size: Size of structuring element (default 3)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')
        iterations: Number of times to apply dilation

    Example:
        'dilate(3)' or 'dilate(kernel_size=5,iterations=2)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    kernel_size: int = 3
    shape: str = 'rect'
    iterations: int = 1

    _primary_param: ClassVar[str] = 'kernel_size'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag.filters.morphology_filters import dilate
        # Rust dilate takes radius (float), kernel_size = 2*radius+1
        radius = float((self.kernel_size - 1) // 2) or 1.0
        result = image
        for _ in range(self.iterations):
            result = _apply_morph_rust(result, dilate, radius)
        return result


@register_filter
@dataclass
class MorphOpen(Filter):
    """Morphological opening (erosion followed by dilation).

    Useful for removing small objects/noise while preserving shape and
    size of larger objects.

    Parameters:
        kernel_size: Size of structuring element (default 3)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')

    Example:
        'morphopen(5)' or 'morphopen(kernel_size=7,shape=ellipse)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    kernel_size: int = 3
    shape: str = 'rect'

    _primary_param: ClassVar[str] = 'kernel_size'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        shape = MorphShape[self.shape.upper()]
        kernel = _get_kernel(shape, self.kernel_size)

        result = cv2.morphologyEx(pixels, cv2.MORPH_OPEN, kernel)
        return ImageClass(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class MorphClose(Filter):
    """Morphological closing (dilation followed by erosion).

    Useful for closing small holes inside foreground objects.

    Parameters:
        kernel_size: Size of structuring element (default 3)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')

    Example:
        'morphclose(5)' or 'morphclose(kernel_size=7,shape=ellipse)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    kernel_size: int = 3
    shape: str = 'rect'

    _primary_param: ClassVar[str] = 'kernel_size'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        shape = MorphShape[self.shape.upper()]
        kernel = _get_kernel(shape, self.kernel_size)

        result = cv2.morphologyEx(pixels, cv2.MORPH_CLOSE, kernel)
        return ImageClass(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class MorphGradient(Filter):
    """Morphological gradient (difference between dilation and erosion).

    Produces an outline of the object.

    Parameters:
        kernel_size: Size of structuring element (default 3)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')

    Example:
        'morphgradient(3)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    kernel_size: int = 3
    shape: str = 'rect'

    _primary_param: ClassVar[str] = 'kernel_size'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        shape = MorphShape[self.shape.upper()]
        kernel = _get_kernel(shape, self.kernel_size)

        result = cv2.morphologyEx(pixels, cv2.MORPH_GRADIENT, kernel)
        return ImageClass(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class TopHat(Filter):
    """Top-hat transform (difference between input and opening).

    Extracts small bright elements on dark background.

    Parameters:
        kernel_size: Size of structuring element (default 9)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')

    Example:
        'tophat(9)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    kernel_size: int = 9
    shape: str = 'rect'

    _primary_param: ClassVar[str] = 'kernel_size'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        shape = MorphShape[self.shape.upper()]
        kernel = _get_kernel(shape, self.kernel_size)

        result = cv2.morphologyEx(pixels, cv2.MORPH_TOPHAT, kernel)
        return ImageClass(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class BlackHat(Filter):
    """Black-hat transform (difference between closing and input).

    Extracts small dark elements on bright background.

    Parameters:
        kernel_size: Size of structuring element (default 9)
        shape: Shape of kernel ('rect', 'ellipse', 'cross')

    Example:
        'blackhat(9)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    kernel_size: int = 9
    shape: str = 'rect'

    _primary_param: ClassVar[str] = 'kernel_size'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        shape = MorphShape[self.shape.upper()]
        kernel = _get_kernel(shape, self.kernel_size)

        result = cv2.morphologyEx(pixels, cv2.MORPH_BLACKHAT, kernel)
        return ImageClass(result, pixel_format=PixelFormat.RGB)
