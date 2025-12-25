# ImageStag Filters - Texture Analysis
"""
Texture analysis filters using scikit-image.

These filters extract texture features:
- Gabor: Multi-scale texture analysis
- LBP: Local Binary Pattern descriptor

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
class Gabor(Filter):
    """Gabor filter for texture analysis.

    Applies a Gabor filter which is useful for texture
    classification and edge detection at specific
    orientations and frequencies.

    Requires: scikit-image (optional dependency)

    Parameters:
        frequency: Spatial frequency of the filter (0.1 typical)
        theta: Orientation in radians (0 = horizontal)
        sigma_x: Standard deviation in x direction
        sigma_y: Standard deviation in y direction
        mode: Filter response mode ('real' or 'magnitude')

    Example:
        'gabor(frequency=0.1)' or 'gabor(frequency=0.2,theta=0.785)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'frequency'

    frequency: float = 0.1
    theta: float = 0.0
    sigma_x: float | None = None
    sigma_y: float | None = None
    mode: str = 'magnitude'  # 'real', 'imaginary', 'magnitude'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import gabor
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Apply Gabor filter
        real, imag = gabor(
            gray,
            frequency=self.frequency,
            theta=self.theta,
            sigma_x=self.sigma_x,
            sigma_y=self.sigma_y,
        )

        # Select output mode
        if self.mode == 'real':
            result = real
        elif self.mode == 'imaginary':
            result = imag
        else:  # magnitude
            result = np.sqrt(real**2 + imag**2)

        # Store both responses in context
        if context is not None:
            context['gabor_real'] = real
            context['gabor_imaginary'] = imag

        # Normalize to 0-255
        result = result - result.min()
        if result.max() > 0:
            result = result / result.max()
        result = (result * 255).astype(np.uint8)
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class LBP(Filter):
    """Local Binary Pattern texture descriptor.

    Computes LBP features at each pixel. LBP encodes
    the local texture pattern by comparing each pixel
    to its neighbors.

    Requires: scikit-image (optional dependency)

    Parameters:
        radius: Radius of the circle (default 1)
        n_points: Number of points on the circle (default 8)
        method: LBP method ('default', 'ror', 'uniform', 'nri_uniform', 'var')

    Example:
        'lbp()' or 'lbp(radius=2,n_points=16)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'radius'

    radius: int = 1
    n_points: int = 8
    method: str = 'default'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.feature import local_binary_pattern
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute LBP
        lbp = local_binary_pattern(gray, self.n_points, self.radius, method=self.method)

        # Store raw LBP in context
        if context is not None:
            context['lbp'] = lbp

        # Normalize to 0-255 for visualization
        lbp_norm = lbp - lbp.min()
        if lbp_norm.max() > 0:
            lbp_norm = lbp_norm / lbp_norm.max()
        result = (lbp_norm * 255).astype(np.uint8)
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class GaborBank(Filter):
    """Apply a bank of Gabor filters at multiple orientations.

    Creates a multi-orientation texture response by applying
    Gabor filters at evenly spaced angles and combining the
    maximum response.

    Requires: scikit-image (optional dependency)

    Parameters:
        frequency: Spatial frequency of the filter
        n_orientations: Number of orientation angles (default 4)

    Example:
        'gaborbank(frequency=0.1)' or 'gaborbank(n_orientations=8)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'frequency'

    frequency: float = 0.1
    n_orientations: int = 4

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import gabor
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Apply Gabor at multiple orientations
        responses = []
        for i in range(self.n_orientations):
            theta = np.pi * i / self.n_orientations
            real, imag = gabor(gray, frequency=self.frequency, theta=theta)
            mag = np.sqrt(real**2 + imag**2)
            responses.append(mag)

        # Max response across all orientations
        result = np.maximum.reduce(responses)

        # Store all responses in context
        if context is not None:
            context['gabor_responses'] = responses

        # Normalize to 0-255
        result = result - result.min()
        if result.max() > 0:
            result = result / result.max()
        result = (result * 255).astype(np.uint8)
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


__all__ = [
    'Gabor',
    'LBP',
    'GaborBank',
]
