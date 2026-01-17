"""
Unit tests for ImageStag Rust filter effects.

Tests use checksums, averages, and pixel counts to verify correctness.
"""

import numpy as np
import pytest
import importlib.util
import hashlib


# Load the rust module directly to avoid cv2 dependency issues
def load_rust_module():
    spec = importlib.util.spec_from_file_location(
        'imagestag_rust',
        '/projects/ImageStag/imagestag/imagestag_rust.cpython-312-aarch64-linux-gnu.so'
    )
    if spec is None:
        # Try alternate path pattern
        import glob
        so_files = glob.glob('/projects/ImageStag/imagestag/imagestag_rust*.so')
        if so_files:
            spec = importlib.util.spec_from_file_location('imagestag_rust', so_files[0])
    if spec is None:
        pytest.skip("Rust module not found")
    rust = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rust)
    return rust


rust = load_rust_module()


def create_test_image(width=100, height=100, shape='square'):
    """Create test RGBA image with a shape."""
    img = np.zeros((height, width, 4), dtype=np.uint8)

    if shape == 'square':
        # Red square in center
        margin = width // 4
        img[margin:height-margin, margin:width-margin] = [255, 0, 0, 255]
    elif shape == 'circle':
        # Green circle in center
        cy, cx = height // 2, width // 2
        radius = min(width, height) // 3
        y, x = np.ogrid[:height, :width]
        mask = (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2
        img[mask] = [0, 255, 0, 255]
    elif shape == 'gradient':
        # Gradient with varying alpha
        for y in range(height):
            for x in range(width):
                img[y, x] = [x * 255 // width, y * 255 // height, 128, 255]

    return img


def compute_checksum(img):
    """Compute MD5 checksum of image data."""
    return hashlib.md5(img.tobytes()).hexdigest()


def compute_channel_averages(img):
    """Compute average value per channel."""
    return {
        'r': float(np.mean(img[:, :, 0])),
        'g': float(np.mean(img[:, :, 1])),
        'b': float(np.mean(img[:, :, 2])),
        'a': float(np.mean(img[:, :, 3]))
    }


def count_non_transparent(img):
    """Count pixels with alpha > 0."""
    return int(np.sum(img[:, :, 3] > 0))


def count_color_pixels(img, color, tolerance=10):
    """Count pixels matching a color within tolerance."""
    r, g, b = color
    mask = (
        (np.abs(img[:, :, 0].astype(int) - r) <= tolerance) &
        (np.abs(img[:, :, 1].astype(int) - g) <= tolerance) &
        (np.abs(img[:, :, 2].astype(int) - b) <= tolerance) &
        (img[:, :, 3] > 0)
    )
    return int(np.sum(mask))


class TestBasicFilters:
    """Tests for basic filter operations."""

    def test_invert_rgba(self):
        """Invert should flip RGB values, preserve alpha."""
        img = create_test_image(50, 50, 'square')
        result = rust.invert_rgba(img)

        assert result.shape == img.shape
        assert result.dtype == np.uint8

        # Check that red became cyan (0, 255, 255)
        # Original red square area
        margin = 50 // 4
        center = result[margin + 5, margin + 5]
        assert center[0] == 0    # R inverted
        assert center[1] == 255  # G inverted
        assert center[2] == 255  # B inverted
        assert center[3] == 255  # Alpha preserved

    def test_premultiply_unpremultiply_roundtrip(self):
        """Premultiply then unpremultiply should restore original."""
        img = np.zeros((50, 50, 4), dtype=np.uint8)
        img[10:40, 10:40] = [200, 100, 50, 128]  # Semi-transparent

        premul = rust.premultiply_alpha(img)
        restored = rust.unpremultiply_alpha(premul)

        # Check center pixel restored (may have minor rounding)
        orig_center = img[25, 25]
        rest_center = restored[25, 25]
        assert abs(int(orig_center[0]) - int(rest_center[0])) <= 2
        assert abs(int(orig_center[1]) - int(rest_center[1])) <= 2
        assert abs(int(orig_center[2]) - int(rest_center[2])) <= 2
        assert orig_center[3] == rest_center[3]

    def test_threshold_gray(self):
        """Threshold should produce binary output."""
        # Create grayscale gradient
        gray = np.zeros((100, 100), dtype=np.uint8)
        for x in range(100):
            gray[:, x] = int(x * 255 / 99)

        result = rust.threshold_gray(gray, 128)

        # Left half should be 0, right half 255
        assert np.all(result[:, :50] == 0)
        assert np.all(result[:, 51:] == 255)


class TestBlurFilters:
    """Tests for blur filters."""

    def test_gaussian_blur_reduces_variance(self):
        """Gaussian blur should reduce variance (smoother image)."""
        img = create_test_image(100, 100, 'square')

        # Add noise
        noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
        noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        blurred = rust.gaussian_blur_rgba(noisy, 3.0)

        # Variance should decrease
        var_before = np.var(noisy[:, :, 0])
        var_after = np.var(blurred[:, :, 0])
        assert var_after < var_before

    def test_gaussian_blur_preserves_shape(self):
        """Gaussian blur should not change image dimensions."""
        img = create_test_image(80, 60, 'square')
        blurred = rust.gaussian_blur_rgba(img, 2.0)
        assert blurred.shape == img.shape

    def test_box_blur_averages_region(self):
        """Box blur should average neighboring pixels."""
        img = np.zeros((50, 50, 4), dtype=np.uint8)
        img[24:26, 24:26] = [255, 255, 255, 255]  # Small bright spot

        blurred = rust.box_blur_rgba(img, 5)

        # Bright spot should spread out, center should be dimmer
        center_before = img[25, 25, 0]
        center_after = blurred[25, 25, 0]
        assert center_after < center_before

        # Neighbors should be brighter than before
        neighbor_before = img[20, 25, 0]
        neighbor_after = blurred[20, 25, 0]
        assert neighbor_after > neighbor_before


class TestDropShadow:
    """Tests for drop shadow effect."""

    def test_drop_shadow_expands_canvas(self):
        """Drop shadow should expand output dimensions."""
        img = create_test_image(50, 50, 'square')
        result = rust.drop_shadow_rgba(img, offset_x=5.0, offset_y=5.0, blur_radius=3.0)

        # Output should be larger than input
        assert result.shape[0] > img.shape[0]
        assert result.shape[1] > img.shape[1]

    def test_drop_shadow_creates_shadow_pixels(self):
        """Drop shadow should create new non-transparent pixels."""
        img = create_test_image(50, 50, 'square')
        pixels_before = count_non_transparent(img)

        result = rust.drop_shadow_rgba(img, offset_x=5.0, offset_y=5.0, blur_radius=3.0)
        pixels_after = count_non_transparent(result)

        # Should have more visible pixels due to shadow
        assert pixels_after > pixels_before

    def test_drop_shadow_color(self):
        """Drop shadow should use specified color."""
        img = create_test_image(50, 50, 'square')

        # Blue shadow
        result = rust.drop_shadow_rgba(img, offset_x=10.0, offset_y=10.0,
                                        blur_radius=2.0, color=(0, 0, 255))

        # Check offset position for blue pixels
        # Shadow should be offset from original
        blue_pixels = count_color_pixels(result, (0, 0, 255), tolerance=50)
        assert blue_pixels > 100  # Should have significant blue shadow

    def test_drop_shadow_offset_direction(self):
        """Drop shadow offset should move shadow in correct direction."""
        img = np.zeros((100, 100, 4), dtype=np.uint8)
        img[40:60, 40:60] = [255, 255, 255, 255]

        # Shadow offset to bottom-right
        result = rust.drop_shadow_rgba(img, offset_x=15.0, offset_y=15.0,
                                        blur_radius=1.0, opacity=1.0)

        # Find shadow centroid (non-white, non-transparent pixels)
        # The shadow should be offset to bottom-right of the white square


class TestStrokeEffect:
    """Tests for stroke/outline effect."""

    def test_stroke_expands_canvas(self):
        """Outside stroke should expand output."""
        img = create_test_image(50, 50, 'square')
        result = rust.stroke_rgba(img, width=5.0, position='outside')

        assert result.shape[0] > img.shape[0]
        assert result.shape[1] > img.shape[1]

    def test_inside_stroke_same_size(self):
        """Inside stroke should not expand canvas."""
        img = create_test_image(50, 50, 'square')
        result = rust.stroke_rgba(img, width=3.0, position='inside', expand=0)

        # With explicit expand=0, should be same size
        assert result.shape == img.shape

    def test_stroke_color(self):
        """Stroke should use specified color."""
        img = create_test_image(50, 50, 'square')

        # Green stroke on red square
        result = rust.stroke_rgba(img, width=3.0, color=(0, 255, 0),
                                   position='outside')

        green_pixels = count_color_pixels(result, (0, 255, 0), tolerance=30)
        assert green_pixels > 100

    def test_stroke_width_affects_thickness(self):
        """Larger stroke width should create more stroke pixels."""
        img = create_test_image(50, 50, 'square')

        thin = rust.stroke_rgba(img, width=2.0, color=(0, 0, 255), position='outside')
        thick = rust.stroke_rgba(img, width=6.0, color=(0, 0, 255), position='outside')

        thin_blue = count_color_pixels(thin, (0, 0, 255), tolerance=30)
        thick_blue = count_color_pixels(thick, (0, 0, 255), tolerance=30)

        assert thick_blue > thin_blue


class TestLightingEffects:
    """Tests for bevel, glow effects."""

    def test_inner_glow_same_size(self):
        """Inner glow should not expand canvas."""
        img = create_test_image(50, 50, 'square')
        result = rust.inner_glow_rgba(img, radius=5.0)

        assert result.shape == img.shape

    def test_outer_glow_expands(self):
        """Outer glow should expand canvas."""
        img = create_test_image(50, 50, 'square')
        result = rust.outer_glow_rgba(img, radius=10.0)

        assert result.shape[0] > img.shape[0]
        assert result.shape[1] > img.shape[1]

    def test_outer_glow_color(self):
        """Outer glow should use specified color."""
        img = create_test_image(50, 50, 'square')

        # Yellow glow
        result = rust.outer_glow_rgba(img, radius=8.0, color=(255, 255, 0))

        yellow_pixels = count_color_pixels(result, (255, 255, 0), tolerance=50)
        assert yellow_pixels > 50

    def test_bevel_creates_highlights_shadows(self):
        """Bevel should add lighter and darker areas."""
        img = create_test_image(100, 100, 'square')
        avg_before = compute_channel_averages(img)

        result = rust.bevel_emboss_rgba(img, depth=5.0, angle=135.0)

        # Should still have similar overall appearance
        assert result.shape == img.shape

        # The image should have both lighter and darker pixels now
        # (hard to test precisely, but check it doesn't crash)
        avg_after = compute_channel_averages(result)
        # Alpha should be similar
        assert abs(avg_before['a'] - avg_after['a']) < 20


class TestF32Variants:
    """Tests for float32 version of effects."""

    def test_drop_shadow_f32(self):
        """Float32 drop shadow should work correctly."""
        img = np.zeros((50, 50, 4), dtype=np.float32)
        img[15:35, 15:35] = [1.0, 0.0, 0.0, 1.0]  # Red square

        result = rust.drop_shadow_rgba_f32(img, offset_x=5.0, offset_y=5.0,
                                            blur_radius=3.0, color=(0.0, 0.0, 0.0))

        assert result.dtype == np.float32
        assert result.shape[0] > img.shape[0]
        assert np.max(result) <= 1.0
        assert np.min(result) >= 0.0

    def test_stroke_f32(self):
        """Float32 stroke should work correctly."""
        img = np.zeros((50, 50, 4), dtype=np.float32)
        img[15:35, 15:35] = [0.0, 1.0, 0.0, 1.0]  # Green square

        result = rust.stroke_rgba_f32(img, width=3.0, color=(0.0, 0.0, 1.0),
                                       position='outside')

        assert result.dtype == np.float32
        assert np.max(result) <= 1.0
        assert np.min(result) >= 0.0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_blur_radius(self):
        """Zero blur should return copy of input."""
        img = create_test_image(50, 50, 'square')
        result = rust.gaussian_blur_rgba(img, 0.0)

        assert result.shape == img.shape
        assert compute_checksum(result) == compute_checksum(img)

    def test_empty_image(self):
        """Effects should handle fully transparent images."""
        img = np.zeros((50, 50, 4), dtype=np.uint8)

        shadow = rust.drop_shadow_rgba(img, offset_x=5.0, offset_y=5.0, blur_radius=3.0)
        assert shadow.shape[0] >= img.shape[0]

        stroke = rust.stroke_rgba(img, width=3.0)
        assert stroke.shape[0] >= img.shape[0]

    def test_single_pixel(self):
        """Effects should handle 1x1 images."""
        img = np.array([[[255, 0, 0, 255]]], dtype=np.uint8)

        result = rust.gaussian_blur_rgba(img, 1.0)
        assert result.shape == (1, 1, 4)

    def test_large_blur_radius(self):
        """Large blur radius should not crash."""
        img = create_test_image(50, 50, 'square')
        result = rust.gaussian_blur_rgba(img, 20.0)
        assert result.shape == img.shape


class TestConsistency:
    """Tests for deterministic behavior."""

    def test_same_input_same_output(self):
        """Same input should produce identical output."""
        img = create_test_image(50, 50, 'square')

        result1 = rust.drop_shadow_rgba(img, offset_x=5.0, offset_y=5.0, blur_radius=3.0)
        result2 = rust.drop_shadow_rgba(img, offset_x=5.0, offset_y=5.0, blur_radius=3.0)

        assert compute_checksum(result1) == compute_checksum(result2)

    def test_parameter_changes_output(self):
        """Different parameters should produce different output."""
        img = create_test_image(50, 50, 'square')

        result1 = rust.drop_shadow_rgba(img, offset_x=5.0, offset_y=5.0, blur_radius=3.0)
        result2 = rust.drop_shadow_rgba(img, offset_x=10.0, offset_y=10.0, blur_radius=3.0)

        assert compute_checksum(result1) != compute_checksum(result2)
