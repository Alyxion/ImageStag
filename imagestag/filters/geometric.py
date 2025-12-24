# ImageStag Filters - Geometric Transforms
"""
Geometric transform filters: Resize, Crop, Rotate, Flip, Lens, Perspective.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, TYPE_CHECKING

from PIL import ImageOps

from .base import Filter, FilterContext, register_filter

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class Resize(Filter):
    """Resize image.

    Either specify size (width, height) or scale factor.
    """
    size: tuple[int, int] | None = None
    scale: float | None = None
    _primary_param = 'scale'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag.interpolation import InterpolationMethod

        if self.scale is not None:
            new_width = int(image.width * self.scale)
            new_height = int(image.height * self.scale)
            return image.resized((new_width, new_height), InterpolationMethod.LANCZOS)
        elif self.size is not None:
            return image.resized(self.size, InterpolationMethod.LANCZOS)
        else:
            return image

    def to_dict(self) -> dict[str, Any]:
        data = {'type': self.type}
        if self.scale is not None:
            data['scale'] = self.scale
        if self.size is not None:
            data['size'] = list(self.size)
        return data


@register_filter
@dataclass
class Crop(Filter):
    """Crop image region.

    x, y: Top-left corner
    width, height: Size of crop region
    """
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        if self.width <= 0 or self.height <= 0:
            return image
        # PIL crop uses (left, upper, right, lower) where right/lower are exclusive
        pil_img = image.to_pil()
        x2 = min(self.x + self.width, image.width)
        y2 = min(self.y + self.height, image.height)
        result = pil_img.crop((self.x, self.y, x2, y2))
        return Img(result)


@register_filter
@dataclass
class CenterCrop(Filter):
    """Crop from center of image."""
    width: int = 0
    height: int = 0

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        if self.width <= 0 or self.height <= 0:
            return image

        x = (image.width - self.width) // 2
        y = (image.height - self.height) // 2
        x = max(0, x)
        y = max(0, y)
        # PIL crop uses (left, upper, right, lower) where right/lower are exclusive
        pil_img = image.to_pil()
        x2 = min(x + self.width, image.width)
        y2 = min(y + self.height, image.height)
        result = pil_img.crop((x, y, x2, y2))
        return Img(result)


@register_filter
@dataclass
class Rotate(Filter):
    """Rotate image.

    angle: Rotation in degrees, counter-clockwise
    expand: If True, expand canvas to fit rotated image
    fill_color: Background color for empty areas
    """
    angle: float = 0.0
    expand: bool = False
    fill_color: tuple[int, int, int] = (0, 0, 0)
    _primary_param = 'angle'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.rotate(
            self.angle,
            expand=self.expand,
            fillcolor=self.fill_color
        )
        return Img(result)


@register_filter
@dataclass
class Flip(Filter):
    """Flip image horizontally and/or vertically."""
    horizontal: bool = False
    vertical: bool = False

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()

        if self.horizontal:
            pil_img = ImageOps.mirror(pil_img)
        if self.vertical:
            pil_img = ImageOps.flip(pil_img)

        return Img(pil_img)


@register_filter
@dataclass
class LensDistortion(Filter):
    """Apply or correct radial lens distortion.

    Uses the Brown-Conrady distortion model with radial coefficients.
    Positive k1 creates barrel distortion, negative creates pincushion.

    Parameters:
        k1: Primary radial distortion coefficient (default 0)
        k2: Secondary radial distortion coefficient (default 0)
        k3: Tertiary radial distortion coefficient (default 0)
        p1: First tangential distortion coefficient (default 0)
        p2: Second tangential distortion coefficient (default 0)

    Common values:
        - Barrel distortion correction: k1=-0.1 to -0.3
        - Pincushion distortion correction: k1=0.1 to 0.3
        - Fish-eye effect: k1=-0.5 or stronger

    Example:
        'lensdistortion(k1=-0.2)' - correct moderate barrel distortion
        'lensdistortion(k1=0.3)' - apply pincushion effect

    For coordinate mapping between distorted and undistorted space:
        result, transform = filter.apply_with_transform(image)
        undist_pt = transform.forward((100, 200))  # distorted -> undistorted
        dist_pt = transform.inverse((150, 180))    # undistorted -> distorted
    """
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0
    p1: float = 0.0
    p2: float = 0.0

    _primary_param: ClassVar[str] = 'k1'

    def _build_matrices(self, w: int, h: int):
        """Build camera matrix and distortion coefficients."""
        import numpy as np

        focal_length = max(w, h)
        cx, cy = w / 2, h / 2
        camera_matrix = np.array([
            [focal_length, 0, cx],
            [0, focal_length, cy],
            [0, 0, 1]
        ], dtype=np.float64)

        dist_coeffs = np.array([self.k1, self.k2, self.p1, self.p2, self.k3], dtype=np.float64)

        return camera_matrix, dist_coeffs

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        result, _ = self.apply_with_transform(image, context)
        return result

    def apply_with_transform(
        self,
        image: 'Image',
        context: FilterContext | None = None
    ) -> tuple['Image', 'LensTransform']:
        """Apply filter and return coordinate transform.

        :returns: Tuple of (result_image, LensTransform).
            The transform maps between distorted and undistorted coordinates.
        """
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat
        from .transforms import LensTransform, IdentityTransform

        pixels = image.get_pixels(PixelFormat.RGB)
        h, w = pixels.shape[:2]

        # No distortion case
        if self.k1 == 0 and self.k2 == 0 and self.k3 == 0 and self.p1 == 0 and self.p2 == 0:
            identity = IdentityTransform()
            # Return identity-like LensTransform
            camera_matrix, dist_coeffs = self._build_matrices(w, h)
            transform = LensTransform(
                camera_matrix=camera_matrix,
                dist_coeffs=np.zeros(5, dtype=np.float64),
                new_camera_matrix=camera_matrix.copy(),
                image_size=(w, h)
            )
            return image, transform

        camera_matrix, dist_coeffs = self._build_matrices(w, h)

        # Get optimal new camera matrix to include all pixels
        new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs, (w, h), 1, (w, h)
        )

        # Undistort
        result = cv2.undistort(pixels, camera_matrix, dist_coeffs, None, new_camera_matrix)

        # Create transform for coordinate mapping
        transform = LensTransform(
            camera_matrix=camera_matrix,
            dist_coeffs=dist_coeffs,
            new_camera_matrix=new_camera_matrix,
            image_size=(w, h)
        )

        return ImageClass(result, pixel_format=PixelFormat.RGB), transform


@register_filter
@dataclass
class Perspective(Filter):
    """Apply perspective transformation.

    Transform image using four source and destination point pairs.
    Points are specified as (x, y) coordinates.

    Parameters:
        src_points: Four source points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
        dst_points: Four destination points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
        output_size: Output size (width, height) or None to auto-calculate

    If only src_points provided, dst_points defaults to image corners
    (perspective correction mode).

    Example:
        # Correct skewed document
        perspective = Perspective(
            src_points=[(10, 20), (590, 30), (600, 470), (5, 460)],
            dst_points=[(0, 0), (600, 0), (600, 480), (0, 480)]
        )

    For coordinate mapping between original and corrected space:
        result, transform = filter.apply_with_transform(image)
        corrected_pt = transform.forward((100, 200))  # original -> corrected
        original_pt = transform.inverse((150, 180))   # corrected -> original
    """
    src_points: tuple | list | None = None
    dst_points: tuple | list | None = None
    output_size: tuple[int, int] | None = None

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        result, _ = self.apply_with_transform(image, context)
        return result

    def apply_with_transform(
        self,
        image: 'Image',
        context: FilterContext | None = None
    ) -> tuple['Image', 'PerspectiveTransform']:
        """Apply filter and return coordinate transform.

        :returns: Tuple of (result_image, PerspectiveTransform).
            The transform maps between original and corrected coordinates.
        """
        import cv2
        import numpy as np
        from imagestag import Image as ImageClass
        from imagestag.pixel_format import PixelFormat
        from .transforms import PerspectiveTransform

        if self.src_points is None:
            # No transform - return identity
            pixels = image.get_pixels(PixelFormat.RGB)
            h, w = pixels.shape[:2]
            # Create identity perspective transform
            src = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype=np.float32)
            transform = PerspectiveTransform.from_points(src, src)
            return image, transform

        pixels = image.get_pixels(PixelFormat.RGB)
        h, w = pixels.shape[:2]

        # Convert points to numpy arrays
        src = np.array(self.src_points, dtype=np.float32)

        # Default destination: image corners
        if self.dst_points is None:
            dst = np.array([
                [0, 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [0, h - 1]
            ], dtype=np.float32)
        else:
            dst = np.array(self.dst_points, dtype=np.float32)

        # Calculate output size
        if self.output_size is not None:
            out_w, out_h = self.output_size
        else:
            # Use bounding box of destination points
            out_w = int(np.max(dst[:, 0]) - np.min(dst[:, 0])) + 1
            out_h = int(np.max(dst[:, 1]) - np.min(dst[:, 1])) + 1
            # Ensure minimum size
            out_w = max(out_w, w)
            out_h = max(out_h, h)

        # Create transform for coordinate mapping
        transform = PerspectiveTransform.from_points(src, dst)

        # Apply transform
        result = cv2.warpPerspective(pixels, transform.matrix, (out_w, out_h))

        return ImageClass(result, pixel_format=PixelFormat.RGB), transform

    def to_dict(self) -> dict[str, Any]:
        data = {'type': self.type}
        if self.src_points is not None:
            data['src_points'] = list(self.src_points)
        if self.dst_points is not None:
            data['dst_points'] = list(self.dst_points)
        if self.output_size is not None:
            data['output_size'] = list(self.output_size)
        return data
