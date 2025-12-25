# ImageStag Filters - Geometry Detection and Drawing
"""
Filters for geometry detection (circles, lines, etc.) and visualization.

Geometry filters output ONLY GeometryList - no image passthrough.
Use DrawGeometry to visualize detected geometries on images.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Any

import numpy as np

from .base import Filter, FilterContext, register_filter
from .graph import CombinerFilter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.geometry_list import GeometryList


@dataclass
class GeometryFilter(Filter):
    """Base class for filters that output only GeometryList.

    Unlike regular filters, geometry filters return detected shapes
    without the original image. Use DrawGeometry combiner to visualize.

    Subclasses should override `detect()` to implement detection logic.
    """

    _output_ports: ClassVar[list[dict]] = [
        {'name': 'output', 'type': 'geometry'},
    ]

    @abstractmethod
    def detect(self, image: 'Image') -> 'GeometryList':
        """Detect geometries in the image.

        :param image: Input image to analyze.
        :returns: GeometryList containing detected shapes.
        """
        pass

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'GeometryList':
        """Apply detection and return geometry list.

        Note: This returns GeometryList, not Image. The type signature
        uses Union via FilterOutput to support this.
        """
        return self.detect(image)


@register_filter
@dataclass
class HoughCircleDetector(GeometryFilter):
    """Detect circles using Hough transform.

    Uses OpenCV's HoughCircles to detect circular shapes in images.
    Works best on edge-detected or high-contrast images.

    Parameters:
        dp: Inverse ratio of accumulator resolution (default 1.0)
        min_dist: Minimum distance between circle centers
        param1: Higher threshold for Canny edge detector
        param2: Accumulator threshold for circle centers
        min_radius: Minimum circle radius (0 = no minimum)
        max_radius: Maximum circle radius (0 = no maximum)

    Example:
        'houghcircledetector(min_dist=30,param2=50)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'min_dist'

    dp: float = 1.0
    min_dist: float = 20.0
    param1: float = 50.0
    param2: float = 30.0
    min_radius: int = 0
    max_radius: int = 0

    def detect(self, image: 'Image') -> 'GeometryList':
        import cv2
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import GeometryList, Circle, GeometryMeta
        from imagestag.color import Colors

        gray = image.get_pixels(PixelFormat.GRAY)

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=self.dp,
            minDist=self.min_dist,
            param1=self.param1,
            param2=self.param2,
            minRadius=self.min_radius,
            maxRadius=self.max_radius,
        )

        geom_list = GeometryList(width=image.width, height=image.height)

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for circle in circles[0, :]:
                cx, cy, radius = circle
                geom_list.add(Circle(
                    cx=float(cx),
                    cy=float(cy),
                    radius=float(radius),
                    meta=GeometryMeta(label='circle', color=Colors.RED),
                ))

        return geom_list


