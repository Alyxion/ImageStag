# ImageStag Filters - Advanced Thresholding
"""
Advanced thresholding filters using scikit-image.

These provide more sophisticated thresholding than simple
binary threshold:
- Otsu: Automatic optimal threshold
- Li: Minimum cross-entropy threshold
- Local (Niblack/Sauvola): Adaptive local thresholding

Requires scikit-image as an optional dependency.
Install with: pip install scikit-image
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, register_filter, _check_skimage
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class ThresholdOtsu(Filter):
    """Otsu's automatic thresholding.

    Computes the optimal threshold to separate foreground
    from background by maximizing inter-class variance.
    Works well when histogram is bimodal.

    Requires: scikit-image (optional dependency)

    Parameters:
        nbins: Number of histogram bins (default 256)

    Example:
        'thresholdotsu()' or 'thresholdotsu(nbins=128)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'nbins'

    nbins: int = 256

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import threshold_otsu
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute Otsu threshold
        thresh = threshold_otsu(gray, nbins=self.nbins)

        # Store threshold value in context
        if context is not None:
            context['otsu_threshold'] = float(thresh)

        # Apply threshold
        result = (gray > thresh).astype(np.uint8) * 255
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class ThresholdLi(Filter):
    """Li's minimum cross-entropy thresholding.

    Iteratively minimizes cross-entropy between foreground
    and background. Often works better than Otsu for
    non-bimodal histograms.

    Requires: scikit-image (optional dependency)

    Parameters:
        tolerance: Convergence tolerance (default 0.5)

    Example:
        'thresholdli()' or 'thresholdli(tolerance=0.1)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'tolerance'

    tolerance: float = 0.5

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import threshold_li
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute Li threshold
        thresh = threshold_li(gray, tolerance=self.tolerance)

        # Store threshold value in context
        if context is not None:
            context['li_threshold'] = float(thresh)

        # Apply threshold
        result = (gray > thresh).astype(np.uint8) * 255
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class ThresholdYen(Filter):
    """Yen's maximum entropy thresholding.

    Maximizes the entropy of the thresholded image.
    Works well for images with uneven illumination.

    Requires: scikit-image (optional dependency)

    Parameters:
        nbins: Number of histogram bins (default 256)

    Example:
        'thresholdyen()' or 'thresholdyen(nbins=128)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'nbins'

    nbins: int = 256

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import threshold_yen
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute Yen threshold
        thresh = threshold_yen(gray, nbins=self.nbins)

        # Store threshold value in context
        if context is not None:
            context['yen_threshold'] = float(thresh)

        # Apply threshold
        result = (gray > thresh).astype(np.uint8) * 255
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class ThresholdTriangle(Filter):
    """Triangle thresholding algorithm.

    Works well for unimodal histograms (one peak).
    Finds threshold at maximum distance from line
    connecting histogram peak to tail.

    Requires: scikit-image (optional dependency)

    Parameters:
        nbins: Number of histogram bins (default 256)

    Example:
        'thresholdtriangle()' or 'thresholdtriangle(nbins=128)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'nbins'

    nbins: int = 256

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import threshold_triangle
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute triangle threshold
        thresh = threshold_triangle(gray, nbins=self.nbins)

        # Store threshold value in context
        if context is not None:
            context['triangle_threshold'] = float(thresh)

        # Apply threshold
        result = (gray > thresh).astype(np.uint8) * 255
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class ThresholdNiblack(Filter):
    """Niblack's local thresholding.

    Computes threshold for each pixel based on local mean
    and standard deviation. Better for uneven illumination
    than global thresholds.

    Requires: scikit-image (optional dependency)

    Parameters:
        window_size: Size of local window (must be odd)
        k: Sensitivity parameter (typically -0.2 to 0.2)

    Example:
        'thresholdniblack(window_size=25,k=0.2)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'window_size'

    window_size: int = 15
    k: float = 0.2

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import threshold_niblack
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute local threshold
        thresh = threshold_niblack(gray, window_size=self.window_size, k=self.k)

        # Apply threshold
        result = (gray > thresh).astype(np.uint8) * 255
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class ThresholdSauvola(Filter):
    """Sauvola's local thresholding.

    Improved version of Niblack that normalizes the local
    standard deviation. Better for document images and
    text binarization.

    Requires: scikit-image (optional dependency)

    Parameters:
        window_size: Size of local window (must be odd)
        k: Sensitivity parameter (typically 0.2 to 0.5)
        r: Dynamic range of standard deviation (default 128)

    Example:
        'thresholdsauvola(window_size=25,k=0.35)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'window_size'

    window_size: int = 15
    k: float = 0.2
    r: float = 128.0

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import threshold_sauvola
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute local threshold
        thresh = threshold_sauvola(gray, window_size=self.window_size, k=self.k, r=self.r)

        # Apply threshold
        result = (gray > thresh).astype(np.uint8) * 255
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


__all__ = [
    'ThresholdOtsu',
    'ThresholdLi',
    'ThresholdYen',
    'ThresholdTriangle',
    'ThresholdNiblack',
    'ThresholdSauvola',
]
