# ImageStag Filters - Ridge/Vessel Detection
"""
Ridge and vessel detection filters using scikit-image.

These filters are particularly useful for medical imaging:
- Blood vessel detection in retinal scans
- Vein detection in angiography
- Neural structure detection in microscopy

Requires scikit-image as an optional dependency.
Install with: pip install scikit-image
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, register_filter, _check_skimage
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
class Frangi(Filter):
    """Frangi vesselness filter for vessel/ridge detection.

    Detects tubular structures like blood vessels using the
    Hessian-based Frangi filter. Particularly effective for
    retinal scans and angiography images.

    Requires: scikit-image (optional dependency)

    Parameters:
        scale_min: Minimum sigma for Gaussian derivatives
        scale_max: Maximum sigma for Gaussian derivatives
        scale_step: Step size between scales
        beta1: Frangi correction constant (plate-like vs blob-like)
        beta2: Frangi correction constant (background threshold)
        black_ridges: If True, detect black ridges on white background

    Example:
        'frangi()' - default settings
        'frangi(scale_min=1,scale_max=10,black_ridges=false)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    scale_min: float = 1.0
    scale_max: float = 10.0
    scale_step: float = 2.0
    beta1: float = 0.5
    beta2: float = 15.0
    black_ridges: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import frangi
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale float image
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Apply Frangi filter
        sigmas = np.arange(self.scale_min, self.scale_max, self.scale_step)
        result = frangi(
            gray,
            sigmas=sigmas,
            beta=self.beta1,
            gamma=self.beta2,
            black_ridges=self.black_ridges,
        )

        # Normalize to 0-255
        if result.max() > 0:
            result = (result / result.max() * 255).astype(np.uint8)
        else:
            result = result.astype(np.uint8)

        result_rgb = np.stack([result, result, result], axis=-1)
        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
class Sato(Filter):
    """Sato tubeness filter for 2D/3D tubular structure detection.

    Similar to Frangi but uses different Hessian eigenvalue
    combinations, often preferred for 3D data.

    Requires: scikit-image (optional dependency)

    Parameters:
        scale_min: Minimum sigma for Gaussian derivatives
        scale_max: Maximum sigma for Gaussian derivatives
        scale_step: Step size between scales
        black_ridges: If True, detect black ridges on white background

    Example:
        'sato()' or 'sato(scale_min=0.5,scale_max=5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    scale_min: float = 1.0
    scale_max: float = 10.0
    scale_step: float = 2.0
    black_ridges: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import sato
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale float image
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Apply Sato filter
        sigmas = np.arange(self.scale_min, self.scale_max, self.scale_step)
        result = sato(
            gray,
            sigmas=sigmas,
            black_ridges=self.black_ridges,
        )

        # Normalize to 0-255
        if result.max() > 0:
            result = (result / result.max() * 255).astype(np.uint8)
        else:
            result = result.astype(np.uint8)

        result_rgb = np.stack([result, result, result], axis=-1)
        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
class Meijering(Filter):
    """Meijering neuriteness filter for neural structure detection.

    Optimized for detecting neurites (nerve cell extensions) in
    microscopy images. Uses a modification of the Frangi filter.

    Requires: scikit-image (optional dependency)

    Parameters:
        scale_min: Minimum sigma for Gaussian derivatives
        scale_max: Maximum sigma for Gaussian derivatives
        scale_step: Step size between scales
        black_ridges: If True, detect black ridges on white background

    Example:
        'meijering()' or 'meijering(scale_min=0.5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    scale_min: float = 1.0
    scale_max: float = 10.0
    scale_step: float = 2.0
    black_ridges: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import meijering
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale float image
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Apply Meijering filter
        sigmas = np.arange(self.scale_min, self.scale_max, self.scale_step)
        result = meijering(
            gray,
            sigmas=sigmas,
            black_ridges=self.black_ridges,
        )

        # Normalize to 0-255
        if result.max() > 0:
            result = (result / result.max() * 255).astype(np.uint8)
        else:
            result = result.astype(np.uint8)

        result_rgb = np.stack([result, result, result], axis=-1)
        return Img(result_rgb, pixel_format=PixelFormat.RGB)


@register_filter
class Hessian(Filter):
    """Hessian-based ridge detection (general-purpose).

    Computes the Hessian matrix eigenvalues at each pixel
    to detect ridges and edges at multiple scales.

    Requires: scikit-image (optional dependency)

    Parameters:
        scale_min: Minimum sigma for Gaussian derivatives
        scale_max: Maximum sigma for Gaussian derivatives
        scale_step: Step size between scales
        beta: Threshold for distinguishing ridges from noise
        black_ridges: If True, detect black ridges on white background

    Example:
        'hessian()' or 'hessian(scale_max=20)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    scale_min: float = 1.0
    scale_max: float = 10.0
    scale_step: float = 2.0
    beta: float = 0.5
    black_ridges: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        _check_skimage()
        from skimage.filters import hessian
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get grayscale float image
        gray = image.get_pixels(PixelFormat.GRAY).astype(np.float64) / 255.0

        # Apply Hessian filter
        sigmas = np.arange(self.scale_min, self.scale_max, self.scale_step)
        result = hessian(
            gray,
            sigmas=sigmas,
            black_ridges=self.black_ridges,
        )

        # Normalize to 0-255
        if result.max() > 0:
            result = (result / result.max() * 255).astype(np.uint8)
        else:
            result = result.astype(np.uint8)

        result_rgb = np.stack([result, result, result], axis=-1)
        return Img(result_rgb, pixel_format=PixelFormat.RGB)


__all__ = [
    'Frangi',
    'Sato',
    'Meijering',
    'Hessian',
]
