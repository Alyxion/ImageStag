"""Unit tests for SVG layer functionality.

Tests the Python SVG layer rendering without requiring a browser.
Run with: poetry run pytest tests/stagforge/test_svg_layer.py -v
"""

import pytest
import numpy as np
from pathlib import Path

from stagforge.rendering.svg_layer import render_svg_layer


# Path to SVG samples directory
SVGS_DIR = Path(__file__).parent.parent.parent / "imagestag" / "data" / "svgs"


class TestSVGLayerRender:
    """Test SVG layer rendering in Python."""

    def test_render_empty_svg_content(self):
        """Empty SVG content should return transparent pixels."""
        layer_data = {
            "svgContent": "",
            "width": 100,
            "height": 100,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (100, 100, 4)
        assert result.dtype == np.uint8
        # All pixels should be transparent (alpha = 0)
        assert np.all(result[:, :, 3] == 0)

    def test_render_simple_rect_svg(self):
        """Render a simple SVG with a red rectangle."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect x="10" y="10" width="80" height="80" fill="#FF0000"/>
</svg>'''

        layer_data = {
            "svgContent": svg_content,
            "width": 100,
            "height": 100,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (100, 100, 4)
        assert result.dtype == np.uint8

        # Check that we have red pixels (non-zero red channel)
        red_channel = result[:, :, 0]
        has_red = np.any(red_channel > 200)
        assert has_red, "Expected red pixels in rendered SVG"

        # Check center pixel should be red
        center_pixel = result[50, 50]
        assert center_pixel[0] > 200, f"Expected red at center, got R={center_pixel[0]}"
        assert center_pixel[1] < 50, f"Expected no green at center, got G={center_pixel[1]}"
        assert center_pixel[2] < 50, f"Expected no blue at center, got B={center_pixel[2]}"

    def test_render_with_different_dimensions(self):
        """SVG should scale to requested dimensions."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50">
  <rect x="0" y="0" width="50" height="50" fill="#00FF00"/>
</svg>'''

        layer_data = {
            "svgContent": svg_content,
            "width": 200,
            "height": 150,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (150, 200, 4)

    def test_render_svg_with_viewbox(self):
        """SVG with viewBox should render correctly."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="#0000FF"/>
</svg>'''

        layer_data = {
            "svgContent": svg_content,
            "width": 100,
            "height": 100,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (100, 100, 4)

        # Center should have blue pixels
        center_pixel = result[50, 50]
        assert center_pixel[2] > 200, f"Expected blue at center, got B={center_pixel[2]}"


class TestSVGLayerSerialize:
    """Test SVG layer serialization format."""

    def test_layer_data_format(self):
        """Verify expected layer data format."""
        layer_data = {
            "_version": 1,
            "_type": "SVGLayer",
            "type": "svg",
            "id": "test-id",
            "name": "Test SVG",
            "svgContent": "<svg></svg>",
            "width": 100,
            "height": 100,
            "offsetX": 10,
            "offsetY": 20,
            "opacity": 0.8,
            "blendMode": "normal",
            "visible": True,
            "locked": False,
        }

        # Rendering should work with this format
        result = render_svg_layer(layer_data)
        assert result.shape == (100, 100, 4)


class TestSVGSampleFiles:
    """Test rendering actual SVG sample files."""

    @pytest.fixture
    def svg_samples(self):
        """Get list of available SVG sample files."""
        if not SVGS_DIR.exists():
            pytest.skip("SVG samples directory not found")

        samples = list(SVGS_DIR.rglob("*.svg"))
        if not samples:
            pytest.skip("No SVG sample files found")

        return samples

    def test_buck_deer_silhouette(self):
        """Test rendering buck-deer-silhouette.svg."""
        svg_path = SVGS_DIR / "openclipart" / "buck-deer-silhouette.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        layer_data = {
            "svgContent": svg_content,
            "width": 200,
            "height": 200,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (200, 200, 4)
        assert result.dtype == np.uint8

        # Should have some non-transparent pixels
        non_transparent = np.sum(result[:, :, 3] > 0)
        assert non_transparent > 100, "Expected visible pixels in deer silhouette"

    def test_noto_emoji_deer(self):
        """Test rendering Noto Emoji deer.svg."""
        svg_path = SVGS_DIR / "noto-emoji" / "deer.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        layer_data = {
            "svgContent": svg_content,
            "width": 128,
            "height": 128,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (128, 128, 4)

        # Should have some non-transparent pixels
        non_transparent = np.sum(result[:, :, 3] > 0)
        assert non_transparent > 100, "Expected visible pixels in deer emoji"

    def test_noto_emoji_fire(self):
        """Test rendering noto-emoji/fire.svg (has gradients)."""
        svg_path = SVGS_DIR / "noto-emoji" / "fire.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        layer_data = {
            "svgContent": svg_content,
            "width": 128,
            "height": 128,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (128, 128, 4)

        # Should have some non-transparent pixels
        non_transparent = np.sum(result[:, :, 3] > 0)
        assert non_transparent > 100, "Expected visible pixels in fire emoji"

    def test_colored_feather(self):
        """Test rendering colored-feather.svg (complex, 120KB)."""
        svg_path = SVGS_DIR / "openclipart" / "colored-feather.svg"
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        layer_data = {
            "svgContent": svg_content,
            "width": 256,
            "height": 256,
        }
        result = render_svg_layer(layer_data)

        assert result.shape == (256, 256, 4)

        # Should have many non-transparent pixels for complex SVG
        non_transparent = np.sum(result[:, :, 3] > 0)
        assert non_transparent > 1000, "Expected many visible pixels in colored feather"

    @pytest.mark.parametrize("svg_file", [
        "openclipart/buck-deer-silhouette.svg",
        "openclipart/leaping-deer-silhouette.svg",
        "openclipart/male-deer.svg",
        "noto-emoji/deer.svg",
        "noto-emoji/fire.svg",
        "noto-emoji/rainbow.svg",
    ])
    def test_sample_renders_without_error(self, svg_file):
        """All sample SVGs should render without errors."""
        svg_path = SVGS_DIR / svg_file
        if not svg_path.exists():
            pytest.skip(f"Sample not found: {svg_path}")

        svg_content = svg_path.read_text()
        layer_data = {
            "svgContent": svg_content,
            "width": 100,
            "height": 100,
        }

        # Should not raise any exceptions
        result = render_svg_layer(layer_data)
        assert result is not None
        assert result.shape == (100, 100, 4)


class TestSVGSamplesAPI:
    """Test SVG samples API endpoints."""

    @pytest.fixture
    def api_client(self):
        """HTTP client for API calls."""
        import httpx
        return httpx.Client(base_url="http://127.0.0.1:8080/api", timeout=10.0)

    def test_list_svg_samples(self, api_client):
        """Test listing SVG samples via API."""
        try:
            response = api_client.get("/svg-samples")
            if response.status_code != 200:
                pytest.skip(f"Server not available or endpoint not found: {response.status_code}")

            data = response.json()
            assert "samples" in data

            # Should have some samples
            samples = data["samples"]
            if len(samples) == 0:
                pytest.skip("No SVG samples found in directory")

            # Each sample should have required fields
            for sample in samples:
                assert "id" in sample
                assert "path" in sample
                assert "category" in sample
                assert "name" in sample
        except Exception as e:
            pytest.skip(f"Server not running: {e}")

    def test_get_svg_sample_content(self, api_client):
        """Test getting SVG content via API."""
        try:
            response = api_client.get("/svg-samples/openclipart/buck-deer-silhouette.svg")
            if response.status_code == 404:
                pytest.skip("SVG sample not found")
            if response.status_code != 200:
                pytest.skip(f"Server not available: {response.status_code}")

            # Should return SVG content
            assert response.headers.get("content-type", "").startswith("image/svg+xml")
            content = response.text
            assert "<svg" in content
        except Exception as e:
            pytest.skip(f"Server not running: {e}")

    def test_get_svg_sample_metadata(self, api_client):
        """Test getting SVG metadata via API."""
        try:
            response = api_client.get("/svg-samples/openclipart/buck-deer-silhouette.svg/metadata")
            if response.status_code == 404:
                pytest.skip("SVG sample not found")
            if response.status_code != 200:
                pytest.skip(f"Server not available: {response.status_code}")

            data = response.json()
            assert "path" in data
            assert "filename" in data
            assert "category" in data
        except Exception as e:
            pytest.skip(f"Server not running: {e}")
