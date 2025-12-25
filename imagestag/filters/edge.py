# ImageStag Filters - Edge Detection
"""
Edge detection filters using OpenCV.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, FilterBackend, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class Canny(Filter):
    """Canny edge detection.

    Detects edges using the Canny algorithm with hysteresis thresholding.

    Parameters:
        threshold1: Lower threshold for hysteresis (default 100)
        threshold2: Upper threshold for hysteresis (default 200)
        aperture_size: Sobel kernel size (3, 5, or 7)

    Example:
        'canny(100,200)' or 'canny(threshold1=50,threshold2=150)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    threshold1: float = 100.0
    threshold2: float = 200.0
    aperture_size: int = 3

    _primary_param: ClassVar[str] = 'threshold1'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        # Convert to grayscale for edge detection
        gray = image.get_pixels(PixelFormat.GRAY)

        # Apply Canny
        edges = cv2.Canny(gray, self.threshold1, self.threshold2,
                         apertureSize=self.aperture_size)

        # Convert back to RGB (edges as white on black)
        rgb = np.stack([edges, edges, edges], axis=-1)
        return ImageClass(rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class Sobel(Filter):
    """Sobel edge detection.

    Computes gradient using Sobel operator.

    Parameters:
        dx: Order of derivative in x direction (0 or 1)
        dy: Order of derivative in y direction (0 or 1)
        kernel_size: Sobel kernel size (1, 3, 5, or 7)
        scale: Scale factor for computed values
        normalize: Normalize output to 0-255 range

    Example:
        'sobel(1,0)' for horizontal edges
        'sobel(0,1)' for vertical edges
        'sobel(1,1)' for both directions
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    dx: int = 1
    dy: int = 1
    kernel_size: int = 3
    scale: float = 1.0
    normalize: bool = True

    _primary_param: ClassVar[str] = 'dx'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute Sobel derivatives
        if self.dx > 0 and self.dy > 0:
            # Combine both directions
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=self.kernel_size)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=self.kernel_size)
            sobel = np.sqrt(sobel_x**2 + sobel_y**2)
        else:
            sobel = cv2.Sobel(gray, cv2.CV_64F, self.dx, self.dy,
                             ksize=self.kernel_size, scale=self.scale)
            sobel = np.abs(sobel)

        # Normalize to 0-255
        if self.normalize:
            sobel = (sobel / sobel.max() * 255).astype(np.uint8)
        else:
            sobel = np.clip(sobel, 0, 255).astype(np.uint8)

        rgb = np.stack([sobel, sobel, sobel], axis=-1)
        return ImageClass(rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class Laplacian(Filter):
    """Laplacian edge detection.

    Computes Laplacian of the image for edge detection.

    Parameters:
        kernel_size: Kernel size (1, 3, 5, or 7)
        scale: Scale factor
        normalize: Normalize output to 0-255 range

    Example:
        'laplacian(3)' or 'laplacian(kernel_size=5)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    kernel_size: int = 3
    scale: float = 1.0
    normalize: bool = True

    _primary_param: ClassVar[str] = 'kernel_size'

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)

        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=self.kernel_size,
                                  scale=self.scale)
        laplacian = np.abs(laplacian)

        if self.normalize:
            if laplacian.max() > 0:
                laplacian = (laplacian / laplacian.max() * 255).astype(np.uint8)
            else:
                laplacian = laplacian.astype(np.uint8)
        else:
            laplacian = np.clip(laplacian, 0, 255).astype(np.uint8)

        rgb = np.stack([laplacian, laplacian, laplacian], axis=-1)
        return ImageClass(rgb, pixel_format=PixelFormat.RGB)


@register_filter
@dataclass
class EdgeEnhance(Filter):
    """Enhance edges in image.

    Uses PIL's edge enhancement filters.

    Parameters:
        strength: 'normal' or 'more'

    Example:
        'edgeenhance(normal)' or 'edgeenhance(more)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    strength: str = 'normal'

    _primary_param: ClassVar[str] = 'strength'

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from PIL import ImageFilter
        from imagestag import Image as ImageClass

        pil_img = image.to_pil()

        if self.strength == 'more':
            result = pil_img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        else:
            result = pil_img.filter(ImageFilter.EDGE_ENHANCE)

        return ImageClass(result)


@register_filter
@dataclass
class Scharr(Filter):
    """Scharr edge detection.

    Computes gradients using the Scharr operator, which is more accurate
    than Sobel for rotational symmetry.

    Parameters:
        dx: Order of derivative in x direction (0 or 1)
        dy: Order of derivative in y direction (0 or 1)
        scale: Scale factor for computed values
        normalize: Normalize output to 0-255 range

    Example:
        'scharr(1,0)' for horizontal edges
        'scharr(0,1)' for vertical edges
        'scharr(1,1)' for both directions
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'dx'

    dx: int = 1
    dy: int = 1
    scale: float = 1.0
    normalize: bool = True

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)

        # Compute Scharr derivatives
        if self.dx > 0 and self.dy > 0:
            # Combine both directions
            scharr_x = cv2.Scharr(gray, cv2.CV_64F, 1, 0, scale=self.scale)
            scharr_y = cv2.Scharr(gray, cv2.CV_64F, 0, 1, scale=self.scale)
            scharr = np.sqrt(scharr_x**2 + scharr_y**2)
        elif self.dx > 0:
            scharr = cv2.Scharr(gray, cv2.CV_64F, 1, 0, scale=self.scale)
            scharr = np.abs(scharr)
        else:
            scharr = cv2.Scharr(gray, cv2.CV_64F, 0, 1, scale=self.scale)
            scharr = np.abs(scharr)

        # Normalize to 0-255
        if self.normalize:
            if scharr.max() > 0:
                scharr = (scharr / scharr.max() * 255).astype(np.uint8)
            else:
                scharr = scharr.astype(np.uint8)
        else:
            scharr = np.clip(scharr, 0, 255).astype(np.uint8)

        rgb = np.stack([scharr, scharr, scharr], axis=-1)
        return ImageClass(rgb, pixel_format=PixelFormat.RGB)
