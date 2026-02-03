"""
Contour extraction from alpha masks.

This module provides sub-pixel precision contour extraction using:
- Marching Squares algorithm for contour extraction
- Douglas-Peucker algorithm for polyline simplification
- Bezier curve fitting for smooth curves

The output is geometric data (contours with points/curves), not a modified image.

Usage:
    # Class-based (recommended for filter pipeline):
    from imagestag.filters.contour import ContourExtractor
    extractor = ContourExtractor(simplify_epsilon=0.5, fit_beziers=True)
    geometry_list = extractor(image)

    # Function-based (for direct numpy array processing):
    from imagestag.filters.contour import extract_contours
    contours = extract_contours(mask, simplify_epsilon=0.5)
"""

from dataclasses import dataclass, field
from typing import Optional, ClassVar, TYPE_CHECKING
import numpy as np

from .base import register_filter, FilterContext
from .geometry import GeometryFilter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.geometry_list import GeometryList


@dataclass
class Point:
    """A 2D point with sub-pixel precision."""
    x: float
    y: float

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (x, y) tuple."""
        return (self.x, self.y)


@dataclass
class BezierSegment:
    """A cubic Bezier curve segment."""
    p0: Point  # Start point
    p1: Point  # First control point
    p2: Point  # Second control point
    p3: Point  # End point

    def to_tuple(self) -> tuple[tuple[float, float], ...]:
        """Convert to tuple of (x, y) tuples."""
        return (self.p0.to_tuple(), self.p1.to_tuple(),
                self.p2.to_tuple(), self.p3.to_tuple())


@dataclass
class Contour:
    """A contour represented as either a polyline or Bezier curves."""
    points: list[Point]
    is_closed: bool
    beziers: Optional[list[BezierSegment]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            'points': [p.to_tuple() for p in self.points],
            'is_closed': self.is_closed,
        }
        if self.beziers is not None:
            result['beziers'] = [b.to_tuple() for b in self.beziers]
        return result

    def to_svg_path(self) -> str:
        """Convert contour to SVG path data string."""
        if not self.points:
            return ""

        path_parts = []

        if self.beziers is not None:
            # Use Bezier curves
            path_parts.append(f"M {self.beziers[0].p0.x:.3f},{self.beziers[0].p0.y:.3f}")
            for bez in self.beziers:
                path_parts.append(
                    f"C {bez.p1.x:.3f},{bez.p1.y:.3f} "
                    f"{bez.p2.x:.3f},{bez.p2.y:.3f} "
                    f"{bez.p3.x:.3f},{bez.p3.y:.3f}"
                )
        else:
            # Use polyline
            path_parts.append(f"M {self.points[0].x:.3f},{self.points[0].y:.3f}")
            for point in self.points[1:]:
                path_parts.append(f"L {point.x:.3f},{point.y:.3f}")

        if self.is_closed:
            path_parts.append("Z")

        return " ".join(path_parts)


# =============================================================================
# ContourExtractor Filter Class
# =============================================================================

@register_filter
@dataclass
class ContourExtractor(GeometryFilter):
    """Extract contours from image alpha channel using Marching Squares.

    This filter extracts sub-pixel precision contours from the alpha channel
    of an image. Contours are returned as Polygon geometries in a GeometryList.

    The extraction pipeline:
    1. Marching Squares algorithm for sub-pixel contour extraction
    2. Optional Douglas-Peucker simplification to reduce point count
    3. Optional Bezier curve fitting for smooth curves

    Parameters:
        threshold: Alpha threshold (0.0-1.0) for inside/outside classification.
        simplify_epsilon: Douglas-Peucker simplification epsilon.
            0 = no simplification, higher = more simplification.
            Recommended: 0.3-0.5 for good balance of detail and smoothness.
        fit_beziers: Whether to fit cubic Bezier curves to the simplified polyline.
        bezier_smoothness: Smoothness factor for Bezier fitting (0.1-0.5).
            Higher values produce smoother curves.

    Example:
        # Basic usage
        extractor = ContourExtractor(simplify_epsilon=0.5)
        geometry_list = extractor(image)

        # With Bezier curve fitting
        extractor = ContourExtractor(
            simplify_epsilon=0.5,
            fit_beziers=True,
            bezier_smoothness=0.25
        )
        geometry_list = extractor(image)

        # Chain with visualization
        'contourextractor(simplify_epsilon=0.5) | drawgeometry'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'simplify_epsilon'

    threshold: float = 0.5
    simplify_epsilon: float = 0.0
    fit_beziers: bool = False
    bezier_smoothness: float = 0.25

    def detect(self, image: 'Image') -> 'GeometryList':
        """Extract contours from image alpha channel.

        Args:
            image: Input image (alpha channel will be used as mask).

        Returns:
            GeometryList containing Polygon geometries for each contour.
        """
        from imagestag.pixel_format import PixelFormat
        from imagestag.geometry_list import GeometryList, Polygon, GeometryMeta
        from imagestag.color import Colors

        # Get alpha channel as mask
        rgba = image.get_pixels(PixelFormat.RGBA)
        mask = rgba[:, :, 3]  # Alpha channel
        height, width = mask.shape

        # Extract contours using the standalone function
        contours = extract_contours(
            mask=mask,
            threshold=self.threshold,
            simplify_epsilon=self.simplify_epsilon,
            fit_beziers=self.fit_beziers,
            bezier_smoothness=self.bezier_smoothness,
        )

        # Convert to GeometryList with Polygon geometries
        geometry_list = GeometryList(width=width, height=height)

        for contour in contours:
            # Convert points to tuple format
            points = [(p.x, p.y) for p in contour.points]

            # Store bezier data in metadata if available
            extra = {}
            if contour.beziers is not None:
                extra['beziers'] = [b.to_tuple() for b in contour.beziers]

            meta = GeometryMeta(
                color=Colors.GREEN,
                thickness=2,
                filled=False,
                extra=extra,
            )

            polygon = Polygon(
                points=points,
                closed=contour.is_closed,
                meta=meta,
            )
            geometry_list.add(polygon)

        return geometry_list


