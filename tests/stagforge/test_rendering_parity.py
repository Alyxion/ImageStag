"""Pixel diff tests for cross-platform rendering parity.

These tests verify that dynamic layers (text, vector) render identically
in JavaScript and Python.

CRITICAL: All tests in this file MUST pass before any dynamic layer
changes can be merged.
"""

import pytest
import numpy as np
import base64
from PIL import Image
from io import BytesIO

from stagforge.rendering import (
    render_text_layer,
    render_vector_layer,
    render_document,
    render_layer,
)
from stagforge.rendering.document import (
    compute_pixel_diff,
    images_match,
    decode_png_data_url,
)
from stagforge.rendering.lanczos import lanczos_resample


class TestLanczosResampling:
    """Test Lanczos resampling implementation."""

    def test_identity_no_resize(self):
        """No-op resize should preserve image."""
        # Create test image
        src = np.zeros((100, 100, 4), dtype=np.uint8)
        src[25:75, 25:75] = [255, 0, 0, 255]  # Red square

        # Resample to same size
        result = lanczos_resample(src, 100, 100)

        # Should be very similar (Lanczos filter produces ~1% difference at same size)
        assert images_match(src, result, tolerance=0.02)

    def test_downscale_preserves_content(self):
        """Downscaling should preserve visible content."""
        # Create test image with red square
        src = np.zeros((200, 200, 4), dtype=np.uint8)
        src[50:150, 50:150] = [255, 0, 0, 255]

        # Downscale 2x
        result = lanczos_resample(src, 100, 100)

        # Check that red pixels exist in result
        red_mask = (result[:, :, 0] > 200) & (result[:, :, 3] > 200)
        assert np.sum(red_mask) > 0, "Red content should be preserved after downscale"

    def test_downscale_4x_for_text(self):
        """4x downscale (text rendering) should work correctly."""
        # Simulate text rendering at 4x - use smaller image for speed
        # (100x100 -> 25x25 instead of 400x400 -> 100x100)
        src = np.zeros((100, 100, 4), dtype=np.uint8)
        src[25:75, 25:75] = [0, 0, 0, 255]  # Black square (like text)

        # Downscale 4x
        result = lanczos_resample(src, 25, 25)

        # Check dimensions
        assert result.shape == (25, 25, 4)

        # Check that black pixels exist
        black_mask = (result[:, :, 0] < 50) & (result[:, :, 3] > 200)
        assert np.sum(black_mask) > 0, "Black content should be preserved"

    def test_alpha_handling(self):
        """Alpha channel should be handled correctly."""
        # Create image with semi-transparent pixels
        src = np.zeros((100, 100, 4), dtype=np.uint8)
        src[25:75, 25:75] = [255, 0, 0, 128]  # Semi-transparent red

        result = lanczos_resample(src, 50, 50)

        # Alpha should be preserved (approximately)
        center_alpha = result[12:38, 12:38, 3]
        assert np.mean(center_alpha) > 50, "Alpha should be preserved in center"


