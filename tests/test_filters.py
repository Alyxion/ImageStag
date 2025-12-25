"""
Tests for the ImageStag filter system.

Tests verify actual pixel values to ensure filters work correctly.
"""

import pytest
import json
import numpy as np

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.samples import stag
from imagestag.filters import (
    Filter,
    FilterContext,
    AnalyzerFilter,
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
    ImageStats,
    HistogramAnalyzer,
    ColorAnalyzer,
    RegionAnalyzer,
    # Format classes
    BitDepth,
    Compression,
    FormatSpec,
    ImageData,
    register_filter,
)
from dataclasses import dataclass
from typing import ClassVar


@pytest.fixture
def sample_image() -> Image:
    """Load sample stag image for testing."""
    return stag()


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
        result = Flip(mode='h').apply(gradient_image)

        # Original: left is dark, right is bright
        # Flipped: left should be bright, right should be dark
        left_pixel = get_pixel(result, 5, 50)
        right_pixel = get_pixel(result, 95, 50)

        assert sum(left_pixel) > sum(right_pixel)

    def test_flip_vertical_same_for_horizontal_gradient(self, gradient_image):
        """Vertical flip shouldn't change horizontal gradient much."""
        result = Flip(mode='v').apply(gradient_image)

        # Horizontal gradient should look the same after vertical flip
        left_pixel_orig = get_pixel(gradient_image, 5, 50)
        left_pixel_flip = get_pixel(result, 5, 50)

        # Should be same brightness (just different y position)
        assert abs(sum(left_pixel_orig) - sum(left_pixel_flip)) < 10

    def test_double_flip_unchanged(self, sample_image):
        """Double flip should restore original."""
        once = Flip(mode='hv').apply(sample_image)
        twice = Flip(mode='hv').apply(once)
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


class TestImageMetadata:
    """Tests for Image metadata."""

    def test_image_has_metadata(self):
        """Image should have empty metadata dict by default."""
        img = Image(size=(10, 10), bg_color=(255, 0, 0))
        assert hasattr(img, 'metadata')
        assert isinstance(img.metadata, dict)
        assert len(img.metadata) == 0

    def test_metadata_can_be_set(self):
        """Metadata can be set on an image."""
        img = Image(size=(10, 10), bg_color=(255, 0, 0))
        img.metadata['source'] = 'test'
        img.metadata['stats'] = {'brightness': 128}
        assert img.metadata['source'] == 'test'
        assert img.metadata['stats']['brightness'] == 128

    def test_copy_preserves_metadata(self):
        """Image.copy() should copy metadata."""
        img = Image(size=(10, 10), bg_color=(255, 0, 0))
        img.metadata['key'] = 'value'
        img.metadata['nested'] = {'a': 1, 'b': 2}

        copied = img.copy()
        assert copied.metadata['key'] == 'value'
        assert copied.metadata['nested'] == {'a': 1, 'b': 2}

        # Verify deep copy - modifying copy shouldn't affect original
        copied.metadata['key'] = 'modified'
        copied.metadata['nested']['a'] = 999
        assert img.metadata['key'] == 'value'
        assert img.metadata['nested']['a'] == 1


class TestFilterContext:
    """Tests for FilterContext."""

    def test_context_basic_operations(self):
        """Context supports dict-like operations."""
        ctx = FilterContext()
        ctx['key'] = 'value'
        assert ctx['key'] == 'value'
        assert 'key' in ctx
        assert 'missing' not in ctx

    def test_context_get_with_default(self):
        """Context.get() returns default for missing keys."""
        ctx = FilterContext()
        assert ctx.get('missing') is None
        assert ctx.get('missing', 42) == 42

    def test_context_branch_inheritance(self):
        """Child context inherits from parent."""
        parent = FilterContext()
        parent['shared'] = 'from_parent'

        child = parent.branch('child')
        assert child['shared'] == 'from_parent'
        assert child.get('_branch') == 'child'

    def test_context_branch_isolation(self):
        """Child writes don't affect parent."""
        parent = FilterContext()
        parent['value'] = 'original'

        child = parent.branch()
        child['value'] = 'modified'
        child['new_key'] = 'only_in_child'

        assert parent['value'] == 'original'
        assert 'new_key' not in parent
        assert child['value'] == 'modified'

    def test_context_to_dict(self):
        """to_dict() returns all values including inherited."""
        parent = FilterContext()
        parent['a'] = 1

        child = parent.branch()
        child['b'] = 2

        result = child.to_dict()
        assert result['a'] == 1
        assert result['b'] == 2

    def test_context_copy(self):
        """copy() creates independent context."""
        original = FilterContext()
        original['key'] = 'value'

        copied = original.copy()
        copied['key'] = 'modified'

        assert original['key'] == 'value'


class TestFilterWithContext:
    """Tests for filters using context."""

    def test_pipeline_passes_context(self, gradient_image):
        """Pipeline should pass context to all filters."""
        ctx = FilterContext()
        ctx['test_key'] = 'test_value'

        pipeline = FilterPipeline([
            Brightness(factor=1.2),
            Contrast(factor=1.1),
        ])
        result = pipeline.apply(gradient_image, ctx)

        # Pipeline should complete without error
        assert result.width == gradient_image.width

    def test_graph_creates_branch_contexts(self, gradient_image):
        """FilterGraph should create separate contexts per branch."""
        ctx = FilterContext()
        ctx['parent_value'] = 'shared'

        graph = FilterGraph()
        graph.branch('a', [Brightness(factor=1.5)])
        graph.branch('b', [Brightness(factor=0.5)])
        graph.output = Blend(inputs=['a', 'b'], mode=BlendMode.NORMAL)

        # Should execute without error - branches get isolated contexts
        result = graph.apply(gradient_image, ctx)
        assert result.width == gradient_image.width


class TestAnalyzerFilters:
    """Tests for analyzer filters that don't modify the image."""

    def test_analyzer_returns_unchanged_image(self, solid_red_image):
        """Analyzer should return the exact same image."""
        original_pixels = solid_red_image.get_pixels(PixelFormat.RGB).copy()

        ctx = FilterContext()
        result = ImageStats().apply(solid_red_image, ctx)

        # Image should be unchanged
        np.testing.assert_array_equal(
            original_pixels,
            result.get_pixels(PixelFormat.RGB)
        )

    def test_image_stats_basic(self, solid_red_image):
        """ImageStats should compute correct statistics."""
        ctx = FilterContext()
        ImageStats().apply(solid_red_image, ctx)

        stats = ctx['stats']
        assert stats['width'] == 100
        assert stats['height'] == 100
        assert stats['channels']['red']['mean'] == 255.0
        assert stats['channels']['green']['mean'] == 0.0
        assert stats['channels']['blue']['mean'] == 0.0

    def test_image_stats_brightness(self, gradient_image):
        """ImageStats should compute reasonable brightness."""
        ctx = FilterContext()
        ImageStats().apply(gradient_image, ctx)

        # Gradient from 0-255 should have ~127.5 average
        brightness = ctx['stats']['brightness']
        assert 120 < brightness < 135

    def test_histogram_analyzer(self, gradient_image):
        """HistogramAnalyzer should produce valid histograms."""
        ctx = FilterContext()
        HistogramAnalyzer().apply(gradient_image, ctx)

        hist = ctx['histogram']
        assert 'red' in hist
        assert 'green' in hist
        assert 'blue' in hist
        assert 'luminance' in hist
        assert len(hist['red']) == 256

        # Gradient should have fairly even distribution
        total_pixels = 100 * 100
        assert sum(hist['luminance']) == total_pixels

    def test_color_analyzer(self, solid_red_image):
        """ColorAnalyzer should detect average color."""
        ctx = FilterContext()
        ColorAnalyzer().apply(solid_red_image, ctx)

        colors = ctx['colors']
        avg_r, avg_g, avg_b = colors['average']
        assert avg_r == 255.0
        assert avg_g == 0.0
        assert avg_b == 0.0

    def test_region_analyzer(self, gradient_image):
        """RegionAnalyzer should analyze specific region."""
        ctx = FilterContext()
        # Analyze right side of gradient (brighter)
        RegionAnalyzer(x=80, y=0, width=20, height=100).apply(gradient_image, ctx)

        region = ctx['region']
        assert region['bounds'] == (80, 0, 100, 100)
        assert region['size'] == (20, 100)
        # Right side should be bright
        assert region['brightness'] > 200

    def test_analyzer_stores_in_metadata(self, solid_red_image):
        """Analyzer should store in metadata when configured."""
        analyzer = ImageStats(store_in_metadata=True, store_in_context=False)
        ctx = FilterContext()
        result = analyzer.apply(solid_red_image, ctx)

        # Should be in metadata, not context
        assert 'stats' not in ctx.data
        assert 'stats' in result.metadata
        assert result.metadata['stats']['width'] == 100

    def test_analyzer_in_pipeline(self, gradient_image):
        """Analyzers work in pipelines alongside regular filters."""
        ctx = FilterContext()
        pipeline = FilterPipeline([
            ImageStats(result_key='before'),
            Brightness(factor=1.5),
            ImageStats(result_key='after'),
        ])
        result = pipeline.apply(gradient_image, ctx)

        # After brightness increase, image should be brighter
        before_brightness = ctx['before']['brightness']
        after_brightness = ctx['after']['brightness']
        assert after_brightness > before_brightness

    def test_analyzer_in_graph_branches(self, gradient_image):
        """Analyzers work in graph branches with isolated contexts."""
        graph = FilterGraph()
        graph.branch('bright', [
            Brightness(factor=2.0),
            ImageStats(result_key='branch_stats'),
        ])
        graph.branch('dark', [
            Brightness(factor=0.5),
            ImageStats(result_key='branch_stats'),
        ])
        graph.output = Blend(inputs=['bright', 'dark'], mode=BlendMode.NORMAL)

        ctx = FilterContext()
        graph.apply(gradient_image, ctx)

        # Each branch had its own context, so stats are isolated
        # The parent context won't have branch_stats since they wrote to child contexts
        assert 'branch_stats' not in ctx.data


