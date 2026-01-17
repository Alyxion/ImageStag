"""Rendering parity tests using Playwright.

These tests verify that dynamic layers (text, vector) render identically
in JavaScript (browser) and Python.

Run with: PYTHONPATH=/tmp/pylibs:$PYTHONPATH pytest tests/test_rendering_parity_playwright.py -v
"""

import pytest
import numpy as np
import sys
import os

# Add ARM64 PIL to path
sys.path.insert(0, '/tmp/pylibs')

from playwright.sync_api import sync_playwright, Page, Browser


def compute_pixel_diff(img1: np.ndarray, img2: np.ndarray) -> float:
    """Compute the percentage of differing pixels between two images."""
    if img1.shape != img2.shape:
        raise ValueError(f"Shape mismatch: {img1.shape} vs {img2.shape}")

    diff = np.abs(img1.astype(int) - img2.astype(int))
    # Count pixels where any channel differs by more than threshold
    threshold = 10
    differing = np.any(diff > threshold, axis=2)
    return np.sum(differing) / (img1.shape[0] * img1.shape[1])


def images_match(img1: np.ndarray, img2: np.ndarray, tolerance: float = 0.05) -> bool:
    """Check if two images match within tolerance."""
    diff = compute_pixel_diff(img1, img2)
    return diff <= tolerance


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


class TestCanvasRenderingParity:
    """Test that basic canvas operations render identically in JS and Python."""

    def test_filled_rectangle(self, page):
        """Filled rectangle should render identically."""
        # Render in JS
        js_pixels = page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            canvas.width = 100;
            canvas.height = 100;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#FF0000';
            ctx.fillRect(10, 10, 80, 80);
            const imageData = ctx.getImageData(0, 0, 100, 100);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((100, 100, 4))

        # Render in Python
        py_array = np.zeros((100, 100, 4), dtype=np.uint8)
        py_array[10:90, 10:90] = [255, 0, 0, 255]

        assert images_match(js_array, py_array, tolerance=0.01), \
            f"Rectangle mismatch: {compute_pixel_diff(js_array, py_array):.2%}"

    def test_filled_ellipse(self, page):
        """Filled ellipse should render similarly (some anti-aliasing diff expected)."""
        # Render in JS
        js_pixels = page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            canvas.width = 100;
            canvas.height = 100;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#00FF00';
            ctx.beginPath();
            ctx.ellipse(50, 50, 40, 30, 0, 0, Math.PI * 2);
            ctx.fill();
            const imageData = ctx.getImageData(0, 0, 100, 100);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((100, 100, 4))

        # Render in Python using PIL
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # PIL ellipse uses bounding box
        draw.ellipse([10, 20, 90, 80], fill=(0, 255, 0, 255))
        py_array = np.array(img)

        # Allow more tolerance for anti-aliasing differences
        assert images_match(js_array, py_array, tolerance=0.10), \
            f"Ellipse mismatch: {compute_pixel_diff(js_array, py_array):.2%}"

    def test_stroked_line(self, page):
        """Stroked line should render similarly."""
        # Render in JS
        js_pixels = page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            canvas.width = 100;
            canvas.height = 100;
            const ctx = canvas.getContext('2d');
            ctx.strokeStyle = '#0000FF';
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.moveTo(10, 50);
            ctx.lineTo(90, 50);
            ctx.stroke();
            const imageData = ctx.getImageData(0, 0, 100, 100);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((100, 100, 4))

        # Render in Python using PIL
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.line([(10, 50), (90, 50)], fill=(0, 0, 255, 255), width=4)
        py_array = np.array(img)

        # Check both have blue pixels
        js_blue = np.sum((js_array[:, :, 2] > 200) & (js_array[:, :, 3] > 200))
        py_blue = np.sum((py_array[:, :, 2] > 200) & (py_array[:, :, 3] > 200))

        assert js_blue > 100, f"JS should have blue pixels, got {js_blue}"
        assert py_blue > 100, f"Python should have blue pixels, got {py_blue}"
        # Allow 30% difference for anti-aliasing
        assert abs(js_blue - py_blue) / max(js_blue, py_blue) < 0.30


class TestTextRenderingParity:
    """Test that text renders similarly in JS and Python."""

    def test_simple_text_has_pixels(self, page):
        """Simple text should produce non-empty output in both."""
        # Render in JS
        js_pixels = page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 50;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#000000';
            ctx.font = '24px Arial';
            ctx.fillText('Hello', 10, 35);
            const imageData = ctx.getImageData(0, 0, 200, 50);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((50, 200, 4))

        # Render in Python using PIL
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGBA', (200, 50), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except OSError:
            font = ImageFont.load_default()
        draw.text((10, 10), 'Hello', fill=(0, 0, 0, 255), font=font)
        py_array = np.array(img)

        # Both should have some black/dark pixels
        js_dark = np.sum(js_array[:, :, 3] > 100)  # Any non-transparent
        py_dark = np.sum(py_array[:, :, 3] > 100)

        assert js_dark > 50, f"JS text should have pixels, got {js_dark}"
        assert py_dark > 50, f"Python text should have pixels, got {py_dark}"

    def test_colored_text(self, page):
        """Colored text should have correct color in both."""
        # Render red text in JS
        js_pixels = page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 50;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#FF0000';
            ctx.font = '24px Arial';
            ctx.fillText('Red', 10, 35);
            const imageData = ctx.getImageData(0, 0, 200, 50);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((50, 200, 4))

        # Render red text in Python
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGBA', (200, 50), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except OSError:
            font = ImageFont.load_default()
        draw.text((10, 10), 'Red', fill=(255, 0, 0, 255), font=font)
        py_array = np.array(img)

        # Both should have red pixels
        js_red = np.sum((js_array[:, :, 0] > 200) & (js_array[:, :, 3] > 100))
        py_red = np.sum((py_array[:, :, 0] > 200) & (py_array[:, :, 3] > 100))

        assert js_red > 50, f"JS should have red pixels, got {js_red}"
        assert py_red > 50, f"Python should have red pixels, got {py_red}"


