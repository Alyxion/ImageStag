# ImageStag - Geometry List
"""
GeometryList and geometry primitives for detection filter outputs.

Stores geometric shapes (rectangles, circles, ellipses, lines, polygons)
with metadata for visualization and region-based processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Union, TYPE_CHECKING

import numpy as np

from .color import Color, Colors

if TYPE_CHECKING:
    from imagestag import Image


class GeometryType(Enum):
    """Types of geometry primitives."""
    RECTANGLE = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    LINE = auto()
    POLYGON = auto()
    POINT = auto()


@dataclass
class GeometryMeta:
    """Metadata attached to any geometry."""
    confidence: float = 1.0
    label: str = ""
    color: Color = field(default_factory=lambda: Colors.RED)
    thickness: int = 2
    filled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Rectangle:
    """Axis-aligned rectangle (x, y, width, height)."""
    x: float
    y: float
    width: float
    height: float
    meta: GeometryMeta = field(default_factory=GeometryMeta)

    @property
    def geometry_type(self) -> GeometryType:
        return GeometryType.RECTANGLE

    @property
    def x2(self) -> float:
        """Right edge x coordinate."""
        return self.x + self.width

    @property
    def y2(self) -> float:
        """Bottom edge y coordinate."""
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        """Center point of the rectangle."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        """Area of the rectangle."""
        return self.width * self.height

    def to_int_tuple(self) -> tuple[int, int, int, int]:
        """Return as (x, y, width, height) integer tuple."""
        return (int(self.x), int(self.y), int(self.width), int(self.height))

    def to_dict(self) -> dict:
        return {
            'type': 'rectangle',
            'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height
        }

    @classmethod
    def from_dict(cls, data: dict, meta: GeometryMeta | None = None) -> 'Rectangle':
        return cls(
            x=data['x'], y=data['y'],
            width=data['width'], height=data['height'],
            meta=meta or GeometryMeta()
        )


@dataclass
class Circle:
    """Circle defined by center and radius."""
    cx: float
    cy: float
    radius: float
    meta: GeometryMeta = field(default_factory=GeometryMeta)

    @property
    def geometry_type(self) -> GeometryType:
        return GeometryType.CIRCLE

    @property
    def center(self) -> tuple[float, float]:
        """Center point of the circle."""
        return (self.cx, self.cy)

    @property
    def area(self) -> float:
        """Area of the circle."""
        return np.pi * self.radius ** 2

    @property
    def bounding_rect(self) -> Rectangle:
        """Bounding rectangle of the circle."""
        return Rectangle(
            x=self.cx - self.radius,
            y=self.cy - self.radius,
            width=self.radius * 2,
            height=self.radius * 2
        )

    def to_dict(self) -> dict:
        return {
            'type': 'circle',
            'cx': self.cx, 'cy': self.cy,
            'radius': self.radius
        }

    @classmethod
    def from_dict(cls, data: dict, meta: GeometryMeta | None = None) -> 'Circle':
        return cls(
            cx=data['cx'], cy=data['cy'],
            radius=data['radius'],
            meta=meta or GeometryMeta()
        )


@dataclass
class Ellipse:
    """Ellipse with optional rotation."""
    cx: float
    cy: float
    rx: float  # semi-axis in x direction
    ry: float  # semi-axis in y direction
    angle: float = 0.0  # rotation in degrees
    meta: GeometryMeta = field(default_factory=GeometryMeta)

    @property
    def geometry_type(self) -> GeometryType:
        return GeometryType.ELLIPSE

    @property
    def center(self) -> tuple[float, float]:
        """Center point of the ellipse."""
        return (self.cx, self.cy)

    @property
    def area(self) -> float:
        """Area of the ellipse."""
        return np.pi * self.rx * self.ry

    @property
    def bounding_rect(self) -> Rectangle:
        """Approximate bounding rectangle (exact for angle=0)."""
        max_r = max(self.rx, self.ry)
        return Rectangle(
            x=self.cx - max_r,
            y=self.cy - max_r,
            width=max_r * 2,
            height=max_r * 2
        )

    def to_dict(self) -> dict:
        return {
            'type': 'ellipse',
            'cx': self.cx, 'cy': self.cy,
            'rx': self.rx, 'ry': self.ry,
            'angle': self.angle
        }

    @classmethod
    def from_dict(cls, data: dict, meta: GeometryMeta | None = None) -> 'Ellipse':
        return cls(
            cx=data['cx'], cy=data['cy'],
            rx=data['rx'], ry=data['ry'],
            angle=data.get('angle', 0.0),
            meta=meta or GeometryMeta()
        )


@dataclass
class Line:
    """Line segment from (x1, y1) to (x2, y2)."""
    x1: float
    y1: float
    x2: float
    y2: float
    meta: GeometryMeta = field(default_factory=GeometryMeta)

    @property
    def geometry_type(self) -> GeometryType:
        return GeometryType.LINE

    @property
    def length(self) -> float:
        """Length of the line segment."""
        return np.sqrt((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2)

    @property
    def midpoint(self) -> tuple[float, float]:
        """Midpoint of the line segment."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def angle(self) -> float:
        """Angle of the line in degrees (0-180)."""
        return np.degrees(np.arctan2(self.y2 - self.y1, self.x2 - self.x1)) % 180

    @property
    def bounding_rect(self) -> Rectangle:
        """Bounding rectangle of the line."""
        x_min, x_max = min(self.x1, self.x2), max(self.x1, self.x2)
        y_min, y_max = min(self.y1, self.y2), max(self.y1, self.y2)
        return Rectangle(
            x=x_min, y=y_min,
            width=max(x_max - x_min, 1),
            height=max(y_max - y_min, 1)
        )

    def to_dict(self) -> dict:
        return {
            'type': 'line',
            'x1': self.x1, 'y1': self.y1,
            'x2': self.x2, 'y2': self.y2
        }

    @classmethod
    def from_dict(cls, data: dict, meta: GeometryMeta | None = None) -> 'Line':
        return cls(
            x1=data['x1'], y1=data['y1'],
            x2=data['x2'], y2=data['y2'],
            meta=meta or GeometryMeta()
        )