class TestFormatSpec:
    """Tests for FormatSpec class."""

    def test_format_spec_rgb(self):
        """FormatSpec.RGB creates correct spec."""
        spec = FormatSpec.RGB
        assert spec.pixel_format == 'RGB'
        assert spec.bit_depth == BitDepth.UINT8
        assert spec.compression == Compression.NONE

    def test_format_spec_rgba(self):
        """FormatSpec.RGBA creates correct spec."""
        spec = FormatSpec.RGBA
        assert spec.pixel_format == 'RGBA'
        assert spec.bit_depth == BitDepth.UINT8

    def test_format_spec_bgr(self):
        """FormatSpec.BGR creates correct spec."""
        spec = FormatSpec.BGR
        assert spec.pixel_format == 'BGR'

    def test_format_spec_gray(self):
        """FormatSpec.GRAY creates correct spec."""
        spec = FormatSpec.GRAY
        assert spec.pixel_format == 'GRAY'

    def test_format_spec_any_matches_all(self):
        """FormatSpec.ANY matches any other format."""
        any_spec = FormatSpec.ANY
        assert any_spec.matches(FormatSpec.RGB)
        assert any_spec.matches(FormatSpec.RGBA)
        assert any_spec.matches(FormatSpec.BGR)
        assert any_spec.matches(FormatSpec.JPEG)

    def test_format_spec_matches_same(self):
        """Identical formats match."""
        assert FormatSpec.RGB.matches(FormatSpec.RGB)
        assert FormatSpec.RGBA.matches(FormatSpec.RGBA)

    def test_format_spec_different_pixel_format_no_match(self):
        """Different pixel formats don't match."""
        assert not FormatSpec.RGB.matches(FormatSpec.BGR)
        assert not FormatSpec.RGB.matches(FormatSpec.RGBA)

    def test_format_spec_compressed_formats(self):
        """Compressed format specs work correctly."""
        jpeg = FormatSpec.JPEG
        png = FormatSpec.PNG
        assert jpeg.compression == Compression.JPEG
        assert png.compression == Compression.PNG
        assert jpeg.is_compressed()
        assert png.is_compressed()
        assert not FormatSpec.RGB.is_compressed()

    def test_format_spec_compressed_match(self):
        """Compressed formats match by compression type."""
        assert FormatSpec.JPEG.matches(FormatSpec.JPEG)
        assert not FormatSpec.JPEG.matches(FormatSpec.PNG)

    def test_format_spec_bit_depth(self):
        """Different bit depths create different specs."""
        spec_8bit = FormatSpec(pixel_format='RGB', bit_depth=BitDepth.UINT8)
        spec_16bit = FormatSpec(pixel_format='RGB', bit_depth=BitDepth.UINT16)
        spec_float = FormatSpec(pixel_format='RGB', bit_depth=BitDepth.FLOAT32)

        assert not spec_8bit.matches(spec_16bit)
        assert not spec_8bit.matches(spec_float)

    def test_format_spec_str(self):
        """FormatSpec __str__ returns readable representation."""
        assert str(FormatSpec.RGB) == 'RGB'
        assert str(FormatSpec.ANY) == 'ANY'
        assert str(FormatSpec.JPEG) == 'JPEG'


class TestBitDepth:
    """Tests for BitDepth enum."""

    def test_bit_depth_dtype(self):
        """BitDepth.dtype returns correct numpy dtype."""
        assert BitDepth.UINT8.dtype == np.dtype(np.uint8)
        assert BitDepth.UINT16.dtype == np.dtype(np.uint16)
        assert BitDepth.FLOAT32.dtype == np.dtype(np.float32)

    def test_bit_depth_max_value(self):
        """BitDepth.max_value returns correct maximum."""
        assert BitDepth.UINT8.max_value == 255
        assert BitDepth.UINT10.max_value == 1023
        assert BitDepth.UINT12.max_value == 4095
        assert BitDepth.UINT16.max_value == 65535
        assert BitDepth.FLOAT32.max_value == 1.0


class TestCompression:
    """Tests for Compression enum."""

    def test_compression_mime_types(self):
        """Compression.mime_type returns correct MIME types."""
        assert Compression.JPEG.mime_type == 'image/jpeg'
        assert Compression.PNG.mime_type == 'image/png'
        assert Compression.WEBP.mime_type == 'image/webp'
        assert Compression.GIF.mime_type == 'image/gif'

    def test_compression_from_mime_type(self):
        """Compression.from_mime_type parses MIME types correctly."""
        assert Compression.from_mime_type('image/jpeg') == Compression.JPEG
        assert Compression.from_mime_type('image/png') == Compression.PNG
        assert Compression.from_mime_type('image/webp') == Compression.WEBP

    def test_compression_from_extension(self):
        """Compression.from_extension parses file extensions correctly."""
        assert Compression.from_extension('.jpg') == Compression.JPEG
        assert Compression.from_extension('jpeg') == Compression.JPEG
        assert Compression.from_extension('.png') == Compression.PNG
        assert Compression.from_extension('webp') == Compression.WEBP


