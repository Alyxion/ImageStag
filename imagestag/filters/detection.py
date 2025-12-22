# ImageStag Filters - Detection Filters
"""
Object detection filters including face detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Any

from .base import AnalyzerFilter, Filter, FilterContext, FilterBackend, register_filter

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class FaceDetector(AnalyzerFilter):
    """Detect faces in images using OpenCV Haar cascades.

    Stores detected face bounding boxes in context. Can optionally draw
    rectangles around detected faces.

    Parameters:
        draw: Draw rectangles around detected faces (default False)
        color: Rectangle color as (R, G, B) tuple
        thickness: Rectangle line thickness
        scale_factor: Scale factor for detection pyramid (default 1.1)
        min_neighbors: Minimum neighbors for detection (default 5)
        min_size: Minimum face size as (width, height)

    Result stored as list of dicts with keys: x, y, width, height, confidence

    Example:
        'facedetector' - just detect
        'facedetector(draw=true)' - detect and draw
    """
    draw: bool = False
    color: tuple = (0, 255, 0)
    thickness: int = 2
    scale_factor: float = 1.1
    min_neighbors: int = 5
    min_size: tuple = (30, 30)

    result_key: str = 'faces'
    _cascade = None

    def _get_cascade(self):
        """Load Haar cascade classifier."""
        import cv2
        if FaceDetector._cascade is None:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            FaceDetector._cascade = cv2.CascadeClassifier(cascade_path)
        return FaceDetector._cascade

    def analyze(self, image: 'Image') -> list[dict]:
        import cv2
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)
        cascade = self._get_cascade()

        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
        )

        results = []
        for (x, y, w, h) in faces:
            results.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
            })

        return results

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        # Run analysis
        faces = self.analyze(image)

        # Store in context
        if context is not None and self.store_in_context:
            context[self.result_key] = faces

        if self.store_in_metadata:
            image.metadata[self.result_key] = faces

        # Optionally draw rectangles
        if self.draw and faces:
            import cv2
            from imagestag import Image as ImageClass
            from imagestag.pixel_format import PixelFormat

            pixels = image.get_pixels(PixelFormat.RGB).copy()
            # Convert RGB color to BGR for OpenCV
            bgr_color = (self.color[2], self.color[1], self.color[0])

            for face in faces:
                x, y, w, h = face['x'], face['y'], face['width'], face['height']
                # OpenCV expects BGR but we're working with RGB array
                cv2.rectangle(pixels, (x, y), (x + w, y + h),
                            self.color, self.thickness)

            return ImageClass(pixels, pixel_format=PixelFormat.RGB)

        return image


@register_filter
@dataclass
class EyeDetector(AnalyzerFilter):
    """Detect eyes in images using OpenCV Haar cascades.

    Parameters:
        draw: Draw rectangles around detected eyes
        color: Rectangle color as (R, G, B)
        thickness: Rectangle line thickness

    Result stored as list of dicts with keys: x, y, width, height

    Example:
        'eyedetector(draw=true)'
    """
    draw: bool = False
    color: tuple = (255, 0, 0)
    thickness: int = 2
    scale_factor: float = 1.1
    min_neighbors: int = 5

    result_key: str = 'eyes'
    _cascade = None

    def _get_cascade(self):
        import cv2
        if EyeDetector._cascade is None:
            cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
            EyeDetector._cascade = cv2.CascadeClassifier(cascade_path)
        return EyeDetector._cascade

    def analyze(self, image: 'Image') -> list[dict]:
        import cv2
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)
        cascade = self._get_cascade()

        eyes = cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
        )

        results = []
        for (x, y, w, h) in eyes:
            results.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
            })

        return results

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        eyes = self.analyze(image)

        if context is not None and self.store_in_context:
            context[self.result_key] = eyes

        if self.store_in_metadata:
            image.metadata[self.result_key] = eyes

        if self.draw and eyes:
            import cv2
            from imagestag import Image as ImageClass
            from imagestag.pixel_format import PixelFormat

            pixels = image.get_pixels(PixelFormat.RGB).copy()

            for eye in eyes:
                x, y, w, h = eye['x'], eye['y'], eye['width'], eye['height']
                cv2.rectangle(pixels, (x, y), (x + w, y + h),
                            self.color, self.thickness)

            return ImageClass(pixels, pixel_format=PixelFormat.RGB)

        return image


@register_filter
@dataclass
class ContourDetector(AnalyzerFilter):
    """Detect contours in images.

    Finds contours (boundaries) in the image. Works best on binary
    or edge-detected images.

    Parameters:
        threshold: Threshold value for binarization (0 = use input as-is)
        min_area: Minimum contour area to include
        draw: Draw contours on image
        color: Contour color as (R, G, B)
        thickness: Line thickness (-1 for filled)

    Result stored as list of contour dicts with keys: area, perimeter, bbox

    Example:
        'contourdetector(threshold=128,draw=true)'
    """
    threshold: int = 0
    min_area: float = 100.0
    draw: bool = False
    color: tuple = (0, 255, 0)
    thickness: int = 2

    result_key: str = 'contours'
    _primary_param: ClassVar[str] = 'threshold'

    def analyze(self, image: 'Image') -> list[dict]:
        import cv2
        from imagestag.pixel_format import PixelFormat

        gray = image.get_pixels(PixelFormat.GRAY)

        # Apply threshold if specified
        if self.threshold > 0:
            _, binary = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
        else:
            binary = gray

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        results = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                perimeter = cv2.arcLength(contour, True)
                x, y, w, h = cv2.boundingRect(contour)
                results.append({
                    'area': float(area),
                    'perimeter': float(perimeter),
                    'bbox': {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)},
                    'points': contour.tolist(),
                })

        return results

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        import cv2
        from imagestag.pixel_format import PixelFormat

        contour_info = self.analyze(image)

        if context is not None and self.store_in_context:
            context[self.result_key] = contour_info

        if self.store_in_metadata:
            image.metadata[self.result_key] = contour_info

        if self.draw and contour_info:
            import numpy as np
            from imagestag import Image as ImageClass

            pixels = image.get_pixels(PixelFormat.RGB).copy()

            for info in contour_info:
                contour = np.array(info['points'], dtype=np.int32)
                cv2.drawContours(pixels, [contour], -1, self.color, self.thickness)

            return ImageClass(pixels, pixel_format=PixelFormat.RGB)

        return image