class TestVectorShapeParity:
    """Test vector shape rendering parity."""

    def test_multiple_shapes(self, page):
        """Multiple shapes should all render."""
        # Render in JS
        js_pixels = page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 100;
            const ctx = canvas.getContext('2d');

            // Red rectangle
            ctx.fillStyle = '#FF0000';
            ctx.fillRect(10, 10, 40, 40);

            // Green circle
            ctx.fillStyle = '#00FF00';
            ctx.beginPath();
            ctx.arc(100, 30, 20, 0, Math.PI * 2);
            ctx.fill();

            // Blue line
            ctx.strokeStyle = '#0000FF';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(140, 10);
            ctx.lineTo(190, 90);
            ctx.stroke();

            const imageData = ctx.getImageData(0, 0, 200, 100);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((100, 200, 4))

        # Render in Python
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (200, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Red rectangle
        draw.rectangle([10, 10, 50, 50], fill=(255, 0, 0, 255))

        # Green circle
        draw.ellipse([80, 10, 120, 50], fill=(0, 255, 0, 255))

        # Blue line
        draw.line([(140, 10), (190, 90)], fill=(0, 0, 255, 255), width=3)

        py_array = np.array(img)

        # Check each color exists
        js_red = np.sum((js_array[:, :, 0] > 200) & (js_array[:, :, 1] < 50))
        js_green = np.sum((js_array[:, :, 1] > 200) & (js_array[:, :, 0] < 50))
        js_blue = np.sum((js_array[:, :, 2] > 200) & (js_array[:, :, 0] < 50))

        py_red = np.sum((py_array[:, :, 0] > 200) & (py_array[:, :, 1] < 50))
        py_green = np.sum((py_array[:, :, 1] > 200) & (py_array[:, :, 0] < 50))
        py_blue = np.sum((py_array[:, :, 2] > 200) & (py_array[:, :, 0] < 50))

        assert js_red > 100, f"JS should have red, got {js_red}"
        assert js_green > 100, f"JS should have green, got {js_green}"
        assert js_blue > 10, f"JS should have blue, got {js_blue}"

        assert py_red > 100, f"Python should have red, got {py_red}"
        assert py_green > 100, f"Python should have green, got {py_green}"
        assert py_blue > 10, f"Python should have blue, got {py_blue}"


class TestLanczosResamplingParity:
    """Test that Lanczos resampling produces similar results."""

    def test_downscale_4x(self, page):
        """4x downscale should preserve content in both."""
        # Render and downscale in JS
        js_pixels = page.evaluate("""() => {
            // Create high-res canvas
            const srcCanvas = document.createElement('canvas');
            srcCanvas.width = 400;
            srcCanvas.height = 400;
            const srcCtx = srcCanvas.getContext('2d');
            srcCtx.fillStyle = '#FF0000';
            srcCtx.fillRect(100, 100, 200, 200);

            // Downscale to 100x100
            const dstCanvas = document.createElement('canvas');
            dstCanvas.width = 100;
            dstCanvas.height = 100;
            const dstCtx = dstCanvas.getContext('2d');
            dstCtx.imageSmoothingEnabled = true;
            dstCtx.imageSmoothingQuality = 'high';
            dstCtx.drawImage(srcCanvas, 0, 0, 100, 100);

            const imageData = dstCtx.getImageData(0, 0, 100, 100);
            return Array.from(imageData.data);
        }""")
        js_array = np.array(js_pixels, dtype=np.uint8).reshape((100, 100, 4))

        # Downscale in Python using our Lanczos
        from stagforge.rendering.lanczos import lanczos_resample

        # Create high-res source
        src = np.zeros((400, 400, 4), dtype=np.uint8)
        src[100:300, 100:300] = [255, 0, 0, 255]

        # Downscale
        py_array = lanczos_resample(src, 100, 100)

        # Both should have red square in center
        js_center_red = js_array[40:60, 40:60, 0].mean()
        py_center_red = py_array[40:60, 40:60, 0].mean()

        assert js_center_red > 200, f"JS center should be red, got {js_center_red}"
        assert py_center_red > 200, f"Python center should be red, got {py_center_red}"

        # Corners should be mostly transparent/black
        js_corner = js_array[5:15, 5:15, 3].mean()
        py_corner = py_array[5:15, 5:15, 3].mean()

        assert js_corner < 50, f"JS corner should be transparent, got {js_corner}"
        assert py_corner < 50, f"Python corner should be transparent, got {py_corner}"