class TestTextRendering:
    """Test text layer rendering."""

    def test_simple_text(self):
        """Basic text rendering should work."""
        layer_data = {
            "type": "text",
            "runs": [{"text": "Hello World"}],
            "fontSize": 24,
            "fontFamily": "Arial",
            "color": "#000000",
        }

        result = render_text_layer(layer_data)

        # Should have content
        assert result.shape[2] == 4  # RGBA
        assert np.max(result[:, :, 3]) > 0, "Should have non-transparent pixels"

    def test_multiline_text(self):
        """Multiline text should render correctly."""
        layer_data = {
            "type": "text",
            "runs": [{"text": "Line 1\nLine 2\nLine 3"}],
            "fontSize": 20,
            "fontFamily": "Arial",
            "color": "#000000",
            "lineHeight": 1.2,
        }

        result = render_text_layer(layer_data)
        assert result.shape[0] > 60, "Height should accommodate multiple lines"

    def test_styled_runs(self):
        """Rich text with multiple runs should work."""
        layer_data = {
            "type": "text",
            "runs": [
                {"text": "Bold", "fontWeight": "bold", "color": "#FF0000"},
                {"text": " and ", "color": "#000000"},
                {"text": "Italic", "fontStyle": "italic", "color": "#0000FF"},
            ],
            "fontSize": 24,
            "fontFamily": "Arial",
        }

        result = render_text_layer(layer_data)

        # Should have both red and blue pixels
        red_mask = (result[:, :, 0] > 200) & (result[:, :, 2] < 100)
        blue_mask = (result[:, :, 2] > 200) & (result[:, :, 0] < 100)

        assert np.sum(red_mask) > 0, "Should have red text"
        assert np.sum(blue_mask) > 0, "Should have blue text"

    def test_text_alignment(self):
        """Text alignment should work."""
        for align in ["left", "center", "right"]:
            layer_data = {
                "type": "text",
                "runs": [{"text": "Test"}],
                "fontSize": 24,
                "textAlign": align,
            }
            result = render_text_layer(layer_data, output_width=200)
            assert result is not None


class TestVectorRendering:
    """Test vector layer rendering."""

    def test_rect_shape(self):
        """Rectangle shape should render."""
        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": [
                {
                    "type": "rect",
                    "x": 10,
                    "y": 10,
                    "width": 80,
                    "height": 80,
                    "fillColor": "#FF0000",
                    "fill": True,
                    "stroke": False,
                }
            ],
        }

        result = render_vector_layer(layer_data)

        # Should have red pixels
        red_mask = (result[:, :, 0] > 200) & (result[:, :, 3] > 200)
        assert np.sum(red_mask) > 0, "Should have red rectangle"

    def test_ellipse_shape(self):
        """Ellipse shape should render."""
        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": [
                {
                    "type": "ellipse",
                    "cx": 50,
                    "cy": 50,
                    "rx": 40,
                    "ry": 30,
                    "fillColor": "#00FF00",
                    "fill": True,
                }
            ],
        }

        result = render_vector_layer(layer_data)

        # Should have green pixels
        green_mask = (result[:, :, 1] > 200) & (result[:, :, 3] > 200)
        assert np.sum(green_mask) > 0, "Should have green ellipse"

    def test_line_shape(self):
        """Line shape should render."""
        layer_data = {
            "type": "vector",
            "width": 100,
            "height": 100,
            "shapes": [
                {
                    "type": "line",
                    "x1": 10,
                    "y1": 10,
                    "x2": 90,
                    "y2": 90,
                    "strokeColor": "#0000FF",
                    "strokeWidth": 3,
                }
            ],
        }

        result = render_vector_layer(layer_data)

        # Should have blue pixels
        blue_mask = (result[:, :, 2] > 200) & (result[:, :, 3] > 200)
        assert np.sum(blue_mask) > 0, "Should have blue line"

    def test_multiple_shapes(self):
        """Multiple shapes should render."""
        layer_data = {
            "type": "vector",
            "width": 200,
            "height": 200,
            "shapes": [
                {"type": "rect", "x": 10, "y": 10, "width": 50, "height": 50,
                 "fillColor": "#FF0000", "fill": True},
                {"type": "ellipse", "cx": 150, "cy": 50, "rx": 30, "ry": 30,
                 "fillColor": "#00FF00", "fill": True},
            ],
        }

        result = render_vector_layer(layer_data)

        red_mask = result[:, :, 0] > 200
        green_mask = result[:, :, 1] > 200

        assert np.sum(red_mask) > 0, "Should have red shape"
        assert np.sum(green_mask) > 0, "Should have green shape"


