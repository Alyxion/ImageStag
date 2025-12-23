"""
Tests for GeometryList and geometry filter system.
"""

import pytest
import numpy as np

from imagestag import Image, GeometryList, Rectangle, Circle, Ellipse, Line, Polygon
from imagestag.geometry_list import GeometryMeta, GeometryType
from imagestag.color import Colors


@pytest.fixture
def sample_image():
    """Create a sample 100x100 RGB image."""
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    pixels[20:80, 20:80] = [255, 255, 255]  # White square in center
    return Image(pixels)


class TestGeometryPrimitives:
    """Tests for individual geometry classes."""

    def test_rectangle_creation(self):
        """Rectangle stores coordinates correctly."""
        rect = Rectangle(x=10, y=20, width=50, height=30)
        assert rect.x == 10
        assert rect.y == 20
        assert rect.width == 50
        assert rect.height == 30
        assert rect.geometry_type == GeometryType.RECTANGLE

    def test_rectangle_properties(self):
        """Rectangle computed properties work."""
        rect = Rectangle(x=10, y=20, width=50, height=30)
        assert rect.x2 == 60
        assert rect.y2 == 50
        assert rect.center == (35.0, 35.0)
        assert rect.area == 1500

    def test_rectangle_to_int_tuple(self):
        """Rectangle converts to int tuple."""
        rect = Rectangle(x=10.5, y=20.7, width=50.2, height=30.9)
        assert rect.to_int_tuple() == (10, 20, 50, 30)

    def test_circle_creation(self):
        """Circle stores center and radius."""
        circle = Circle(cx=50, cy=50, radius=25)
        assert circle.cx == 50
        assert circle.cy == 50
        assert circle.radius == 25
        assert circle.geometry_type == GeometryType.CIRCLE

    def test_circle_properties(self):
        """Circle computed properties work."""
        circle = Circle(cx=50, cy=50, radius=10)
        assert circle.center == (50, 50)
        assert abs(circle.area - np.pi * 100) < 0.01
        bbox = circle.bounding_rect
        assert bbox.x == 40
        assert bbox.y == 40
        assert bbox.width == 20
        assert bbox.height == 20

    def test_ellipse_creation(self):
        """Ellipse stores semi-axes and angle."""
        ellipse = Ellipse(cx=50, cy=50, rx=30, ry=20, angle=45)
        assert ellipse.cx == 50
        assert ellipse.rx == 30
        assert ellipse.ry == 20
        assert ellipse.angle == 45
        assert ellipse.geometry_type == GeometryType.ELLIPSE

    def test_line_creation(self):
        """Line stores endpoints."""
        line = Line(x1=0, y1=0, x2=100, y2=100)
        assert line.x1 == 0
        assert line.x2 == 100
        assert line.geometry_type == GeometryType.LINE

    def test_line_properties(self):
        """Line computed properties work."""
        line = Line(x1=0, y1=0, x2=100, y2=0)
        assert line.length == 100
        assert line.midpoint == (50, 0)
        assert line.angle == 0  # Horizontal line

    def test_polygon_creation(self):
        """Polygon stores points."""
        points = [(0, 0), (100, 0), (100, 100), (0, 100)]
        poly = Polygon(points=points, closed=True)
        assert len(poly.points) == 4
        assert poly.closed is True
        assert poly.geometry_type == GeometryType.POLYGON

    def test_polygon_area(self):
        """Polygon area calculation (shoelace)."""
        # Unit square
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]
        poly = Polygon(points=points)
        assert poly.area == 1.0


class TestGeometryMeta:
    """Tests for geometry metadata."""

    def test_default_meta(self):
        """Default metadata has sensible values."""
        meta = GeometryMeta()
        assert meta.confidence == 1.0
        assert meta.label == ""
        assert meta.thickness == 2
        assert meta.filled is False

    def test_custom_meta(self):
        """Custom metadata is stored."""
        meta = GeometryMeta(
            confidence=0.95,
            label='face',
            color=Colors.GREEN,
            thickness=3,
            filled=True,
            extra={'score': 0.98}
        )
        assert meta.confidence == 0.95
        assert meta.label == 'face'
        assert meta.thickness == 3
        assert meta.filled is True
        assert meta.extra['score'] == 0.98


