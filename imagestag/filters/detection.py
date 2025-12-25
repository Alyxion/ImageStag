# ImageStag Filters - Detection Filters
"""
Object detection filters including face detection.

Detection filters output GeometryList - no image passthrough.
Use DrawGeometry to visualize detected objects on images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Any

from .base import AnalyzerFilter, Filter, FilterContext, FilterBackend, register_filter
from .geometry import GeometryFilter
from imagestag.definitions import ImsFramework
from imagestag.color import Color, Colors

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.geometry_list import GeometryList


@register_filter
@dataclass
class FaceDetector(GeometryFilter):
    """Detect faces in images using OpenCV Haar cascades.

    Returns a GeometryList containing Rectangle geometries for each detected face.
    Use DrawGeometry combiner to visualize faces on the original image.

    Uses multiple cascades (frontal, frontal-alt, profile) for better detection
    of faces at various angles.

    Parameters:
        scale_factor: Scale factor for detection pyramid (default 1.1)
        min_neighbors: Minimum neighbors for detection (default 5)
        min_size: Minimum face size as (width, height)
        use_profile: Also detect profile/side faces (default True)
        rotation_range: Max rotation angle for tilted faces (0=disabled, 15=try -15° to +15°)
        rotation_step: Step between rotation angles (default 5)
        color: Rectangle color for visualization (default green)
        thickness: Line thickness for visualization (default 2)

    Example:
        # Detect and visualize:
        Source -> FaceDetector -+-> DrawGeometry -> Output
                   |            |
                   +-- (image) -+

        # In pipeline string:
        'facedetector(min_neighbors=3)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'min_neighbors'

    scale_factor: float = 1.1
    min_neighbors: int = 5
    min_size: tuple = (30, 30)
    use_profile: bool = True
    rotation_range: int = 0  # Max rotation angle (0 = disabled, 15 = try -15 to +15)
    rotation_step: int = 5   # Step between rotation angles
    color: Color = field(default_factory=lambda: Colors.GREEN)
    thickness: int = 2

    def __post_init__(self):
        """Ensure color parameter is a Color object."""
        if not isinstance(self.color, Color):
            self.color = Color(self.color)

    _cascades: ClassVar[dict] = {}

    def _get_cascades(self) -> list:
        """Load Haar cascade classifiers."""
        import cv2

        if not FaceDetector._cascades:
            # Load multiple cascades for better coverage
            cascade_names = [
                'haarcascade_frontalface_default.xml',
                'haarcascade_frontalface_alt2.xml',
            ]
            for name in cascade_names:
                path = cv2.data.haarcascades + name
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    FaceDetector._cascades[name] = cascade

            # Profile cascades (left and right)
            profile_path = cv2.data.haarcascades + 'haarcascade_profileface.xml'
            profile = cv2.CascadeClassifier(profile_path)
            if not profile.empty():
                FaceDetector._cascades['profile'] = profile

        return FaceDetector._cascades

    def _boxes_overlap(self, box1: tuple, box2: tuple, threshold: float = 0.5) -> bool:
        """Check if two boxes overlap significantly."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        # Calculate intersection
        ix1 = max(x1, x2)
        iy1 = max(y1, y2)
        ix2 = min(x1 + w1, x2 + w2)
        iy2 = min(y1 + h1, y2 + h2)

        if ix2 <= ix1 or iy2 <= iy1:
            return False

        intersection = (ix2 - ix1) * (iy2 - iy1)
        area1 = w1 * h1
        area2 = w2 * h2
        min_area = min(area1, area2)

        return intersection / min_area > threshold

    def _merge_detections(self, all_faces: list) -> list:
        """Merge overlapping detections from multiple cascades."""
        if not all_faces:
            return []

        # Sort by area (larger first)
        sorted_faces = sorted(all_faces, key=lambda f: f[2] * f[3], reverse=True)
        merged = []

        for face in sorted_faces:
            # Check if this face overlaps with any already merged face
            is_duplicate = False
            for existing in merged:
                if self._boxes_overlap(face, existing):
                    is_duplicate = True
                    break
            if not is_duplicate:
                merged.append(face)

        return merged

    def _rotate_image(self, gray, angle: float):
        """Rotate image and return rotated image + transformation matrix."""
        import cv2
        import numpy as np

        h, w = gray.shape[:2]
        center = (w / 2, h / 2)

        # Get rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calculate new image bounds
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int(h * sin + w * cos)
        new_h = int(h * cos + w * sin)

        # Adjust rotation matrix for new bounds
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2

        rotated = cv2.warpAffine(gray, M, (new_w, new_h))
        return rotated, M, (w, h)

    def _transform_box_back(self, box: tuple, M, orig_size: tuple) -> tuple:
        """Transform a bounding box from rotated space back to original."""
        import cv2
        import numpy as np

        x, y, w, h = box
        orig_w, orig_h = orig_size

        # Get inverse transformation
        M_inv = cv2.invertAffineTransform(M)

        # Transform all 4 corners of the box
        corners = np.array([
            [x, y],
            [x + w, y],
            [x + w, y + h],
            [x, y + h]
        ], dtype=np.float32)

        # Apply inverse transform
        ones = np.ones((4, 1))
        corners_h = np.hstack([corners, ones])
        transformed = corners_h @ M_inv.T

        # Get bounding box of transformed corners, strictly within image bounds
        min_x = max(0, int(np.min(transformed[:, 0])))
        min_y = max(0, int(np.min(transformed[:, 1])))
        max_x = min(orig_w - 1, int(np.max(transformed[:, 0])))
        max_y = min(orig_h - 1, int(np.max(transformed[:, 1])))

        # Ensure valid box
        if max_x <= min_x or max_y <= min_y:
            return (0, 0, 0, 0)

        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def _detect_on_image(self, gray, cascades) -> list:
        """Run detection on a single image with all cascades."""
        import cv2

        all_faces = []

        for name, cascade in cascades.items():
            if name == 'profile' and not self.use_profile:
                continue

            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=self.scale_factor,
                minNeighbors=self.min_neighbors,
                minSize=self.min_size,
            )
            all_faces.extend([tuple(f) for f in faces])

            # For profile, also try flipped image
            if name == 'profile':
                h, w = gray.shape[:2]
                flipped = cv2.flip(gray, 1)
                faces_flipped = cascade.detectMultiScale(
                    flipped,
                    scaleFactor=self.scale_factor,
                    minNeighbors=self.min_neighbors,
                    minSize=self.min_size,
                )
                for (x, y, fw, fh) in faces_flipped:
                    all_faces.append((w - x - fw, y, fw, fh))

        return all_faces

    def detect(self, image: 'Image') -> 'GeometryList':
        import cv2
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import GeometryList, Rectangle, GeometryMeta

        gray = image.get_pixels(PixelFormat.GRAY)
        cascades = self._get_cascades()

        all_faces = []

        # Detect on original image
        all_faces.extend(self._detect_on_image(gray, cascades))

        # Detect on rotated images for tilted faces
        if self.rotation_range > 0 and self.rotation_step > 0:
            # Generate angles: e.g., range=15, step=5 -> [-15, -10, -5, 5, 10, 15]
            angles = []
            for a in range(self.rotation_step, self.rotation_range + 1, self.rotation_step):
                angles.extend([-a, a])
            for angle in angles:
                rotated, M, orig_size = self._rotate_image(gray, angle)
                rotated_faces = self._detect_on_image(rotated, cascades)

                # Transform faces back to original coordinates
                for face in rotated_faces:
                    transformed = self._transform_box_back(face, M, orig_size)
                    # Only add if box is valid
                    if transformed[2] > 10 and transformed[3] > 10:
                        all_faces.append(transformed)

        # Merge overlapping detections
        merged_faces = self._merge_detections(all_faces)

        geom_list = GeometryList(width=image.width, height=image.height)

        for (x, y, w, h) in merged_faces:
            geom_list.add(Rectangle(
                x=float(x),
                y=float(y),
                width=float(w),
                height=float(h),
                meta=GeometryMeta(
                    label='face',
                    color=self.color,
                    thickness=self.thickness,
                ),
            ))

        return geom_list


@register_filter
@dataclass
class EyeDetector(GeometryFilter):
    """Detect eyes in images using OpenCV Haar cascades.

    Returns a GeometryList containing Rectangle geometries for each detected eye.
    Use DrawGeometry combiner to visualize eyes on the original image.

    Parameters:
        scale_factor: Scale factor for detection pyramid (default 1.1)
        min_neighbors: Minimum neighbors for detection (default 5)
        color: Rectangle color for visualization (default red)
        thickness: Line thickness for visualization (default 2)

    Example:
        'eyedetector(min_neighbors=3)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    scale_factor: float = 1.1
    min_neighbors: int = 5
    color: Color = field(default_factory=lambda: Colors.RED)
    thickness: int = 2

    def __post_init__(self):
        """Ensure color parameter is a Color object."""
        if not isinstance(self.color, Color):
            self.color = Color(self.color)

    _cascade = None

    def _get_cascade(self):
        import cv2
        if EyeDetector._cascade is None:
            cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
            EyeDetector._cascade = cv2.CascadeClassifier(cascade_path)
        return EyeDetector._cascade

    def detect(self, image: 'Image') -> 'GeometryList':
        import cv2
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import GeometryList, Rectangle, GeometryMeta

        gray = image.get_pixels(PixelFormat.GRAY)
        cascade = self._get_cascade()

        eyes = cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
        )

        geom_list = GeometryList(width=image.width, height=image.height)

        for (x, y, w, h) in eyes:
            geom_list.add(Rectangle(
                x=float(x),
                y=float(y),
                width=float(w),
                height=float(h),
                meta=GeometryMeta(
                    label='eye',
                    color=self.color,
                    thickness=self.thickness,
                ),
            ))

        return geom_list