# =============================================================================
# Standalone Functions (for direct numpy array processing)
# =============================================================================

def extract_contours(
    mask: np.ndarray,
    threshold: float = 0.5,
    simplify_epsilon: float = 0.0,
    fit_beziers: bool = False,
    bezier_smoothness: float = 0.25,
) -> list[Contour]:
    """
    Extract contours from an alpha mask using Marching Squares.

    Args:
        mask: Alpha mask as numpy array. Can be:
            - 2D array (H, W) with values 0-255
            - 3D array (H, W, C) where alpha is last channel
            - dtype uint8 (0-255) or float32 (0.0-1.0)
        threshold: Alpha threshold (0.0-1.0) for inside/outside classification.
        simplify_epsilon: Douglas-Peucker simplification epsilon.
            0 = no simplification, higher = more simplification.
            Recommended: 0.3-0.5 for good balance of detail and smoothness.
        fit_beziers: Whether to fit cubic Bezier curves to the simplified polyline.
        bezier_smoothness: Smoothness factor for Bezier fitting (0.1-0.5).
            Higher values produce smoother curves.

    Returns:
        List of Contour objects, each containing:
        - points: List of Point objects forming the contour
        - is_closed: Whether the contour is closed
        - beziers: Optional list of BezierSegment objects (if fit_beziers=True)

    Raises:
        ValueError: If mask has invalid shape or dtype.

    Example:
        >>> import numpy as np
        >>> from imagestag.filters.contour import extract_contours
        >>> # Create a simple mask with a circle
        >>> mask = np.zeros((100, 100), dtype=np.uint8)
        >>> y, x = np.ogrid[:100, :100]
        >>> mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255
        >>> # Extract contours
        >>> contours = extract_contours(mask, simplify_epsilon=0.5)
        >>> print(f"Found {len(contours)} contour(s)")
        >>> for c in contours:
        ...     print(f"  {len(c.points)} points, closed={c.is_closed}")
    """
    from imagestag import imagestag_rust

    # Validate and normalize input
    mask = _normalize_mask(mask)
    height, width = mask.shape

    # Call Rust implementation
    raw_contours = imagestag_rust.extract_contours_precise(
        mask=mask.flatten().tolist(),
        width=width,
        height=height,
        threshold=threshold,
        simplify_epsilon=simplify_epsilon,
        fit_beziers=fit_beziers,
        bezier_smoothness=bezier_smoothness,
    )

    # Convert to Python objects
    return [_raw_contour_to_contour(raw) for raw in raw_contours]