class TestGeometryList:
    """Tests for GeometryList container."""

    def test_empty_list(self):
        """Empty GeometryList works."""
        gl = GeometryList()
        assert len(gl) == 0
        assert bool(gl) is False
        assert gl.width == 0
        assert gl.height == 0

    def test_add_geometry(self):
        """Adding geometries works."""
        gl = GeometryList(width=100, height=100)
        gl.add(Rectangle(x=10, y=10, width=20, height=20))
        gl.add(Circle(cx=50, cy=50, radius=10))
        assert len(gl) == 2
        assert bool(gl) is True

    def test_iteration(self):
        """GeometryList is iterable."""
        gl = GeometryList(width=100, height=100)
        gl.add(Rectangle(x=10, y=10, width=20, height=20))
        gl.add(Circle(cx=50, cy=50, radius=10))
        geoms = list(gl)
        assert len(geoms) == 2
        assert isinstance(geoms[0], Rectangle)
        assert isinstance(geoms[1], Circle)

    def test_indexing(self):
        """GeometryList supports indexing."""
        gl = GeometryList()
        gl.add(Rectangle(x=0, y=0, width=10, height=10))
        gl.add(Circle(cx=50, cy=50, radius=5))
        assert isinstance(gl[0], Rectangle)
        assert isinstance(gl[1], Circle)

    def test_filter_by_type(self):
        """Filter by geometry type works."""
        gl = GeometryList()
        gl.add(Rectangle(x=0, y=0, width=10, height=10))
        gl.add(Circle(cx=50, cy=50, radius=5))
        gl.add(Rectangle(x=20, y=20, width=5, height=5))

        rects = gl.rectangles()
        assert len(rects) == 2
        assert all(isinstance(r, Rectangle) for r in rects)

        circles = gl.circles()
        assert len(circles) == 1

    def test_to_preview_image(self):
        """Preview image is generated correctly."""
        gl = GeometryList(width=100, height=100)
        gl.add(Rectangle(x=10, y=10, width=30, height=30, meta=GeometryMeta(color=Colors.RED)))
        gl.add(Circle(cx=70, cy=70, radius=15, meta=GeometryMeta(color=Colors.GREEN)))

        preview = gl.to_preview_image()
        assert preview.width == 100
        assert preview.height == 100

    def test_serialization(self):
        """GeometryList serializes and deserializes."""
        gl = GeometryList(width=100, height=100)
        gl.add(Rectangle(x=10, y=20, width=30, height=40))
        gl.add(Circle(cx=50, cy=60, radius=15))

        data = gl.to_dict()
        assert data['width'] == 100
        assert data['height'] == 100
        assert len(data['geometries']) == 2

        restored = GeometryList.from_dict(data)
        assert len(restored) == 2
        assert restored.width == 100

    def test_copy(self):
        """GeometryList copy works."""
        gl = GeometryList(width=100, height=100)
        gl.add(Rectangle(x=10, y=10, width=20, height=20))

        gl_copy = gl.copy()
        assert len(gl_copy) == 1
        assert gl_copy.width == 100


class TestGeometryFilters:
    """Tests for geometry-producing filters."""

    def test_hough_circle_detector(self, sample_image):
        """HoughCircleDetector returns GeometryList."""
        from imagestag.filters import HoughCircleDetector

        detector = HoughCircleDetector(min_dist=10, param2=20)
        result = detector.apply(sample_image)

        assert isinstance(result, GeometryList)
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_hough_line_detector(self, sample_image):
        """HoughLineDetector returns GeometryList."""
        from imagestag.filters import HoughLineDetector

        detector = HoughLineDetector(threshold=50, min_length=10)
        result = detector.apply(sample_image)

        assert isinstance(result, GeometryList)
        # All geometries should be Lines
        for geom in result:
            assert isinstance(geom, Line)

    def test_face_detector_returns_geometry(self, sample_image):
        """FaceDetector returns GeometryList (not Image)."""
        from imagestag.filters import FaceDetector

        detector = FaceDetector()
        result = detector.apply(sample_image)

        assert isinstance(result, GeometryList)
        assert result.width == sample_image.width

    def test_contour_detector_returns_geometry(self, sample_image):
        """ContourDetector returns GeometryList with polygons."""
        from imagestag.filters import ContourDetector

        detector = ContourDetector(threshold=128, min_area=10)
        result = detector.apply(sample_image)

        assert isinstance(result, GeometryList)
        # All geometries should be Polygons
        for geom in result:
            assert isinstance(geom, Polygon)