@register_filter
@dataclass
class ContourDetector(GeometryFilter):
    """Detect contours in images.

    Returns a GeometryList containing Polygon geometries for each detected contour.
    Works best on binary or edge-detected images.

    Parameters:
        threshold: Threshold value for binarization (0 = use input as-is)
        min_area: Minimum contour area to include
        color: Contour color for visualization (default green)
        thickness: Line thickness for visualization (default 2)

    Example:
        'contourdetector(threshold=128,min_area=200)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'threshold'

    threshold: int = 0
    min_area: float = 100.0
    color: Color = field(default_factory=lambda: Colors.GREEN)
    thickness: int = 2

    def __post_init__(self):
        """Ensure color parameter is a Color object."""
        if not isinstance(self.color, Color):
            self.color = Color(self.color)

    def detect(self, image: 'Image') -> 'GeometryList':
        import cv2
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import GeometryList, Polygon, GeometryMeta

        gray = image.get_pixels(PixelFormat.GRAY)

        # Apply threshold if specified
        if self.threshold > 0:
            _, binary = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
        else:
            binary = gray

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        geom_list = GeometryList(width=image.width, height=image.height)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                # Convert contour to list of (x, y) tuples
                points = [(float(p[0][0]), float(p[0][1])) for p in contour]
                geom_list.add(Polygon(
                    points=points,
                    closed=True,
                    meta=GeometryMeta(
                        label='contour',
                        color=self.color,
                        thickness=self.thickness,
                        extra={'area': float(area)},
                    ),
                ))

        return geom_list
