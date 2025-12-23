# Tests for Blend filter with mask functionality
"""
Test Blend filter with optional alpha mask input.
"""

import numpy as np
import pytest

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import Blend, BlendMode


@pytest.fixture
def red_image():
    """Create a solid red 100x100 image."""
    data = np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


@pytest.fixture
def blue_image():
    """Create a solid blue 100x100 image."""
    data = np.full((100, 100, 3), [0, 0, 255], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


@pytest.fixture
def white_mask():
    """Create a solid white mask (full opacity)."""
    data = np.full((100, 100), 255, dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.GRAY)


@pytest.fixture
def black_mask():
    """Create a solid black mask (no opacity)."""
    data = np.full((100, 100), 0, dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.GRAY)


@pytest.fixture
def half_mask():
    """Create a 50% gray mask."""
    data = np.full((100, 100), 128, dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.GRAY)


@pytest.fixture
def gradient_mask():
    """Create a horizontal gradient mask (left=black, right=white)."""
    data = np.zeros((100, 100), dtype=np.uint8)
    for x in range(100):
        data[:, x] = int(x * 2.55)
    return Image(data, pixel_format=PixelFormat.GRAY)


class TestBlendWithoutMask:
    """Tests for Blend without mask (should work as before)."""

    def test_blend_normal_mode(self, red_image, blue_image):
        """Normal blend at 50% opacity should mix colors."""
        blend = Blend(
            inputs=['base', 'overlay'],
            mode=BlendMode.NORMAL,
            opacity=0.5,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
        })

        pixels = result.get_pixels()
        # Should be roughly purple (mix of red and blue)
        assert 100 < pixels[50, 50, 0] < 150  # R
        assert 100 < pixels[50, 50, 2] < 150  # B

    def test_blend_full_opacity(self, red_image, blue_image):
        """Full opacity should show overlay completely."""
        blend = Blend(
            inputs=['base', 'overlay'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
        })

        pixels = result.get_pixels()
        # Should be blue (overlay)
        assert pixels[50, 50, 0] < 10   # R
        assert pixels[50, 50, 2] > 245  # B

    def test_blend_zero_opacity(self, red_image, blue_image):
        """Zero opacity should show base only."""
        blend = Blend(
            inputs=['base', 'overlay'],
            mode=BlendMode.NORMAL,
            opacity=0.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
        })

        pixels = result.get_pixels()
        # Should be red (base)
        assert pixels[50, 50, 0] > 245  # R
        assert pixels[50, 50, 2] < 10   # B


class TestBlendWithMask:
    """Tests for Blend with alpha mask."""

    def test_white_mask_fully_applies_overlay(self, red_image, blue_image, white_mask):
        """White mask with opacity 1.0 should fully apply overlay."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': white_mask,
        })

        pixels = result.get_pixels()
        # Should be blue (overlay fully applied)
        assert pixels[50, 50, 0] < 10   # R
        assert pixels[50, 50, 2] > 245  # B

    def test_black_mask_shows_base_only(self, red_image, blue_image, black_mask):
        """Black mask should show base only."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': black_mask,
        })

        pixels = result.get_pixels()
        # Should be red (base)
        assert pixels[50, 50, 0] > 245  # R
        assert pixels[50, 50, 2] < 10   # B

    def test_half_mask_blends_equally(self, red_image, blue_image, half_mask):
        """50% gray mask should blend equally."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': half_mask,
        })

        pixels = result.get_pixels()
        # Should be roughly purple
        assert 100 < pixels[50, 50, 0] < 150  # R
        assert 100 < pixels[50, 50, 2] < 150  # B

    def test_gradient_mask_creates_smooth_transition(self, red_image, blue_image, gradient_mask):
        """Gradient mask should create smooth left-to-right transition."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': gradient_mask,
        })

        pixels = result.get_pixels()
        # Left side should be more red (base)
        assert pixels[50, 10, 0] > pixels[50, 90, 0]  # R decreases left to right
        # Right side should be more blue (overlay)
        assert pixels[50, 10, 2] < pixels[50, 90, 2]  # B increases left to right

    def test_mask_combined_with_opacity(self, red_image, blue_image, white_mask):
        """Mask and opacity should combine multiplicatively."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=0.5,  # Half opacity
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': white_mask,  # Full mask
        })

        pixels = result.get_pixels()
        # Should be roughly purple (50% blend due to opacity)
        assert 100 < pixels[50, 50, 0] < 150  # R
        assert 100 < pixels[50, 50, 2] < 150  # B


class TestBlendModes:
    """Tests for different blend modes with mask."""

    def test_multiply_mode_with_mask(self, red_image, blue_image, half_mask):
        """MULTIPLY mode should work with mask."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.MULTIPLY,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': half_mask,
        })

        # Should produce a result without errors
        assert result.width == 100
        assert result.height == 100

    def test_screen_mode_with_mask(self, red_image, blue_image, gradient_mask):
        """SCREEN mode should work with mask."""
        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.SCREEN,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': gradient_mask,
        })

        # Should produce a result without errors
        assert result.width == 100
        assert result.height == 100