class TestDrawGeometry:
    """Tests for DrawGeometry combiner."""

    def test_draw_geometry_combines_inputs(self, sample_image):
        """DrawGeometry draws geometries on image."""
        from imagestag.filters import DrawGeometry

        gl = GeometryList(width=sample_image.width, height=sample_image.height)
        gl.add(Rectangle(x=10, y=10, width=20, height=20, meta=GeometryMeta(color=Colors.RED)))

        drawer = DrawGeometry(inputs=['image', 'geometry'])
        result = drawer.apply_multi({
            'image': sample_image,
            'geometry': gl,
        })

        assert isinstance(result, Image)
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_draw_geometry_no_geometry(self, sample_image):
        """DrawGeometry returns unchanged image when no geometry."""
        from imagestag.filters import DrawGeometry

        drawer = DrawGeometry(inputs=['image', 'geometry'])
        result = drawer.apply_multi({
            'image': sample_image,
            'geometry': None,
        })

        assert isinstance(result, Image)


class TestExtractMergeRegions:
    """Tests for region extraction and merging."""

    def test_extract_regions(self, sample_image):
        """ExtractRegions produces ImageList with metadata."""
        from imagestag.filters import ExtractRegions
        from imagestag.image_list import ImageList

        gl = GeometryList(width=sample_image.width, height=sample_image.height)
        gl.add(Rectangle(x=10, y=10, width=20, height=20))
        gl.add(Rectangle(x=50, y=50, width=30, height=30))

        extractor = ExtractRegions(inputs=['image', 'geometry'])
        result = extractor.apply_multi({
            'image': sample_image,
            'geometry': gl,
        })

        assert isinstance(result, ImageList)
        assert len(result) == 2
        assert result.source_width == sample_image.width
        assert result.source_height == sample_image.height
        # Check metadata
        meta0 = result.get_meta(0)
        assert meta0.x == 10
        assert meta0.y == 10
        assert meta0.width == 20
        assert meta0.height == 20

    def test_filter_auto_handles_imagelist(self, sample_image):
        """Filters automatically apply to each image in ImageList."""
        from imagestag.filters import GaussianBlur
        from imagestag.image_list import ImageList, RegionMeta

        # Create ImageList with 3 images
        img_list = ImageList(source_width=100, source_height=100)
        for i in range(3):
            crop = sample_image.cropped((10, 10, 30, 30))
            img_list.add(crop, RegionMeta(x=10, y=10, width=20, height=20, index=i))

        # Apply filter using __call__ which auto-handles ImageList
        blur = GaussianBlur(radius=2)
        result = blur(img_list)

        assert isinstance(result, ImageList)
        assert len(result) == 3
        # Metadata should be preserved
        assert result.source_width == 100
        meta = result.get_meta(0)
        assert meta.x == 10


class TestGeometryFilterRegistry:
    """Tests for filter registration."""

    def test_geometry_filters_registered(self):
        """New geometry filters are in registry."""
        from imagestag.filters import FILTER_REGISTRY

        assert 'houghcircledetector' in FILTER_REGISTRY
        assert 'houghlinedetector' in FILTER_REGISTRY
        assert 'drawgeometry' in FILTER_REGISTRY
        assert 'extractregions' in FILTER_REGISTRY
        assert 'mergeregions' in FILTER_REGISTRY

    def test_geometry_filter_is_geometry_output(self):
        """GeometryFilter subclasses have geometry output port."""
        from imagestag.filters import FaceDetector, HoughCircleDetector

        ports = FaceDetector.get_output_ports()
        assert len(ports) == 1
        assert ports[0].get('type') == 'geometry'

        ports = HoughCircleDetector.get_output_ports()
        assert len(ports) == 1
        assert ports[0].get('type') == 'geometry'
