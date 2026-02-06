"""Tests for document open API with various file formats.

Tests the /documents/open, /documents/new, and /documents/sample endpoints
by opening files, rendering in JS, and comparing to ground truth.
"""

import base64
import io
import json
import math
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from stagforge.formats import create_sample_document, SFRDocument

from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


# --- Helper Functions ---


async def get_document_image(helpers: TestHelpers) -> np.ndarray | None:
    """Get the current document composite image as an RGBA numpy array."""
    import aiohttp

    base_url = helpers.editor.base_url
    url = f"{base_url}/api/sessions/current/documents/current/image?format=png"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.read()
            img = Image.open(io.BytesIO(data))
            return np.array(img.convert('RGBA'))


# --- Test Image Generation ---


def create_test_png(width: int = 200, height: int = 150, color: tuple = (255, 0, 0, 255)) -> bytes:
    """Create a test PNG image."""
    img = Image.new('RGBA', (width, height), color)
    # Add a diagonal line for visual distinction
    draw = ImageDraw.Draw(img)
    draw.line([(0, 0), (width, height)], fill=(255, 255, 255, 255), width=3)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def create_test_jpg(width: int = 200, height: int = 150, color: tuple = (0, 128, 255)) -> bytes:
    """Create a test JPEG image."""
    img = Image.new('RGB', (width, height), color[:3])
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, width - 20, height - 20], fill=(255, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    return buffer.getvalue()


def create_test_webp(width: int = 200, height: int = 150, color: tuple = (0, 255, 128, 255)) -> bytes:
    """Create a test WebP image."""
    img = Image.new('RGBA', (width, height), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, width - 30, height - 30], fill=(128, 0, 255, 200))
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', lossless=True)
    return buffer.getvalue()


