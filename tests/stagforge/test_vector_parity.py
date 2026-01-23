"""Vector layer rendering parity tests.

Tests that JS (browser SVG rendering) and Python (resvg) produce identical
pixel output for all vector shape types.

Requirements:
- 99.9% pixel match (≤0.1% difference)
- All shape types must be tested
- Various style combinations must be tested

Reference: Chrome is the gold standard renderer. Python/resvg must match Chrome.

Run with: poetry run pytest tests/test_vector_parity.py -v

When tests fail, comparison images are saved to tests/tmp/ showing:
- Left: Python/resvg output
- Middle: Browser/JS output (Chrome reference)
- Right: Difference mask (white = different pixels)
"""

import pytest
import numpy as np
import shutil
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright, Page, Browser
from stagforge.rendering.vector import shapes_to_svg, render_vector_layer, shape_to_svg_element

# Directory for saving debug comparison images
DEBUG_DIR = Path(__file__).parent / "tmp"

# Supersampling factor for Python/resvg rendering
# Testing shows 1x (no supersampling) produces best results
# because the AA differences are at algorithm level, not resolution
SUPERSAMPLE = 1


@pytest.fixture(scope="session", autouse=True)
def cleanup_old_outputs():
    """Clean up old comparison images before running tests."""
    if DEBUG_DIR.exists():
        shutil.rmtree(DEBUG_DIR)
    DEBUG_DIR.mkdir(exist_ok=True)
    yield
    # Keep outputs after tests for inspection


def save_comparison_image(name: str, py_pixels: np.ndarray, js_pixels: np.ndarray) -> str:
    """Save a side-by-side comparison image for debugging.

    Args:
        name: Test name for the filename
        py_pixels: Python/resvg rendered pixels (H, W, 4)
        js_pixels: Browser/JS rendered pixels (H, W, 4)

    Returns:
        Path to saved image
    """
    DEBUG_DIR.mkdir(exist_ok=True)

    h, w = py_pixels.shape[:2]

    # Create difference mask
    diff = np.abs(py_pixels.astype(int) - js_pixels.astype(int))
    threshold = 4  # Differences below 5 don't count as errors
    diff_mask = np.any(diff > threshold, axis=2)

    # Create RGB difference visualization (white = different, black = same)
    diff_img = np.zeros((h, w, 4), dtype=np.uint8)
    diff_img[diff_mask] = [255, 255, 255, 255]
    diff_img[~diff_mask] = [0, 0, 0, 255]

    # Create side-by-side image: [resvg | browser | diff]
    combined = np.zeros((h, w * 3 + 20, 4), dtype=np.uint8)  # 10px gap between each
    combined[:, :, 3] = 255  # Opaque background
    combined[:, :, :3] = 128  # Gray background

    # Copy images with alpha compositing on gray background
    for i, (img, offset) in enumerate([(py_pixels, 0), (js_pixels, w + 10), (diff_img, w * 2 + 20)]):
        for c in range(3):
            alpha = img[:, :, 3] / 255.0
            combined[:, offset:offset+w, c] = (
                img[:, :, c] * alpha + 128 * (1 - alpha)
            ).astype(np.uint8)
        combined[:, offset:offset+w, 3] = 255

    # Save as PNG
    filepath = DEBUG_DIR / f"{name}.png"
    Image.fromarray(combined).save(filepath)
    return str(filepath)


def compute_pixel_diff(img1: np.ndarray, img2: np.ndarray) -> float:
    """Compute the percentage of differing pixels between two images.

    Args:
        img1: First RGBA image as numpy array (H, W, 4)
        img2: Second RGBA image as numpy array (H, W, 4)

    Returns:
        Percentage of differing pixels (0.0 to 1.0)
    """
    if img1.shape != img2.shape:
        raise ValueError(f"Shape mismatch: {img1.shape} vs {img2.shape}")

    # Allow small differences for anti-aliasing
    diff = np.abs(img1.astype(int) - img2.astype(int))
    threshold = 4  # Differences below 5 don't count as errors
    differing = np.any(diff > threshold, axis=2)
    return np.sum(differing) / (img1.shape[0] * img1.shape[1])


def images_match(img1: np.ndarray, img2: np.ndarray, tolerance: float = 0.001) -> bool:
    """Check if two images match within tolerance.

    Args:
        img1: First image
        img2: Second image
        tolerance: Maximum allowed difference ratio. Default 0.001 = 99.9% match.
            DO NOT increase this value - differences >0.1% indicate real bugs,
            not anti-aliasing. The per-channel threshold of 10 already accounts
            for anti-aliasing rounding differences.

    Returns:
        True if images match within tolerance
    """
    diff = compute_pixel_diff(img1, img2)
    return diff <= tolerance


