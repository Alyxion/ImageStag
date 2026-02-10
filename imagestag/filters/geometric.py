# ImageStag Filters - Geometric Transforms
"""
Geometric transform filters: Resize, Crop, Rotate, Flip, Lens, Perspective.
"""

from __future__ import annotations

from typing import Any, ClassVar, TYPE_CHECKING

from pydantic import Field, field_validator
from .base import Filter, FilterContext, register_filter
from imagestag.definitions import ImsFramework
from imagestag.color import Color, Colors

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
class Resize(Filter):
    """Resize image.

    Either specify size (width, height) or scale factor.
    Uses OpenCV for ~20x faster performance (does not preserve input framework).

    :param size: Target size as (width, height)
    :param scale: Scale factor (alternative to size)
    :param interpolation: Interpolation method ('lanczos', 'linear', 'area', 'cubic')
                         Default is 'lanczos' for quality, 'area' recommended for downscaling.
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.PIL]
    _preserve_framework: ClassVar[bool] = False  # Always use OpenCV for performance

    size: tuple[int, int] | None = None
    scale: float | None = None
    interpolation: str = 'lanczos'
    _primary_param: ClassVar[str] = 'scale'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        from imagestag.definitions import ImsFramework

        # Calculate target size
        if self.scale is not None:
            target_size = (int(image.width * self.scale), int(image.height * self.scale))
        elif self.size is not None:
            target_size = self.size
        else:
            return image

        # Always use OpenCV for performance (20x faster than PIL)
        try:
            import cv2

            # Map interpolation names to OpenCV constants
            interp_map = {
                'lanczos': cv2.INTER_LANCZOS4,
                'linear': cv2.INTER_LINEAR,
                'bilinear': cv2.INTER_LINEAR,
                'area': cv2.INTER_AREA,
                'cubic': cv2.INTER_CUBIC,
                'nearest': cv2.INTER_NEAREST,
            }
            cv_interp = interp_map.get(self.interpolation.lower(), cv2.INTER_LANCZOS4)

            # Get pixels in BGR format (OpenCV native)
            pixels = image.get_pixels(PixelFormat.BGR)

            # cv2.resize expects (width, height)
            resized = cv2.resize(pixels, target_size, interpolation=cv_interp)

            # Return as CV framework with BGR order
            return Img(resized, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)

        except ImportError:
            # Fall back to PIL
            from imagestag.interpolation import InterpolationMethod
            return image.resized(target_size, InterpolationMethod.LANCZOS)

    def to_dict(self) -> dict[str, Any]:
        data = {'type': self.type}
        if self.scale is not None:
            data['scale'] = self.scale
        if self.size is not None:
            data['size'] = list(self.size)
        if self.interpolation != 'lanczos':
            data['interpolation'] = self.interpolation
        return data


@register_filter
class Crop(Filter):
    """Crop image region.

    x, y: Top-left corner
    width, height: Size of crop region
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

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
class CenterCrop(Filter):
    """Crop from center of image."""

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

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
class Rotate(Filter):
    """Rotate image by angle in degrees.

    For 90°, 180°, 270° rotations, uses fast transpose operations.
    For other angles, uses interpolation with optional canvas expansion.

    Supports multiple backends for optimal performance on fixed angles.

    Parameters:
        angle: Rotation in degrees, counter-clockwise (0, 90, 180, 270, or any)
        expand: If True, expand canvas to fit rotated image (only for non-90° angles)
        fill: Background color as hex string, e.g., '#000000' (only for non-90° angles)
        backend: Processing backend ('auto', 'pil', 'cv', 'numpy')

    Example:
        'rotate 90'      - rotate 90° CCW (fast)
        'rotate 180'     - rotate 180° (fast)
        'rotate -90'     - rotate 90° CW (fast)
        'rotate 45'      - rotate 45° with interpolation
        'rotate 45 expand=true' - rotate with canvas expansion

    Aliases:
        'rot90', 'rot180', 'rot270' - shortcuts for fixed angles
        'rotcw', 'rotccw' - 90° clockwise/counter-clockwise
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL, ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'angle'

    angle: float = 0.0
    expand: bool = False
    fill: Color = Field(default_factory=lambda: Colors.BLACK)
    backend: str = 'auto'

    @field_validator('fill', mode='before')
    @classmethod
    def _coerce_color(cls, v):
        if isinstance(v, Color):
            return v
        return Color(v)

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img

        # Normalize angle to 0-360 range
        angle = self.angle % 360

        # Check if this is a fast 90° multiple (with tolerance for slider imprecision)
        for fast_angle in (0, 90, 180, 270):
            if abs(angle - fast_angle) < 0.01:
                return self._apply_fast(image, fast_angle)

        # General rotation with interpolation (PIL only)
        pil_img = image.to_pil()
        result = pil_img.rotate(
            self.angle,
            expand=self.expand,
            fillcolor=self.fill.to_int_rgb()
        )
        return Img(result)

    def _apply_fast(self, image: Image, angle: int) -> Image:
        """Fast rotation for 90° multiples using transpose."""
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        from PIL import Image as PILImage
        import numpy as np

        if angle == 0:
            return image

        backend = self.backend.lower()

        # Auto-select backend based on image framework
        if backend == 'auto':
            if image.framework == ImsFramework.CV:
                backend = 'cv'
            elif image.framework == ImsFramework.RAW:
                backend = 'numpy'
            else:
                backend = 'pil'

        if backend == 'cv':
            import cv2
            pixels = image.get_pixels(PixelFormat.RGB)
            if angle == 90:
                result = cv2.rotate(pixels, cv2.ROTATE_90_COUNTERCLOCKWISE)
            elif angle == 180:
                result = cv2.rotate(pixels, cv2.ROTATE_180)
            else:  # 270
                result = cv2.rotate(pixels, cv2.ROTATE_90_CLOCKWISE)
            return Img(result, pixel_format=PixelFormat.RGB)

        elif backend == 'numpy':
            pixels = image.get_pixels(PixelFormat.RGB)
            k = angle // 90  # 1 for 90°, 2 for 180°, 3 for 270°
            result = np.rot90(pixels, k=k)
            return Img(result.copy(), pixel_format=PixelFormat.RGB)

        else:  # PIL
            pil_img = image.to_pil()
            if angle == 90:
                result = pil_img.transpose(PILImage.Transpose.ROTATE_90)
            elif angle == 180:
                result = pil_img.transpose(PILImage.Transpose.ROTATE_180)
            else:  # 270
                result = pil_img.transpose(PILImage.Transpose.ROTATE_270)
            return Img(result)


@register_filter
class Flip(Filter):
    """Flip image horizontally and/or vertically.

    Parameters:
        mode: Flip direction - 'h' (horizontal/mirror), 'v' (vertical), 'hv' or 'vh' (both)

    Example:
        'flip h'    - mirror horizontally (left-right)
        'flip v'    - flip vertically (top-bottom)
        'flip hv'   - flip both (rotate 180°)

    Aliases:
        'mirror' or 'fliplr' - horizontal flip
        'flipud' or 'flipv'  - vertical flip
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'mode'

    mode: str = ''  # 'h', 'v', 'hv', 'vh'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        from imagestag.filters.rotate import flip_horizontal, flip_vertical

        mode = self.mode.lower()
        horizontal = 'h' in mode
        vertical = 'v' in mode

        if not horizontal and not vertical:
            return image

        has_alpha = image.pixel_format in (PixelFormat.RGBA, PixelFormat.BGRA)
        pf = PixelFormat.RGBA if has_alpha else PixelFormat.RGB
        pixels = image.get_pixels(pf)
        if horizontal:
            pixels = flip_horizontal(pixels)
        if vertical:
            pixels = flip_vertical(pixels)
        return Img(pixels, pixel_format=pf)


@register_filter
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

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

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

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

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