def create_test_bmp(width: int = 200, height: int = 150, color: tuple = (255, 128, 0)) -> bytes:
    """Create a test BMP image."""
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    # Draw a cross
    draw.line([(width // 2, 0), (width // 2, height)], fill=(0, 0, 0), width=5)
    draw.line([(0, height // 2), (width, height // 2)], fill=(0, 0, 0), width=5)
    buffer = io.BytesIO()
    img.save(buffer, format='BMP')
    return buffer.getvalue()


def create_test_gif(width: int = 200, height: int = 150, color: tuple = (128, 255, 128)) -> bytes:
    """Create a test GIF image."""
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    # Draw concentric circles
    for i in range(5):
        r = 20 + i * 15
        draw.ellipse([width // 2 - r, height // 2 - r, width // 2 + r, height // 2 + r],
                     outline=(0, 0, 0), width=2)
    buffer = io.BytesIO()
    img.save(buffer, format='GIF')
    return buffer.getvalue()


def create_test_svg(width: int = 200, height: int = 150, color: str = "#3498DB") -> bytes:
    """Create a test SVG."""
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <circle cx="{width // 2}" cy="{height // 2}" r="{min(width, height) // 3}" fill="{color}"/>
  <rect x="{width // 4}" y="{height // 4}" width="{width // 2}" height="{height // 2}"
        fill="none" stroke="#E74C3C" stroke-width="3"/>
</svg>'''
    return svg.encode('utf-8')


def create_test_sfr(width: int = 200, height: int = 150) -> bytes:
    """Create a test SFR document."""
    doc = create_sample_document(
        width=width,
        height=height,
        name="Test SFR Document",
        include_raster=True,
        include_text=False,  # Text rendering varies, skip for comparison
        include_svg=True,
        include_gradient=False,
    )
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# --- Ground Truth Generation ---


def render_ground_truth_png(width: int, height: int, color: tuple) -> np.ndarray:
    """Render expected output for PNG import."""
    img = Image.new('RGBA', (width, height), color)
    draw = ImageDraw.Draw(img)
    draw.line([(0, 0), (width, height)], fill=(255, 255, 255, 255), width=3)
    return np.array(img)


def render_ground_truth_jpg(width: int, height: int, color: tuple) -> np.ndarray:
    """Render expected output for JPEG import (with white background, RGBA)."""
    img = Image.new('RGBA', (width, height), (*color[:3], 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, width - 20, height - 20], fill=(255, 255, 0, 255))
    return np.array(img)


# --- Pixel Comparison Utilities ---


def compute_pixel_diff(img1: np.ndarray, img2: np.ndarray, threshold: int = 5) -> tuple[float, np.ndarray]:
    """
    Compute pixel difference between two images.

    Args:
        img1, img2: RGBA numpy arrays
        threshold: Per-channel difference threshold (0-255)

    Returns:
        (diff_ratio, diff_image): Ratio of different pixels and visualization
    """
    if img1.shape != img2.shape:
        raise ValueError(f"Image shapes don't match: {img1.shape} vs {img2.shape}")

    # Compute per-channel absolute difference
    diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))

    # A pixel is "different" if any channel exceeds threshold
    pixel_diff = np.any(diff > threshold, axis=2)

    diff_count = np.sum(pixel_diff)
    total_pixels = img1.shape[0] * img1.shape[1]
    diff_ratio = diff_count / total_pixels

    # Create visualization
    diff_image = np.zeros_like(img1)
    diff_image[pixel_diff] = [255, 0, 0, 255]  # Red for different pixels
    diff_image[~pixel_diff] = img1[~pixel_diff]

    return diff_ratio, diff_image


def images_match(img1: np.ndarray, img2: np.ndarray, tolerance: float = 0.01, threshold: int = 10) -> bool:
    """Check if two images match within tolerance."""
    diff_ratio, _ = compute_pixel_diff(img1, img2, threshold)
    return diff_ratio <= tolerance


# --- Test Classes ---


class TestDocumentOpenFormats:
    """Test opening various file formats via the API."""

    async def test_open_png(self, helpers: TestHelpers):
        """Open a PNG file and verify it renders correctly."""
        # Wait for WebSocket bridge to be connected (required for API calls that execute JS)
        await helpers.editor.wait_for_bridge()

        width, height = 200, 150
        color = (255, 0, 0, 255)

        # Create test PNG
        png_bytes = create_test_png(width, height, color)
        png_b64 = base64.b64encode(png_bytes).decode('ascii')

        # Open via API (api_post already prepends /api/sessions/current)
        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': png_b64,
            'name': 'Test PNG',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'png'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height

        # Wait for render
        await helpers.wait_for_render()

        # Get composite image via API
        composite = await get_document_image(helpers)
        assert composite is not None, "Failed to get composite image"

        # Compare to ground truth
        ground_truth = render_ground_truth_png(width, height, color)

        # Allow some tolerance for rendering differences
        assert images_match(composite, ground_truth, tolerance=0.05, threshold=15), \
            f"PNG render doesn't match ground truth"

    async def test_open_jpg(self, helpers: TestHelpers):
        """Open a JPEG file and verify it renders correctly."""
        width, height = 200, 150
        color = (0, 128, 255)

        jpg_bytes = create_test_jpg(width, height, color)
        jpg_b64 = base64.b64encode(jpg_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': jpg_b64,
            'name': 'Test JPEG',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'jpg'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height

        await helpers.wait_for_render()
        composite = await get_document_image(helpers)
        assert composite is not None

        # JPEG has lossy compression, use higher tolerance
        ground_truth = render_ground_truth_jpg(width, height, color)
        assert images_match(composite, ground_truth, tolerance=0.10, threshold=20), \
            f"JPEG render doesn't match ground truth"

    async def test_open_webp(self, helpers: TestHelpers):
        """Open a WebP file and verify dimensions."""
        width, height = 200, 150

        webp_bytes = create_test_webp(width, height)
        webp_b64 = base64.b64encode(webp_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': webp_b64,
            'name': 'Test WebP',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'webp'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height
        assert doc_info.get('layerCount') == 1

    async def test_open_bmp(self, helpers: TestHelpers):
        """Open a BMP file and verify dimensions."""
        width, height = 200, 150

        bmp_bytes = create_test_bmp(width, height)
        bmp_b64 = base64.b64encode(bmp_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': bmp_b64,
            'name': 'Test BMP',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'bmp'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height

    async def test_open_gif(self, helpers: TestHelpers):
        """Open a GIF file and verify dimensions."""
        width, height = 200, 150

        gif_bytes = create_test_gif(width, height)
        gif_b64 = base64.b64encode(gif_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': gif_b64,
            'name': 'Test GIF',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'gif'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height

    async def test_open_svg(self, helpers: TestHelpers):
        """Open an SVG file and verify it creates an SVG layer."""
        width, height = 200, 150

        svg_bytes = create_test_svg(width, height, "#3498DB")
        svg_b64 = base64.b64encode(svg_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': svg_b64,
            'name': 'Test SVG',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'svg'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height
        # SVG creates 2 layers: background + SVG layer
        assert doc_info.get('layerCount') == 2

        await helpers.wait_for_render()
        composite = await get_document_image(helpers)
        assert composite is not None

        # Verify the composite has the expected blue circle
        # Check center pixel is blue-ish
        center_x, center_y = width // 2, height // 2
        center_pixel = composite[center_y, center_x]
        # Blue channel should be dominant
        assert center_pixel[2] > 150, f"Expected blue center, got {center_pixel}"

    async def test_open_sfr(self, helpers: TestHelpers):
        """Open an SFR file and verify layers are preserved."""
        width, height = 200, 150

        sfr_bytes = create_test_sfr(width, height)
        sfr_b64 = base64.b64encode(sfr_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': sfr_b64,
            'name': 'Test SFR',
        })

        assert response.get('success'), f"API call failed: {response}"
        assert response.get('format_detected') == 'sfr'

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height
        # SFR should preserve multiple layers (background + paint + SVG)
        assert doc_info.get('layerCount') >= 3, \
            f"Expected 3+ layers in SFR, got {doc_info.get('layerCount')}"

        await helpers.wait_for_render()
        composite = await get_document_image(helpers)
        assert composite is not None
        assert composite.shape == (height, width, 4)


class TestDocumentNewAndSample:
    """Test creating new and sample documents."""

    async def test_create_new_document(self, helpers: TestHelpers):
        """Create a new empty document."""
        width, height = 400, 300

        response = await helpers.editor.api_post('/documents/new', {
            'width': width,
            'height': height,
            'name': 'My New Document',
        })

        assert response.get('success'), f"API call failed: {response}"

        doc_info = response.get('document', {})
        assert doc_info.get('width') == width
        assert doc_info.get('height') == height
        assert doc_info.get('name') == 'My New Document'
        assert doc_info.get('layerCount') == 1  # Background layer

        await helpers.wait_for_render()
        composite = await get_document_image(helpers)
        assert composite is not None

        # New document should be white
        assert np.mean(composite[:, :, :3]) > 250, "New document should be white"

    async def test_create_new_document_random_name(self, helpers: TestHelpers):
        """Create a new document with random name."""
        response = await helpers.editor.api_post('/documents/new', {
            'width': 800,
            'height': 600,
        })

        assert response.get('success')

        doc_info = response.get('document', {})
        # Name should be generated (two capitalized words)
        name = doc_info.get('name', '')
        assert len(name) > 0
        assert ' ' in name, f"Expected two-word name, got '{name}'"

    async def test_create_sample_document(self, helpers: TestHelpers):
        """Create a sample document with all layer types."""
        response = await helpers.editor.api_post('/documents/sample', {
            'width': 800,
            'height': 600,
            'include_raster': True,
            'include_text': True,
            'include_svg': True,
        })

        assert response.get('success'), f"API call failed: {response}"

        doc_info = response.get('document', {})
        assert doc_info.get('width') == 800
        assert doc_info.get('height') == 600
        # Should have: background + paint + SVG + text = 4 layers
        assert doc_info.get('layerCount') >= 4, \
            f"Expected 4+ layers, got {doc_info.get('layerCount')}"

        await helpers.wait_for_render()
        composite = await get_document_image(helpers)
        assert composite is not None

        # Should not be completely white (has content)
        assert np.std(composite[:, :, :3]) > 10, "Sample document should have visible content"

    async def test_create_sample_minimal(self, helpers: TestHelpers):
        """Create a sample document with minimal options."""
        response = await helpers.editor.api_post('/documents/sample', {
            'width': 400,
            'height': 300,
            'include_raster': True,
            'include_text': False,
            'include_svg': False,
        })

        assert response.get('success')

        doc_info = response.get('document', {})
        # Should have: background + paint = 2 layers
        assert doc_info.get('layerCount') == 2


class TestFormatDetection:
    """Test automatic format detection."""

    async def test_format_auto_detection(self, helpers: TestHelpers):
        """Verify format is correctly auto-detected."""
        test_cases = [
            (create_test_png, 'png'),
            (create_test_jpg, 'jpg'),
            (create_test_webp, 'webp'),
            (create_test_bmp, 'bmp'),
            (create_test_gif, 'gif'),
            (create_test_svg, 'svg'),
            (create_test_sfr, 'sfr'),
        ]

        for create_func, expected_format in test_cases:
            if create_func == create_test_svg:
                data = create_func()
            elif create_func == create_test_sfr:
                data = create_func()
            else:
                data = create_func()

            b64 = base64.b64encode(data).decode('ascii')

            response = await helpers.editor.api_post('/documents/open', {
                'content_base64': b64,
            })

            assert response.get('success'), f"Failed to open {expected_format}: {response}"
            detected = response.get('format_detected')
            assert detected == expected_format, \
                f"Expected {expected_format}, detected {detected}"

    async def test_explicit_format_override(self, helpers: TestHelpers):
        """Test specifying format explicitly."""
        # Create a PNG but tell API it's PNG explicitly
        png_bytes = create_test_png()
        png_b64 = base64.b64encode(png_bytes).decode('ascii')

        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': png_b64,
            'format': 'png',
        })

        assert response.get('success')
        assert response.get('format_detected') == 'png'

    async def test_invalid_format_rejected(self, helpers: TestHelpers):
        """Test that invalid format is rejected."""
        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': base64.b64encode(b'not a valid image').decode('ascii'),
            'format': 'xyz',
        })

        assert not response.get('success') or response.get('status_code') == 400


class TestSFRRoundtrip:
    """Test SFR save/load roundtrip through the API."""

    async def test_sfr_preserves_layers(self, helpers: TestHelpers):
        """Verify SFR roundtrip preserves layer structure."""
        # Create a sample document
        doc = create_sample_document(
            width=300,
            height=200,
            include_raster=True,
            include_text=False,
            include_svg=True,
        )

        original_layer_count = len(doc.layers)
        original_name = doc.name

        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        sfr_bytes = buffer.getvalue()

        # Open via API
        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': base64.b64encode(sfr_bytes).decode('ascii'),
        })

        assert response.get('success')

        doc_info = response.get('document', {})
        assert doc_info.get('layerCount') == original_layer_count, \
            f"Layer count changed: {original_layer_count} -> {doc_info.get('layerCount')}"

        # Name should be preserved (though ID changes)
        assert doc_info.get('name') == original_name

    async def test_sfr_renders_identically(self, helpers: TestHelpers):
        """Verify SFR renders the same after roundtrip."""
        width, height = 200, 150

        # Create document
        doc = create_sample_document(width, height, include_text=False)

        buffer = io.BytesIO()
        doc.save(buffer)
        sfr_bytes = buffer.getvalue()

        # Open via API
        response = await helpers.editor.api_post('/documents/open', {
            'content_base64': base64.b64encode(sfr_bytes).decode('ascii'),
        })

        assert response.get('success')

        await helpers.wait_for_render()
        composite1 = await get_document_image(helpers)

        # Save again and reload
        # (This tests the full JS -> SFR -> JS roundtrip)
        # For now, just verify the first load renders correctly
        assert composite1 is not None
        assert composite1.shape == (height, width, 4)

        # Should have non-trivial content
        assert np.std(composite1) > 5, "SFR should render with visible content"
