"""Parity tests for shape scaling between JavaScript and Python.

These tests verify that the Python scale_shape() function produces
the same results as the JavaScript VectorShape.scale() implementations.

Uses Playwright to run JavaScript in a real browser and compare outputs.
"""

import pytest
import json
import copy

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from stagforge.rendering.vector import scale_shape


# Skip all tests if Playwright not available
pytestmark = pytest.mark.skipif(
    not HAS_PLAYWRIGHT,
    reason="Playwright not installed"
)


@pytest.fixture(scope="module")
def browser():
    """Create a browser instance for the test module."""
    if not HAS_PLAYWRIGHT:
        pytest.skip("Playwright not installed")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


def run_js_scale(page, shape_type: str, shape_data: dict, scale_x: float, scale_y: float,
                 center_x=None, center_y=None) -> dict:
    """Run the JavaScript scale() function and return the result."""

    # Build the JS code to create and scale the shape
    js_code = f"""
    async () => {{
        // Import the shape classes
        const {{ RectShape }} = await import('/static/js/core/shapes/RectShape.js');
        const {{ EllipseShape }} = await import('/static/js/core/shapes/EllipseShape.js');
        const {{ LineShape }} = await import('/static/js/core/shapes/LineShape.js');
        const {{ PolygonShape }} = await import('/static/js/core/shapes/PolygonShape.js');
        const {{ PathShape }} = await import('/static/js/core/shapes/PathShape.js');

        const shapeData = {json.dumps(shape_data)};
        const scaleX = {scale_x};
        const scaleY = {scale_y};
        const centerX = {json.dumps(center_x)};
        const centerY = {json.dumps(center_y)};

        let shape;
        switch ("{shape_type}") {{
            case "rect":
                shape = RectShape.fromData(shapeData);
                break;
            case "ellipse":
                shape = EllipseShape.fromData(shapeData);
                break;
            case "line":
                shape = LineShape.fromData(shapeData);
                break;
            case "polygon":
                shape = PolygonShape.fromData(shapeData);
                break;
            case "path":
                shape = PathShape.fromData(shapeData);
                break;
        }}

        shape.scale(scaleX, scaleY, centerX, centerY);
        return shape.toData();
    }}
    """

    return page.evaluate(js_code)


class TestRectScalingParity:
    """Parity tests for RectShape scaling."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page):
        """Navigate to the editor page."""
        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        self.page = page

    def test_rect_scale_uniform(self):
        """RectShape uniform scaling should match between JS and Python."""
        shape = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 30,
            "cornerRadius": 5,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        # Run Python scaling
        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 2.0, 2.0)

        # Run JavaScript scaling
        js_shape = run_js_scale(self.page, "rect", shape, 2.0, 2.0)

        # Compare results
        assert py_shape["x"] == pytest.approx(js_shape["x"], abs=0.001)
        assert py_shape["y"] == pytest.approx(js_shape["y"], abs=0.001)
        assert py_shape["width"] == pytest.approx(js_shape["width"], abs=0.001)
        assert py_shape["height"] == pytest.approx(js_shape["height"], abs=0.001)
        assert py_shape["cornerRadius"] == pytest.approx(js_shape["cornerRadius"], abs=0.001)

    def test_rect_scale_with_center(self):
        """RectShape scaling with custom center should match."""
        shape = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
            "cornerRadius": 0,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 2.0, 2.0, center_x=0, center_y=0)

        js_shape = run_js_scale(self.page, "rect", shape, 2.0, 2.0, 0, 0)

        assert py_shape["x"] == pytest.approx(js_shape["x"], abs=0.001)
        assert py_shape["y"] == pytest.approx(js_shape["y"], abs=0.001)


class TestEllipseScalingParity:
    """Parity tests for EllipseShape scaling."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page):
        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        self.page = page

    def test_ellipse_scale_uniform(self):
        """EllipseShape uniform scaling should match."""
        shape = {
            "type": "ellipse",
            "cx": 100,
            "cy": 100,
            "rx": 50,
            "ry": 30,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 2.0, 2.0)

        js_shape = run_js_scale(self.page, "ellipse", shape, 2.0, 2.0)

        assert py_shape["cx"] == pytest.approx(js_shape["cx"], abs=0.001)
        assert py_shape["cy"] == pytest.approx(js_shape["cy"], abs=0.001)
        assert py_shape["rx"] == pytest.approx(js_shape["rx"], abs=0.001)
        assert py_shape["ry"] == pytest.approx(js_shape["ry"], abs=0.001)