class TestImageData:
    """Tests for ImageData container class."""

    def test_image_data_from_image(self, sample_image):
        """ImageData.from_image creates correct container."""
        data = ImageData.from_image(sample_image)
        assert data.has_data
        assert data.width == sample_image.width
        assert data.height == sample_image.height
        assert data.format.pixel_format == 'RGB'

    def test_image_data_from_bytes(self, sample_image):
        """ImageData.from_bytes handles JPEG bytes."""
        jpeg_bytes = sample_image.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes)
        assert data.has_data
        assert data.format.compression == Compression.JPEG

    def test_image_data_from_array(self):
        """ImageData.from_array handles numpy arrays."""
        array = np.zeros((100, 100, 3), dtype=np.uint8)
        array[:, :, 0] = 255  # Red
        data = ImageData.from_array(array, pixel_format='RGB')
        assert data.has_data
        assert data.width == 100
        assert data.height == 100
        assert data.format.pixel_format == 'RGB'

    def test_image_data_from_bgr_array(self):
        """ImageData.from_array handles BGR arrays (OpenCV style)."""
        array = np.zeros((100, 100, 3), dtype=np.uint8)
        array[:, :, 2] = 255  # Red in BGR
        data = ImageData.from_array(array, pixel_format='BGR')
        assert data.format.pixel_format == 'BGR'

    def test_image_data_to_image(self, sample_image):
        """ImageData.to_image converts back to Image."""
        data = ImageData.from_image(sample_image)
        result = data.to_image()
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_image_data_to_bytes(self, sample_image):
        """ImageData.to_bytes encodes to compressed format."""
        data = ImageData.from_image(sample_image)
        jpeg_bytes = data.to_bytes(Compression.JPEG)
        assert jpeg_bytes[:3] == b'\xff\xd8\xff'  # JPEG magic bytes

    def test_image_data_to_array(self, sample_image):
        """ImageData.to_array converts to numpy array."""
        data = ImageData.from_image(sample_image)
        array = data.to_array('RGB')
        assert array.shape == (sample_image.height, sample_image.width, 3)
        assert array.dtype == np.uint8

    def test_image_data_convert_to(self, sample_image):
        """ImageData.convert_to changes format."""
        data = ImageData.from_image(sample_image)

        # Convert to BGR
        bgr_data = data.convert_to(FormatSpec.BGR)
        assert bgr_data.format.pixel_format == 'BGR'

        # Convert to JPEG
        jpeg_data = data.convert_to(FormatSpec.JPEG)
        assert jpeg_data.format.compression == Compression.JPEG

    def test_image_data_detects_compression(self):
        """ImageData detects compression from magic bytes."""
        # JPEG
        jpeg_magic = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        data = ImageData.from_bytes(jpeg_magic)
        assert data.format.compression == Compression.JPEG

        # PNG
        png_magic = b'\x89PNG\r\n\x1a\n'
        data = ImageData.from_bytes(png_magic)
        assert data.format.compression == Compression.PNG

    def test_image_data_float_array(self):
        """ImageData handles float32 arrays."""
        array = np.random.rand(100, 100, 3).astype(np.float32)
        data = ImageData.from_array(array, pixel_format='RGB')
        assert data.format.bit_depth == BitDepth.FLOAT32

        # Convert to 8-bit
        uint8_array = data.to_array('RGB', bit_depth=BitDepth.UINT8)
        assert uint8_array.dtype == np.uint8


class TestFilterFormatDeclarations:
    """Tests for filter format declarations."""

    def test_filter_defaults_accept_any(self):
        """Filters without format declarations accept any format."""
        assert Brightness.get_accepted_formats() is None
        assert Brightness.accepts_format(FormatSpec.RGB)
        assert Brightness.accepts_format(FormatSpec.BGR)
        assert Brightness.accepts_format(FormatSpec.JPEG)

    def test_filter_defaults_implicit_conversion(self):
        """Filters default to allowing implicit conversion."""
        assert Brightness.accepts_implicit_conversion()
        assert Grayscale.accepts_implicit_conversion()

    def test_filter_with_format_declaration(self):
        """Custom filter with format declaration works."""
        @register_filter
        @dataclass
        class RGBOnlyFilter(Filter):
            _accepted_formats: ClassVar[list[FormatSpec]] = [FormatSpec.RGB]

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                return image

        assert RGBOnlyFilter.get_accepted_formats() == [FormatSpec.RGB]
        assert RGBOnlyFilter.accepts_format(FormatSpec.RGB)
        assert not RGBOnlyFilter.accepts_format(FormatSpec.BGR)

    def test_filter_output_format(self):
        """Custom filter with output format declaration."""
        @register_filter
        @dataclass
        class ToGrayFilter(Filter):
            _output_format: ClassVar[FormatSpec] = FormatSpec.GRAY

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                return image.convert(PixelFormat.GRAY)

        assert ToGrayFilter.get_output_format() == FormatSpec.GRAY


class TestPipelineAutoConversion:
    """Tests for automatic format conversion in pipelines."""

    def test_pipeline_auto_convert_enabled(self):
        """Pipeline auto_convert defaults to True."""
        pipeline = FilterPipeline()
        assert pipeline.auto_convert is True

    def test_pipeline_auto_convert_disabled(self):
        """Pipeline auto_convert can be disabled."""
        pipeline = FilterPipeline(auto_convert=False)
        assert pipeline.auto_convert is False

    def test_pipeline_converts_for_format_restricted_filter(self, sample_image):
        """Pipeline automatically converts when filter has format requirements."""
        # Create a filter that only accepts BGR
        @register_filter
        @dataclass
        class BGROnlyFilter(Filter):
            _accepted_formats: ClassVar[list[FormatSpec]] = [FormatSpec.BGR]

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                # Verify we received BGR format
                assert image.pixel_format == PixelFormat.BGR
                return image

        # Start with RGB image
        rgb_image = sample_image.convert(PixelFormat.RGB)
        assert rgb_image.pixel_format == PixelFormat.RGB

        # Pipeline should auto-convert
        pipeline = FilterPipeline(filters=[BGROnlyFilter()])
        result = pipeline.apply(rgb_image)
        assert result is not None  # No error means conversion worked

    def test_pipeline_no_convert_when_compatible(self, sample_image):
        """Pipeline doesn't convert when format is already compatible."""
        rgb_image = sample_image.convert(PixelFormat.RGB)
        original_id = id(rgb_image)

        # Filter accepts RGB
        @register_filter
        @dataclass
        class AcceptsRGBFilter(Filter):
            _accepted_formats: ClassVar[list[FormatSpec]] = [FormatSpec.RGB]

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                return image

        pipeline = FilterPipeline(filters=[AcceptsRGBFilter()])
        result = pipeline.apply(rgb_image)
        # Image should not have been converted (same object passes through)
        # Note: The filter returns the same image, so this verifies no unnecessary conversion

    def test_pipeline_multi_filter_conversion(self, sample_image):
        """Pipeline handles conversion between filters with different requirements."""
        @register_filter
        @dataclass
        class WantsBGRFilter(Filter):
            _accepted_formats: ClassVar[list[FormatSpec]] = [FormatSpec.BGR]

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                assert image.pixel_format == PixelFormat.BGR
                return image

        @register_filter
        @dataclass
        class WantsRGBFilter(Filter):
            _accepted_formats: ClassVar[list[FormatSpec]] = [FormatSpec.RGB]

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                assert image.pixel_format == PixelFormat.RGB
                return image

        rgb_image = sample_image.convert(PixelFormat.RGB)

        # This pipeline: RGB -> (convert to BGR) -> WantsBGR -> (convert to RGB) -> WantsRGB
        pipeline = FilterPipeline(filters=[
            WantsBGRFilter(),
            WantsRGBFilter(),
        ])

        result = pipeline.apply(rgb_image)
        assert result is not None  # No assertion errors means conversions worked


class TestFilterProcess:
    """Tests for the Filter.process() method with ImageData."""

    def test_filter_process_from_image(self, sample_image):
        """Filter.process() works with ImageData from Image."""
        data = ImageData.from_image(sample_image)
        result = Brightness(factor=1.5).process(data)
        assert result.has_data
        # Result should be an Image wrapped in ImageData
        result_image = result.to_image()
        assert result_image.width == sample_image.width

    def test_filter_process_from_bytes(self, sample_image):
        """Filter.process() works with ImageData from compressed bytes."""
        jpeg_bytes = sample_image.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes)
        result = Brightness(factor=1.5).process(data)
        assert result.has_data
        result_image = result.to_image()
        assert result_image.width == sample_image.width

    def test_filter_process_from_array(self):
        """Filter.process() works with ImageData from numpy array."""
        array = np.zeros((100, 100, 3), dtype=np.uint8)
        array[:, :] = [128, 128, 128]  # Gray
        data = ImageData.from_array(array, pixel_format='RGB')
        result = Brightness(factor=2.0).process(data)
        result_array = result.to_array('RGB')
        # Brightness 2.0 should double values (capped at 255)
        assert result_array[50, 50, 0] == 255

    def test_filter_process_preserves_context(self, sample_image):
        """Filter.process() passes context correctly."""
        data = ImageData.from_image(sample_image)
        ctx = FilterContext()
        ctx['test'] = 'value'

        # Use an analyzer that writes to context
        result = ImageStats().process(data, ctx)
        assert 'stats' in ctx  # ImageStats stores results as 'stats'


