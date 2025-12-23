# Tests for SizeMatcher filter
"""
Test SizeMatcher filter for matching image dimensions.
"""

import numpy as np
import pytest

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import (
    SizeMatcher,
    SizeMatchMode,
    AspectMode,
    CropPosition,
)


@pytest.fixture
def small_image():
    """Create a small 100x80 test image."""
    data = np.full((80, 100, 3), [100, 150, 200], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


@pytest.fixture
def large_image():
    """Create a larger 200x160 test image."""
    data = np.full((160, 200, 3), [50, 100, 150], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


@pytest.fixture
def square_image():
    """Create a 100x100 square test image."""
    data = np.full((100, 100, 3), [75, 125, 175], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


class TestSizeMatchModes:
    """Tests for different size matching modes."""

    def test_smaller_wins_uses_minimum_dimensions(self, small_image, large_image):
        """SMALLER_WINS should resize to min(w), min(h)."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.SMALLER_WINS,
            aspect_mode=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'image_a': large_image,  # 200x160
            'image_b': small_image,  # 100x80
        })

        # Target should be 100x80
        assert result['output_a'].width == 100
        assert result['output_a'].height == 80
        assert result['output_b'].width == 100
        assert result['output_b'].height == 80

    def test_bigger_wins_uses_maximum_dimensions(self, small_image, large_image):
        """BIGGER_WINS should resize to max(w), max(h)."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.BIGGER_WINS,
            aspect_mode=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'image_a': small_image,  # 100x80
            'image_b': large_image,  # 200x160
        })

        # Target should be 200x160
        assert result['output_a'].width == 200
        assert result['output_a'].height == 160
        assert result['output_b'].width == 200
        assert result['output_b'].height == 160

    def test_first_wins_matches_first_dimensions(self, small_image, large_image):
        """FIRST_WINS should resize second to match first."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,
            aspect_mode=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'image_a': small_image,  # 100x80
            'image_b': large_image,  # 200x160
        })

        # Both should match first image: 100x80
        assert result['output_a'].width == 100
        assert result['output_a'].height == 80
        assert result['output_b'].width == 100
        assert result['output_b'].height == 80

    def test_second_wins_matches_second_dimensions(self, small_image, large_image):
        """SECOND_WINS should resize first to match second."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.SECOND_WINS,
            aspect_mode=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'image_a': small_image,  # 100x80
            'image_b': large_image,  # 200x160
        })

        # Both should match second image: 200x160
        assert result['output_a'].width == 200
        assert result['output_a'].height == 160
        assert result['output_b'].width == 200
        assert result['output_b'].height == 160


class TestAspectModes:
    """Tests for different aspect ratio handling modes."""

    def test_stretch_mode_distorts(self, small_image, square_image):
        """STRETCH mode should resize to exact dimensions (may distort)."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,  # Use square's dimensions
            aspect_mode=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'image_a': square_image,  # 100x100
            'image_b': small_image,   # 100x80
        })

        # Both should be exactly 100x100
        assert result['output_a'].width == 100
        assert result['output_a'].height == 100
        assert result['output_b'].width == 100
        assert result['output_b'].height == 100

    def test_fit_mode_adds_borders(self, small_image, square_image):
        """FIT mode should fit within bounds and add borders."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,
            aspect_mode=AspectMode.FIT,
            fill_color_r=255,
            fill_color_g=0,
            fill_color_b=0,
        )
        result = matcher.apply_multi({
            'image_a': square_image,  # 100x100
            'image_b': small_image,   # 100x80 (wider aspect)
        })

        # Output should be 100x100 with red borders
        assert result['output_b'].width == 100
        assert result['output_b'].height == 100

        # Check corners have fill color (red)
        pixels = result['output_b'].get_pixels()
        # Top-left corner should be red (border)
        assert pixels[0, 0, 0] == 255  # R
        assert pixels[0, 0, 1] == 0    # G
        assert pixels[0, 0, 2] == 0    # B

    def test_fill_mode_crops(self, small_image, square_image):
        """FILL mode should fill bounds and crop excess."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,
            aspect_mode=AspectMode.FILL,
        )
        result = matcher.apply_multi({
            'image_a': square_image,  # 100x100
            'image_b': small_image,   # 100x80 (wider aspect)
        })

        # Output should be exactly 100x100
        assert result['output_b'].width == 100
        assert result['output_b'].height == 100


class TestCropPositions:
    """Tests for different crop positions."""

    def test_center_crop_position(self, small_image, large_image):
        """CENTER crop position should crop from center."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,
            aspect_mode=AspectMode.FILL,
            crop_position=CropPosition.CENTER,
        )
        result = matcher.apply_multi({
            'image_a': small_image,
            'image_b': large_image,
        })

        assert result['output_b'].width == small_image.width
        assert result['output_b'].height == small_image.height

    def test_top_left_crop_position(self, small_image, large_image):
        """TOP_LEFT crop position should crop from top-left."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,
            aspect_mode=AspectMode.FILL,
            crop_position=CropPosition.TOP_LEFT,
        )
        result = matcher.apply_multi({
            'image_a': small_image,
            'image_b': large_image,
        })

        assert result['output_b'].width == small_image.width
        assert result['output_b'].height == small_image.height


class TestFillColor:
    """Tests for fill color in FIT mode."""

    def test_fill_color_applied(self, small_image, square_image):
        """Fill color should be applied to borders in FIT mode."""
        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.FIRST_WINS,
            aspect_mode=AspectMode.FIT,
            fill_color_r=0,
            fill_color_g=255,
            fill_color_b=0,  # Green
        )
        result = matcher.apply_multi({
            'image_a': square_image,  # 100x100
            'image_b': small_image,   # 100x80
        })

        pixels = result['output_b'].get_pixels()
        # Check border color is green
        assert pixels[0, 0, 1] == 255  # G channel should be 255


class TestPortSpecs:
    """Tests for port specifications."""

    def test_is_multi_input(self):
        """SizeMatcher should be multi-input."""
        assert SizeMatcher.is_multi_input()

    def test_is_multi_output(self):
        """SizeMatcher should be multi-output."""
        assert SizeMatcher.is_multi_output()

    def test_input_ports(self):
        """SizeMatcher should have 2 input ports."""
        ports = SizeMatcher.get_input_ports()
        assert len(ports) == 2
        assert ports[0]['name'] == 'image_a'
        assert ports[1]['name'] == 'image_b'

    def test_output_ports(self):
        """SizeMatcher should have 2 output ports."""
        ports = SizeMatcher.get_output_ports()
        assert len(ports) == 2
        assert ports[0]['name'] == 'output_a'
        assert ports[1]['name'] == 'output_b'


class TestSameSize:
    """Tests when images already have matching dimensions."""

    def test_same_size_passthrough(self, small_image):
        """Images with same size should pass through unchanged."""
        # Create another image with same dimensions
        data = np.full((80, 100, 3), [200, 100, 50], dtype=np.uint8)
        same_size_image = Image(data, pixel_format=PixelFormat.RGB)

        matcher = SizeMatcher(
            inputs=['image_a', 'image_b'],
            size_mode=SizeMatchMode.SMALLER_WINS,
        )
        result = matcher.apply_multi({
            'image_a': small_image,
            'image_b': same_size_image,
        })

        assert result['output_a'].width == 100
        assert result['output_a'].height == 80
        assert result['output_b'].width == 100
        assert result['output_b'].height == 80
