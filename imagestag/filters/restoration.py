# ImageStag Filters - Image Restoration
"""
Advanced denoising and restoration filters using scikit-image.

These provide higher-quality denoising than simple blur filters:
- Non-local means (NLMeans) - patch-based, excellent noise removal
- Total Variation (TV) - edge-preserving regularization
- Wavelet denoising - multi-scale frequency-domain filtering
- Inpainting - fill missing/damaged regions

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
class DenoiseNLMeans(Filter):
    """Non-local means denoising.

    State-of-the-art denoising using patch matching. Finds similar
    patches across the image and averages them, preserving detail
    while removing noise. Slower but much better quality than
    simple blur filters.

    Requires: scikit-image (optional dependency)

    Parameters:
        h: Filter strength (higher = more smoothing, 0.06-0.12 typical)
        patch_size: Size of patches to compare (default 5)
        patch_distance: Maximum distance to search for patches (default 6)
        fast_mode: Use faster but approximate algorithm (default True)

    Example:
        'denoisenlmeans()' - default settings
        'denoisenlmeans(h=0.1,fast_mode=false)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'h'

    h: float = 0.08
    patch_size: int = 5
    patch_distance: int = 6
    fast_mode: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.restoration import denoise_nl_means, estimate_sigma
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        try:
            sigma_est = float(np.mean(estimate_sigma(pixels, channel_axis=2)))
        except ImportError:
            diff_x = pixels[:, 1:, :] - pixels[:, :-1, :]
            diff_y = pixels[1:, :, :] - pixels[:-1, :, :]
            sigma_est = float((np.std(diff_x) + np.std(diff_y)) / (2.0 * np.sqrt(2.0)))
            if sigma_est <= 1e-6:
                sigma_est = 1e-3

        # Apply non-local means denoising
        result = denoise_nl_means(
            pixels,
            h=self.h * sigma_est,
            patch_size=self.patch_size,
            patch_distance=self.patch_distance,
            fast_mode=self.fast_mode,
            channel_axis=2,
        )

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class DenoiseTV(Filter):
    """Total Variation (Chambolle) denoising.

    Edge-preserving denoising using TV regularization.
    Good at preserving sharp edges while smoothing noise.

    Requires: scikit-image (optional dependency)

    Parameters:
        weight: Denoising weight (higher = more smoothing, 0.1-0.3 typical)
        n_iter_max: Maximum iterations (default 200)

    Example:
        'denoisetv()' or 'denoisetv(weight=0.2)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'weight'

    weight: float = 0.1
    n_iter_max: int = 200

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.restoration import denoise_tv_chambolle
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        # Apply TV denoising
        result = denoise_tv_chambolle(
            pixels,
            weight=self.weight,
            max_num_iter=self.n_iter_max,
            channel_axis=2,
        )

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class DenoiseWavelet(Filter):
    """Wavelet-based denoising.

    Denoises using wavelet decomposition. Effective for
    multi-scale noise patterns.

    Requires: scikit-image (optional dependency)

    Parameters:
        sigma: Noise standard deviation (None = estimate)
        wavelet: Wavelet type ('db1', 'sym4', 'coif1', etc.)
        mode: Signal extension mode
        rescale_sigma: Rescale sigma for each level (default True)

    Example:
        'denoisewavelet()' or 'denoisewavelet(wavelet=sym4)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    sigma: float | None = None
    wavelet: str = 'db1'
    mode: str = 'soft'
    rescale_sigma: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.restoration import denoise_wavelet
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        # Apply wavelet denoising
        result = denoise_wavelet(
            pixels,
            sigma=self.sigma,
            wavelet=self.wavelet,
            mode=self.mode,
            rescale_sigma=self.rescale_sigma,
            channel_axis=2,
        )

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class Inpaint(Filter):
    """Biharmonic inpainting to fill missing regions.

    Fills holes or damaged regions using biharmonic interpolation.
    Requires a mask image specifying which pixels to fill.

    Requires: scikit-image (optional dependency)

    Parameters:
        mask_threshold: Threshold to binarize mask (0-255)

    Note: Pass the mask via context['inpaint_mask'] as a numpy array
    or Image where white pixels indicate regions to fill.

    Example:
        'inpaint()' or 'inpaint(mask_threshold=128)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'mask_threshold'

    mask_threshold: int = 128

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.restoration import inpaint_biharmonic
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels as float
        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float64) / 255.0

        # Get mask from context
        mask = None
        if context is not None:
            mask_data = context.get('inpaint_mask')
            if mask_data is not None:
                if hasattr(mask_data, 'get_pixels'):
                    mask = mask_data.get_pixels(PixelFormat.GRAY)
                else:
                    mask = np.asarray(mask_data)
                mask = mask > self.mask_threshold

        if mask is None:
            # No mask provided, return unchanged
            return image

        # Apply inpainting
        result = inpaint_biharmonic(pixels, mask, channel_axis=2)

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result, pixel_format=PixelFormat.RGB)


__all__ = [
    'DenoiseNLMeans',
    'DenoiseTV',
    'DenoiseWavelet',
    'Inpaint',
]