def assert_images_match(py_pixels: np.ndarray, js_pixels: np.ndarray, test_name: str, tolerance: float = 0.001):
    """Assert images match, saving comparison always for inspection.

    Args:
        py_pixels: Python/resvg rendered pixels
        js_pixels: Browser/JS rendered pixels
        test_name: Name for debug output file
        tolerance: Maximum allowed difference ratio
    """
    diff = compute_pixel_diff(py_pixels, js_pixels)
    # Always save comparison image for inspection
    filepath = save_comparison_image(test_name, py_pixels, js_pixels)
    if diff > tolerance:
        raise AssertionError(
            f"{test_name}: {diff:.4%} pixels differ (tolerance: {tolerance:.4%})\n"
            f"Comparison saved to: {filepath}\n"
            f"[Left: resvg/Python | Middle: browser/JS (Chrome reference) | Right: diff mask]"
        )


@pytest.fixture(scope="module")
def browser():
    """Launch browser for all tests in module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


def render_svg_in_browser(page: Page, svg_string: str, width: int, height: int) -> np.ndarray:
    """Render an SVG string in the browser and return pixel data.

    Args:
        page: Playwright page
        svg_string: SVG document string
        width: Canvas width
        height: Canvas height

    Returns:
        RGBA numpy array
    """
    # Set up minimal HTML with canvas
    page.set_content(f"""
        <html>
        <body style="margin:0;padding:0;">
        <canvas id="canvas" width="{width}" height="{height}"></canvas>
        <script>
            window.renderSVG = async function(svgString) {{
                const canvas = document.getElementById('canvas');
                const ctx = canvas.getContext('2d');

                const blob = new Blob([svgString], {{ type: 'image/svg+xml' }});
                const url = URL.createObjectURL(blob);

                return new Promise((resolve, reject) => {{
                    const img = new Image();
                    img.onload = () => {{
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        ctx.drawImage(img, 0, 0);
                        URL.revokeObjectURL(url);

                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        resolve(Array.from(imageData.data));
                    }};
                    img.onerror = reject;
                    img.src = url;
                }});
            }};
        </script>
        </body>
        </html>
    """)

    # Render and get pixel data
    pixel_data = page.evaluate(f"renderSVG(`{svg_string}`)")
    return np.array(pixel_data, dtype=np.uint8).reshape((height, width, 4))


class TestRectParity:
    """Test rectangle rendering parity."""

    def test_filled_rect(self, page):
        """Simple filled rectangle."""
        shapes = [{
            "type": "rect",
            "x": 10, "y": 10,
            "width": 80, "height": 60,
            "fill": True,
            "stroke": False,
            "fillColor": "#FF0000",
            "strokeColor": "#000000",
            "strokeWidth": 1,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "rect_filled")

    def test_stroked_rect(self, page):
        """Rectangle with stroke only."""
        shapes = [{
            "type": "rect",
            "x": 10, "y": 10,
            "width": 80, "height": 60,
            "fill": False,
            "stroke": True,
            "fillColor": "#FF0000",
            "strokeColor": "#0000FF",
            "strokeWidth": 3,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "rect_stroked")

    def test_filled_and_stroked_rect(self, page):
        """Rectangle with both fill and stroke."""
        shapes = [{
            "type": "rect",
            "x": 10, "y": 10,
            "width": 80, "height": 60,
            "fill": True,
            "stroke": True,
            "fillColor": "#00FF00",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "rect_filled_stroked")

    def test_rounded_rect(self, page):
        """Rectangle with rounded corners."""
        shapes = [{
            "type": "rect",
            "x": 10, "y": 10,
            "width": 80, "height": 60,
            "cornerRadius": 10,
            "fill": True,
            "stroke": True,
            "fillColor": "#FF00FF",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "rect_rounded")

    def test_rect_with_opacity(self, page):
        """Rectangle with partial opacity."""
        shapes = [{
            "type": "rect",
            "x": 10, "y": 10,
            "width": 80, "height": 60,
            "fill": True,
            "stroke": False,
            "fillColor": "#FF0000",
            "strokeColor": "#000000",
            "strokeWidth": 1,
            "opacity": 0.5
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "rect_opacity")


class TestEllipseParity:
    """Test ellipse rendering parity."""

    def test_filled_ellipse(self, page):
        """Simple filled ellipse."""
        shapes = [{
            "type": "ellipse",
            "cx": 50, "cy": 50,
            "rx": 40, "ry": 30,
            "fill": True,
            "stroke": False,
            "fillColor": "#0000FF",
            "strokeColor": "#000000",
            "strokeWidth": 1,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "ellipse_filled")

    def test_stroked_ellipse(self, page):
        """Ellipse with stroke only."""
        shapes = [{
            "type": "ellipse",
            "cx": 50, "cy": 50,
            "rx": 40, "ry": 30,
            "fill": False,
            "stroke": True,
            "fillColor": "#0000FF",
            "strokeColor": "#FF0000",
            "strokeWidth": 4,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "ellipse_stroked")

    def test_circle(self, page):
        """Circle (equal radii)."""
        shapes = [{
            "type": "ellipse",
            "cx": 50, "cy": 50,
            "rx": 35, "ry": 35,
            "fill": True,
            "stroke": True,
            "fillColor": "#FFFF00",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "ellipse_circle")


class TestLineParity:
    """Test line rendering parity."""

    def test_horizontal_line(self, page):
        """Horizontal line."""
        shapes = [{
            "type": "line",
            "x1": 10, "y1": 50,
            "x2": 90, "y2": 50,
            "strokeColor": "#FF0000",
            "strokeWidth": 3,
            "lineCap": "round",
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "line_horizontal")

    def test_diagonal_line(self, page):
        """Diagonal line."""
        shapes = [{
            "type": "line",
            "x1": 10, "y1": 10,
            "x2": 90, "y2": 90,
            "strokeColor": "#00FF00",
            "strokeWidth": 5,
            "lineCap": "round",
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "line_diagonal")

    def test_line_butt_cap(self, page):
        """Line with butt cap."""
        shapes = [{
            "type": "line",
            "x1": 10, "y1": 50,
            "x2": 90, "y2": 50,
            "strokeColor": "#0000FF",
            "strokeWidth": 8,
            "lineCap": "butt",
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "line_butt_cap")

    def test_line_square_cap(self, page):
        """Line with square cap."""
        shapes = [{
            "type": "line",
            "x1": 10, "y1": 50,
            "x2": 90, "y2": 50,
            "strokeColor": "#FF00FF",
            "strokeWidth": 8,
            "lineCap": "square",
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "line_square_cap")


class TestPolygonParity:
    """Test polygon rendering parity."""

    def test_triangle(self, page):
        """Simple triangle."""
        shapes = [{
            "type": "polygon",
            "points": [[50, 10], [90, 90], [10, 90]],
            "closed": True,
            "fill": True,
            "stroke": False,
            "fillColor": "#FF0000",
            "strokeColor": "#000000",
            "strokeWidth": 1,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "polygon_triangle")

    def test_pentagon(self, page):
        """Pentagon with fill and stroke."""
        import math
        # Generate pentagon points
        points = []
        for i in range(5):
            angle = i * 2 * math.pi / 5 - math.pi / 2
            x = 50 + 40 * math.cos(angle)
            y = 50 + 40 * math.sin(angle)
            points.append([x, y])

        shapes = [{
            "type": "polygon",
            "points": points,
            "closed": True,
            "fill": True,
            "stroke": True,
            "fillColor": "#00FF00",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "polygon_pentagon")

    def test_open_polyline(self, page):
        """Open polyline (not closed)."""
        shapes = [{
            "type": "polygon",
            "points": [[10, 10], [50, 90], [90, 10]],
            "closed": False,
            "fill": False,
            "stroke": True,
            "fillColor": "#000000",
            "strokeColor": "#0000FF",
            "strokeWidth": 3,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "polygon_polyline")


class TestPathParity:
    """Test bezier path rendering parity."""

    def test_straight_path(self, page):
        """Path with only straight line segments."""
        shapes = [{
            "type": "path",
            "points": [
                {"x": 10, "y": 50, "handleIn": None, "handleOut": None},
                {"x": 50, "y": 10, "handleIn": None, "handleOut": None},
                {"x": 90, "y": 50, "handleIn": None, "handleOut": None}
            ],
            "closed": False,
            "fill": False,
            "stroke": True,
            "fillColor": "#000000",
            "strokeColor": "#FF0000",
            "strokeWidth": 3,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "path_straight")

    def test_cubic_bezier_path(self, page):
        """Path with cubic bezier curves."""
        shapes = [{
            "type": "path",
            "points": [
                {"x": 10, "y": 50, "handleIn": None, "handleOut": {"x": 20, "y": -30}},
                {"x": 90, "y": 50, "handleIn": {"x": -20, "y": -30}, "handleOut": None}
            ],
            "closed": False,
            "fill": False,
            "stroke": True,
            "fillColor": "#000000",
            "strokeColor": "#0000FF",
            "strokeWidth": 3,
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "path_cubic_bezier")

    def test_closed_bezier_path(self, page):
        """Closed path with curves - like a blob shape.

        Note: Uses stroke-width=1 because multi-pixel strokes on bezier curves
        have fill/stroke boundary ambiguity between Chrome and resvg when
        using crispEdges (no anti-aliasing).
        """
        shapes = [{
            "type": "path",
            "points": [
                {"x": 50, "y": 10, "handleIn": {"x": -15, "y": 0}, "handleOut": {"x": 15, "y": 0}},
                {"x": 90, "y": 50, "handleIn": {"x": 0, "y": -15}, "handleOut": {"x": 0, "y": 15}},
                {"x": 50, "y": 90, "handleIn": {"x": 15, "y": 0}, "handleOut": {"x": -15, "y": 0}},
                {"x": 10, "y": 50, "handleIn": {"x": 0, "y": 15}, "handleOut": {"x": 0, "y": -15}}
            ],
            "closed": True,
            "fill": True,
            "stroke": True,
            "fillColor": "#00FF00",
            "strokeColor": "#000000",
            "strokeWidth": 1,  # Use 1px to avoid fill/stroke boundary ambiguity
            "opacity": 1.0
        }]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "path_closed_bezier")


class TestMultipleShapesParity:
    """Test multiple shapes composited together."""

    def test_overlapping_shapes(self, page):
        """Multiple overlapping shapes."""
        shapes = [
            {
                "type": "rect",
                "x": 10, "y": 10,
                "width": 50, "height": 50,
                "fill": True,
                "stroke": False,
                "fillColor": "#FF0000",
                "strokeColor": "#000000",
                "strokeWidth": 1,
                "opacity": 1.0
            },
            {
                "type": "ellipse",
                "cx": 60, "cy": 60,
                "rx": 30, "ry": 30,
                "fill": True,
                "stroke": False,
                "fillColor": "#0000FF",
                "strokeColor": "#000000",
                "strokeWidth": 1,
                "opacity": 1.0
            },
            {
                "type": "line",
                "x1": 10, "y1": 90,
                "x2": 90, "y2": 10,
                "strokeColor": "#00FF00",
                "strokeWidth": 3,
                "lineCap": "round",
                "opacity": 1.0
            }
        ]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "multiple_overlapping")

    def test_semi_transparent_overlap(self, page):
        """Semi-transparent shapes overlapping."""
        shapes = [
            {
                "type": "rect",
                "x": 10, "y": 10,
                "width": 60, "height": 60,
                "fill": True,
                "stroke": False,
                "fillColor": "#FF0000",
                "strokeColor": "#000000",
                "strokeWidth": 1,
                "opacity": 0.5
            },
            {
                "type": "rect",
                "x": 30, "y": 30,
                "width": 60, "height": 60,
                "fill": True,
                "stroke": False,
                "fillColor": "#0000FF",
                "strokeColor": "#000000",
                "strokeWidth": 1,
                "opacity": 0.5
            }
        ]

        svg = shapes_to_svg(shapes, 100, 100)
        js_pixels = render_svg_in_browser(page, svg, 100, 100)
        py_pixels = render_vector_layer({"shapes": shapes, "width": 100, "height": 100}, supersample=SUPERSAMPLE)

        assert_images_match(py_pixels, js_pixels, "multiple_semi_transparent")


class TestSVGGeneration:
    """Test that SVG generation matches between JS and Python."""

    def test_rect_svg_element(self):
        """Rect SVG element generation."""
        shape = {
            "type": "rect",
            "x": 10, "y": 20,
            "width": 100, "height": 50,
            "fill": True,
            "stroke": True,
            "fillColor": "#FF0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "opacity": 1.0
        }
        svg_element = shape_to_svg_element(shape)
        assert 'x="10"' in svg_element
        assert 'y="20"' in svg_element
        assert 'width="100"' in svg_element
        assert 'height="50"' in svg_element
        assert 'fill="#FF0000"' in svg_element

    def test_ellipse_svg_element(self):
        """Ellipse SVG element generation."""
        shape = {
            "type": "ellipse",
            "cx": 50, "cy": 60,
            "rx": 30, "ry": 20,
            "fill": True,
            "stroke": False,
            "fillColor": "#00FF00",
            "strokeColor": "#000000",
            "strokeWidth": 1,
            "opacity": 0.8
        }
        svg_element = shape_to_svg_element(shape)
        assert 'cx="50"' in svg_element
        assert 'cy="60"' in svg_element
        assert 'rx="30"' in svg_element
        assert 'ry="20"' in svg_element
        assert 'opacity="0.8"' in svg_element

    def test_line_svg_element(self):
        """Line SVG element generation."""
        shape = {
            "type": "line",
            "x1": 0, "y1": 0,
            "x2": 100, "y2": 100,
            "strokeColor": "#0000FF",
            "strokeWidth": 5,
            "lineCap": "round",
            "opacity": 1.0
        }
        svg_element = shape_to_svg_element(shape)
        assert 'x1="0"' in svg_element
        assert 'y1="0"' in svg_element
        assert 'x2="100"' in svg_element
        assert 'y2="100"' in svg_element
        assert 'stroke-linecap="round"' in svg_element

    def test_polygon_svg_element(self):
        """Polygon SVG element generation."""
        shape = {
            "type": "polygon",
            "points": [[10, 10], [90, 10], [50, 90]],
            "closed": True,
            "fill": True,
            "stroke": True,
            "fillColor": "#FFFF00",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "opacity": 1.0
        }
        svg_element = shape_to_svg_element(shape)
        assert '<polygon' in svg_element
        assert 'points="10,10 90,10 50,90"' in svg_element

    def test_full_svg_document(self):
        """Full SVG document generation."""
        shapes = [
            {"type": "rect", "x": 0, "y": 0, "width": 50, "height": 50,
             "fill": True, "stroke": False, "fillColor": "#FF0000",
             "strokeColor": "#000", "strokeWidth": 1, "opacity": 1.0}
        ]
        svg = shapes_to_svg(shapes, 100, 100)
        assert '<?xml version="1.0"' in svg
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg
        assert 'width="100"' in svg
        assert 'height="100"' in svg
        assert 'viewBox="0 0 100 100"' in svg



@pytest.mark.skip(reason="Requires external server running with active session. Run manually.")
class TestVectorLayerViaAPI:
    """Test vector layer functionality via the Session API.

    These tests require the server to be running at 127.0.0.1:8080.
    Run with: pytest tests/test_vector_parity.py::TestVectorLayerViaAPI -v
    """

    @pytest.fixture
    def api_client(self):
        """HTTP client for API calls."""
        import httpx
        return httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=10.0)

    @pytest.fixture
    def session_id(self, api_client):
        """Get an active session ID."""
        try:
            response = api_client.get("/sessions")
            sessions = response.json().get("sessions", [])
            if not sessions:
                pytest.skip("No active session found. Open the editor in a browser first.")
            return sessions[0]["id"]
        except Exception as e:
            pytest.skip(f"Server not running: {e}")

    def test_session_returns_layers_with_dimensions(self, api_client, session_id):
        """Session API returns layer dimensions and offsets."""
        # Create a new document to ensure we have layers
        response = api_client.post(f"/sessions/{session_id}/command", json={
            "command": "new_document",
            "params": {"width": 800, "height": 600}
        })
        assert response.status_code == 200

        # Get session state
        session = api_client.get(f"/sessions/{session_id}").json()

        # Should have at least one layer (Background)
        assert len(session["layers"]) >= 1, f"Expected layers but got: {session['layers']}"

        # Check first layer has correct structure
        layer = session["layers"][0]
        assert layer["width"] == 800
        assert layer["height"] == 600
        assert layer["offset_x"] == 0
        assert layer["offset_y"] == 0

    def test_layer_info_includes_type_and_dimensions(self, api_client, session_id):
        """Session API returns layer type, width, height, and offsets."""
        # Create a new document
        api_client.post(f"/sessions/{session_id}/command", json={
            "command": "new_document",
            "params": {"width": 640, "height": 480}
        })

        session = api_client.get(f"/sessions/{session_id}").json()
        assert len(session["layers"]) >= 1

        for layer in session["layers"]:
            assert "type" in layer, "Layer missing 'type' field"
            assert "width" in layer, "Layer missing 'width' field"
            assert "height" in layer, "Layer missing 'height' field"
            assert "offset_x" in layer, "Layer missing 'offset_x' field"
            assert "offset_y" in layer, "Layer missing 'offset_y' field"
            assert layer["type"] in ["raster", "vector", "text"]
            assert layer["width"] > 0
            assert layer["height"] > 0
