# ImageStag Filters - Skeleton Operations
"""
Skeleton and topology filters using scikit-image.

These filters require scikit-image as an optional dependency.
Install with: pip install scikit-image
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, register_filter, _check_skimage
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
class Skeletonize(Filter):
    """Reduce binary shapes to 1-pixel-wide skeleton.

    Computes the skeleton of a binary image using morphological thinning.
    Useful for shape analysis, path finding, and topology extraction.

    Requires: scikit-image (optional dependency)

    Parameters:
        method: Skeletonization method ('zhang' or 'lee')

    Example:
        'skeletonize()' or 'skeletonize(method=lee)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'method'

    method: str = 'zhang'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.morphology import skeletonize
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale pixels
        gray = image.get_pixels(PixelFormat.GRAY)

        # Binarize if needed (threshold at 128)
        binary = gray > 128

        # Apply skeletonization
        skeleton = skeletonize(binary, method=self.method)

        # Convert back to uint8 RGB
        result = (skeleton * 255).astype(np.uint8)
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
class MedialAxis(Filter):
    """Compute the medial axis transform.

    Returns the skeleton plus distance transform values.
    The distance at each skeleton point indicates the radius
    of the maximum inscribed disk.

    Requires: scikit-image (optional dependency)

    Parameters:
        return_distance: If True, also stores distance in context

    Example:
        'medialaxis()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    return_distance: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.morphology import medial_axis
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale pixels
        gray = image.get_pixels(PixelFormat.GRAY)

        # Binarize if needed
        binary = gray > 128

        # Compute medial axis
        if self.return_distance:
            skeleton, distance = medial_axis(binary, return_distance=True)
            if context is not None:
                context['medial_axis_distance'] = distance
        else:
            skeleton = medial_axis(binary, return_distance=False)

        # Convert back to uint8 RGB
        result = (skeleton * 255).astype(np.uint8)
        result_rgb = np.stack([result, result, result], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
class RemoveSmallObjects(Filter):
    """Remove small connected regions from binary image.

    Filters objects by area threshold - much more intuitive than
    iterating morphological operations.

    Requires: scikit-image (optional dependency)

    Parameters:
        min_size: Minimum object size in pixels to keep
        connectivity: Pixel connectivity (1 = 4-connected, 2 = 8-connected)

    Example:
        'removesmallobjects(min_size=100)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'min_size'

    min_size: int = 64
    connectivity: int = 1

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.morphology import remove_small_objects
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale pixels
        gray = image.get_pixels(PixelFormat.GRAY)

        # Binarize
        binary = gray > 128

        # Remove small objects
        result = remove_small_objects(binary, min_size=self.min_size, connectivity=self.connectivity)

        # Convert back to uint8 RGB
        result_uint8 = (result * 255).astype(np.uint8)
        result_rgb = np.stack([result_uint8, result_uint8, result_uint8], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
class RemoveSmallHoles(Filter):
    """Fill small holes in binary objects.

    Fills holes (background regions surrounded by foreground)
    that are smaller than the specified area.

    Requires: scikit-image (optional dependency)

    Parameters:
        area_threshold: Maximum hole size to fill
        connectivity: Pixel connectivity (1 = 4-connected, 2 = 8-connected)

    Example:
        'removesmallholes(area_threshold=50)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'area_threshold'

    area_threshold: int = 64
    connectivity: int = 1

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.morphology import remove_small_holes
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale pixels
        gray = image.get_pixels(PixelFormat.GRAY)

        # Binarize
        binary = gray > 128

        # Remove small holes
        result = remove_small_holes(binary, area_threshold=self.area_threshold, connectivity=self.connectivity)

        # Convert back to uint8 RGB
        result_uint8 = (result * 255).astype(np.uint8)
        result_rgb = np.stack([result_uint8, result_uint8, result_uint8], axis=-1)

        return Img(result_rgb, pixel_format=PixelFormat.RGB)


__all__ = [
    'Skeletonize',
    'MedialAxis',
    'RemoveSmallObjects',
    'RemoveSmallHoles',
]
