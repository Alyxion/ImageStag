"""
Tests for the AsciiRenderer class.
"""

import numpy as np
import pytest

from imagestag import Image, AsciiRenderer, RenderMode


class TestAsciiRenderer:
    """Tests for AsciiRenderer class."""

    @pytest.fixture
    def test_image(self):
        """Create a simple test image."""
        pixels = np.zeros((20, 40, 3), dtype=np.uint8)
        # Create gradient
        for y in range(20):
            for x in range(40):
                pixels[y, x] = [int(x * 6), int(y * 12), 128]
        return Image(pixels)

    def test_render_block(self, test_image):
        """Test block mode rendering."""
        renderer = AsciiRenderer(width=40, mode=RenderMode.BLOCK)
        output = renderer.render(test_image)
        assert len(output) > 0
        assert "█" in output or " " in output  # Contains blocks or spaces
        assert "\033[" in output  # Contains ANSI codes

    def test_render_half_block(self, test_image):
        """Test half-block mode rendering."""
        renderer = AsciiRenderer(width=40, mode=RenderMode.HALF_BLOCK)
        output = renderer.render(test_image)
        assert len(output) > 0
        assert "▀" in output or "▄" in output or " " in output
        assert "\033[" in output

    def test_render_ascii(self, test_image):
        """Test ASCII mode rendering."""
        renderer = AsciiRenderer(width=40, mode=RenderMode.ASCII)
        output = renderer.render(test_image)
        assert len(output) > 0
        # Should not contain ANSI codes in plain ASCII mode
        assert "\033[38;2" not in output

    def test_render_ascii_color(self, test_image):
        """Test colored ASCII mode rendering."""
        renderer = AsciiRenderer(width=40, mode=RenderMode.ASCII_COLOR)
        output = renderer.render(test_image)
        assert len(output) > 0
        assert "\033[" in output  # Contains ANSI codes

    def test_render_braille(self, test_image):
        """Test braille mode rendering."""
        renderer = AsciiRenderer(width=40, mode=RenderMode.BRAILLE)
        output = renderer.render(test_image)
        assert len(output) > 0

    def test_width_auto_detection(self):
        """Test that width can be auto-detected."""
        # Should not raise even without terminal
        renderer = AsciiRenderer(width=None)
        assert renderer.width > 0

    def test_custom_width(self):
        """Test custom width setting (capped to terminal)."""
        # Width gets capped to terminal size, but we can verify it's set
        renderer = AsciiRenderer(width=30)
        assert renderer.width == 30  # Should work if terminal is >= 30 cols

    def test_max_height_limits_output(self):
        """Test that max_height limits output size."""
        # Create a very tall image
        tall_pixels = np.zeros((500, 40, 3), dtype=np.uint8)
        tall_pixels[:, :] = [128, 128, 128]
        img = Image(tall_pixels)

        renderer = AsciiRenderer(width=40, mode=RenderMode.HALF_BLOCK, max_height=15)
        output = renderer.render(img)
        lines = output.split('\n')

        # Should be limited to max_height
        assert len(lines) <= 16  # 15 lines + possible reset line

    def test_grayscale_image(self):
        """Test rendering grayscale images."""
        gray_pixels = np.full((20, 40), 128, dtype=np.uint8)
        img = Image(gray_pixels, pixel_format="L")
        renderer = AsciiRenderer(width=40, mode=RenderMode.BLOCK)
        output = renderer.render(img)
        assert len(output) > 0

    def test_rgba_image(self):
        """Test rendering RGBA images."""
        rgba_pixels = np.zeros((20, 40, 4), dtype=np.uint8)
        rgba_pixels[:, :, :3] = 128
        rgba_pixels[:, :, 3] = 255
        img = Image(rgba_pixels, pixel_format="RGBA")
        renderer = AsciiRenderer(width=40, mode=RenderMode.BLOCK)
        output = renderer.render(img)
        assert len(output) > 0

    def test_output_contains_reset(self, test_image):
        """Test that output ends with ANSI reset code."""
        renderer = AsciiRenderer(width=40, mode=RenderMode.BLOCK)
        output = renderer.render(test_image)
        assert output.endswith("\033[0m") or "\033[0m\n" in output

    def test_black_image_is_spaces(self):
        """Test that black image renders as spaces."""
        black = np.zeros((10, 20, 3), dtype=np.uint8)
        img = Image(black)
        renderer = AsciiRenderer(width=20, mode=RenderMode.BLOCK)
        output = renderer.render(img)
        # Should mostly be spaces (very dark threshold)
        lines = output.split("\n")
        for line in lines[:-1]:  # Last line is just reset code
            if line.strip():  # Skip empty lines
                # Should contain spaces for black pixels
                assert " " in line or line == "\033[0m"


class TestRenderMode:
    """Tests for RenderMode enum."""

    def test_all_modes_exist(self):
        """Test that all expected modes exist."""
        assert RenderMode.BLOCK
        assert RenderMode.HALF_BLOCK
        assert RenderMode.ASCII
        assert RenderMode.ASCII_COLOR
        assert RenderMode.BRAILLE

    def test_mode_values(self):
        """Test mode string values."""
        assert RenderMode.BLOCK.value == "block"
        assert RenderMode.HALF_BLOCK.value == "half_block"
        assert RenderMode.ASCII.value == "ascii"
        assert RenderMode.ASCII_COLOR.value == "ascii_color"
        assert RenderMode.BRAILLE.value == "braille"
