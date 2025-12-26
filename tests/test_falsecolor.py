"""Tests for FalseColor filter."""

import pytest
import numpy as np
from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import FalseColor, Filter


@pytest.fixture
def grayscale_gradient():
    """Create horizontal grayscale gradient (0 to 255)."""
    pixels = np.zeros((100, 100), dtype=np.uint8)
    for x in range(100):
        pixels[:, x] = int(x * 255 / 99)
    return Image(pixels, pixel_format=PixelFormat.GRAY)


@pytest.fixture
def rgb_gradient():
    """Create RGB gradient for auto-grayscale test."""
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    for x in range(100):
        val = int(x * 255 / 99)
        pixels[:, x, :] = [val, val, val]
    return Image(pixels, pixel_format=PixelFormat.RGB)


@pytest.fixture
def solid_black():
    """Create solid black image."""
    pixels = np.zeros((50, 50), dtype=np.uint8)
    return Image(pixels, pixel_format=PixelFormat.GRAY)


@pytest.fixture
def solid_white():
    """Create solid white image."""
    pixels = np.full((50, 50), 255, dtype=np.uint8)
    return Image(pixels, pixel_format=PixelFormat.GRAY)


@pytest.fixture
def mid_gray():
    """Create solid mid-gray image."""
    pixels = np.full((50, 50), 128, dtype=np.uint8)
    return Image(pixels, pixel_format=PixelFormat.GRAY)


class TestFalseColorFilter:
    """Tests for FalseColor filter."""

    def test_grayscale_input_produces_rgb(self, grayscale_gradient):
        """Test with grayscale input produces RGB output."""
        result = FalseColor(colormap='viridis').apply(grayscale_gradient)
        assert result.pixel_format == PixelFormat.RGB
        assert result.width == 100
        assert result.height == 100

    def test_rgb_input_auto_grayscale(self, rgb_gradient):
        """Test RGB input is auto-converted to grayscale."""
        result = FalseColor(colormap='hot').apply(rgb_gradient)
        assert result.pixel_format == PixelFormat.RGB
        assert result.width == 100
        assert result.height == 100

    def test_colormap_viridis_endpoints(self, grayscale_gradient):
        """Verify viridis colormap produces expected endpoint colors."""
        result = FalseColor(colormap='viridis').apply(grayscale_gradient)
        pixels = result.get_pixels(PixelFormat.RGB)

        # Left edge (value 0) should be dark purple ~(68, 1, 84)
        left = pixels[50, 0]
        assert left[0] < 100  # R low
        assert left[1] < 50   # G low
        assert left[2] > 50   # B moderate

        # Right edge (value 255) should be yellow ~(253, 231, 37)
        right = pixels[50, 99]
        assert right[0] > 200  # R high
        assert right[1] > 200  # G high
        assert right[2] < 100  # B low

    def test_colormap_hot_lava(self, grayscale_gradient):
        """Verify hot colormap goes from black through red/yellow to white."""
        result = FalseColor(colormap='hot').apply(grayscale_gradient)
        pixels = result.get_pixels(PixelFormat.RGB)

        # Left edge (value 0) should be dark/black
        left = pixels[50, 0]
        assert np.mean(left) < 30

        # Right edge (value 255) should be white
        right = pixels[50, 99]
        assert np.mean(right) > 240

        # Middle should have strong red component
        mid = pixels[50, 50]
        assert mid[0] > 200  # Strong red

    def test_colormap_jet(self, grayscale_gradient):
        """Verify jet colormap covers blue to red spectrum."""
        result = FalseColor(colormap='jet').apply(grayscale_gradient)
        pixels = result.get_pixels(PixelFormat.RGB)

        # Left edge should be blue-ish
        left = pixels[50, 5]
        assert left[2] > left[0]  # More blue than red

        # Right edge should be red-ish
        right = pixels[50, 94]
        assert right[0] > right[2]  # More red than blue

    def test_colormap_inferno(self, grayscale_gradient):
        """Verify inferno colormap (thermal)."""
        result = FalseColor(colormap='inferno').apply(grayscale_gradient)
        pixels = result.get_pixels(PixelFormat.RGB)

        # Should have dark left edge, bright right edge
        left_brightness = np.mean(pixels[50, 0])
        right_brightness = np.mean(pixels[50, 99])
        assert right_brightness > left_brightness * 2

    def test_invalid_colormap_raises(self, grayscale_gradient):
        """Test invalid colormap raises ValueError."""
        with pytest.raises(ValueError, match="Unknown colormap"):
            FalseColor(colormap='not_a_real_colormap').apply(grayscale_gradient)

    def test_reverse_colormap(self, grayscale_gradient):
        """Test reverse parameter inverts colormap."""
        normal = FalseColor(colormap='viridis').apply(grayscale_gradient)
        reversed_result = FalseColor(colormap='viridis', reverse=True).apply(grayscale_gradient)

        normal_px = normal.get_pixels(PixelFormat.RGB)
        reversed_px = reversed_result.get_pixels(PixelFormat.RGB)

        # Left edge of normal should approximately match right edge of reversed
        np.testing.assert_array_almost_equal(
            normal_px[50, 0], reversed_px[50, 99], decimal=0
        )
        np.testing.assert_array_almost_equal(
            normal_px[50, 99], reversed_px[50, 0], decimal=0
        )

    def test_custom_input_range(self):
        """Test custom input range normalization."""
        # Create image with values 100-200
        pixels = np.linspace(100, 200, 50 * 50).reshape(50, 50).astype(np.uint8)
        img = Image(pixels, pixel_format=PixelFormat.GRAY)

        # With custom range, the min value maps to colormap start
        result = FalseColor(
            colormap='viridis',
            input_min=100.0,
            input_max=200.0
        ).apply(img)

        result_px = result.get_pixels(PixelFormat.RGB)

        # Check that we get the full colormap range
        # Top-left (value ~100) should be dark purple
        assert result_px[0, 0, 2] > 50  # Some blue

        # Bottom-right (value ~200) should be yellow
        assert result_px[49, 49, 0] > 200  # High red
        assert result_px[49, 49, 1] > 200  # High green

    def test_solid_black_maps_to_colormap_start(self, solid_black):
        """Solid black should map to colormap's 0.0 value."""
        result = FalseColor(colormap='hot').apply(solid_black)
        pixels = result.get_pixels(PixelFormat.RGB)

        # Hot colormap at 0.0 is black
        assert np.mean(pixels) < 10

    def test_solid_white_maps_to_colormap_end(self, solid_white):
        """Solid white should map to colormap's 1.0 value."""
        result = FalseColor(colormap='hot').apply(solid_white)
        pixels = result.get_pixels(PixelFormat.RGB)

        # Hot colormap at 1.0 is white
        assert np.mean(pixels) > 250

    def test_uniform_input_produces_uniform_output(self, mid_gray):
        """Uniform input should produce uniform colored output."""
        result = FalseColor(colormap='viridis').apply(mid_gray)
        pixels = result.get_pixels(PixelFormat.RGB)

        # All pixels should be nearly identical
        std_r = np.std(pixels[:, :, 0])
        std_g = np.std(pixels[:, :, 1])
        std_b = np.std(pixels[:, :, 2])
        assert std_r < 1.0
        assert std_g < 1.0
        assert std_b < 1.0


