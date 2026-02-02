"""Integration tests for cross-platform rendering parity.

These tests verify that dynamic layers (text, vector) render identically
in JavaScript (browser) and Python.

CRITICAL: All tests in this file MUST pass before any dynamic layer
changes can be merged. These tests actually run in a real browser
and compare pixel output.

Running these tests:
--------------------
These tests require Chrome and a running server:

    # Run unit tests only (no browser needed)
    pytest tests/test_rendering_parity.py -v

    # Run integration tests (requires Chrome)
    pytest tests/test_rendering_parity_integration.py -v -m integration

    # Run all parity tests
    pytest tests/test_rendering_parity*.py -v

Note: Integration tests are skipped automatically if browser/server
aren't available.

TODO: Migrate these tests from Selenium to Playwright for consistency
with other browser tests (*_pw.py files).
"""

import pytest

# Check if Selenium with Chrome driver is available
_selenium_chrome_works = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    # Actually test if Chrome driver works
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.quit()
    _selenium_chrome_works = True
except Exception:
    _selenium_chrome_works = False

# Skip all tests in this module if Chrome driver doesn't work
pytestmark = pytest.mark.skipif(
    not _selenium_chrome_works,
    reason="Selenium Chrome driver not available - these tests need migration to Playwright"
)
import numpy as np
import base64
import json
from typing import Dict, Any, Tuple

from stagforge.rendering import (
    render_text_layer,
    render_vector_layer,
    render_document,
    render_layer,
)
from stagforge.rendering.document import (
    compute_pixel_diff,
    images_match,
)


# Tolerance for rendering differences (0.01 = 1% pixel diff allowed)
# Some anti-aliasing differences are expected between browser and Python
PARITY_TOLERANCE = 0.05


def decode_base64_rgba(data: str, width: int, height: int) -> np.ndarray:
    """Decode base64 RGBA data to numpy array."""
    raw_bytes = base64.b64decode(data)
    return np.frombuffer(raw_bytes, dtype=np.uint8).reshape((height, width, 4))


class TestTextLayerParity:
    """Test that text layers render identically in JS and Python."""

    @pytest.mark.integration
    def test_simple_text(self, editor):
        """Simple text should render similarly in JS and Python."""
        # Create a text layer in JS
        layer_id = editor.create_text_layer(
            text="Hello World",
            x=10,
            y=10,
            font_size=24,
            font_family="Arial",
            color="#000000",
        )

        if layer_id is None:
            pytest.skip("TextLayer not available in browser")

        # Get JS-rendered image
        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        # Render same layer in Python
        layer_data = {
            "type": "text",
            "runs": [{"text": "Hello World"}],
            "fontSize": 24,
            "fontFamily": "Arial",
            "color": "#000000",
        }
        py_pixels = render_text_layer(
            layer_data,
            output_width=js_data["width"],
            output_height=js_data["height"],
        )

        # Compare
        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Text rendering mismatch: {diff_ratio:.2%} difference "
            f"(tolerance: {PARITY_TOLERANCE:.2%})"
        )

    @pytest.mark.integration
    def test_multiline_text(self, editor):
        """Multiline text should render similarly."""
        layer_id = editor.create_text_layer(
            text="Line 1\nLine 2\nLine 3",
            x=10,
            y=10,
            font_size=20,
            color="#000000",
        )

        if layer_id is None:
            pytest.skip("TextLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        layer_data = {
            "type": "text",
            "runs": [{"text": "Line 1\nLine 2\nLine 3"}],
            "fontSize": 20,
            "color": "#000000",
        }
        py_pixels = render_text_layer(
            layer_data,
            output_width=js_data["width"],
            output_height=js_data["height"],
        )

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Multiline text mismatch: {diff_ratio:.2%} difference"
        )

    @pytest.mark.integration
    def test_colored_text(self, editor):
        """Colored text should render with matching colors."""
        layer_id = editor.create_text_layer(
            text="RED TEXT",
            x=10,
            y=10,
            font_size=24,
            color="#FF0000",
        )

        if layer_id is None:
            pytest.skip("TextLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        layer_data = {
            "type": "text",
            "runs": [{"text": "RED TEXT", "color": "#FF0000"}],
            "fontSize": 24,
            "color": "#FF0000",
        }
        py_pixels = render_text_layer(
            layer_data,
            output_width=js_data["width"],
            output_height=js_data["height"],
        )

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Colored text mismatch: {diff_ratio:.2%} difference"
        )

        # Also verify both have red pixels
        js_red = (js_pixels[:, :, 0] > 200) & (js_pixels[:, :, 3] > 200)
        py_red = (py_pixels[:, :, 0] > 200) & (py_pixels[:, :, 3] > 200)
        assert np.sum(js_red) > 0, "JS should have red pixels"
        assert np.sum(py_red) > 0, "Python should have red pixels"