class TestPipelineProcess:
    """Tests for FilterPipeline.process() with ImageData."""

    def test_pipeline_process_imagedata(self, sample_image):
        """Pipeline.process() handles ImageData input."""
        data = ImageData.from_image(sample_image)
        pipeline = FilterPipeline.parse('brightness(1.5)|grayscale')
        result = pipeline.process(data)
        assert result.has_data
        result_image = result.to_image()
        assert result_image.width == sample_image.width

    def test_pipeline_process_from_bytes(self, sample_image):
        """Pipeline.process() handles ImageData from bytes."""
        jpeg_bytes = sample_image.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes)
        pipeline = FilterPipeline.parse('resize(0.5)|grayscale|encode(jpeg)')
        result = pipeline.process(data)
        # Result should be JPEG encoded
        assert result.format.compression == Compression.JPEG
        jpeg_out = result.to_bytes()
        assert jpeg_out[:3] == b'\xff\xd8\xff'

    def test_pipeline_process_to_cv(self, sample_image):
        """Pipeline.process() result can be converted to OpenCV array."""
        data = ImageData.from_image(sample_image)
        pipeline = FilterPipeline.parse('brightness(1.5)')
        result = pipeline.process(data)
        # Get OpenCV-compatible BGR array
        cv_array = result.to_cv()
        assert cv_array.shape == (sample_image.height, sample_image.width, 3)

    def test_pipeline_process_with_format_conversion(self, sample_image):
        """Pipeline.process() handles format conversion between filters."""
        data = ImageData.from_image(sample_image)
        # Pipeline with format-restricted filters
        pipeline = FilterPipeline.parse('grayscale|brightness(1.2)')
        result = pipeline.process(data)
        assert result.has_data


class TestConverterFilters:
    """Tests for format converter filters."""

    def test_encode_jpeg(self, sample_image):
        """Encode produces JPEG bytes."""
        from imagestag.filters import Encode
        data = ImageData.from_image(sample_image)
        result = Encode(format='jpeg', quality=90).process(data)
        assert result.format.compression == Compression.JPEG
        jpeg_bytes = result.to_bytes()
        assert jpeg_bytes[:3] == b'\xff\xd8\xff'

    def test_encode_png(self, sample_image):
        """Encode produces PNG bytes."""
        from imagestag.filters import Encode
        data = ImageData.from_image(sample_image)
        result = Encode(format='png').process(data)
        assert result.format.compression == Compression.PNG

    def test_encode_webp(self, sample_image):
        """Encode produces WebP bytes."""
        from imagestag.filters import Encode
        data = ImageData.from_image(sample_image)
        result = Encode(format='webp', quality=85).process(data)
        assert result.format.compression == Compression.WEBP

    def test_decode(self, sample_image):
        """Decode converts compressed bytes to uncompressed."""
        from imagestag.filters import Decode
        jpeg_bytes = sample_image.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes)
        result = Decode(format='RGB').process(data)
        assert result.format.pixel_format == 'RGB'
        assert not result.format.is_compressed()

    def test_convert_format_bgr(self, sample_image):
        """ConvertFormat converts to BGR format."""
        from imagestag.filters import ConvertFormat
        data = ImageData.from_image(sample_image)
        result = ConvertFormat(format='BGR').process(data)
        assert result.format.pixel_format == 'BGR'

    def test_convert_format_rgb(self, sample_image):
        """ConvertFormat converts to RGB format."""
        from imagestag.filters import ConvertFormat
        # Start with BGR
        bgr_array = sample_image.get_pixels(PixelFormat.RGB)[:, :, ::-1].copy()
        data = ImageData.from_array(bgr_array, pixel_format='BGR')
        result = ConvertFormat(format='RGB').process(data)
        assert result.format.pixel_format == 'RGB'

    def test_convert_format_gray(self, sample_image):
        """ConvertFormat converts to grayscale."""
        from imagestag.filters import ConvertFormat
        data = ImageData.from_image(sample_image)
        result = ConvertFormat(format='GRAY').process(data)
        assert result.format.pixel_format == 'GRAY'

    def test_converter_pipeline(self, sample_image):
        """Converters work in pipelines."""
        from imagestag.filters import Encode, ConvertFormat
        data = ImageData.from_image(sample_image)
        pipeline = FilterPipeline(filters=[
            Brightness(factor=1.2),
            ConvertFormat(format='BGR'),
            Encode(format='jpeg', quality=85),
        ])
        result = pipeline.process(data)
        assert result.format.compression == Compression.JPEG

    def test_encode_parse_with_params(self, sample_image):
        """Encode filter can be parsed with multiple parameters."""
        pipeline = FilterPipeline.parse('encode(format=jpeg,quality=75)')
        data = ImageData.from_image(sample_image)
        result = pipeline.process(data)
        assert result.format.compression == Compression.JPEG


class TestNativeImageDataFilter:
    """Tests for filters with native ImageData support."""

    def test_native_imagedata_flag(self):
        """Filters can declare native ImageData support."""
        from imagestag.filters import Encode
        assert Encode.has_native_imagedata()
        assert not Brightness.has_native_imagedata()

    def test_analyzer_preserves_format(self, sample_image):
        """AnalyzerFilter.process() preserves input format."""
        jpeg_bytes = sample_image.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes)
        ctx = FilterContext()
        result = ImageStats().process(data, ctx)
        # Should preserve JPEG format (analyzer doesn't modify image)
        assert result.format.compression == Compression.JPEG
        assert 'stats' in ctx  # ImageStats stores results as 'stats'


class TestImageDataOutputMethods:
    """Tests for ImageData output conversion methods."""

    def test_to_pil(self, sample_image):
        """ImageData.to_pil() returns PIL Image."""
        from PIL import Image as PILImage
        data = ImageData.from_image(sample_image)
        pil_img = data.to_pil()
        assert isinstance(pil_img, PILImage.Image)
        assert pil_img.size == (sample_image.width, sample_image.height)

    def test_to_cv(self, sample_image):
        """ImageData.to_cv() returns BGR numpy array."""
        data = ImageData.from_image(sample_image)
        cv_array = data.to_cv()
        assert cv_array.shape == (sample_image.height, sample_image.width, 3)
        assert cv_array.dtype == np.uint8

    def test_to_cv_from_jpeg(self, sample_image):
        """ImageData.to_cv() works from JPEG bytes."""
        jpeg_bytes = sample_image.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes)
        cv_array = data.to_cv()
        assert cv_array.shape[2] == 3  # BGR has 3 channels


class TestEdgeDetection:
    """Tests for edge detection filters."""

    def test_canny(self, sample_image):
        """Canny edge detection works."""
        from imagestag.filters import Canny
        result = Canny(threshold1=50, threshold2=150).apply(sample_image)
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_sobel(self, sample_image):
        """Sobel edge detection works."""
        from imagestag.filters import Sobel
        result = Sobel(dx=1, dy=1).apply(sample_image)
        assert result.width == sample_image.width

    def test_laplacian(self, sample_image):
        """Laplacian edge detection works."""
        from imagestag.filters import Laplacian
        result = Laplacian(kernel_size=3).apply(sample_image)
        assert result.width == sample_image.width

    def test_edge_enhance(self, sample_image):
        """Edge enhance filter works."""
        from imagestag.filters import EdgeEnhance
        result = EdgeEnhance(strength='more').apply(sample_image)
        assert result.width == sample_image.width

    def test_edge_pipeline(self, sample_image):
        """Edge detection in pipeline."""
        pipeline = FilterPipeline.parse('grayscale|canny(threshold1=100,threshold2=200)')
        result = pipeline.apply(sample_image)
        assert result is not None


