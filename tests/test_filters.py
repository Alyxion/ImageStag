"""
Tests for the ImageStag filter system.

Tests verify actual pixel values to ensure filters work correctly.
"""

import pytest
import json
import numpy as np

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.media.samples import STAG_PATH
from imagestag.filters import (
    Filter,
    FilterPipeline,
    FilterGraph,
    FILTER_REGISTRY,
    Brightness,
    Contrast,
    Saturation,
    Grayscale,
    Invert,
    Threshold,
    GaussianBlur,
    BoxBlur,
    UnsharpMask,
    Sharpen,
    Resize,
    Crop,
    CenterCrop,
    Rotate,
    Flip,
    BlendMode,
    Blend,
    Composite,
    MaskApply,
)


@pytest.fixture
def sample_image() -> Image:
    """Load sample stag image for testing."""
    return Image(STAG_PATH)


@pytest.fixture
def solid_red_image() -> Image:
    """Create a solid red 100x100 image."""
    img = Image(size=(100, 100), bg_color=(255, 0, 0))
    return img


@pytest.fixture
def gradient_image() -> Image:
    """Create a horizontal gradient image (black to white)."""
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    for x in range(100):
        pixels[:, x, :] = x * 255 // 99  # 0 to 255
    return Image(pixels, pixel_format=PixelFormat.RGB)