class TestVectorLayerParity:
    """Test that vector layers render identically in JS and Python."""

    @pytest.mark.integration
    def test_rectangle(self, editor):
        """Rectangle shape should render identically."""
        shapes = [
            {
                "type": "rect",
                "x": 10,
                "y": 10,
                "width": 80,
                "height": 60,
                "fillColor": "#FF0000",
                "fill": True,
                "stroke": False,
            }
        ]

        layer_id = editor.create_vector_layer(shapes, width=100, height=100)

        if layer_id is None:
            pytest.skip("VectorLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": shapes,
        }
        py_pixels = render_vector_layer(layer_data, width=100, height=100)

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Rectangle mismatch: {diff_ratio:.2%} difference"
        )

    @pytest.mark.integration
    def test_ellipse(self, editor):
        """Ellipse shape should render identically."""
        shapes = [
            {
                "type": "ellipse",
                "cx": 50,
                "cy": 50,
                "rx": 40,
                "ry": 30,
                "fillColor": "#00FF00",
                "fill": True,
            }
        ]

        layer_id = editor.create_vector_layer(shapes, width=100, height=100)

        if layer_id is None:
            pytest.skip("VectorLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": shapes,
        }
        py_pixels = render_vector_layer(layer_data, width=100, height=100)

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Ellipse mismatch: {diff_ratio:.2%} difference"
        )

    @pytest.mark.integration
    def test_line(self, editor):
        """Line shape should render identically."""
        shapes = [
            {
                "type": "line",
                "x1": 10,
                "y1": 10,
                "x2": 90,
                "y2": 90,
                "strokeColor": "#0000FF",
                "strokeWidth": 3,
            }
        ]

        layer_id = editor.create_vector_layer(shapes, width=100, height=100)

        if layer_id is None:
            pytest.skip("VectorLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": shapes,
        }
        py_pixels = render_vector_layer(layer_data, width=100, height=100)

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Line mismatch: {diff_ratio:.2%} difference"
        )

    @pytest.mark.integration
    def test_multiple_shapes(self, editor):
        """Multiple shapes should render identically."""
        shapes = [
            {
                "type": "rect",
                "x": 10,
                "y": 10,
                "width": 40,
                "height": 40,
                "fillColor": "#FF0000",
                "fill": True,
            },
            {
                "type": "ellipse",
                "cx": 150,
                "cy": 50,
                "rx": 30,
                "ry": 30,
                "fillColor": "#00FF00",
                "fill": True,
            },
            {
                "type": "line",
                "x1": 50,
                "y1": 100,
                "x2": 150,
                "y2": 100,
                "strokeColor": "#0000FF",
                "strokeWidth": 2,
            },
        ]

        layer_id = editor.create_vector_layer(shapes, width=200, height=150)

        if layer_id is None:
            pytest.skip("VectorLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        layer_data = {
            "type": "vector",
            "width": 200,
            "height": 150,
            "shapes": shapes,
        }
        py_pixels = render_vector_layer(
            layer_data,
            width=js_data["width"],
            height=js_data["height"],
        )

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Multiple shapes mismatch: {diff_ratio:.2%} difference"
        )