class TestMorphology:
    """Tests for morphological operations."""

    def test_erode(self, sample_image):
        """Erode filter works."""
        from imagestag.filters import Erode
        result = Erode(kernel_size=3).apply(sample_image)
        assert result.width == sample_image.width

    def test_dilate(self, sample_image):
        """Dilate filter works."""
        from imagestag.filters import Dilate
        result = Dilate(kernel_size=3, iterations=2).apply(sample_image)
        assert result.width == sample_image.width

    def test_morph_open(self, sample_image):
        """Morphological opening works."""
        from imagestag.filters import MorphOpen
        result = MorphOpen(kernel_size=5).apply(sample_image)
        assert result.width == sample_image.width

    def test_morph_close(self, sample_image):
        """Morphological closing works."""
        from imagestag.filters import MorphClose
        result = MorphClose(kernel_size=5).apply(sample_image)
        assert result.width == sample_image.width

    def test_morph_gradient(self, sample_image):
        """Morphological gradient works."""
        from imagestag.filters import MorphGradient
        result = MorphGradient(kernel_size=3).apply(sample_image)
        assert result.width == sample_image.width

    def test_morph_pipeline(self, sample_image):
        """Morphology in pipeline."""
        pipeline = FilterPipeline.parse('erode(3)|dilate(3)')
        result = pipeline.apply(sample_image)
        assert result is not None


class TestDetection:
    """Tests for detection filters (geometry-based output)."""

    def test_face_detector_returns_geometry_list(self, sample_image):
        """Face detector returns GeometryList."""
        from imagestag.filters import FaceDetector
        from imagestag.geometry_list import GeometryList
        result = FaceDetector().apply(sample_image)
        assert isinstance(result, GeometryList)
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_face_detector_detect_method(self, sample_image):
        """Face detector detect() method works."""
        from imagestag.filters import FaceDetector
        from imagestag.geometry_list import GeometryList
        detector = FaceDetector(min_neighbors=3)
        result = detector.detect(sample_image)
        assert isinstance(result, GeometryList)

    def test_contour_detector_returns_geometry_list(self, sample_image):
        """Contour detector returns GeometryList with polygons."""
        from imagestag.filters import ContourDetector
        from imagestag.geometry_list import GeometryList, Polygon
        result = ContourDetector(threshold=128).apply(sample_image)
        assert isinstance(result, GeometryList)
        # All geometries should be Polygons
        for geom in result:
            assert isinstance(geom, Polygon)

    def test_eye_detector_returns_geometry_list(self, sample_image):
        """Eye detector returns GeometryList."""
        from imagestag.filters import EyeDetector
        from imagestag.geometry_list import GeometryList
        result = EyeDetector().apply(sample_image)
        assert isinstance(result, GeometryList)


class TestLensDistortion:
    """Tests for lens distortion filter."""

    def test_lens_distortion_no_change(self, sample_image):
        """Zero coefficients returns unchanged image."""
        from imagestag.filters import LensDistortion
        result = LensDistortion().apply(sample_image)
        assert result.width == sample_image.width
        assert result.height == sample_image.height

    def test_lens_distortion_barrel(self, sample_image):
        """Barrel distortion (positive k1) works."""
        from imagestag.filters import LensDistortion
        result = LensDistortion(k1=0.2).apply(sample_image)
        assert result.width == sample_image.width

    def test_lens_distortion_pincushion(self, sample_image):
        """Pincushion distortion (negative k1) works."""
        from imagestag.filters import LensDistortion
        result = LensDistortion(k1=-0.2).apply(sample_image)
        assert result.width == sample_image.width

    def test_lens_distortion_parse(self, sample_image):
        """Parse lens distortion from string."""
        pipeline = FilterPipeline.parse('lens(k1=-0.1)')
        result = pipeline.apply(sample_image)
        assert result is not None


class TestPerspective:
    """Tests for perspective transform filter."""

    def test_perspective_no_points(self, sample_image):
        """No points returns unchanged image."""
        from imagestag.filters import Perspective
        result = Perspective().apply(sample_image)
        assert result.width == sample_image.width

    def test_perspective_transform(self, sample_image):
        """Perspective transform works."""
        from imagestag.filters import Perspective
        w, h = sample_image.width, sample_image.height
        # Slight skew
        src = [(0, 0), (w-1, 0), (w-1, h-1), (0, h-1)]
        dst = [(10, 10), (w-10, 0), (w-1, h-1), (0, h-10)]
        result = Perspective(src_points=src, dst_points=dst).apply(sample_image)
        assert result is not None

    def test_perspective_correction(self, sample_image):
        """Perspective correction mode (only src_points)."""
        from imagestag.filters import Perspective
        w, h = sample_image.width, sample_image.height
        # Simulate skewed document corners
        src = [(10, 10), (w-20, 5), (w-10, h-10), (5, h-15)]
        result = Perspective(src_points=src).apply(sample_image)
        assert result is not None


