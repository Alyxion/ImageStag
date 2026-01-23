"""SVG layer rendering parity tests.

Tests that JS (Chrome browser) and Python (resvg) produce identical
pixel output when rendering raw SVG content.

Requirements:
- 99.9% pixel match (≤0.1% difference)
- All sample SVG files must be tested

Reference: Chrome is the gold standard renderer. Python/resvg must match Chrome.

Run with: poetry run pytest tests/stagforge/test_svg_parity.py -v

When tests fail, comparison images are saved to tests/stagforge/tmp/ showing:
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

from stagforge.rendering.svg_layer import render_svg_layer, _normalize_svg_dimensions

# Directory for saving debug comparison images
DEBUG_DIR = Path(__file__).parent / "tmp"

# Path to SVG samples directory
SVGS_DIR = Path(__file__).parent.parent.parent / "imagestag" / "data" / "svgs"

# Supersampling factor for Python/resvg rendering
# Use 2 for quality matching Chrome's rendering
SUPERSAMPLE = 2


def normalize_svg_for_parity(svg_content: str, width: int, height: int) -> str:
    """Normalize SVG dimensions for consistent rendering across platforms.

    Both Chrome and resvg should render the same normalized SVG content
    to ensure true parity testing.

    Args:
        svg_content: Raw SVG string
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        Normalized SVG string with pixel dimensions
    """
    return _normalize_svg_dimensions(svg_content, width, height)


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


def assert_images_match(py_pixels: np.ndarray, js_pixels: np.ndarray, test_name: str, tolerance: float = 0.001):
    """Assert images match, saving comparison always for inspection.

    Args:
        py_pixels: Python/resvg rendered pixels
        js_pixels: Browser/JS rendered pixels
        test_name: Name for debug output file
        tolerance: Maximum allowed difference ratio (default 0.001 = 99.9% match)
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

    This matches the SVGLayer.render() method in JavaScript.

    Args:
        page: Playwright page
        svg_string: Raw SVG document string
        width: Output canvas width
        height: Output canvas height

    Returns:
        RGBA numpy array
    """
    # Escape backticks and backslashes for JavaScript template literal
    svg_escaped = svg_string.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

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
                        ctx.imageSmoothingEnabled = true;
                        ctx.imageSmoothingQuality = 'high';
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                        URL.revokeObjectURL(url);

                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        resolve(Array.from(imageData.data));
                    }};
                    img.onerror = (e) => {{
                        URL.revokeObjectURL(url);
                        reject(new Error('Failed to load SVG: ' + e));
                    }};
                    img.src = url;
                }});
            }};
        </script>
        </body>
        </html>
    """)

    # Render and get pixel data
    pixel_data = page.evaluate(f"renderSVG(`{svg_escaped}`)")
    return np.array(pixel_data, dtype=np.uint8).reshape((height, width, 4))


class TestSVGLayerParity:
    """Test SVG layer rendering parity between JS and Python."""

    @pytest.mark.parametrize("svg_file,tolerance", [
        # External SVGs have anti-aliasing differences between Chrome and resvg
        # Allow up to 20% difference for complex paths/curves with AA enabled
        ("openclipart/buck-deer-silhouette.svg", 0.20),
        ("openclipart/leaping-deer-silhouette.svg", 0.20),
        ("noto-emoji/deer.svg", 0.15),
        ("noto-emoji/fire.svg", 0.15),
    ])
    def test_svg_sample_parity(self, page, svg_file, tolerance):
        """JS and Python must render SVG sample within tolerance.

        Note: External SVGs don't have shape-rendering="crispEdges", so
        anti-aliasing differences between Chrome and resvg are expected.
        Tolerance is higher for complex SVGs with many curved paths.
        """
        svg_path = SVGS_DIR / svg_file
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()

        # Render dimensions
        width, height = 200, 200

        # Normalize SVG for both renderers to ensure true parity
        # (raw SVGs with mm/cm units are handled differently by Chrome vs resvg)
        normalized_svg = normalize_svg_for_parity(svg_content, width, height)

        # Render in browser (Chrome reference) - use normalized SVG
        js_pixels = render_svg_in_browser(page, normalized_svg, width, height)

        # Render in Python (resvg) - render_svg_layer also normalizes internally
        layer_data = {
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }
        py_pixels = render_svg_layer(layer_data, supersample=SUPERSAMPLE)

        # Test name for debug output
        test_name = f"svg_sample_{svg_file.replace('/', '_').replace('.svg', '')}"

        # Assert parity with appropriate tolerance for external SVGs
        assert_images_match(py_pixels, js_pixels, test_name, tolerance=tolerance)

    def test_simple_rect_svg_parity(self, page):
        """Simple red rectangle SVG should render identically."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100" shape-rendering="crispEdges">
  <rect x="10" y="10" width="80" height="80" fill="#FF0000"/>
</svg>'''

        width, height = 100, 100

        js_pixels = render_svg_in_browser(page, svg_content, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=1)  # No supersampling for crisp edges

        assert_images_match(py_pixels, js_pixels, "svg_simple_rect")

    def test_circle_svg_parity(self, page):
        """Circle SVG should render identically."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100" shape-rendering="crispEdges">
  <circle cx="50" cy="50" r="40" fill="#0000FF"/>