def contours_to_svg(
    contours: list[Contour],
    width: int,
    height: int,
    fill_color: str = "#FFFFFF",
    stroke_color: Optional[str] = None,
    stroke_width: float = 0.0,
    background_color: Optional[str] = None,
) -> str:
    """
    Convert contours to a complete SVG document.

    Args:
        contours: List of Contour objects to render.
        width: SVG width in pixels.
        height: SVG height in pixels.
        fill_color: Fill color for paths (e.g., "#FFFFFF").
        stroke_color: Optional stroke color for paths.
        stroke_width: Stroke width in pixels.
        background_color: Optional background color (adds a rect behind paths).

    Returns:
        Complete SVG document as a string.

    Example:
        >>> contours = extract_contours(mask, simplify_epsilon=0.5)
        >>> svg = contours_to_svg(contours, 512, 512, fill_color="#000000")
        >>> with open("output.svg", "w") as f:
        ...     f.write(svg)
    """
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}px" height="{height}px" viewBox="0 0 {width} {height}">'
    ]

    if background_color:
        parts.append(
            f'  <rect x="0" y="0" width="{width}" height="{height}" '
            f'fill="{background_color}"/>'
        )

    for contour in contours:
        path_data = contour.to_svg_path()
        if path_data:
            path_attrs = [f'd="{path_data}"', f'fill="{fill_color}"']
            if stroke_color:
                path_attrs.append(f'stroke="{stroke_color}"')
                path_attrs.append(f'stroke-width="{stroke_width:.2f}"')
            parts.append(f'  <path {" ".join(path_attrs)}/>')

    parts.append('</svg>')
    return '\n'.join(parts)


def extract_contours_to_svg(
    mask: np.ndarray,
    threshold: float = 0.5,
    simplify_epsilon: float = 0.5,
    fit_beziers: bool = True,
    bezier_smoothness: float = 0.25,
    fill_color: str = "#FFFFFF",
    stroke_color: Optional[str] = None,
    stroke_width: float = 0.0,
    background_color: Optional[str] = None,
) -> str:
    """
    Extract contours from mask and convert directly to SVG.

    This is a convenience function combining extract_contours() and contours_to_svg().

    Args:
        mask: Alpha mask (see extract_contours for details).
        threshold: Alpha threshold (0.0-1.0).
        simplify_epsilon: Douglas-Peucker simplification epsilon.
        fit_beziers: Whether to fit Bezier curves.
        bezier_smoothness: Smoothness factor for Bezier fitting.
        fill_color: SVG fill color.
        stroke_color: Optional SVG stroke color.
        stroke_width: SVG stroke width.
        background_color: Optional SVG background color.

    Returns:
        Complete SVG document as a string.
    """
    # Normalize mask to get dimensions
    mask = _normalize_mask(mask)
    height, width = mask.shape

    contours = extract_contours(
        mask=mask,
        threshold=threshold,
        simplify_epsilon=simplify_epsilon,
        fit_beziers=fit_beziers,
        bezier_smoothness=bezier_smoothness,
    )

    return contours_to_svg(
        contours=contours,
        width=width,
        height=height,
        fill_color=fill_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        background_color=background_color,
    )