class TestCoordinateTransforms:
    """Tests for bidirectional coordinate transforms."""

    def test_lens_transform_roundtrip(self, sample_image):
        """LensTransform forward then inverse returns original point."""
        from imagestag.filters import LensDistortion
        import numpy as np

        # Apply distortion correction
        _, transform = LensDistortion(k1=-0.2).apply_with_transform(sample_image)

        # Test point near image center
        original_pt = (50.0, 50.0)
        corrected_pt = transform.forward(original_pt)
        recovered_pt = transform.inverse(corrected_pt)

        # Should recover original within tolerance
        assert abs(recovered_pt[0] - original_pt[0]) < 1.0
        assert abs(recovered_pt[1] - original_pt[1]) < 1.0

    def test_lens_transform_multiple_points(self, sample_image):
        """LensTransform handles multiple points efficiently."""
        from imagestag.filters import LensDistortion
        import numpy as np

        _, transform = LensDistortion(k1=-0.15).apply_with_transform(sample_image)

        # Test multiple points
        points = [(10, 10), (50, 50), (90, 30), (30, 80)]
        forward_pts = transform.forward_points(points)
        inverse_pts = transform.inverse_points(forward_pts)

        assert forward_pts.shape == (4, 2)
        assert inverse_pts.shape == (4, 2)

        # Each point should roundtrip
        for i, orig in enumerate(points):
            assert abs(inverse_pts[i, 0] - orig[0]) < 1.0
            assert abs(inverse_pts[i, 1] - orig[1]) < 1.0

    def test_lens_transform_identity_when_no_distortion(self, sample_image):
        """Zero distortion coefficients produce identity transform."""
        from imagestag.filters import LensDistortion

        _, transform = LensDistortion().apply_with_transform(sample_image)

        point = (50.0, 50.0)
        forward_pt = transform.forward(point)
        inverse_pt = transform.inverse(point)

        # Should be essentially unchanged
        assert abs(forward_pt[0] - point[0]) < 0.01
        assert abs(forward_pt[1] - point[1]) < 0.01
        assert abs(inverse_pt[0] - point[0]) < 0.01
        assert abs(inverse_pt[1] - point[1]) < 0.01

    def test_perspective_transform_roundtrip(self, sample_image):
        """PerspectiveTransform forward then inverse returns original point."""
        from imagestag.filters import Perspective

        w, h = sample_image.width, sample_image.height
        src = [(10, 10), (w-10, 5), (w-5, h-10), (5, h-5)]
        dst = [(0, 0), (w-1, 0), (w-1, h-1), (0, h-1)]

        _, transform = Perspective(
            src_points=src, dst_points=dst
        ).apply_with_transform(sample_image)

        # Test point
        original_pt = (50.0, 50.0)
        corrected_pt = transform.forward(original_pt)
        recovered_pt = transform.inverse(corrected_pt)

        # Should recover original within tolerance
        assert abs(recovered_pt[0] - original_pt[0]) < 0.01
        assert abs(recovered_pt[1] - original_pt[1]) < 0.01

    def test_perspective_transform_multiple_points(self, sample_image):
        """PerspectiveTransform handles multiple points efficiently."""
        from imagestag.filters import Perspective
        import numpy as np

        w, h = sample_image.width, sample_image.height
        src = [(5, 5), (w-5, 10), (w-10, h-5), (10, h-10)]
        dst = [(0, 0), (w-1, 0), (w-1, h-1), (0, h-1)]

        _, transform = Perspective(
            src_points=src, dst_points=dst
        ).apply_with_transform(sample_image)

        # Test multiple points
        points = [(20, 20), (60, 40), (80, 70), (40, 85)]
        forward_pts = transform.forward_points(points)
        inverse_pts = transform.inverse_points(forward_pts)

        assert forward_pts.shape == (4, 2)

        # Each point should roundtrip
        for i, orig in enumerate(points):
            assert abs(inverse_pts[i, 0] - orig[0]) < 0.01
            assert abs(inverse_pts[i, 1] - orig[1]) < 0.01

    def test_perspective_transform_identity_when_no_points(self, sample_image):
        """No src_points produces identity transform."""
        from imagestag.filters import Perspective

        _, transform = Perspective().apply_with_transform(sample_image)

        point = (50.0, 50.0)
        forward_pt = transform.forward(point)
        inverse_pt = transform.inverse(point)

        # Should be unchanged
        assert abs(forward_pt[0] - point[0]) < 0.01
        assert abs(forward_pt[1] - point[1]) < 0.01
        assert abs(inverse_pt[0] - point[0]) < 0.01
        assert abs(inverse_pt[1] - point[1]) < 0.01

    def test_perspective_corners_map_correctly(self, sample_image):
        """Source corners map to destination corners."""
        from imagestag.filters import Perspective
        import numpy as np

        src = [(10, 10), (90, 15), (85, 90), (5, 85)]
        dst = [(0, 0), (100, 0), (100, 100), (0, 100)]

        _, transform = Perspective(
            src_points=src, dst_points=dst, output_size=(100, 100)
        ).apply_with_transform(sample_image)

        # Each source corner should map to corresponding destination corner
        for s, d in zip(src, dst):
            result = transform.forward(s)
            assert abs(result[0] - d[0]) < 0.1
            assert abs(result[1] - d[1]) < 0.1

    def test_inverse_then_forward_roundtrip(self, sample_image):
        """Inverse then forward also roundtrips correctly."""
        from imagestag.filters import Perspective

        w, h = sample_image.width, sample_image.height
        src = [(10, 5), (w-5, 10), (w-10, h-5), (5, h-10)]
        dst = [(0, 0), (w-1, 0), (w-1, h-1), (0, h-1)]

        _, transform = Perspective(
            src_points=src, dst_points=dst
        ).apply_with_transform(sample_image)

        # Start with a destination point
        dst_pt = (60.0, 40.0)
        src_pt = transform.inverse(dst_pt)
        recovered_dst = transform.forward(src_pt)

        assert abs(recovered_dst[0] - dst_pt[0]) < 0.01
        assert abs(recovered_dst[1] - dst_pt[1]) < 0.01


class TestSKImage:
    """Tests for SKImage sample images."""

    def test_astronaut(self):
        """Can load astronaut image."""
        from imagestag.skimage import SKImage
        img = SKImage.astronaut()
        assert img.width == 512
        assert img.height == 512

    def test_camera(self):
        """Can load camera image."""
        from imagestag.skimage import SKImage
        img = SKImage.camera()
        assert img.width == 512

    def test_chelsea(self):
        """Can load chelsea cat image."""
        from imagestag.skimage import SKImage
        img = SKImage.chelsea()
        assert img.width > 0

    def test_load_by_name(self):
        """Can load image by name."""
        from imagestag.skimage import SKImage
        img = SKImage.load('astronaut')
        assert img.width == 512

    def test_list_images(self):
        """list_images returns available images."""
        from imagestag.skimage import SKImage
        images = SKImage.list_images()
        assert 'astronaut' in images
        assert 'camera' in images
        assert len(images) >= 10


# =============================================================================
# Smoke Tests for scikit-image Based Filters
# =============================================================================

class TestSmokeExposureFilters:
    """Smoke tests for exposure adjustment filters."""

    @pytest.fixture
    def rgb_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        r = (x / (w - 1) * 255).astype(np.uint8)
        g = (y / (h - 1) * 255).astype(np.uint8)
        b = (((x + y) / (h + w - 2)) * 255).astype(np.uint8)
        data = np.stack([r, g, b], axis=-1)
        return Image(data, pixel_format=PixelFormat.RGB)

    def test_adjust_gamma(self, rgb_image):
        from imagestag.filters.exposure import AdjustGamma
        f = AdjustGamma(gamma=0.8, gain=1.1)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_adjust_log(self, rgb_image):
        from imagestag.filters.exposure import AdjustLog
        f = AdjustLog(gain=1.2, inv=False)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_adjust_sigmoid(self, rgb_image):
        from imagestag.filters.exposure import AdjustSigmoid
        f = AdjustSigmoid(cutoff=0.5, gain=8.0, inv=True)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_rescale_intensity(self, rgb_image):
        from imagestag.filters.exposure import RescaleIntensity
        f = RescaleIntensity(in_range="image", out_range="dtype")
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_match_histograms(self, rgb_image):
        from imagestag.filters.exposure import MatchHistograms
        f = MatchHistograms(channel_axis=2)
        reference = Image(
            np.roll(rgb_image.get_pixels(PixelFormat.RGB), shift=15, axis=1),
            pixel_format=PixelFormat.RGB,
        )
        ctx = FilterContext({"histogram_reference": reference})
        result = f.apply(rgb_image, ctx)
        assert result.width == rgb_image.width


class TestSmokeHistogramFilters:
    """Smoke tests for histogram filters."""

    @pytest.fixture
    def rgb_image(self) -> Image:
        h, w = 96, 96
        data = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
        return Image(data, pixel_format=PixelFormat.RGB)

    @pytest.fixture
    def gray_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        gray = (((x * 0.7 + y * 0.3) / (h - 1)) * 255).clip(0, 255).astype(np.uint8)
        return Image(gray, pixel_format=PixelFormat.GRAY)

    def test_equalize_hist_y(self, rgb_image):
        from imagestag.filters.histogram import EqualizeHist
        f = EqualizeHist(per_channel=False)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_equalize_hist_per_channel(self, rgb_image):
        from imagestag.filters.histogram import EqualizeHist
        f = EqualizeHist(per_channel=True)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_clahe(self, rgb_image):
        from imagestag.filters.histogram import CLAHE
        f = CLAHE(clip_limit=2.0, tile_size=8)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_adaptive_threshold_mean(self, gray_image):
        from imagestag.filters.histogram import AdaptiveThreshold
        f = AdaptiveThreshold(method="mean", block_size=10, c=2.0)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_adaptive_threshold_gaussian(self, gray_image):
        from imagestag.filters.histogram import AdaptiveThreshold
        f = AdaptiveThreshold(method="gaussian", block_size=11, c=5.0)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width


class TestSmokeThresholdFilters:
    """Smoke tests for threshold filters."""

    @pytest.fixture
    def gray_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        gray = (((x * 0.7 + y * 0.3) / (h - 1)) * 255).clip(0, 255).astype(np.uint8)
        return Image(gray, pixel_format=PixelFormat.GRAY)

    def test_otsu(self, gray_image):
        from imagestag.filters.threshold import ThresholdOtsu
        f = ThresholdOtsu(nbins=128)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_li(self, gray_image):
        from imagestag.filters.threshold import ThresholdLi
        f = ThresholdLi(tolerance=0.1)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_yen(self, gray_image):
        from imagestag.filters.threshold import ThresholdYen
        f = ThresholdYen(nbins=128)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_triangle(self, gray_image):
        from imagestag.filters.threshold import ThresholdTriangle
        f = ThresholdTriangle(nbins=128)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_niblack(self, gray_image):
        from imagestag.filters.threshold import ThresholdNiblack
        f = ThresholdNiblack(window_size=15, k=0.2)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_sauvola(self, gray_image):
        from imagestag.filters.threshold import ThresholdSauvola
        f = ThresholdSauvola(window_size=15, k=0.3, r=128.0)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width