@dataclass
class Polygon:
    """Polygon/contour defined by list of points."""
    points: list[tuple[float, float]]  # List of (x, y) tuples
    closed: bool = True
    meta: GeometryMeta = field(default_factory=GeometryMeta)

    @property
    def geometry_type(self) -> GeometryType:
        return GeometryType.POLYGON

    @property
    def num_points(self) -> int:
        """Number of points in the polygon."""
        return len(self.points)

    @property
    def bounding_rect(self) -> Rectangle:
        """Bounding rectangle of the polygon."""
        if not self.points:
            return Rectangle(x=0, y=0, width=0, height=0)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        return Rectangle(
            x=x_min, y=y_min,
            width=x_max - x_min,
            height=y_max - y_min
        )

    @property
    def area(self) -> float:
        """Area of the polygon using shoelace formula."""
        if len(self.points) < 3:
            return 0.0
        n = len(self.points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i][0] * self.points[j][1]
            area -= self.points[j][0] * self.points[i][1]
        return abs(area) / 2.0

    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array for OpenCV."""
        return np.array(self.points, dtype=np.int32)

    def to_dict(self) -> dict:
        return {
            'type': 'polygon',
            'points': self.points,
            'closed': self.closed
        }

    @classmethod
    def from_dict(cls, data: dict, meta: GeometryMeta | None = None) -> 'Polygon':
        return cls(
            points=data['points'],
            closed=data.get('closed', True),
            meta=meta or GeometryMeta()
        )


# Union type for any geometry
Geometry = Union[Rectangle, Circle, Ellipse, Line, Polygon]


@dataclass
class GeometryList:
    """Collection of geometry primitives with source image dimensions.

    Used as output from detection filters (FaceDetector, HoughCircleDetector, etc.)
    and as input to visualization (DrawGeometry) and region processing (ExtractRegions).
    """

    geometries: list[Geometry] = field(default_factory=list)
    width: int = 0   # Source image width (for rendering preview)
    height: int = 0  # Source image height

    def add(self, geom: Geometry) -> None:
        """Add a geometry to the list."""
        self.geometries.append(geom)

    def __len__(self) -> int:
        return len(self.geometries)

    def __iter__(self):
        return iter(self.geometries)

    def __getitem__(self, idx: int) -> Geometry:
        return self.geometries[idx]

    def __bool__(self) -> bool:
        return len(self.geometries) > 0

    def filter_by_type(self, geom_type: GeometryType) -> list[Geometry]:
        """Filter geometries by type."""
        return [g for g in self.geometries if g.geometry_type == geom_type]

    def rectangles(self) -> list[Rectangle]:
        """Get all rectangles."""
        return [g for g in self.geometries if isinstance(g, Rectangle)]

    def circles(self) -> list[Circle]:
        """Get all circles."""
        return [g for g in self.geometries if isinstance(g, Circle)]

    def ellipses(self) -> list[Ellipse]:
        """Get all ellipses."""
        return [g for g in self.geometries if isinstance(g, Ellipse)]

    def lines(self) -> list[Line]:
        """Get all lines."""
        return [g for g in self.geometries if isinstance(g, Line)]

    def polygons(self) -> list[Polygon]:
        """Get all polygons."""
        return [g for g in self.geometries if isinstance(g, Polygon)]

    def to_preview_image(self, background_color: Color | None = None) -> 'Image':
        """Render geometries as preview image (red shapes on black background).

        :param background_color: Background color (default: black)
        :returns: Image with rendered geometries
        """
        import cv2
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat

        if background_color is None:
            background_color = Colors.BLACK

        # Ensure we have valid dimensions
        h = max(self.height, 100)
        w = max(self.width, 100)

        # Create canvas in BGR (OpenCV format)
        canvas = np.full((h, w, 3), background_color.to_int_bgr(), dtype=np.uint8)

        for geom in self.geometries:
            color = geom.meta.color.to_int_bgr()
            thickness = geom.meta.thickness if not geom.meta.filled else -1

            if isinstance(geom, Rectangle):
                pt1 = (int(geom.x), int(geom.y))
                pt2 = (int(geom.x + geom.width), int(geom.y + geom.height))
                cv2.rectangle(canvas, pt1, pt2, color, thickness)

            elif isinstance(geom, Circle):
                center = (int(geom.cx), int(geom.cy))
                cv2.circle(canvas, center, int(geom.radius), color, thickness)

            elif isinstance(geom, Ellipse):
                center = (int(geom.cx), int(geom.cy))
                axes = (int(geom.rx), int(geom.ry))
                cv2.ellipse(canvas, center, axes, geom.angle, 0, 360, color, thickness)

            elif isinstance(geom, Line):
                pt1 = (int(geom.x1), int(geom.y1))
                pt2 = (int(geom.x2), int(geom.y2))
                cv2.line(canvas, pt1, pt2, color, geom.meta.thickness)

            elif isinstance(geom, Polygon):
                pts = geom.to_numpy().reshape((-1, 1, 2))
                if geom.meta.filled:
                    cv2.fillPoly(canvas, [pts], color)
                else:
                    cv2.polylines(canvas, [pts], geom.closed, color, thickness)

        # Convert BGR to RGB for Image
        canvas_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        return Img(canvas_rgb, pixel_format=PixelFormat.RGB)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'width': self.width,
            'height': self.height,
            'geometries': [g.to_dict() for g in self.geometries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GeometryList':
        """Deserialize from dictionary."""
        geom_list = cls(width=data['width'], height=data['height'])

        type_map = {
            'rectangle': Rectangle,
            'circle': Circle,
            'ellipse': Ellipse,
            'line': Line,
            'polygon': Polygon,
        }

        for g_data in data.get('geometries', []):
            geom_type = g_data.get('type', 'rectangle')
            geom_cls = type_map.get(geom_type)
            if geom_cls:
                geom_list.add(geom_cls.from_dict(g_data))

        return geom_list

    def copy(self) -> 'GeometryList':
        """Create a shallow copy."""
        return GeometryList(
            geometries=list(self.geometries),
            width=self.width,
            height=self.height
        )


__all__ = [
    'GeometryType',
    'GeometryMeta',
    'Rectangle',
    'Circle',
    'Ellipse',
    'Line',
    'Polygon',
    'Geometry',
    'GeometryList',
]