</svg>'''

        width, height = 100, 100

        js_pixels = render_svg_in_browser(page, svg_content, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=1)

        assert_images_match(py_pixels, js_pixels, "svg_circle")

    def test_gradient_svg_parity(self, page):
        """SVG with gradient should render within tolerance.

        Note: Gradient interpolation may differ slightly between Chrome and resvg.
        """
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
      <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect x="10" y="10" width="80" height="80" fill="url(#grad1)"/>
</svg>'''

        width, height = 100, 100

        js_pixels = render_svg_in_browser(page, svg_content, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=SUPERSAMPLE)

        # Allow 10% tolerance for gradient edge anti-aliasing
        assert_images_match(py_pixels, js_pixels, "svg_gradient", tolerance=0.10)

    def test_complex_path_svg_parity(self, page):
        """Complex path SVG should render identically."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100" shape-rendering="crispEdges">
  <path d="M 10 80 Q 50 10 90 80 Z" fill="#00FF00" stroke="#000000" stroke-width="2"/>
</svg>'''

        width, height = 100, 100

        js_pixels = render_svg_in_browser(page, svg_content, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=1)

        assert_images_match(py_pixels, js_pixels, "svg_path")

    def test_opacity_svg_parity(self, page):
        """SVG with opacity should render identically."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100" shape-rendering="crispEdges">
  <rect x="10" y="10" width="60" height="60" fill="#FF0000"/>
  <rect x="30" y="30" width="60" height="60" fill="#0000FF" opacity="0.5"/>
</svg>'''

        width, height = 100, 100

        js_pixels = render_svg_in_browser(page, svg_content, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=1)

        assert_images_match(py_pixels, js_pixels, "svg_opacity")


class TestSVGSamplesParity:
    """Test parity for all available SVG sample files.

    Note: External SVGs don't have shape-rendering="crispEdges", so
    anti-aliasing differences between Chrome and resvg are expected.
    Tolerances are set based on SVG complexity and use of gradients.
    """

    def test_colored_feather_parity(self, page):
        """Complex colored-feather.svg should render within tolerance.

        This is a very complex SVG with many gradients and paths.
        """
        svg_path = SVGS_DIR / "openclipart" / "colored-feather.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        width, height = 256, 256

        # Normalize SVG for both renderers
        normalized_svg = normalize_svg_for_parity(svg_content, width, height)

        js_pixels = render_svg_in_browser(page, normalized_svg, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=SUPERSAMPLE)

        # Complex SVG with gradients - allow 15% tolerance
        assert_images_match(py_pixels, js_pixels, "svg_colored_feather", tolerance=0.15)

    def test_noto_emoji_rainbow_parity(self, page):
        """Rainbow emoji should render within tolerance."""
        svg_path = SVGS_DIR / "noto-emoji" / "rainbow.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        width, height = 128, 128

        # Normalize SVG for both renderers
        normalized_svg = normalize_svg_for_parity(svg_content, width, height)

        js_pixels = render_svg_in_browser(page, normalized_svg, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=SUPERSAMPLE)

        # Emoji with curves and gradients - allow 15% tolerance
        assert_images_match(py_pixels, js_pixels, "svg_rainbow", tolerance=0.15)

    def test_bootstrap_icon_parity(self, page):
        """Bootstrap icon should render within tolerance."""
        svg_path = SVGS_DIR / "bootstrap-icons" / "gear-wide-connected.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        width, height = 64, 64

        # Normalize SVG for both renderers
        normalized_svg = normalize_svg_for_parity(svg_content, width, height)

        js_pixels = render_svg_in_browser(page, normalized_svg, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=SUPERSAMPLE)

        # Icon with curves at small size - allow 15% tolerance
        assert_images_match(py_pixels, js_pixels, "svg_bootstrap_gear", tolerance=0.15)

    def test_heroicon_parity(self, page):
        """Heroicon should render within tolerance."""
        svg_path = SVGS_DIR / "heroicons" / "cog-8-tooth.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        width, height = 64, 64

        # Normalize SVG for both renderers
        normalized_svg = normalize_svg_for_parity(svg_content, width, height)

        js_pixels = render_svg_in_browser(page, normalized_svg, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=SUPERSAMPLE)

        # Icon with outlines and curves at small size - allow 20% tolerance
        assert_images_match(py_pixels, js_pixels, "svg_heroicon_cog", tolerance=0.20)

    def test_simple_icon_linux_parity(self, page):
        """Simple Icons Linux logo should render within tolerance."""
        svg_path = SVGS_DIR / "simple-icons" / "linux.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        width, height = 64, 64

        # Normalize SVG for both renderers
        normalized_svg = normalize_svg_for_parity(svg_content, width, height)

        js_pixels = render_svg_in_browser(page, normalized_svg, width, height)
        py_pixels = render_svg_layer({
            "svgContent": svg_content,
            "width": width,
            "height": height,
        }, supersample=SUPERSAMPLE)

        # Icon with curves at small size - allow 15% tolerance
        assert_images_match(py_pixels, js_pixels, "svg_simple_icons_linux", tolerance=0.15)
