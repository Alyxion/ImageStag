# ImageStag Filters - Exposure Adjustments
"""
Advanced exposure and color correction filters using scikit-image.

These provide more sophisticated tone adjustments than basic
brightness/contrast:
- Gamma: Gamma correction
- Log: Logarithmic correction
- Sigmoid: S-curve contrast
- MatchHistograms: Match color distribution to reference

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
class AdjustGamma(Filter):
    """Gamma correction for exposure adjustment.

    Applies power-law (gamma) transformation:
    - gamma < 1: brighten shadows, compress highlights
    - gamma > 1: darken image, expand highlights
    - gamma = 1: no change

    Requires: scikit-image (optional dependency)

    Parameters:
        gamma: Gamma value (default 1.0)
        gain: Multiplicative factor (default 1.0)

    Example:
        'adjustgamma(0.5)' - brighten shadows
        'adjustgamma(2.0)' - darken image
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'gamma'

    gamma: float = 1.0
    gain: float = 1.0

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.exposure import adjust_gamma
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        # Apply gamma correction
        result = adjust_gamma(pixels, gamma=self.gamma, gain=self.gain)

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class AdjustLog(Filter):
    """Logarithmic correction for exposure adjustment.

    Applies logarithmic transformation to expand dark regions.
    Useful for images with high dynamic range.

    Requires: scikit-image (optional dependency)

    Parameters:
        gain: Multiplicative factor (default 1.0)
        inv: If True, apply inverse log transform (default False)

    Example:
        'adjustlog()' or 'adjustlog(gain=1.5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'gain'

    gain: float = 1.0
    inv: bool = False

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.exposure import adjust_log
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        # Apply log correction
        result = adjust_log(pixels, gain=self.gain, inv=self.inv)

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class AdjustSigmoid(Filter):
    """Sigmoid (S-curve) contrast adjustment.

    Applies sigmoid function for contrast enhancement.
    Similar to curves adjustment in photo editors.

    Requires: scikit-image (optional dependency)

    Parameters:
        cutoff: Center point of the sigmoid (0.5 = midtones)
        gain: Steepness of the curve (higher = more contrast)
        inv: If True, apply inverse sigmoid (default False)

    Example:
        'adjustsigmoid(cutoff=0.5,gain=10)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'gain'

    cutoff: float = 0.5
    gain: float = 10.0
    inv: bool = False

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.exposure import adjust_sigmoid
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        # Apply sigmoid correction
        result = adjust_sigmoid(pixels, cutoff=self.cutoff, gain=self.gain, inv=self.inv)

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class MatchHistograms(Filter):
    """Match histogram to a reference image.

    Transforms image colors to match the color distribution
    of a reference image. Useful for style transfer and
    color grading.

    Requires: scikit-image (optional dependency)

    Note: Pass reference image via context['histogram_reference']

    Parameters:
        channel_axis: Axis for color channels (default 2 for RGB)

    Example:
        'matchhistograms()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    channel_axis: int = 2

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.exposure import match_histograms
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get reference image from context
        reference = None
        if context is not None:
            ref_data = context.get('histogram_reference')
            if ref_data is not None:
                if hasattr(ref_data, 'get_pixels'):
                    reference = ref_data.get_pixels(PixelFormat.RGB)
                else:
                    reference = np.asarray(ref_data)

        if reference is None:
            # No reference provided, return unchanged
            return image

        # Get source pixels
        pixels = image.get_pixels(PixelFormat.RGB)

        # Match histograms
        result = match_histograms(pixels, reference, channel_axis=self.channel_axis)

        return Img(result.astype(np.uint8), pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class RescaleIntensity(Filter):
    """Rescale image intensity to a specified range.

    Linearly scales pixel values to fit within a new range.
    Useful for normalizing image contrast.

    Requires: scikit-image (optional dependency)

    Parameters:
        in_range: Input range ('image' = actual range, 'dtype' = dtype range)
        out_range: Output range ('dtype' = full dtype range, or tuple)

    Example:
        'rescaleintensity()' - stretch to full range
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    in_range: str = 'image'
    out_range: str = 'dtype'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.exposure import rescale_intensity
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels
        pixels = image.get_pixels(PixelFormat.RGB)

        # Rescale intensity
        result = rescale_intensity(
            pixels,
            in_range=self.in_range,
            out_range=self.out_range,
        )

        return Img(result.astype(np.uint8), pixel_format=PixelFormat.RGB)


__all__ = [
    'AdjustGamma',
    'AdjustLog',
    'AdjustSigmoid',
    'MatchHistograms',
    'RescaleIntensity',
]