class TestLineScalingParity:
    """Parity tests for LineShape scaling."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page):
        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        self.page = page

    def test_line_scale_uniform(self):
        """LineShape uniform scaling should match."""
        shape = {
            "type": "line",
            "x1": 0,
            "y1": 0,
            "x2": 100,
            "y2": 100,
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "lineCap": "round",
            "arrowStart": False,
            "arrowEnd": False,
            "arrowSize": 10,
            "fill": False,
            "stroke": True,
            "opacity": 1.0,
        }

        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 2.0, 2.0)

        js_shape = run_js_scale(self.page, "line", shape, 2.0, 2.0)

        assert py_shape["x1"] == pytest.approx(js_shape["x1"], abs=0.001)
        assert py_shape["y1"] == pytest.approx(js_shape["y1"], abs=0.001)
        assert py_shape["x2"] == pytest.approx(js_shape["x2"], abs=0.001)
        assert py_shape["y2"] == pytest.approx(js_shape["y2"], abs=0.001)
        assert py_shape["strokeWidth"] == pytest.approx(js_shape["strokeWidth"], abs=0.001)


class TestPolygonScalingParity:
    """Parity tests for PolygonShape scaling."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page):
        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        self.page = page

    def test_polygon_scale_uniform(self):
        """PolygonShape uniform scaling should match."""
        shape = {
            "type": "polygon",
            "points": [[0, 0], [100, 0], [50, 100]],
            "closed": True,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 2.0, 2.0)

        js_shape = run_js_scale(self.page, "polygon", shape, 2.0, 2.0)

        # Compare each point
        for i, (py_pt, js_pt) in enumerate(zip(py_shape["points"], js_shape["points"])):
            # JS uses [x, y] array format
            assert py_pt[0] == pytest.approx(js_pt[0], abs=0.001), f"Point {i} X mismatch"
            assert py_pt[1] == pytest.approx(js_pt[1], abs=0.001), f"Point {i} Y mismatch"


class TestPathScalingParity:
    """Parity tests for PathShape scaling."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page):
        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        self.page = page

    def test_path_scale_with_handles(self):
        """PathShape scaling with bezier handles should match."""
        shape = {
            "type": "path",
            "points": [
                {"x": 0, "y": 0, "handleOut": {"x": 20, "y": 0}, "type": "corner"},
                {"x": 100, "y": 0, "handleIn": {"x": -20, "y": 0}, "type": "corner"},
                {"x": 100, "y": 100, "type": "corner"},
            ],
            "closed": False,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 2.0, 2.0)

        js_shape = run_js_scale(self.page, "path", shape, 2.0, 2.0)

        # Compare anchor points
        for i, (py_pt, js_pt) in enumerate(zip(py_shape["points"], js_shape["points"])):
            assert py_pt["x"] == pytest.approx(js_pt["x"], abs=0.001), f"Point {i} X mismatch"
            assert py_pt["y"] == pytest.approx(js_pt["y"], abs=0.001), f"Point {i} Y mismatch"

            # Compare handles if present
            if py_pt.get("handleIn"):
                assert py_pt["handleIn"]["x"] == pytest.approx(js_pt["handleIn"]["x"], abs=0.001)
                assert py_pt["handleIn"]["y"] == pytest.approx(js_pt["handleIn"]["y"], abs=0.001)
            if py_pt.get("handleOut"):
                assert py_pt["handleOut"]["x"] == pytest.approx(js_pt["handleOut"]["x"], abs=0.001)
                assert py_pt["handleOut"]["y"] == pytest.approx(js_pt["handleOut"]["y"], abs=0.001)

    def test_path_scale_non_uniform(self):
        """PathShape non-uniform scaling should match."""
        shape = {
            "type": "path",
            "points": [
                {"x": 50, "y": 50, "handleOut": {"x": 10, "y": 10}, "type": "corner"},
                {"x": 100, "y": 100, "type": "corner"},
            ],
            "closed": False,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        py_shape = copy.deepcopy(shape)
        scale_shape(py_shape, 3.0, 0.5)

        js_shape = run_js_scale(self.page, "path", shape, 3.0, 0.5)

        # Handle should scale differently in X and Y
        assert py_shape["points"][0]["handleOut"]["x"] == pytest.approx(js_shape["points"][0]["handleOut"]["x"], abs=0.001)
        assert py_shape["points"][0]["handleOut"]["y"] == pytest.approx(js_shape["points"][0]["handleOut"]["y"], abs=0.001)
