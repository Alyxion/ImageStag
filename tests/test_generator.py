# Tests for ImageGenerator filter
"""
Test ImageGenerator filter for creating gradient images.
"""

import numpy as np
import pytest

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import (
    ImageGenerator,
    GradientType,
)


@pytest.fixture
def input_image():
    """Create a 100x100 test image for dimension reference."""
    data = np.full((100, 100, 3), [128, 128, 128], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


class TestSolidColor:
    """Tests for solid color generation."""

    def test_solid_gray(self):
        """SOLID should produce uniform gray color."""
        gen = ImageGenerator(
            gradient_type=GradientType.SOLID,
            width=50,
            height=50,
            output_format=PixelFormat.GRAY,
            color_start="#808080",  # Gray (128, 128, 128) -> grayscale 128
        )
        result = gen.apply()

        assert result.width == 50
        assert result.height == 50
        assert result.pixel_format == PixelFormat.GRAY

        pixels = result.get_pixels()
        # All pixels should be the same value (gray computed from RGB, may be 127 or 128 due to rounding)
        assert np.all((pixels == 127) | (pixels == 128))

    def test_solid_rgb(self):
        """SOLID should produce uniform RGB color."""
        gen = ImageGenerator(
            gradient_type=GradientType.SOLID,
            width=50,
            height=50,
            output_format=PixelFormat.RGB,
            color_start="#FF8040",  # R=255, G=128, B=64
        )
        result = gen.apply()

        assert result.pixel_format == PixelFormat.RGB
        pixels = result.get_pixels()
        assert np.all(pixels[:, :, 0] == 255)  # R
        assert np.all(pixels[:, :, 1] == 128)  # G
        assert np.all(pixels[:, :, 2] == 64)   # B

    def test_solid_rgba(self):
        """SOLID should produce uniform RGBA color."""
        gen = ImageGenerator(
            gradient_type=GradientType.SOLID,
            width=50,
            height=50,
            output_format=PixelFormat.RGBA,
            color_start="#FF000080",  # R=255, G=0, B=0, A=128
        )
        result = gen.apply()

        assert result.pixel_format == PixelFormat.RGBA
        pixels = result.get_pixels()
        assert np.all(pixels[:, :, 0] == 255)  # R
        assert np.all(pixels[:, :, 1] == 0)    # G
        assert np.all(pixels[:, :, 2] == 0)    # B
        assert np.all(pixels[:, :, 3] == 128)  # A


class TestLinearGradients:
    """Tests for linear gradients."""

    def test_horizontal_gradient(self):
        """Angle 0 should produce left-to-right gradient."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=0.0,
            width=100,
            height=50,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        assert result.width == 100
        assert result.height == 50
        assert result.pixel_format == PixelFormat.GRAY

        pixels = result.get_pixels()
        # Left edge should be dark (start color)
        assert pixels[25, 0] < 10
        # Right edge should be bright (end color)
        assert pixels[25, 99] > 245
        # Middle should be in between
        assert 100 < pixels[25, 50] < 150

    def test_vertical_gradient(self):
        """Angle 90 should produce top-to-bottom gradient."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=90.0,
            width=50,
            height=100,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        pixels = result.get_pixels()
        # Top edge should be dark
        assert pixels[0, 25] < 10
        # Bottom edge should be bright
        assert pixels[99, 25] > 245
        # Middle should be in between
        assert 100 < pixels[50, 25] < 150

    def test_diagonal_gradient(self):
        """Angle 45 should produce diagonal gradient."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=45.0,
            width=100,
            height=100,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        pixels = result.get_pixels()
        # Top-left corner should be darkest
        assert pixels[0, 0] < 10
        # Bottom-right corner should be brightest
        assert pixels[99, 99] > 245
        # Center should be in between
        assert 100 < pixels[50, 50] < 150

    def test_negative_angle_gradient(self):
        """Negative angle should work correctly."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=-45.0,
            width=100,
            height=100,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        pixels = result.get_pixels()
        # Should have a gradient from one corner to opposite
        assert result.width == 100
        assert result.height == 100


class TestRadialGradients:
    """Tests for radial gradients."""

    def test_radial_gradient_center(self):
        """Radial gradient should be darkest at center (default)."""
        gen = ImageGenerator(
            gradient_type=GradientType.RADIAL,
            width=100,
            height=100,
            center_x=0.5,
            center_y=0.5,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        pixels = result.get_pixels()
        # Center should be dark (start color)
        assert pixels[50, 50] < 10
        # Corners should be bright (end color)
        assert pixels[0, 0] > 200
        assert pixels[99, 99] > 200

    def test_radial_gradient_off_center(self):
        """Off-center radial gradient should work."""
        gen = ImageGenerator(
            gradient_type=GradientType.RADIAL,
            width=100,
            height=100,
            center_x=0.25,
            center_y=0.25,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        pixels = result.get_pixels()
        # Near specified center should be dark
        assert pixels[25, 25] < 10
        # Far corner should be bright
        assert pixels[99, 99] > 200


class TestOutputFormats:
    """Tests for different output formats."""

    def test_output_format_gray(self):
        """GRAY output should be single channel."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=0.0,
            width=50,
            height=50,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        assert result.pixel_format == PixelFormat.GRAY
        pixels = result.get_pixels()
        assert len(pixels.shape) == 2  # 2D array for grayscale

    def test_output_format_rgb(self):
        """RGB output should interpolate colors."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=0.0,
            width=100,
            height=50,
            output_format=PixelFormat.RGB,
            color_start="#FF0000",  # Red
            color_end="#0000FF",    # Blue
        )
        result = gen.apply()

        assert result.pixel_format == PixelFormat.RGB
        pixels = result.get_pixels()
        assert len(pixels.shape) == 3
        assert pixels.shape[2] == 3

        # Left edge should be red
        assert pixels[25, 0, 0] > 245  # R
        assert pixels[25, 0, 2] < 10   # B

        # Right edge should be blue
        assert pixels[25, 99, 0] < 10   # R
        assert pixels[25, 99, 2] > 245  # B

    def test_output_format_rgba(self):
        """RGBA output should include alpha channel."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=0.0,
            width=50,
            height=50,
            output_format=PixelFormat.RGBA,
            color_start="#FF0000FF",  # Red, full opacity
            color_end="#0000FF00",    # Blue, fully transparent
        )
        result = gen.apply()

        assert result.pixel_format == PixelFormat.RGBA
        pixels = result.get_pixels()
        assert len(pixels.shape) == 3
        assert pixels.shape[2] == 4

        # Check alpha interpolation
        assert pixels[25, 0, 3] > 245   # Start alpha high
        assert pixels[25, 49, 3] < 10   # End alpha low


class TestDimensions:
    """Tests for dimension handling."""

    def test_uses_input_image_dimensions(self, input_image):
        """Should use input image dimensions when provided."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            width=50,  # This should be ignored
            height=50,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply(input_image)

        # Should use input_image dimensions (100x100), not 50x50
        assert result.width == 100
        assert result.height == 100

    def test_uses_specified_dimensions(self):
        """Should use width/height params when no input."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            width=200,
            height=150,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        assert result.width == 200
        assert result.height == 150


class TestColorInterpolation:
    """Tests for color interpolation."""

    def test_color_interpolation_midpoint(self):
        """Midpoint should have averaged color values."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=0.0,
            width=101,  # Odd width for exact center
            height=50,
            output_format=PixelFormat.RGB,
            color_start="#000000",  # Black
            color_end="#C86432",    # RGB(200, 100, 50)
        )
        result = gen.apply()

        pixels = result.get_pixels()
        # Center column (50) should have roughly half values
        center_r = pixels[25, 50, 0]
        center_g = pixels[25, 50, 1]
        center_b = pixels[25, 50, 2]

        # Allow some tolerance for interpolation
        assert 90 < center_r < 110  # ~100
        assert 45 < center_g < 55   # ~50
        assert 20 < center_b < 30   # ~25


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_pixel_image(self):
        """Should handle 1x1 image."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            width=1,
            height=1,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        assert result.width == 1
        assert result.height == 1

    def test_single_row_image(self):
        """Should handle single row image."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=0.0,
            width=100,
            height=1,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        assert result.width == 100
        assert result.height == 1

        pixels = result.get_pixels()
        # Should still have gradient
        assert pixels[0, 0] < pixels[0, 99]

    def test_single_column_image(self):
        """Should handle single column image."""
        gen = ImageGenerator(
            gradient_type=GradientType.LINEAR,
            angle=90.0,
            width=1,
            height=100,
            output_format=PixelFormat.GRAY,
        )
        result = gen.apply()

        assert result.width == 1
        assert result.height == 100

        pixels = result.get_pixels()
        # Should still have gradient
        assert pixels[0, 0] < pixels[99, 0]