@register_filter
@dataclass
class HoughLineDetector(GeometryFilter):
    """Detect lines using probabilistic Hough transform.

    Uses OpenCV's HoughLinesP to detect line segments.
    Works best on edge-detected images.

    Parameters:
        rho: Distance resolution in pixels (default 1.0)
        theta: Angle resolution in radians (default pi/180)
        threshold: Accumulator threshold (default 100)
        min_length: Minimum line length (default 50)
        max_gap: Maximum gap between line segments (default 10)

    Example:
        'houghlinedetector(threshold=80,min_length=30)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'threshold'

    rho: float = 1.0
    theta: float = 0.0174533  # np.pi / 180
    threshold: int = 100
    min_length: float = 50.0
    max_gap: float = 10.0

    def detect(self, image: 'Image') -> 'GeometryList':
        import cv2
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import GeometryList, Line, GeometryMeta
        from imagestag.color import Colors

        gray = image.get_pixels(PixelFormat.GRAY)

        # HoughLinesP expects edge-detected image, so apply Canny
        edges = cv2.Canny(gray, 50, 150)

        lines = cv2.HoughLinesP(
            edges,
            rho=self.rho,
            theta=self.theta,
            threshold=self.threshold,
            minLineLength=self.min_length,
            maxLineGap=self.max_gap,
        )

        geom_list = GeometryList(width=image.width, height=image.height)

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                geom_list.add(Line(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    meta=GeometryMeta(label='line', color=Colors.RED),
                ))

        return geom_list


@register_filter
@dataclass
class DrawGeometry(CombinerFilter):
    """Draw geometries onto an image.

    Combines an image with a GeometryList, drawing each geometry
    using its metadata styles (color, thickness, filled).

    Inputs:
        image: Base image to draw on
        geometry: GeometryList containing shapes to draw

    Parameters:
        use_geometry_styles: Use per-geometry colors/thickness (default True)
        color: Default color as hex string (e.g., "#FF0000")
        thickness: Default line thickness

    Example:
        Source -> FaceDetector -> DrawGeometry -> Output
                      |              ^
                      +-- (image) ---+
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.RAW]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'input', 'type': 'image', 'description': 'Base image'},
        {'name': 'geometry', 'type': 'geometry', 'description': 'Geometries to draw'},
    ]

    color: str = "#00FF00"  # Green - hex string for UI color picker
    thickness: int = 2

    def apply_multi(
        self,
        images: dict[str, Any],
        contexts: dict[str, FilterContext] | None = None
    ) -> 'Image':
        import cv2
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import (
            GeometryList, Rectangle, Circle, Ellipse, Line, Polygon
        )
        from imagestag.color import Color

        # Get inputs by port name
        image = images.get('input') or images.get('image')  # 'image' for legacy
        if image is None and self.inputs:
            image = images.get(self.inputs[0])
        geom_input = images.get('geometry')
        if geom_input is None and len(self.inputs) > 1:
            geom_input = images.get(self.inputs[1])

        if image is None:
            raise ValueError("DrawGeometry requires an image input")

        # If no geometry, return image unchanged
        if geom_input is None:
            return image

        # Handle GeometryList input
        if not isinstance(geom_input, GeometryList):
            # Might be passed as first value if not using port names
            return image

        geom_list = geom_input

        # Get pixels for drawing (use RGB, convert to BGR for OpenCV)
        pixels = image.get_pixels(PixelFormat.RGB).copy()

        for geom in geom_list:
            # Always use custom color/thickness from UI
            draw_color = Color(self.color).to_int_rgb()
            draw_thickness = self.thickness
            filled = False

            thickness_cv = -1 if filled else draw_thickness

            if isinstance(geom, Rectangle):
                pt1 = (int(geom.x), int(geom.y))
                pt2 = (int(geom.x + geom.width), int(geom.y + geom.height))
                cv2.rectangle(pixels, pt1, pt2, draw_color, thickness_cv)

            elif isinstance(geom, Circle):
                center = (int(geom.cx), int(geom.cy))
                cv2.circle(pixels, center, int(geom.radius), draw_color, thickness_cv)

            elif isinstance(geom, Ellipse):
                center = (int(geom.cx), int(geom.cy))
                axes = (int(geom.rx), int(geom.ry))
                cv2.ellipse(pixels, center, axes, geom.angle, 0, 360, draw_color, thickness_cv)

            elif isinstance(geom, Line):
                pt1 = (int(geom.x1), int(geom.y1))
                pt2 = (int(geom.x2), int(geom.y2))
                cv2.line(pixels, pt1, pt2, draw_color, draw_thickness)

            elif isinstance(geom, Polygon):
                pts = geom.to_numpy().reshape((-1, 1, 2))
                if filled:
                    cv2.fillPoly(pixels, [pts], draw_color)
                else:
                    cv2.polylines(pixels, [pts], geom.closed, draw_color, draw_thickness)

        return Img(pixels, pixel_format=PixelFormat.RGB)

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Single input fallback - returns image unchanged."""
        return image


@register_filter
@dataclass
class ExtractRegions(CombinerFilter):
    """Extract image regions based on geometry bounding boxes.

    Takes an image and GeometryList, crops out each region as a
    separate ImageList. The ImageList contains metadata for each region
    so it can be merged back later.

    Inputs:
        image: Source image to crop from
        geometry: GeometryList defining regions

    Parameters:
        padding: Extra pixels around each bounding box (default 0)
        min_size: Minimum region size (skip smaller regions)

    Outputs:
        output: ImageList with cropped regions and metadata
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'input', 'type': 'image', 'description': 'Source image'},
        {'name': 'geometry', 'type': 'geometry', 'description': 'Regions to extract'},
    ]
    _output_ports: ClassVar[list[dict]] = [
        {'name': 'output', 'type': 'image_list', 'description': 'ImageList with regions'},
    ]

    padding: int = 0
    min_size: int = 1

    def apply_multi(
        self,
        images: dict[str, Any],
        contexts: dict[str, FilterContext] | None = None
    ) -> 'ImageList':
        from imagestag.geometry_list import GeometryList, Rectangle
        from imagestag.image_list import ImageList, RegionMeta

        # Get inputs by port name
        image = images.get('input') or images.get('image')  # 'image' for legacy
        if image is None and self.inputs:
            image = images.get(self.inputs[0])
        geom_input = images.get('geometry')
        if geom_input is None and len(self.inputs) > 1:
            geom_input = images.get(self.inputs[1])

        if image is None:
            raise ValueError("ExtractRegions requires an image input")

        # Create ImageList with source dimensions
        result = ImageList(
            source_width=image.width,
            source_height=image.height,
        )

        if isinstance(geom_input, GeometryList):
            for i, geom in enumerate(geom_input):
                # Get bounding rectangle
                if isinstance(geom, Rectangle):
                    bbox = geom
                elif hasattr(geom, 'bounding_rect'):
                    bbox = geom.bounding_rect
                else:
                    continue

                # Apply padding and clamp to image bounds
                x1 = max(0, int(bbox.x) - self.padding)
                y1 = max(0, int(bbox.y) - self.padding)
                x2 = min(image.width, int(bbox.x + bbox.width) + self.padding)
                y2 = min(image.height, int(bbox.y + bbox.height) + self.padding)

                w, h = x2 - x1, y2 - y1
                if w >= self.min_size and h >= self.min_size:
                    # Crop the region
                    crop = image.cropped((x1, y1, x2, y2))

                    # Create metadata for this region
                    meta = RegionMeta(
                        x=x1,
                        y=y1,
                        width=w,
                        height=h,
                        padding=self.padding,
                        geometry=geom,
                        index=i,
                    )
                    result.add(crop, meta)

        return result

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Single input fallback."""
        return image


@register_filter
@dataclass
class MergeRegions(CombinerFilter):
    """Merge processed regions back into original image.

    Takes the original image and an ImageList containing processed
    region crops with metadata. Uses the metadata to paste regions
    back at their original positions.

    Inputs:
        original: Original full image
        regions: ImageList with processed regions (contains position metadata)

    Parameters:
        blend_edges: Feather edges for smooth blending (default False)
        feather_size: Edge feathering radius (default 5)
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'input', 'type': 'image', 'description': 'Original image'},
        {'name': 'regions', 'type': 'image_list', 'description': 'ImageList with regions'},
    ]

    blend_edges: bool = False
    feather_size: int = 5

    def apply_multi(
        self,
        images: dict[str, Any],
        contexts: dict[str, FilterContext] | None = None
    ) -> 'Image':
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        from imagestag.image_list import ImageList

        # Get inputs by port name
        original = images.get('input') or images.get('original')  # 'original' for legacy
        if original is None and self.inputs:
            original = images.get(self.inputs[0])
        regions_input = images.get('regions')
        if regions_input is None and len(self.inputs) > 1:
            regions_input = images.get(self.inputs[1])

        if original is None:
            raise ValueError("MergeRegions requires original image")

        # Copy original for output
        result = original.get_pixels(PixelFormat.RGB).copy()

        if isinstance(regions_input, ImageList) and regions_input:
            for i, region in enumerate(regions_input.images):
                meta = regions_input.get_meta(i)

                # Get position from metadata
                x1 = meta.x
                y1 = meta.y
                target_w = meta.width
                target_h = meta.height

                # Resize region if needed to match original bbox
                region_px = region.get_pixels(PixelFormat.RGB)

                if region_px.shape[:2] != (target_h, target_w):
                    region_resized = region.resized((target_w, target_h))
                    region_px = region_resized.get_pixels(PixelFormat.RGB)

                # Clamp to image bounds
                x2 = min(result.shape[1], x1 + region_px.shape[1])
                y2 = min(result.shape[0], y1 + region_px.shape[0])
                x1 = max(0, x1)
                y1 = max(0, y1)

                # Paste region
                rh, rw = y2 - y1, x2 - x1
                if rh > 0 and rw > 0:
                    result[y1:y2, x1:x2] = region_px[:rh, :rw]

        return Img(result, pixel_format=PixelFormat.RGB)

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Single input fallback."""
        return image


__all__ = [
    'GeometryFilter',
    'HoughCircleDetector',
    'HoughLineDetector',
    'DrawGeometry',
    'ExtractRegions',
    'MergeRegions',
]
