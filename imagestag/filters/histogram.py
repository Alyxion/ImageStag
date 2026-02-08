# ImageStag Filters - Histogram Operations
"""
Histogram-based filters including equalization, adaptive thresholding, and CLAHE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class CLAHE(Filter):
    """Contrast Limited Adaptive Histogram Equalization.

    Improves local contrast while limiting noise amplification.
    Divides image into tiles and applies histogram equalization to each.

    Parameters:
        clip_limit: Threshold for contrast limiting (default 2.0)
        tile_size: Size of grid for histogram equalization (default 8)

    Example:
        'clahe()' - default settings
        'clahe(clip_limit=4.0,tile_size=16)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'clip_limit'

    clip_limit: float = 2.0
    tile_size: int = 8

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)

        # Create CLAHE object
        clahe = cv2.createCLAHE(
            clipLimit=self.clip_limit,
            tileGridSize=(self.tile_size, self.tile_size)
        )

        # Convert to LAB and apply CLAHE to L channel
        lab = cv2.cvtColor(pixels, cv2.COLOR_RGB2LAB)
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        return ImageClass(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class AdaptiveThreshold(Filter):
    """Adaptive thresholding based on local image regions.

    Computes threshold for each pixel based on its neighborhood,
    handling uneven lighting better than global thresholding.

    Parameters:
        max_value: Value assigned to pixels exceeding threshold (default 255)
        method: 'mean' or 'gaussian' - how to compute local threshold
        block_size: Size of neighborhood (must be odd, default 11)
        c: Constant subtracted from mean/weighted mean (default 2)

    Example:
        'adaptivethreshold()' - default settings
        'adaptivethreshold(method=gaussian,block_size=15,c=5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'block_size'

    max_value: int = 255
    method: str = 'gaussian'  # 'mean' or 'gaussian'
    block_size: int = 11
    c: float = 2.0

    def __post_init__(self):
        # Ensure block_size is odd
        if self.block_size % 2 == 0:
            self.block_size += 1

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)

        # Select adaptive method
        if self.method.lower() == 'mean':
            adaptive_method = cv2.ADAPTIVE_THRESH_MEAN_C
        else:
            adaptive_method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C

        result = cv2.adaptiveThreshold(
            gray,
            self.max_value,
            adaptive_method,
            cv2.THRESH_BINARY,
            self.block_size,
            self.c
        )

        # Convert back to RGB
        rgb = np.stack([result, result, result], axis=-1)
        return ImageClass(rgb, pixel_format=PixelFormat.RGB)