def _normalize_mask(mask: np.ndarray) -> np.ndarray:
    """Normalize mask to 2D uint8 array (H, W) with values 0-255."""
    if mask.ndim == 3:
        # Extract alpha channel (last channel)
        mask = mask[:, :, -1]
    elif mask.ndim != 2:
        raise ValueError(
            f"Expected 2D or 3D array, got shape {mask.shape}"
        )

    if mask.dtype == np.float32 or mask.dtype == np.float64:
        # Convert 0.0-1.0 to 0-255
        mask = (np.clip(mask, 0.0, 1.0) * 255).astype(np.uint8)
    elif mask.dtype != np.uint8:
        raise ValueError(
            f"Expected uint8 or float32/float64 dtype, got {mask.dtype}"
        )

    return mask


def _raw_contour_to_contour(raw: dict) -> Contour:
    """Convert raw contour dict from Rust to Contour object."""
    points = [Point(x=p[0], y=p[1]) for p in raw['points']]

    beziers = None
    if 'beziers' in raw:
        beziers = [
            BezierSegment(
                p0=Point(x=b[0][0], y=b[0][1]),
                p1=Point(x=b[1][0], y=b[1][1]),
                p2=Point(x=b[2][0], y=b[2][1]),
                p3=Point(x=b[3][0], y=b[3][1]),
            )
            for b in raw['beziers']
        ]

    return Contour(
        points=points,
        is_closed=raw['is_closed'],
        beziers=beziers,
    )


# =============================================================================
# Douglas-Peucker Polyline Simplification
# =============================================================================

def douglas_peucker(
    points: list[tuple[float, float]],
    epsilon: float,
) -> list[tuple[float, float]]:
    """
    Simplify a polyline using the Douglas-Peucker algorithm.

    The Douglas-Peucker algorithm reduces the number of points in a polyline
    while preserving its shape. Points that deviate less than epsilon from
    the simplified line are removed.

    Args:
        points: List of (x, y) tuples representing the polyline.
        epsilon: Maximum distance threshold for simplification.
            Higher values produce more simplification (fewer points).
            Typical values: 0.1-1.0 for sub-pixel precision, 1.0-5.0 for
            aggressive simplification.

    Returns:
        Simplified list of (x, y) tuples.

    Example:
        >>> points = [(0, 0), (1, 0.1), (2, -0.1), (3, 0), (4, 0)]
        >>> simplified = douglas_peucker(points, epsilon=0.5)
        >>> # Result: [(0, 0), (4, 0)] - middle points removed
    """
    from imagestag import imagestag_rust
    return imagestag_rust.douglas_peucker(points, epsilon)


def douglas_peucker_closed(
    points: list[tuple[float, float]],
    epsilon: float,
) -> list[tuple[float, float]]:
    """
    Simplify a closed polygon using the Douglas-Peucker algorithm.

    This version is optimized for closed polygons. It finds the point farthest
    from the centroid to use as the starting point, which produces better
    results than the standard algorithm for closed shapes.

    Args:
        points: List of (x, y) tuples representing the closed polygon.
            The first and last points should be the same (or will be treated
            as if the polygon is closed).
        epsilon: Maximum distance threshold for simplification.
            Higher values produce more simplification (fewer points).

    Returns:
        Simplified list of (x, y) tuples (closed polygon).

    Example:
        >>> # Square with extra points on edges
        >>> points = [(0, 0), (5, 0), (10, 0), (10, 5), (10, 10),
        ...           (5, 10), (0, 10), (0, 5), (0, 0)]
        >>> simplified = douglas_peucker_closed(points, epsilon=0.5)
        >>> # Result: [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    """
    from imagestag import imagestag_rust
    return imagestag_rust.douglas_peucker_closed(points, epsilon)
