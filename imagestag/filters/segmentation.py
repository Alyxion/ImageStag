# ImageStag Filters - Image Segmentation
"""
Image segmentation filters using scikit-image.

These filters divide images into regions:
- SLIC: Fast superpixel segmentation
- Felzenszwalb: Graph-based segmentation
- Watershed: Region growing from markers

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
class SLIC(Filter):
    """Simple Linear Iterative Clustering superpixels.

    Fast superpixel segmentation that groups pixels into
    compact, nearly uniform regions. Useful for pre-processing
    before further analysis.

    Requires: scikit-image (optional dependency)

    Parameters:
        n_segments: Approximate number of superpixels (default 100)
        compactness: Balance between color proximity and space proximity
        sigma: Gaussian smoothing before segmentation
        start_label: Label of first superpixel (default 0)
        mask: Optional binary mask (via context['slic_mask'])

    Example:
        'slic()' or 'slic(n_segments=200,compactness=20)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'n_segments'

    n_segments: int = 100
    compactness: float = 10.0
    sigma: float = 1.0
    start_label: int = 0

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.segmentation import slic, mark_boundaries
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels
        pixels = image.get_pixels(PixelFormat.RGB)

        # Get optional mask from context
        mask = None
        if context is not None:
            mask_data = context.get('slic_mask')
            if mask_data is not None:
                if hasattr(mask_data, 'get_pixels'):
                    mask = mask_data.get_pixels(PixelFormat.GRAY) > 128
                else:
                    mask = np.asarray(mask_data) > 128

        # Apply SLIC
        segments = slic(
            pixels,
            n_segments=self.n_segments,
            compactness=self.compactness,
            sigma=self.sigma,
            start_label=self.start_label,
            mask=mask,
            channel_axis=2,
        )

        # Store segments in context
        if context is not None:
            context['slic_segments'] = segments
            context['slic_n_labels'] = segments.max() + 1

        # Create visualization with boundaries
        result = mark_boundaries(pixels, segments, color=(1, 1, 0))
        result = (result * 255).astype(np.uint8)

        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class Felzenszwalb(Filter):
    """Felzenszwalb's efficient graph-based segmentation.

    Produces segments that are more irregular than SLIC
    but often better match object boundaries.

    Requires: scikit-image (optional dependency)

    Parameters:
        scale: Free parameter controlling segment size
        sigma: Gaussian pre-smoothing width
        min_size: Minimum segment size

    Example:
        'felzenszwalb()' or 'felzenszwalb(scale=200,min_size=50)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'scale'

    scale: float = 100.0
    sigma: float = 0.5
    min_size: int = 50

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.segmentation import felzenszwalb, mark_boundaries
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get pixels
        pixels = image.get_pixels(PixelFormat.RGB)

        # Apply Felzenszwalb
        segments = felzenszwalb(
            pixels,
            scale=self.scale,
            sigma=self.sigma,
            min_size=self.min_size,
            channel_axis=2,
        )

        # Store segments in context
        if context is not None:
            context['felzenszwalb_segments'] = segments
            context['felzenszwalb_n_labels'] = segments.max() + 1

        # Create visualization with boundaries
        result = mark_boundaries(pixels, segments, color=(1, 1, 0))
        result = (result * 255).astype(np.uint8)

        return Img(result, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class Watershed(Filter):
    """Watershed segmentation from markers.

    Grows regions from seed points (markers) using watershed
    algorithm. Requires markers via context['watershed_markers'].

    Requires: scikit-image (optional dependency)

    Parameters:
        compactness: Higher values make segments more compact
        watershed_line: Include a one-pixel line between segments

    Example:
        'watershed()' or 'watershed(compactness=0.1)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'compactness'

    compactness: float = 0.0
    watershed_line: bool = False

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.segmentation import watershed, mark_boundaries
        from skimage.feature import peak_local_max
        from skimage.filters import sobel
        from scipy import ndimage
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale for gradient computation
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Compute gradient (elevation map)
        gradient = sobel(gray)

        # Get markers from context or auto-generate
        markers = None
        if context is not None:
            marker_data = context.get('watershed_markers')
            if marker_data is not None:
                if hasattr(marker_data, 'get_pixels'):
                    markers = marker_data.get_pixels(PixelFormat.GRAY).astype(np.int32)
                else:
                    markers = np.asarray(marker_data).astype(np.int32)

        if markers is None:
            # Auto-generate markers using distance transform
            binary = gray > 0.5
            distance = ndimage.distance_transform_edt(binary)
            local_max = peak_local_max(distance, min_distance=20, labels=binary)
            markers = np.zeros_like(gray, dtype=np.int32)
            for i, (y, x) in enumerate(local_max):
                markers[y, x] = i + 1

        # Apply watershed
        segments = watershed(
            gradient,
            markers,
            compactness=self.compactness,
            watershed_line=self.watershed_line,
        )

        # Store segments in context
        if context is not None:
            context['watershed_segments'] = segments
            context['watershed_n_labels'] = segments.max()

        # Create visualization with boundaries
        pixels = image.get_pixels(PixelFormat.RGB)
        result = mark_boundaries(pixels, segments, color=(1, 1, 0))
        result = (result * 255).astype(np.uint8)

        return Img(result, pixel_format=PixelFormat.RGB)


__all__ = [
    'SLIC',
    'Felzenszwalb',
    'Watershed',
]