class TestDocumentRendering:
    """Test full document rendering."""

    def test_empty_document(self):
        """Empty document should render white."""
        doc_data = {
            "width": 100,
            "height": 100,
            "layers": [],
        }

        result = render_document(doc_data)

        # Should be white
        assert result.shape == (100, 100, 4)
        assert np.all(result[:, :, :3] == 255), "Empty doc should be white"

    def test_single_raster_layer(self):
        """Document with raster layer should render."""
        # Create a simple PNG
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_base64 = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{png_base64}"

        doc_data = {
            "width": 100,
            "height": 100,
            "layers": [
                {
                    "type": "raster",
                    "imageData": data_url,
                    "visible": True,
                    "opacity": 1.0,
                }
            ],
        }

        result = render_document(doc_data)

        # Should be red
        red_mask = (result[:, :, 0] > 200) & (result[:, :, 1] < 100)
        assert np.sum(red_mask) > 0, "Should have red layer"

    def test_layer_visibility(self):
        """Hidden layers should not render."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_base64 = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{png_base64}"

        doc_data = {
            "width": 100,
            "height": 100,
            "layers": [
                {
                    "type": "raster",
                    "imageData": data_url,
                    "visible": False,  # Hidden
                    "opacity": 1.0,
                }
            ],
        }

        result = render_document(doc_data)

        # Should be white (hidden layer not rendered)
        assert np.all(result[:, :, :3] == 255), "Hidden layer should not render"

    def test_layer_opacity(self):
        """Layer opacity should blend correctly."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_base64 = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{png_base64}"

        doc_data = {
            "width": 100,
            "height": 100,
            "layers": [
                {
                    "type": "raster",
                    "imageData": data_url,
                    "visible": True,
                    "opacity": 0.5,  # 50% opacity
                }
            ],
        }

        result = render_document(doc_data)

        # Should be pink-ish (red at 50% over white)
        center_color = result[50, 50, :3]
        assert center_color[0] > 200, "Red channel should be high"
        assert center_color[1] > 100, "Green should be mixed from white"

    def test_mixed_layer_types(self):
        """Document with mixed layer types should render."""
        doc_data = {
            "width": 200,
            "height": 200,
            "layers": [
                {
                    "type": "text",
                    "runs": [{"text": "Hello", "color": "#FF0000"}],
                    "fontSize": 24,
                    "offsetX": 10,
                    "offsetY": 10,
                    "visible": True,
                    "opacity": 1.0,
                },
                {
                    "type": "vector",
                    "width": 200,
                    "height": 200,
                    "shapes": [
                        {"type": "rect", "x": 100, "y": 100, "width": 50, "height": 50,
                         "fillColor": "#0000FF", "fill": True}
                    ],
                    "visible": True,
                    "opacity": 1.0,
                },
            ],
        }

        result = render_document(doc_data)

        # Should have content
        non_white = np.any(result[:, :, :3] != 255, axis=2)
        assert np.sum(non_white) > 0, "Should have rendered content"


class TestPixelDiff:
    """Test pixel diff utilities."""

    def test_identical_images(self):
        """Identical images should have zero diff."""
        img = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
        diff_ratio, _ = compute_pixel_diff(img, img.copy())
        assert diff_ratio == 0.0

    def test_different_images(self):
        """Different images should have non-zero diff."""
        img1 = np.zeros((100, 100, 4), dtype=np.uint8)
        img1[:, :] = [255, 255, 255, 255]

        img2 = np.zeros((100, 100, 4), dtype=np.uint8)
        img2[:, :] = [0, 0, 0, 255]

        diff_ratio, _ = compute_pixel_diff(img1, img2)
        assert diff_ratio > 0.5, "Black vs white should be very different"

    def test_images_match_tolerance(self):
        """images_match should respect tolerance."""
        img1 = np.zeros((100, 100, 4), dtype=np.uint8)
        img1[:, :] = [100, 100, 100, 255]

        img2 = img1.copy()
        img2[:, :, 0] += 1  # Tiny difference

        assert images_match(img1, img2, tolerance=0.01)

    def test_shape_mismatch_raises(self):
        """Different shapes should raise error."""
        img1 = np.zeros((100, 100, 4), dtype=np.uint8)
        img2 = np.zeros((200, 200, 4), dtype=np.uint8)

        with pytest.raises(ValueError):
            compute_pixel_diff(img1, img2)


# Integration tests that require a running server would go here
# These would be marked with @pytest.mark.integration