class TestFalseColorAliases:
    """Tests for FalseColor aliases."""

    def test_lava_alias(self, grayscale_gradient):
        """Test 'lava' alias maps to FalseColor with hot colormap."""
        f = Filter.parse('lava')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'hot'

        # Should work and produce output
        result = f.apply(grayscale_gradient)
        assert result.pixel_format == PixelFormat.RGB

    def test_thermal_alias(self, grayscale_gradient):
        """Test 'thermal' alias maps to FalseColor with inferno colormap."""
        f = Filter.parse('thermal')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'inferno'

    def test_plasma_alias(self, grayscale_gradient):
        """Test 'plasma' alias maps to FalseColor with plasma colormap."""
        f = Filter.parse('plasma')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'plasma'

    def test_viridis_alias(self, grayscale_gradient):
        """Test 'viridis' alias maps to FalseColor with viridis colormap."""
        f = Filter.parse('viridis')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'viridis'

    def test_jet_alias(self, grayscale_gradient):
        """Test 'jet' alias maps to FalseColor with jet colormap."""
        f = Filter.parse('jet')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'jet'


class TestFalseColorParsing:
    """Tests for FalseColor string parsing."""

    def test_parse_with_colormap(self):
        """Test parsing with colormap argument."""
        f = Filter.parse('falsecolor hot')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'hot'

    def test_parse_with_reverse(self):
        """Test parsing with reverse parameter."""
        f = Filter.parse('falsecolor viridis reverse=true')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'viridis'
        assert f.reverse is True

    def test_parse_with_input_range(self):
        """Test parsing with input range parameters."""
        f = Filter.parse('falsecolor jet input_min=50 input_max=200')
        assert isinstance(f, FalseColor)
        assert f.colormap == 'jet'
        assert f.input_min == 50.0
        assert f.input_max == 200.0


class TestFalseColorSerialization:
    """Tests for FalseColor serialization."""

    def test_to_dict(self):
        """Test serialization to dict."""
        f = FalseColor(colormap='hot', input_min=10, input_max=245, reverse=True)
        d = f.to_dict()

        assert d['type'] == 'FalseColor'
        assert d['colormap'] == 'hot'
        assert d['input_min'] == 10.0
        assert d['input_max'] == 245.0
        assert d['reverse'] is True

    def test_from_dict(self, grayscale_gradient):
        """Test deserialization from dict."""
        d = {
            'type': 'FalseColor',
            'colormap': 'inferno',
            'input_min': 0.0,
            'input_max': 255.0,
            'reverse': False,
        }
        f = Filter.from_dict(d)

        assert isinstance(f, FalseColor)
        assert f.colormap == 'inferno'

        # Should work
        result = f.apply(grayscale_gradient)
        assert result.pixel_format == PixelFormat.RGB

    def test_roundtrip(self, grayscale_gradient):
        """Test serialization roundtrip produces same result."""
        original = FalseColor(colormap='plasma', reverse=True)
        restored = Filter.from_dict(original.to_dict())

        original_result = original.apply(grayscale_gradient)
        restored_result = restored.apply(grayscale_gradient)

        np.testing.assert_array_equal(
            original_result.get_pixels(PixelFormat.RGB),
            restored_result.get_pixels(PixelFormat.RGB)
        )
