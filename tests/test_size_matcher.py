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
        """SMALLER should resize to min(w), min(h)."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SMALLER,
            aspect=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'source': large_image,  # 200x160
            'other': small_image,  # 100x80
        })

        # Target should be 100x80
        assert result['a'].width == 100
        assert result['a'].height == 80
        assert result['b'].width == 100
        assert result['b'].height == 80

    def test_bigger_wins_uses_maximum_dimensions(self, small_image, large_image):
        """BIGGER should resize to max(w), max(h)."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.BIGGER,
            aspect=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'source': small_image,  # 100x80
            'other': large_image,  # 200x160
        })

        # Target should be 200x160
        assert result['a'].width == 200
        assert result['a'].height == 160
        assert result['b'].width == 200
        assert result['b'].height == 160

    def test_first_wins_matches_first_dimensions(self, small_image, large_image):
        """SOURCE should resize other to match source."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,
            aspect=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'source': small_image,  # 100x80
            'other': large_image,  # 200x160
        })

        # Both should match first image: 100x80
        assert result['a'].width == 100
        assert result['a'].height == 80
        assert result['b'].width == 100
        assert result['b'].height == 80

    def test_second_wins_matches_second_dimensions(self, small_image, large_image):
        """OTHER should resize source to match other."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.OTHER,
            aspect=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'source': small_image,  # 100x80
            'other': large_image,  # 200x160
        })

        # Both should match second image: 200x160
        assert result['a'].width == 200
        assert result['a'].height == 160
        assert result['b'].width == 200
        assert result['b'].height == 160


class TestAspectModes:
    """Tests for different aspect ratio handling modes."""

    def test_stretch_mode_distorts(self, small_image, square_image):
        """STRETCH mode should resize to exact dimensions (may distort)."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,  # Use square's dimensions
            aspect=AspectMode.STRETCH,
        )
        result = matcher.apply_multi({
            'source': square_image,  # 100x100
            'other': small_image,   # 100x80
        })

        # Both should be exactly 100x100
        assert result['a'].width == 100
        assert result['a'].height == 100
        assert result['b'].width == 100
        assert result['b'].height == 100

    def test_fit_mode_adds_borders(self, small_image, square_image):
        """FIT mode should fit within bounds and add borders."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,
            aspect=AspectMode.FIT,
            fill='#ff0000',  # Red
        )
        result = matcher.apply_multi({
            'source': square_image,  # 100x100
            'other': small_image,   # 100x80 (wider aspect)
        })

        # Output should be 100x100 with red borders
        assert result['b'].width == 100
        assert result['b'].height == 100

        # Check corners have fill color (red)
        pixels = result['b'].get_pixels()
        # Top-left corner should be red (border)
        assert pixels[0, 0, 0] == 255  # R
        assert pixels[0, 0, 1] == 0    # G
        assert pixels[0, 0, 2] == 0    # B

    def test_fill_mode_crops(self, small_image, square_image):
        """FILL mode should fill bounds and crop excess."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,
            aspect=AspectMode.FILL,
        )
        result = matcher.apply_multi({
            'source': square_image,  # 100x100
            'other': small_image,   # 100x80 (wider aspect)
        })

        # Output should be exactly 100x100
        assert result['b'].width == 100
        assert result['b'].height == 100


class TestCropPositions:
    """Tests for different crop positions."""

    def test_center_crop_position(self, small_image, large_image):
        """CENTER crop position should crop from center."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,
            aspect=AspectMode.FILL,
            crop=CropPosition.CENTER,
        )
        result = matcher.apply_multi({
            'source': small_image,
            'other': large_image,
        })

        assert result['b'].width == small_image.width
        assert result['b'].height == small_image.height

    def test_top_left_crop_position(self, small_image, large_image):
        """TOP_LEFT crop position should crop from top-left."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,
            aspect=AspectMode.FILL,
            crop=CropPosition.TOP_LEFT,
        )
        result = matcher.apply_multi({
            'source': small_image,
            'other': large_image,
        })

        assert result['b'].width == small_image.width
        assert result['b'].height == small_image.height


class TestFillColor:
    """Tests for fill color in FIT mode."""

    def test_fill_color_applied(self, small_image, square_image):
        """Fill color should be applied to borders in FIT mode."""
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SOURCE,
            aspect=AspectMode.FIT,
            fill='#00ff00',  # Green
        )
        result = matcher.apply_multi({
            'source': square_image,  # 100x100
            'other': small_image,   # 100x80
        })

        pixels = result['b'].get_pixels()
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
        assert ports[0]['name'] == 'a'
        assert ports[1]['name'] == 'b'

    def test_output_ports(self):
        """SizeMatcher should have 2 output ports."""
        ports = SizeMatcher.get_output_ports()
        assert len(ports) == 2
        assert ports[0]['name'] == 'a'
        assert ports[1]['name'] == 'b'


class TestSameSize:
    """Tests when images already have matching dimensions."""

    def test_same_size_passthrough(self, small_image):
        """Images with same size should pass through unchanged."""
        # Create another image with same dimensions
        data = np.full((80, 100, 3), [200, 100, 50], dtype=np.uint8)
        same_size_image = Image(data, pixel_format=PixelFormat.RGB)

        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode=SizeMatchMode.SMALLER,
        )
        result = matcher.apply_multi({
            'source': small_image,
            'other': same_size_image,
        })

        assert result['a'].width == 100
        assert result['a'].height == 80
        assert result['b'].width == 100
        assert result['b'].height == 80


class TestLegacyCompatibility:
    """Tests for backward compatibility with old parameter names."""

    def test_legacy_mode_values(self, small_image, large_image):
        """Legacy mode values should still work."""
        # Test with string value
        matcher = SizeMatcher(
            inputs=['source', 'other'],
            mode='smaller',  # String instead of enum
        )
        result = matcher.apply_multi({
            'source': large_image,
            'other': small_image,
        })
        assert result['a'].width == 100

    def test_legacy_input_port_names(self, small_image, large_image):
        """Legacy input port names (image_a, image_b) should still work."""
        matcher = SizeMatcher(mode=SizeMatchMode.SMALLER)
        result = matcher.apply_multi({
            'image_a': large_image,
            'image_b': small_image,
        })
        assert result['a'].width == 100
        assert result['b'].width == 100


class TestSerialization:
    """Tests for filter serialization."""

    def test_to_dict_uses_lowercase_enum_values(self):
        """to_dict() should output lowercase enum values."""
        from imagestag.interpolation import InterpolationMethod

        matcher = SizeMatcher(
            mode=SizeMatchMode.SMALLER,
            aspect=AspectMode.FILL,
            crop=CropPosition.CENTER,
            interp=InterpolationMethod.LINEAR,
        )
        d = matcher.to_dict()
        assert d['mode'] == 'smaller'
        assert d['aspect'] == 'fill'
        assert d['crop'] == 'center'
        assert d['interp'] == 'linear'

    def test_to_dict_preserves_non_enum_values(self):
        """to_dict() should preserve non-enum values unchanged."""
        matcher = SizeMatcher(
            mode=SizeMatchMode.BIGGER,
            fill='#ff0000',
        )
        d = matcher.to_dict()
        assert d['fill'] == '#ff0000'
        assert d['type'] == 'SizeMatcher'