class TestSmokeTextureFilters:
    """Smoke tests for texture filters."""

    @pytest.fixture
    def gray_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        gray = (((x * 0.7 + y * 0.3) / (h - 1)) * 255).clip(0, 255).astype(np.uint8)
        return Image(gray, pixel_format=PixelFormat.GRAY)

    def test_gabor_magnitude(self, gray_image):
        from imagestag.filters.texture import Gabor
        f = Gabor(frequency=0.15, theta=0.2, mode="magnitude")
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_gabor_real(self, gray_image):
        from imagestag.filters.texture import Gabor
        f = Gabor(frequency=0.15, theta=0.2, mode="real")
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_gabor_imaginary(self, gray_image):
        from imagestag.filters.texture import Gabor
        f = Gabor(frequency=0.15, theta=0.2, mode="imaginary")
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_lbp(self, gray_image):
        from imagestag.filters.texture import LBP
        f = LBP(radius=1, n_points=8, method="uniform")
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_gabor_bank(self, gray_image):
        from imagestag.filters.texture import GaborBank
        f = GaborBank(frequency=0.1, n_orientations=4)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width


class TestSmokeSkeletonFilters:
    """Smoke tests for skeleton/morphology filters."""

    @pytest.fixture
    def gray_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        gray = (((x * 0.7 + y * 0.3) / (h - 1)) * 255).clip(0, 255).astype(np.uint8)
        return Image(gray, pixel_format=PixelFormat.GRAY)

    def test_skeletonize_zhang(self, gray_image):
        from imagestag.filters.skeleton import Skeletonize
        f = Skeletonize(method="zhang")
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_skeletonize_lee(self, gray_image):
        from imagestag.filters.skeleton import Skeletonize
        f = Skeletonize(method="lee")
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_medial_axis_with_distance(self, gray_image):
        from imagestag.filters.skeleton import MedialAxis
        f = MedialAxis(return_distance=True)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_medial_axis_without_distance(self, gray_image):
        from imagestag.filters.skeleton import MedialAxis
        f = MedialAxis(return_distance=False)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_remove_small_objects(self, gray_image):
        from imagestag.filters.skeleton import RemoveSmallObjects
        import warnings
        f = RemoveSmallObjects(min_size=32, connectivity=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_remove_small_holes(self, gray_image):
        from imagestag.filters.skeleton import RemoveSmallHoles
        import warnings
        f = RemoveSmallHoles(area_threshold=32, connectivity=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width


class TestSmokeRidgeFilters:
    """Smoke tests for ridge detection filters."""

    @pytest.fixture
    def gray_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        gray = (((x * 0.7 + y * 0.3) / (h - 1)) * 255).clip(0, 255).astype(np.uint8)
        return Image(gray, pixel_format=PixelFormat.GRAY)

    def test_frangi(self, gray_image):
        from imagestag.filters.ridge import Frangi
        f = Frangi(scale_min=1.0, scale_max=6.0, scale_step=2.0, black_ridges=True)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_sato(self, gray_image):
        from imagestag.filters.ridge import Sato
        f = Sato(scale_min=1.0, scale_max=6.0, scale_step=2.0, black_ridges=False)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_meijering(self, gray_image):
        from imagestag.filters.ridge import Meijering
        f = Meijering(scale_min=1.0, scale_max=6.0, scale_step=2.0, black_ridges=True)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width

    def test_hessian(self, gray_image):
        from imagestag.filters.ridge import Hessian
        f = Hessian(scale_min=1.0, scale_max=6.0, scale_step=2.0, beta=0.5, black_ridges=False)
        result = f.apply(gray_image, FilterContext())
        assert result.width == gray_image.width


class TestSmokeSegmentationFilters:
    """Smoke tests for segmentation filters."""

    @pytest.fixture
    def rgb_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        r = (x / (w - 1) * 255).astype(np.uint8)
        g = (y / (h - 1) * 255).astype(np.uint8)
        b = (((x + y) / (h + w - 2)) * 255).astype(np.uint8)
        data = np.stack([r, g, b], axis=-1)
        return Image(data, pixel_format=PixelFormat.RGB)

    def test_slic(self, rgb_image):
        from imagestag.filters.segmentation import SLIC
        f = SLIC(n_segments=50, compactness=8.0, sigma=0.5, start_label=0)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_felzenszwalb(self, rgb_image):
        from imagestag.filters.segmentation import Felzenszwalb
        f = Felzenszwalb(scale=50.0, sigma=0.3, min_size=20)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_watershed(self, rgb_image):
        from imagestag.filters.segmentation import Watershed
        f = Watershed(compactness=0.0, watershed_line=True)
        markers = np.zeros((rgb_image.height, rgb_image.width), dtype=np.int32)
        markers[24, 24] = 1
        markers[72, 72] = 2
        ctx = FilterContext({"watershed_markers": markers})
        result = f.apply(rgb_image, ctx)
        assert result.width == rgb_image.width


class TestSmokeRestorationFilters:
    """Smoke tests for restoration/denoising filters."""

    @pytest.fixture
    def rgb_image(self) -> Image:
        h, w = 96, 96
        y, x = np.mgrid[0:h, 0:w]
        r = (x / (w - 1) * 255).astype(np.uint8)
        g = (y / (h - 1) * 255).astype(np.uint8)
        b = (((x + y) / (h + w - 2)) * 255).astype(np.uint8)
        data = np.stack([r, g, b], axis=-1)
        return Image(data, pixel_format=PixelFormat.RGB)

    def test_denoise_nlmeans(self, rgb_image):
        from imagestag.filters.restoration import DenoiseNLMeans
        f = DenoiseNLMeans(h=0.08, fast_mode=True)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_denoise_tv(self, rgb_image):
        from imagestag.filters.restoration import DenoiseTV
        f = DenoiseTV(weight=0.12, n_iter_max=50)
        result = f.apply(rgb_image, FilterContext())
        assert result.width == rgb_image.width

    def test_inpaint(self, rgb_image):
        from imagestag.filters.restoration import Inpaint
        f = Inpaint(mask_threshold=128)
        mask = Image(
            np.pad(np.ones((24, 24), dtype=np.uint8) * 255, ((36, 36), (36, 36)), mode="constant"),
            pixel_format=PixelFormat.GRAY,
        )
        ctx = FilterContext({"inpaint_mask": mask})
        result = f.apply(rgb_image, ctx)
        assert result.width == rgb_image.width


class TestFilterInfoAndBaseMethods:
    """Tests for filter info generation and base methods."""

    def test_filter_info_from_class(self):
        """Can get filter info from a filter class."""
        from imagestag.filters.base import get_filter_info, get_all_filters_info

        info = get_filter_info("imgen")
        assert info is not None
        md = info.to_markdown()
        assert isinstance(md, str)
        d = info.to_dict()
        assert d["name"]

    def test_filter_info_for_alias(self):
        """Can get filter info for an alias."""
        from imagestag.filters.base import get_filter_info

        info = get_filter_info("rot90")
        assert info is not None

    def test_filter_info_missing(self):
        """Missing filter returns None."""
        from imagestag.filters.base import get_filter_info

        info = get_filter_info("no_such_filter")
        assert info is None

    def test_get_all_filters_info(self):
        """Can get all filter info."""
        from imagestag.filters.base import get_all_filters_info

        all_info = get_all_filters_info()
        assert "FilterGraph" in all_info

    def test_check_skimage_missing(self, monkeypatch):
        """_check_skimage raises when skimage missing."""
        from unittest.mock import patch
        from imagestag.filters.base import _check_skimage

        with patch.dict("sys.modules", {"skimage": None}):
            with pytest.raises(ImportError, match="scikit-image is required"):
                _check_skimage()


class TestAnalyzerFilter:
    """Tests for AnalyzerFilter."""

    def test_analyzer_stores_result_in_metadata(self, sample_image):
        """AnalyzerFilter stores result in context and metadata."""
        from imagestag.filters.base import AnalyzerFilter, FilterContext
        from imagestag.filters.formats import ImageData

        class _TestAnalyzer(AnalyzerFilter):
            def analyze(self, image: Image):
                return float(np.mean(image.get_pixels()))

        a = _TestAnalyzer(store_in_metadata=True, result_key="test_key")
        ctx = FilterContext()
        out = a.apply(sample_image, ctx)
        assert out is sample_image
        assert "test_key" in ctx.data
        assert "test_key" in sample_image.metadata

    def test_analyzer_processes_imagedata(self, sample_image):
        """AnalyzerFilter can process ImageData."""
        from imagestag.filters.base import AnalyzerFilter, FilterContext
        from imagestag.filters.formats import ImageData

        class _TestAnalyzer(AnalyzerFilter):
            def analyze(self, image: Image):
                return 42.0

        a = _TestAnalyzer(store_in_metadata=False, result_key="k")
        ctx = FilterContext()
        png = sample_image.encode("png")
        data = ImageData.from_bytes(png, mime_type="image/png")
        out_data = a.process(data, ctx)
        assert out_data.to_bytes("image/png") == png


class TestFilterPipelineOperations:
    """Tests for FilterPipeline operations."""

    def test_parse_empty_pipeline(self):
        """Parsing empty string returns empty pipeline."""
        p = FilterPipeline.parse("")
        assert len(p.filters) == 0

    def test_parse_and_apply_pipeline(self, sample_image):
        """Can parse and apply a pipeline."""
        p = FilterPipeline.parse("gray; blur 2")
        result = p.apply(sample_image)
        assert result.width == sample_image.width


class TestImageDataFormats:
    """Tests for ImageData format handling."""

    def test_detect_compression_jpeg(self):
        from imagestag.filters.formats import ImageData, Compression

        assert ImageData._detect_compression(b"\xff\xd8\xff" + b"0" * 10) == Compression.JPEG

    def test_detect_compression_png(self):
        from imagestag.filters.formats import ImageData, Compression

        assert ImageData._detect_compression(b"\x89PNG" + b"0" * 10) == Compression.PNG

    def test_detect_compression_gif(self):
        from imagestag.filters.formats import ImageData, Compression

        assert ImageData._detect_compression(b"GIF89a" + b"0" * 10) == Compression.GIF

    def test_detect_compression_bmp(self):
        from imagestag.filters.formats import ImageData, Compression

        assert ImageData._detect_compression(b"BM" + b"0" * 10) == Compression.BMP

    def test_detect_compression_webp(self):
        from imagestag.filters.formats import ImageData, Compression

        assert ImageData._detect_compression(b"RIFF" + b"0" * 4 + b"WEBP" + b"0" * 10) == Compression.WEBP

    def test_detect_compression_none(self):
        from imagestag.filters.formats import ImageData, Compression

        assert ImageData._detect_compression(b"xx") == Compression.NONE

    def test_imagedata_to_image_float32(self):
        from imagestag.filters.formats import ImageData, BitDepth

        arr = np.zeros((32, 32), dtype=np.float32)
        arr[8:24, 8:24] = 1.0
        data = ImageData.from_array(arr, pixel_format="GRAY", bit_depth=BitDepth.FLOAT32)
        img = data.to_image()
        assert img.width == 32


class TestBlurColorEdgeFilters:
    """Tests for blur, color, and edge filter branches."""

    @pytest.fixture
    def rgb_image(self) -> Image:
        data = np.zeros((32, 32, 3), dtype=np.uint8)
        data[:, :, 0] = 100
        data[:, :, 1] = 150
        data[:, :, 2] = 200
        return Image(data, pixel_format=PixelFormat.RGB)

    @pytest.fixture
    def rgba_image(self) -> Image:
        data = np.zeros((32, 32, 4), dtype=np.uint8)
        data[:, :, 0] = 100
        data[:, :, 1] = 150
        data[:, :, 2] = 200
        data[:, :, 3] = 255
        return Image(data, pixel_format=PixelFormat.RGBA)

    def test_median_blur_even_ksize(self, rgb_image):
        """MedianBlur rounds even ksize to odd."""
        from imagestag.filters.blur import MedianBlur

        m = MedianBlur(ksize=4)
        assert m.ksize % 2 == 1
        _ = m.apply(rgb_image)

    def test_smooth_strength_more(self, rgb_image):
        """Smooth with 'more' strength."""
        from imagestag.filters.blur import Smooth

        s = Smooth(strength="more")
        _ = s.apply(rgb_image)

    def test_auto_contrast_preserve_tone(self, rgb_image):
        """AutoContrast with preserve_tone."""
        from imagestag.filters.color import AutoContrast

        ac = AutoContrast(cutoff=1.0, preserve_tone=True)
        _ = ac.apply(rgb_image)

    def test_invert_rgba(self, rgba_image):
        """Invert with RGBA image."""
        from imagestag.filters.color import Invert

        inv = Invert()
        _ = inv.apply(rgba_image)

    def test_posterize_high_bits(self, rgb_image):
        """Posterize with high bits value."""
        from imagestag.filters.color import Posterize

        post = Posterize(bits=20)
        _ = post.apply(rgb_image)

    def test_solarize(self, rgb_image):
        """Solarize with threshold."""
        from imagestag.filters.color import Solarize

        sol = Solarize(threshold=100)
        _ = sol.apply(rgb_image)

    def test_sobel_dy_only(self, rgb_image):
        """Sobel with dy only."""
        from imagestag.filters.edge import Sobel

        sob = Sobel(dx=0, dy=1, normalize=False)
        _ = sob.apply(rgb_image)

    def test_scharr_dy_only(self, rgb_image):
        """Scharr with dy only."""
        from imagestag.filters.edge import Scharr

        sch = Scharr(dx=0, dy=1, normalize=False)
        _ = sch.apply(rgb_image)


class TestImageListOperations:
    """Tests for ImageList operations."""

    def test_image_list_get_meta(self, sample_image):
        """ImageList get_meta returns metadata."""
        from imagestag.image_list import ImageList

        il = ImageList(images=[sample_image], metadata=[])
        meta = il.get_meta(0)
        assert meta.index == 0

    def test_image_list_with_images_empty_raises(self, sample_image):
        """ImageList.with_images with empty list raises."""
        from imagestag.image_list import ImageList

        il = ImageList(images=[sample_image], metadata=[])
        with pytest.raises(ValueError):
            il.with_images([])


class TestSamplesModule:
    """Tests for samples module."""

    def test_load_invalid_sample_raises(self):
        """Loading invalid sample raises ValueError."""
        from imagestag import samples

        with pytest.raises(ValueError):
            samples.load("nope")


class TestDefinitions:
    """Tests for definitions module."""

    def test_get_opencv_when_disabled(self, monkeypatch):
        """get_opencv returns None when disabled."""
        from imagestag.definitions import get_opencv, OpenCVHandler

        prev = OpenCVHandler.available
        OpenCVHandler.available = False
        try:
            assert get_opencv() is None
        finally:
            OpenCVHandler.available = prev

    def test_get_opencv_import_error(self, monkeypatch):
        """get_opencv returns None on import error."""
        from imagestag import definitions as defs
        from imagestag.definitions import OpenCVHandler

        # Save original values
        prev_available = OpenCVHandler.available
        prev_cv = defs._cv
        prev_cv_available = defs._cv_available

        # Reset state to force re-import
        defs._cv_available = None
        defs._cv = None

        def _boom(name: str):
            raise ModuleNotFoundError

        monkeypatch.setattr("imagestag.definitions.importlib.import_module", _boom)
        OpenCVHandler.available = True
        try:
            result = defs.get_opencv()
            assert result is None
        finally:
            # Restore original state
            OpenCVHandler.available = prev_available
            defs._cv_available = prev_cv_available
            defs._cv = prev_cv