@pytest.fixture
def checkerboard_image() -> Image:
    """Create a 100x100 checkerboard (10x10 squares)."""
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    for y in range(100):
        for x in range(100):
            if ((x // 10) + (y // 10)) % 2 == 0:
                pixels[y, x] = [255, 255, 255]
            else:
                pixels[y, x] = [0, 0, 0]
    return Image(pixels, pixel_format=PixelFormat.RGB)


def get_pixel(image: Image, x: int, y: int) -> tuple[int, int, int]:
    """Get RGB values at pixel (x, y)."""
    pixels = image.get_pixels(PixelFormat.RGB)
    return (int(pixels[y, x, 0]), int(pixels[y, x, 1]), int(pixels[y, x, 2]))


def get_average_brightness(image: Image) -> float:
    """Get average brightness (0-255) of image."""
    pixels = image.get_pixels(PixelFormat.RGB)
    return float(np.mean(pixels))


def get_average_color(image: Image) -> tuple[float, float, float]:
    """Get average RGB color of image."""
    pixels = image.get_pixels(PixelFormat.RGB)
    return (
        float(np.mean(pixels[:, :, 0])),
        float(np.mean(pixels[:, :, 1])),
        float(np.mean(pixels[:, :, 2])),
    )


class TestFilterRegistry:
    """Tests for filter registration."""

    def test_filters_registered(self):
        """Verify all filters are registered."""
        assert 'Brightness' in FILTER_REGISTRY
        assert 'brightness' in FILTER_REGISTRY
        assert 'GaussianBlur' in FILTER_REGISTRY
        assert 'Resize' in FILTER_REGISTRY

    def test_alias_registered(self):
        """Verify aliases are working."""
        from imagestag.filters import FILTER_ALIASES
        assert 'blur' in FILTER_ALIASES
        assert FILTER_ALIASES['blur'] is GaussianBlur


class TestFilterSerialization:
    """Tests for JSON serialization."""

    def test_brightness_to_dict(self):
        """Test Brightness serialization."""
        f = Brightness(factor=1.5)
        d = f.to_dict()
        assert d['type'] == 'Brightness'
        assert d['factor'] == 1.5

    def test_brightness_from_dict(self):
        """Test Brightness deserialization."""
        d = {'type': 'Brightness', 'factor': 1.5}
        f = Filter.from_dict(d)
        assert isinstance(f, Brightness)
        assert f.factor == 1.5

    def test_brightness_roundtrip(self, gradient_image):
        """Test serialization roundtrip produces same result."""
        original = Brightness(factor=1.3)
        json_str = original.to_json()
        restored = Filter.from_json(json_str)

        result1 = original.apply(gradient_image)
        result2 = restored.apply(gradient_image)

        # Same filter should produce identical results
        np.testing.assert_array_equal(
            result1.get_pixels(PixelFormat.RGB),
            result2.get_pixels(PixelFormat.RGB)
        )

    def test_pipeline_roundtrip(self, gradient_image):
        """Test pipeline serialization roundtrip."""
        original = FilterPipeline([
            Brightness(factor=1.2),
            Contrast(factor=0.8),
        ])
        d = original.to_dict()
        restored = FilterPipeline.from_dict(d)

        result1 = original.apply(gradient_image)
        result2 = restored.apply(gradient_image)

        np.testing.assert_array_equal(
            result1.get_pixels(PixelFormat.RGB),
            result2.get_pixels(PixelFormat.RGB)
        )


class TestStringParsing:
    """Tests for string format parsing."""

    def test_parse_simple_filter(self):
        """Test parsing simple filter."""
        f = Filter.parse('brightness(1.5)')
        assert isinstance(f, Brightness)
        assert f.factor == 1.5

    def test_parse_with_named_param(self):
        """Test parsing with named parameter."""
        f = Filter.parse('gaussianblur(radius=3.0)')
        assert isinstance(f, GaussianBlur)
        assert f.radius == 3.0

    def test_parse_alias(self):
        """Test parsing with alias."""
        f = Filter.parse('blur(2.0)')
        assert isinstance(f, GaussianBlur)
        assert f.radius == 2.0

    def test_parse_pipeline(self):
        """Test parsing pipeline string."""
        pipeline = FilterPipeline.parse('resize(0.5)|blur(1.5)|brightness(1.1)')
        assert len(pipeline) == 3
        assert isinstance(pipeline[0], Resize)
        assert isinstance(pipeline[1], GaussianBlur)
        assert isinstance(pipeline[2], Brightness)

    def test_parsed_pipeline_same_result(self, gradient_image):
        """Test that parsed pipeline produces same result as constructed."""
        constructed = FilterPipeline([
            Resize(scale=0.5),
            Brightness(factor=1.2),
        ])
        parsed = FilterPipeline.parse('resize(0.5)|brightness(1.2)')

        result1 = constructed.apply(gradient_image)
        result2 = parsed.apply(gradient_image)

        np.testing.assert_array_equal(
            result1.get_pixels(PixelFormat.RGB),
            result2.get_pixels(PixelFormat.RGB)
        )


class TestBrightnessFilter:
    """Tests for brightness filter with pixel verification."""

    def test_brightness_increases_values(self, gradient_image):
        """Brightness > 1 should increase pixel values."""
        original_avg = get_average_brightness(gradient_image)
        result = Brightness(factor=1.5).apply(gradient_image)
        new_avg = get_average_brightness(result)
        assert new_avg > original_avg

    def test_brightness_decreases_values(self, gradient_image):
        """Brightness < 1 should decrease pixel values."""
        original_avg = get_average_brightness(gradient_image)
        result = Brightness(factor=0.5).apply(gradient_image)
        new_avg = get_average_brightness(result)
        assert new_avg < original_avg

    def test_brightness_zero_is_black(self, solid_red_image):
        """Brightness 0 should produce black image."""
        result = Brightness(factor=0.0).apply(solid_red_image)
        avg = get_average_brightness(result)
        assert avg < 1.0  # Should be essentially black

    def test_brightness_one_unchanged(self, gradient_image):
        """Brightness 1.0 should leave image unchanged."""
        result = Brightness(factor=1.0).apply(gradient_image)
        np.testing.assert_array_equal(
            gradient_image.get_pixels(PixelFormat.RGB),
            result.get_pixels(PixelFormat.RGB)
        )


class TestContrastFilter:
    """Tests for contrast filter with pixel verification."""

    def test_contrast_zero_is_gray(self, gradient_image):
        """Contrast 0 should produce uniform gray."""
        result = Contrast(factor=0.0).apply(gradient_image)
        pixels = result.get_pixels(PixelFormat.RGB)
        # All pixels should be the same (gray)
        std = np.std(pixels)
        assert std < 1.0  # Very low variance = uniform

    def test_contrast_increases_range(self, gradient_image):
        """Contrast > 1 should increase value range."""
        original = gradient_image.get_pixels(PixelFormat.RGB)
        original_std = np.std(original)

        result = Contrast(factor=2.0).apply(gradient_image)
        result_std = np.std(result.get_pixels(PixelFormat.RGB))

        # Higher contrast = higher standard deviation (more spread)
        assert result_std > original_std

    def test_contrast_one_unchanged(self, gradient_image):
        """Contrast 1.0 should leave image unchanged."""
        result = Contrast(factor=1.0).apply(gradient_image)
        np.testing.assert_array_equal(
            gradient_image.get_pixels(PixelFormat.RGB),
            result.get_pixels(PixelFormat.RGB)
        )


class TestSaturationFilter:
    """Tests for saturation filter with pixel verification."""

    def test_saturation_zero_is_grayscale(self, solid_red_image):
        """Saturation 0 should produce grayscale (R=G=B)."""
        result = Saturation(factor=0.0).apply(solid_red_image)
        r, g, b = get_average_color(result)
        # R, G, B should be equal (grayscale)
        assert abs(r - g) < 2.0
        assert abs(g - b) < 2.0

    def test_saturation_preserves_grayscale(self, gradient_image):
        """Saturation change should not affect grayscale image much."""
        # gradient_image is grayscale (R=G=B)
        result = Saturation(factor=2.0).apply(gradient_image)
        original_avg = get_average_brightness(gradient_image)
        new_avg = get_average_brightness(result)
        # Should be very similar since there's no color to saturate
        assert abs(original_avg - new_avg) < 5.0

    def test_saturation_one_unchanged(self, solid_red_image):
        """Saturation 1.0 should leave image unchanged."""
        result = Saturation(factor=1.0).apply(solid_red_image)
        np.testing.assert_array_equal(
            solid_red_image.get_pixels(PixelFormat.RGB),
            result.get_pixels(PixelFormat.RGB)
        )


class TestGrayscaleFilter:
    """Tests for grayscale filter with pixel verification."""

    def test_grayscale_makes_rgb_equal(self, solid_red_image):
        """Grayscale should make R=G=B for all pixels."""
        result = Grayscale().apply(solid_red_image)
        pixels = result.get_pixels(PixelFormat.RGB)
        # Check that R=G=B for each pixel
        assert np.allclose(pixels[:, :, 0], pixels[:, :, 1])
        assert np.allclose(pixels[:, :, 1], pixels[:, :, 2])

    def test_grayscale_preserves_already_gray(self, gradient_image):
        """Grayscale on grayscale image should be similar."""
        result = Grayscale().apply(gradient_image)
        # Both should have equal RGB channels
        original = gradient_image.get_pixels(PixelFormat.RGB)
        result_pixels = result.get_pixels(PixelFormat.RGB)

        # Check shapes match
        assert original.shape == result_pixels.shape


class TestInvertFilter:
    """Tests for invert filter with pixel verification."""

    def test_invert_black_to_white(self):
        """Inverting black should give white."""
        black = Image(size=(10, 10), bg_color=(0, 0, 0))
        result = Invert().apply(black)
        r, g, b = get_pixel(result, 5, 5)
        assert r == 255
        assert g == 255
        assert b == 255

    def test_invert_white_to_black(self):
        """Inverting white should give black."""
        white = Image(size=(10, 10), bg_color=(255, 255, 255))
        result = Invert().apply(white)
        r, g, b = get_pixel(result, 5, 5)
        assert r == 0
        assert g == 0
        assert b == 0

    def test_invert_red_to_cyan(self, solid_red_image):
        """Inverting red (255,0,0) should give cyan (0,255,255)."""
        result = Invert().apply(solid_red_image)
        r, g, b = get_pixel(result, 50, 50)
        assert r == 0
        assert g == 255
        assert b == 255

    def test_double_invert_unchanged(self, sample_image):
        """Double invert should restore original image."""
        once = Invert().apply(sample_image)
        twice = Invert().apply(once)
        np.testing.assert_array_equal(
            sample_image.get_pixels(PixelFormat.RGB),
            twice.get_pixels(PixelFormat.RGB)
        )


class TestBlurFilters:
    """Tests for blur filters with pixel verification."""

    def test_gaussian_blur_smooths_edges(self, checkerboard_image):
        """Blur should reduce contrast at edges (lower std dev)."""
        original_std = np.std(checkerboard_image.get_pixels(PixelFormat.RGB))
        result = GaussianBlur(radius=5.0).apply(checkerboard_image)
        result_std = np.std(result.get_pixels(PixelFormat.RGB))
        # Blurred image should have lower variance
        assert result_std < original_std

    def test_gaussian_blur_radius_effect(self, checkerboard_image):
        """Larger radius should produce more blurring."""
        small_blur = GaussianBlur(radius=1.0).apply(checkerboard_image)
        large_blur = GaussianBlur(radius=10.0).apply(checkerboard_image)

        small_std = np.std(small_blur.get_pixels(PixelFormat.RGB))
        large_std = np.std(large_blur.get_pixels(PixelFormat.RGB))

        # Larger blur = lower variance
        assert large_std < small_std

    def test_box_blur_smooths(self, checkerboard_image):
        """Box blur should also reduce variance."""
        original_std = np.std(checkerboard_image.get_pixels(PixelFormat.RGB))
        result = BoxBlur(radius=5).apply(checkerboard_image)
        result_std = np.std(result.get_pixels(PixelFormat.RGB))
        assert result_std < original_std

    def test_sharpen_increases_edges(self, checkerboard_image):
        """Sharpen should increase edge contrast."""
        # Blur first to create something to sharpen
        blurred = GaussianBlur(radius=3.0).apply(checkerboard_image)
        sharpened = UnsharpMask(radius=2.0, percent=200).apply(blurred)

        blurred_std = np.std(blurred.get_pixels(PixelFormat.RGB))
        sharpened_std = np.std(sharpened.get_pixels(PixelFormat.RGB))

        # Sharpening should increase variance (restore some edge contrast)
        assert sharpened_std > blurred_std


class TestResizeFilter:
    """Tests for resize filter with pixel verification."""

    def test_resize_half_dimensions(self, sample_image):
        """Resize 0.5 should halve dimensions."""
        result = Resize(scale=0.5).apply(sample_image)
        assert result.width == sample_image.width // 2
        assert result.height == sample_image.height // 2

    def test_resize_double_dimensions(self, solid_red_image):
        """Resize 2.0 should double dimensions."""
        result = Resize(scale=2.0).apply(solid_red_image)
        assert result.width == 200
        assert result.height == 200

    def test_resize_preserves_color(self, solid_red_image):
        """Resize should preserve solid colors."""
        result = Resize(scale=0.5).apply(solid_red_image)
        r, g, b = get_pixel(result, 25, 25)
        assert r == 255
        assert g == 0
        assert b == 0

    def test_resize_to_specific_size(self, sample_image):
        """Resize to specific dimensions."""
        result = Resize(size=(50, 75)).apply(sample_image)
        assert result.width == 50
        assert result.height == 75


class TestCropFilter:
    """Tests for crop filter with pixel verification."""

    def test_crop_dimensions(self, sample_image):
        """Crop should produce correct dimensions."""
        result = Crop(x=10, y=10, width=50, height=30).apply(sample_image)
        assert result.width == 50
        assert result.height == 30

    def test_crop_gets_correct_region(self, gradient_image):
        """Crop should extract the correct region."""
        # Crop from x=50 should get brighter pixels (gradient goes left to right)
        left_crop = Crop(x=0, y=0, width=20, height=100).apply(gradient_image)
        right_crop = Crop(x=80, y=0, width=20, height=100).apply(gradient_image)

        left_avg = get_average_brightness(left_crop)
        right_avg = get_average_brightness(right_crop)

        # Right side of gradient should be brighter
        assert right_avg > left_avg

    def test_center_crop(self, gradient_image):
        """Center crop should get middle region."""
        result = CenterCrop(width=50, height=50).apply(gradient_image)
        assert result.width == 50
        assert result.height == 50

        # Center of gradient (x=50) should be mid-gray
        avg = get_average_brightness(result)
        assert 100 < avg < 155  # Roughly middle brightness


class TestRotateFilter:
    """Tests for rotate filter with pixel verification."""

    def test_rotate_90_swaps_dimensions_with_expand(self, sample_image):
        """90 degree rotation with expand should swap width/height."""
        result = Rotate(angle=90, expand=True).apply(sample_image)
        assert result.width == sample_image.height
        assert result.height == sample_image.width

    def test_rotate_180_preserves_dimensions(self, sample_image):
        """180 degree rotation should preserve dimensions."""
        result = Rotate(angle=180).apply(sample_image)
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_rotate_180_inverts_gradient(self, gradient_image):
        """180 rotation should reverse the gradient direction."""
        result = Rotate(angle=180).apply(gradient_image)

        # Original: left is dark, right is bright
        # Rotated 180: left should be bright, right should be dark
        left_pixel = get_pixel(result, 5, 50)
        right_pixel = get_pixel(result, 95, 50)

        # After 180 rotation, left should be brighter than right
        assert sum(left_pixel) > sum(right_pixel)


class TestFlipFilter:
    """Tests for flip filter with pixel verification."""

    def test_flip_horizontal_reverses_gradient(self, gradient_image):
        """Horizontal flip should reverse left-right gradient."""
        result = Flip(horizontal=True).apply(gradient_image)

        # Original: left is dark, right is bright
        # Flipped: left should be bright, right should be dark
        left_pixel = get_pixel(result, 5, 50)
        right_pixel = get_pixel(result, 95, 50)

        assert sum(left_pixel) > sum(right_pixel)

    def test_flip_vertical_same_for_horizontal_gradient(self, gradient_image):
        """Vertical flip shouldn't change horizontal gradient much."""
        result = Flip(vertical=True).apply(gradient_image)

        # Horizontal gradient should look the same after vertical flip
        left_pixel_orig = get_pixel(gradient_image, 5, 50)
        left_pixel_flip = get_pixel(result, 5, 50)

        # Should be same brightness (just different y position)
        assert abs(sum(left_pixel_orig) - sum(left_pixel_flip)) < 10

    def test_double_flip_unchanged(self, sample_image):
        """Double flip should restore original."""
        once = Flip(horizontal=True, vertical=True).apply(sample_image)
        twice = Flip(horizontal=True, vertical=True).apply(once)
        np.testing.assert_array_equal(
            sample_image.get_pixels(PixelFormat.RGB),
            twice.get_pixels(PixelFormat.RGB)
        )


class TestFilterPipeline:
    """Tests for filter pipeline with pixel verification."""

    def test_pipeline_order_matters(self, gradient_image):
        """Different order should produce different results."""
        pipeline1 = FilterPipeline([
            Brightness(factor=2.0),
            Contrast(factor=0.5),
        ])
        pipeline2 = FilterPipeline([
            Contrast(factor=0.5),
            Brightness(factor=2.0),
        ])

        result1: Image = pipeline1.apply(gradient_image)
        result2: Image = pipeline2.apply(gradient_image)

        # Results should be different
        pixels1 = result1.get_pixels(PixelFormat.RGB)
        pixels2 = result2.get_pixels(PixelFormat.RGB)
        assert not np.array_equal(pixels1, pixels2)

    def test_pipeline_combines_effects(self, solid_red_image):
        """Pipeline should apply all filter effects."""
        pipeline = FilterPipeline([
            Saturation(factor=0.0),  # Make grayscale
            Invert(),                 # Invert the gray
        ])
        result = pipeline.apply(solid_red_image)

        # Red -> Gray (via saturation) -> Inverted gray
        r, g, b = get_average_color(result)
        # Should be grayscale (R=G=B)
        assert abs(r - g) < 2.0
        assert abs(g - b) < 2.0

    def test_empty_pipeline_unchanged(self, gradient_image):
        """Empty pipeline should return identical image."""
        pipeline = FilterPipeline()
        result = pipeline.apply(gradient_image)
        # Note: may not be same object, but should be same pixels
        np.testing.assert_array_equal(
            gradient_image.get_pixels(PixelFormat.RGB),
            result.get_pixels(PixelFormat.RGB)
        )


class TestThresholdFilter:
    """Tests for threshold filter."""

    def test_threshold_produces_binary(self, gradient_image):
        """Threshold should produce only black and white pixels."""
        result = Threshold(value=128).apply(gradient_image)
        pixels = result.get_pixels(PixelFormat.RGB)
        # All pixels should be 0 or 255
        unique = np.unique(pixels)
        assert len(unique) <= 2
        assert 0 in unique or 255 in unique

    def test_threshold_low_mostly_white(self, gradient_image):
        """Low threshold should produce mostly white."""
        result = Threshold(value=50).apply(gradient_image)
        avg = get_average_brightness(result)
        assert avg > 150  # Mostly white

    def test_threshold_high_mostly_black(self, gradient_image):
        """High threshold should produce mostly black."""
        result = Threshold(value=200).apply(gradient_image)
        avg = get_average_brightness(result)
        assert avg < 100  # Mostly black


class TestBlendModes:
    """Tests for blend mode operations."""

    def test_blend_normal(self, solid_red_image, gradient_image):
        """Normal blend should return overlay."""
        blend = Blend(inputs=['a', 'b'], mode=BlendMode.NORMAL)
        result = blend.apply_multi({'a': solid_red_image, 'b': gradient_image})
        # Result should be the gradient (overlay)
        avg = get_average_brightness(result)
        expected_avg = get_average_brightness(gradient_image)
        assert abs(avg - expected_avg) < 5

    def test_blend_multiply_darkens(self, solid_red_image):
        """Multiply blend with gray should darken."""
        # Create 50% gray
        gray = Image(size=(100, 100), bg_color=(128, 128, 128))
        blend = Blend(inputs=['a', 'b'], mode=BlendMode.MULTIPLY)
        result = blend.apply_multi({'a': solid_red_image, 'b': gray})
        # Multiply with 0.5 gray should halve brightness
        r, g, b = get_average_color(result)
        assert r < 200  # Red should be reduced
        assert r > 100  # But not to zero

    def test_blend_screen_lightens(self):
        """Screen blend should lighten."""
        dark = Image(size=(100, 100), bg_color=(50, 50, 50))
        gray = Image(size=(100, 100), bg_color=(128, 128, 128))
        blend = Blend(inputs=['a', 'b'], mode=BlendMode.SCREEN)
        result = blend.apply_multi({'a': dark, 'b': gray})
        avg = get_average_brightness(result)
        # Screen should be brighter than either input
        assert avg > 128

    def test_blend_difference(self, solid_red_image):
        """Difference of same image should be black."""
        blend = Blend(inputs=['a', 'b'], mode=BlendMode.DIFFERENCE)
        result = blend.apply_multi({'a': solid_red_image, 'b': solid_red_image})
        avg = get_average_brightness(result)
        assert avg < 5  # Should be nearly black

    def test_blend_opacity(self, solid_red_image):
        """Opacity should blend between base and result."""
        blue = Image(size=(100, 100), bg_color=(0, 0, 255))
        # 50% opacity blend
        blend = Blend(inputs=['a', 'b'], mode=BlendMode.NORMAL, opacity=0.5)
        result = blend.apply_multi({'a': solid_red_image, 'b': blue})
        r, g, b = get_average_color(result)
        # Should be mix of red and blue
        assert 100 < r < 180
        assert 100 < b < 180


class TestComposite:
    """Tests for composite operation."""

    def test_composite_with_white_mask(self, solid_red_image):
        """White mask should show foreground."""
        blue = Image(size=(100, 100), bg_color=(0, 0, 255))
        white_mask = Image(size=(100, 100), bg_color=(255, 255, 255))

        composite = Composite(inputs=['bg', 'fg', 'mask'])
        result = composite.apply_multi({
            'bg': solid_red_image,
            'fg': blue,
            'mask': white_mask
        })
        r, g, b = get_average_color(result)
        # White mask = show foreground (blue)
        assert b > 200
        assert r < 50

    def test_composite_with_black_mask(self, solid_red_image):
        """Black mask should show background."""
        blue = Image(size=(100, 100), bg_color=(0, 0, 255))
        black_mask = Image(size=(100, 100), bg_color=(0, 0, 0))

        composite = Composite(inputs=['bg', 'fg', 'mask'])
        result = composite.apply_multi({
            'bg': solid_red_image,
            'fg': blue,
            'mask': black_mask
        })
        r, g, b = get_average_color(result)
        # Black mask = show background (red)
        assert r > 200
        assert b < 50

    def test_composite_with_gray_mask(self, solid_red_image):
        """Gray mask should blend."""
        blue = Image(size=(100, 100), bg_color=(0, 0, 255))
        gray_mask = Image(size=(100, 100), bg_color=(128, 128, 128))

        composite = Composite(inputs=['bg', 'fg', 'mask'])
        result = composite.apply_multi({
            'bg': solid_red_image,
            'fg': blue,
            'mask': gray_mask
        })
        r, g, b = get_average_color(result)
        # Should be mix
        assert 80 < r < 180
        assert 80 < b < 180


class TestFilterGraph:
    """Tests for FilterGraph with branching."""

    def test_graph_single_branch(self, gradient_image):
        """Graph with single branch should work like pipeline."""
        graph = FilterGraph()
        graph.branch('main', [Brightness(factor=1.5)])

        result = graph.apply(gradient_image)
        expected = Brightness(factor=1.5).apply(gradient_image)

        np.testing.assert_array_equal(
            result.get_pixels(PixelFormat.RGB),
            expected.get_pixels(PixelFormat.RGB)
        )

    def test_graph_two_branches_blend(self, gradient_image):
        """Graph with two branches and blend."""
        graph = FilterGraph()
        graph.branch('a', [Brightness(factor=2.0)])
        graph.branch('b', [Brightness(factor=0.5)])
        graph.output = Blend(inputs=['a', 'b'], mode=BlendMode.NORMAL)

        result = graph.apply(gradient_image)
        # Result should be branch 'b' (darker) due to NORMAL blend
        expected = Brightness(factor=0.5).apply(gradient_image)
        np.testing.assert_array_equal(
            result.get_pixels(PixelFormat.RGB),
            expected.get_pixels(PixelFormat.RGB)
        )

    def test_graph_with_mask_composite(self, gradient_image):
        """Graph with mask-based compositing."""
        graph = FilterGraph()
        graph.branch('bright', [Brightness(factor=2.0)])
        graph.branch('dark', [Brightness(factor=0.3)])
        graph.branch('mask', [Grayscale(), Threshold(value=128)])
        graph.output = Composite(inputs=['dark', 'bright', 'mask'])

        result = graph.apply(gradient_image)

        # Left side of gradient is dark -> mask is black -> shows 'dark' branch
        # Right side of gradient is bright -> mask is white -> shows 'bright' branch
        left_pixel = get_pixel(result, 10, 50)   # Left side (dark area)
        right_pixel = get_pixel(result, 90, 50)  # Right side (bright area)

        # Right should be much brighter than left
        assert sum(right_pixel) > sum(left_pixel) * 2

    def test_graph_parse_simple(self):
        """Parse simple graph string."""
        graph = FilterGraph.parse('[a:brightness(1.5)]')
        assert 'a' in graph.branches
        assert len(graph.branches['a']) == 1
        assert isinstance(graph.branches['a'][0], Brightness)

    def test_graph_parse_multi_branch(self):
        """Parse multi-branch graph."""
        graph = FilterGraph.parse('''
            [main: resize(0.5)|blur(2.0)]
            [mask: gray|threshold(128)]
            blend(main, mask, multiply)
        ''')
        assert 'main' in graph.branches
        assert 'mask' in graph.branches
        assert len(graph.branches['main']) == 2
        assert len(graph.branches['mask']) == 2
        assert isinstance(graph.output, Blend)
        assert graph.output.mode == BlendMode.MULTIPLY

    def test_graph_parse_single_line(self):
        """Parse single-line graph format."""
        graph = FilterGraph.parse('[a:brightness(1.5)][b:contrast(0.8)]blend(a,b,screen)')
        assert 'a' in graph.branches
        assert 'b' in graph.branches
        assert isinstance(graph.output, Blend)
        assert graph.output.mode == BlendMode.SCREEN

    def test_graph_to_string(self):
        """Convert graph to string."""
        graph = FilterGraph()
        graph.branch('a', [Brightness(factor=1.5)])
        graph.branch('b', [Grayscale()])
        graph.output = Blend(inputs=['a', 'b'], mode=BlendMode.MULTIPLY)

        s = graph.to_string()
        assert '[a:' in s
        assert '[b:' in s
        assert 'blend(' in s
        assert 'multiply' in s.lower()

    def test_graph_roundtrip_string(self, gradient_image):
        """Parse and to_string should produce equivalent graph."""
        original_str = '[a:brightness(1.5)][b:gray]blend(a,b,multiply)'
        graph1 = FilterGraph.parse(original_str)
        result1 = graph1.apply(gradient_image)

        # Convert to string and parse again
        graph2 = FilterGraph.parse(graph1.to_string())
        result2 = graph2.apply(gradient_image)

        np.testing.assert_array_equal(
            result1.get_pixels(PixelFormat.RGB),
            result2.get_pixels(PixelFormat.RGB)
        )

    def test_graph_to_dict(self):
        """Serialize graph to dict."""
        graph = FilterGraph()
        graph.branch('a', [Brightness(factor=1.5)])
        graph.output = Blend(inputs=['a', 'a'], mode=BlendMode.SCREEN)

        d = graph.to_dict()
        assert d['type'] == 'FilterGraph'
        assert 'a' in d['branches']
        assert d['output']['type'] == 'Blend'
        assert d['output']['mode'] == 'SCREEN'

    def test_graph_from_dict(self, gradient_image):
        """Deserialize graph from dict and verify pixel results."""
        d = {
            'type': 'FilterGraph',
            'branches': {
                'main': [{'type': 'Brightness', 'factor': 1.5}],
                'mask': [{'type': 'Grayscale'}],
            },
            'output': {
                'type': 'Blend',
                'inputs': ['main', 'mask'],
                'mode': 'MULTIPLY',
                'opacity': 1.0,
            }
        }
        graph = FilterGraph.from_dict(d)
        assert 'main' in graph.branches
        assert 'mask' in graph.branches
        assert isinstance(graph.output, Blend)

        # Apply and verify pixel results
        result = graph.apply(gradient_image)

        # Build the expected result manually:
        # main = brightness(1.5) on gradient
        # mask = grayscale on gradient (same as original since gradient is already gray)
        # output = multiply(main, mask)
        # Multiply darkens based on overlay - darker areas stay dark, bright areas get modulated

        # Left side: gradient is dark (~0), brightness*1.5 still dark, multiply with dark = very dark
        # Right side: gradient is bright (~255), brightness*1.5 clipped to 255, multiply with bright = bright
        left_pixel = get_pixel(result, 10, 50)
        right_pixel = get_pixel(result, 90, 50)

        # Right side should be significantly brighter than left
        assert sum(right_pixel) > sum(left_pixel) + 100

        # Verify multiply effect: result should be darker than just brightness alone
        bright_only = Brightness(factor=1.5).apply(gradient_image)
        bright_avg = get_average_brightness(bright_only)
        result_avg = get_average_brightness(result)
        assert result_avg < bright_avg  # Multiply darkens