class TestMaskResizing:
    """Tests for mask resizing when dimensions don't match."""

    def test_mask_resized_to_match_base(self, red_image, blue_image):
        """Smaller mask should be resized to match base."""
        # Create a smaller mask
        small_mask_data = np.full((50, 50), 128, dtype=np.uint8)
        small_mask = Image(small_mask_data, pixel_format=PixelFormat.GRAY)

        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': small_mask,
        })

        # Should work without errors
        assert result.width == 100
        assert result.height == 100


class TestPortSpecs:
    """Tests for port specifications."""

    def test_blend_has_three_input_ports(self):
        """Blend should have 3 input ports (base, overlay, mask)."""
        ports = Blend.get_input_ports()
        assert len(ports) == 3
        assert ports[0]['name'] == 'base'
        assert ports[1]['name'] == 'overlay'
        assert ports[2]['name'] == 'mask'
        assert ports[2].get('optional') is True

    def test_blend_is_multi_input(self):
        """Blend should be multi-input."""
        assert Blend.is_multi_input()


class TestHalfMaskBlending:
    """Tests for half-black/half-white mask blending."""

    def test_upper_black_lower_white_mask(self, red_image, blue_image):
        """Upper half black (0%), lower half white (100%) mask.

        Upper half should show base (red), lower half should show overlay (blue).
        """
        # Create mask: upper half = 0 (black), lower half = 255 (white)
        mask_data = np.zeros((100, 100), dtype=np.uint8)
        mask_data[50:, :] = 255  # Lower half white
        mask = Image(mask_data, pixel_format=PixelFormat.GRAY)

        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': mask,
        })

        pixels = result.get_pixels()

        # Upper half (row 25) should be red (base) - mask is black (0)
        assert pixels[25, 50, 0] > 245, f"Upper half R should be >245, got {pixels[25, 50, 0]}"
        assert pixels[25, 50, 2] < 10, f"Upper half B should be <10, got {pixels[25, 50, 2]}"

        # Lower half (row 75) should be blue (overlay) - mask is white (255)
        assert pixels[75, 50, 0] < 10, f"Lower half R should be <10, got {pixels[75, 50, 0]}"
        assert pixels[75, 50, 2] > 245, f"Lower half B should be >245, got {pixels[75, 50, 2]}"

    def test_left_black_right_white_mask(self, red_image, blue_image):
        """Left half black (0%), right half white (100%) mask.

        Left half should show base (red), right half should show overlay (blue).
        """
        # Create mask: left half = 0 (black), right half = 255 (white)
        mask_data = np.zeros((100, 100), dtype=np.uint8)
        mask_data[:, 50:] = 255  # Right half white
        mask = Image(mask_data, pixel_format=PixelFormat.GRAY)

        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': mask,
        })

        pixels = result.get_pixels()

        # Left half (col 25) should be red (base) - mask is black (0)
        assert pixels[50, 25, 0] > 245, f"Left half R should be >245, got {pixels[50, 25, 0]}"
        assert pixels[50, 25, 2] < 10, f"Left half B should be <10, got {pixels[50, 25, 2]}"

        # Right half (col 75) should be blue (overlay) - mask is white (255)
        assert pixels[50, 75, 0] < 10, f"Right half R should be <10, got {pixels[50, 75, 0]}"
        assert pixels[50, 75, 2] > 245, f"Right half B should be >245, got {pixels[50, 75, 2]}"


class TestRGBMask:
    """Tests for RGB masks (converted to grayscale)."""

    def test_rgb_mask_converted_to_gray(self, red_image, blue_image):
        """RGB mask should be averaged to grayscale for alpha."""
        # Create an RGB "mask" - will be averaged
        rgb_mask_data = np.full((100, 100, 3), [128, 128, 128], dtype=np.uint8)
        rgb_mask = Image(rgb_mask_data, pixel_format=PixelFormat.RGB)

        blend = Blend(
            inputs=['base', 'overlay', 'mask'],
            mode=BlendMode.NORMAL,
            opacity=1.0,
        )
        result = blend.apply_multi({
            'base': red_image,
            'overlay': blue_image,
            'mask': rgb_mask,
        })

        pixels = result.get_pixels()
        # Should be roughly purple (50% blend from gray mask)
        assert 100 < pixels[50, 50, 0] < 150
        assert 100 < pixels[50, 50, 2] < 150