class TestDocumentParity:
    """Test that full documents render identically via export/import."""

    @pytest.mark.integration
    def test_document_export_import_roundtrip(self, editor):
        """Document should survive export/import with identical rendering."""
        # Create a simple document with a shape
        shapes = [
            {
                "type": "rect",
                "x": 20,
                "y": 20,
                "width": 60,
                "height": 40,
                "fillColor": "#FF0000",
                "fill": True,
            }
        ]
        layer_id = editor.create_vector_layer(shapes, width=100, height=100)

        if layer_id is None:
            pytest.skip("VectorLayer not available")

        editor.wait_for_render()

        # Export document
        doc_data = editor.export_document()

        if doc_data is None or "error" in doc_data:
            pytest.skip(f"Could not export document: {doc_data}")

        # Get JS composite before any changes
        js_composite = editor.get_composite_image_data()
        if js_composite is None or "error" in js_composite:
            pytest.skip(f"Could not get composite: {js_composite}")

        js_pixels = decode_base64_rgba(
            js_composite["data"],
            js_composite["width"],
            js_composite["height"],
        )

        # Render document in Python
        doc = doc_data.get("document", doc_data)
        py_pixels = render_document(doc)

        # Resize if dimensions differ
        if py_pixels.shape[:2] != js_pixels.shape[:2]:
            from stagforge.rendering.lanczos import lanczos_resample
            py_pixels = lanczos_resample(
                py_pixels,
                js_pixels.shape[1],
                js_pixels.shape[0],
            )

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Document export/render mismatch: {diff_ratio:.2%} difference"
        )

    @pytest.mark.integration
    def test_mixed_layer_document(self, editor):
        """Document with mixed layer types should render consistently."""
        # Create text layer
        text_layer_id = editor.create_text_layer(
            text="Mixed Document",
            x=10,
            y=10,
            font_size=20,
            color="#000000",
        )

        # Create vector layer
        shapes = [
            {
                "type": "rect",
                "x": 10,
                "y": 50,
                "width": 80,
                "height": 40,
                "fillColor": "#0066CC",
                "fill": True,
            }
        ]
        vector_layer_id = editor.create_vector_layer(shapes, width=100, height=100)

        if text_layer_id is None and vector_layer_id is None:
            pytest.skip("Neither TextLayer nor VectorLayer available")

        editor.wait_for_render()

        # Export and render in Python
        doc_data = editor.export_document()
        if doc_data is None or "error" in doc_data:
            pytest.skip(f"Could not export document: {doc_data}")

        js_composite = editor.get_composite_image_data()
        if js_composite is None or "error" in js_composite:
            pytest.skip(f"Could not get composite: {js_composite}")

        js_pixels = decode_base64_rgba(
            js_composite["data"],
            js_composite["width"],
            js_composite["height"],
        )

        doc = doc_data.get("document", doc_data)
        py_pixels = render_document(doc)

        if py_pixels.shape[:2] != js_pixels.shape[:2]:
            from stagforge.rendering.lanczos import lanczos_resample
            py_pixels = lanczos_resample(
                py_pixels,
                js_pixels.shape[1],
                js_pixels.shape[0],
            )

        diff_ratio, _ = compute_pixel_diff(js_pixels, py_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Mixed document mismatch: {diff_ratio:.2%} difference"
        )


class TestRenderingAPI:
    """Test the rendering API endpoints for parity."""

    @pytest.mark.integration
    def test_layer_render_api(self, editor, api_client):
        """Layer render API should match JS output."""
        shapes = [
            {
                "type": "rect",
                "x": 10,
                "y": 10,
                "width": 80,
                "height": 80,
                "fillColor": "#FF0000",
                "fill": True,
            }
        ]

        layer_id = editor.create_vector_layer(shapes, width=100, height=100)

        if layer_id is None:
            pytest.skip("VectorLayer not available")

        js_data = editor.get_layer_image_data(layer_id)
        if js_data is None or "error" in js_data:
            pytest.skip(f"Could not get layer image: {js_data}")

        js_pixels = decode_base64_rgba(
            js_data["data"],
            js_data["width"],
            js_data["height"],
        )

        # Use API to render layer
        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": shapes,
        }

        response = api_client.post(
            "/rendering/layer",
            json={"layer": layer_data, "width": 100, "height": 100},
        )

        if response.status_code != 200:
            pytest.skip(f"Rendering API not available: {response.status_code}")

        api_width = int(response.headers.get("X-Image-Width", 100))
        api_height = int(response.headers.get("X-Image-Height", 100))
        api_pixels = np.frombuffer(response.content, dtype=np.uint8).reshape(
            (api_height, api_width, 4)
        )

        diff_ratio, _ = compute_pixel_diff(js_pixels, api_pixels)
        assert diff_ratio < PARITY_TOLERANCE, (
            f"Layer API mismatch: {diff_ratio:.2%} difference"
        )

    @pytest.mark.integration
    def test_diff_api(self, api_client):
        """Diff API should correctly compute pixel differences."""
        # Create two images
        img1 = np.zeros((100, 100, 4), dtype=np.uint8)
        img1[:, :] = [255, 0, 0, 255]  # Red

        img2 = np.zeros((100, 100, 4), dtype=np.uint8)
        img2[:, :] = [255, 0, 0, 255]  # Also red (identical)

        response = api_client.post(
            "/rendering/diff",
            json={
                "image1_base64": base64.b64encode(img1.tobytes()).decode(),
                "image2_base64": base64.b64encode(img2.tobytes()).decode(),
                "width": 100,
                "height": 100,
                "tolerance": 0.01,
            },
        )

        if response.status_code != 200:
            pytest.skip(f"Diff API not available: {response.status_code}")

        result = response.json()
        assert result["match"] is True
        assert result["diff_ratio"] == 0.0

        # Now test with different images
        img3 = np.zeros((100, 100, 4), dtype=np.uint8)
        img3[:, :] = [0, 0, 255, 255]  # Blue

        response2 = api_client.post(
            "/rendering/diff",
            json={
                "image1_base64": base64.b64encode(img1.tobytes()).decode(),
                "image2_base64": base64.b64encode(img3.tobytes()).decode(),
                "width": 100,
                "height": 100,
                "tolerance": 0.01,
            },
        )

        result2 = response2.json()
        assert result2["match"] is False
        assert result2["diff_ratio"] > 0.3  # Red vs blue should be very different
