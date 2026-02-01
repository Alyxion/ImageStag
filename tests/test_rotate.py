"""Tests for rotation and mirroring filters.

Tests cover:
- All rotation angles (90, 180, 270 degrees clockwise)
- Horizontal and vertical mirroring
- All pixel formats (gray u8/f32, RGB u8/f32, RGBA u8/f32)
- Dimension changes (90/270 swap dimensions)
- Pixel position correctness
"""
import numpy as np
import pytest

from imagestag.filters.rotate import (
    rotate_90_cw, rotate_180, rotate_270_cw, rotate,
    flip_horizontal, flip_vertical,
    rotate_90_cw_f32, rotate_180_f32, rotate_270_cw_f32, rotate_f32,
    flip_horizontal_f32, flip_vertical_f32
)


class TestRotateDimensions:
    """Test that output dimensions are correct."""

    def test_rotate_90_swaps_dimensions(self):
        img = np.zeros((100, 200, 4), dtype=np.uint8)
        result = rotate_90_cw(img)
        assert result.shape == (200, 100, 4)

    def test_rotate_180_preserves_dimensions(self):
        img = np.zeros((100, 200, 4), dtype=np.uint8)
        result = rotate_180(img)
        assert result.shape == (100, 200, 4)

    def test_rotate_270_swaps_dimensions(self):
        img = np.zeros((100, 200, 4), dtype=np.uint8)
        result = rotate_270_cw(img)
        assert result.shape == (200, 100, 4)

    def test_flip_horizontal_preserves_dimensions(self):
        img = np.zeros((100, 200, 4), dtype=np.uint8)
        result = flip_horizontal(img)
        assert result.shape == (100, 200, 4)

    def test_flip_vertical_preserves_dimensions(self):
        img = np.zeros((100, 200, 4), dtype=np.uint8)
        result = flip_vertical(img)
        assert result.shape == (100, 200, 4)


class TestRotatePixelPositions:
    """Test that pixels move to correct positions after rotation."""

    def test_rotate_90_pixel_position(self):
        """After 90° CW, pixel at (y, x) moves to (x, H-1-y)."""
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        img[2, 5] = [255, 0, 0, 255]  # Pixel at (y=2, x=5)

        result = rotate_90_cw(img)
        # After 90° CW: new position is (new_y=5, new_x=10-1-2=7)
        assert np.array_equal(result[5, 7], [255, 0, 0, 255])

    def test_rotate_180_pixel_position(self):
        """After 180°, pixel at (y, x) moves to (H-1-y, W-1-x)."""
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        img[2, 5] = [255, 0, 0, 255]

        result = rotate_180(img)
        # After 180°: (2, 5) -> (10-1-2=7, 20-1-5=14)
        assert np.array_equal(result[7, 14], [255, 0, 0, 255])

    def test_rotate_270_pixel_position(self):
        """After 270° CW (90° CCW), pixel at (y, x) moves to (W-1-x, y)."""
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        img[2, 5] = [255, 0, 0, 255]

        result = rotate_270_cw(img)
        # After 270° CW: (2, 5) -> (new_y=20-1-5=14, new_x=2)
        assert np.array_equal(result[14, 2], [255, 0, 0, 255])

    def test_flip_horizontal_pixel_position(self):
        """After horizontal flip, x -> W-1-x."""
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        img[2, 5] = [255, 0, 0, 255]

        result = flip_horizontal(img)
        # After flip: (2, 5) -> (2, 20-1-5=14)
        assert np.array_equal(result[2, 14], [255, 0, 0, 255])

    def test_flip_vertical_pixel_position(self):
        """After vertical flip, y -> H-1-y."""
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        img[2, 5] = [255, 0, 0, 255]

        result = flip_vertical(img)
        # After flip: (2, 5) -> (10-1-2=7, 5)
        assert np.array_equal(result[7, 5], [255, 0, 0, 255])


class TestRotateIdentity:
    """Test that combining rotations gives expected results."""

    def test_rotate_360_is_identity(self):
        """Four 90° rotations should return to original."""
        img = np.random.randint(0, 256, (10, 15, 4), dtype=np.uint8)

        r1 = rotate_90_cw(img)
        r2 = rotate_90_cw(r1)
        r3 = rotate_90_cw(r2)
        r4 = rotate_90_cw(r3)

        assert np.array_equal(img, r4)

    def test_rotate_180_twice_is_identity(self):
        """Two 180° rotations should return to original."""
        img = np.random.randint(0, 256, (10, 15, 4), dtype=np.uint8)

        r1 = rotate_180(img)
        r2 = rotate_180(r1)

        assert np.array_equal(img, r2)

    def test_flip_horizontal_twice_is_identity(self):
        """Two horizontal flips should return to original."""
        img = np.random.randint(0, 256, (10, 15, 4), dtype=np.uint8)

        f1 = flip_horizontal(img)
        f2 = flip_horizontal(f1)

        assert np.array_equal(img, f2)

    def test_flip_vertical_twice_is_identity(self):
        """Two vertical flips should return to original."""
        img = np.random.randint(0, 256, (10, 15, 4), dtype=np.uint8)

        f1 = flip_vertical(img)
        f2 = flip_vertical(f1)

        assert np.array_equal(img, f2)

    def test_rotate_90_plus_270_is_identity(self):
        """90° + 270° should equal 360° (identity)."""
        img = np.random.randint(0, 256, (10, 15, 4), dtype=np.uint8)

        r1 = rotate_90_cw(img)
        r2 = rotate_270_cw(r1)

        assert np.array_equal(img, r2)


class TestGenericRotate:
    """Test the generic rotate() function."""

    def test_rotate_90(self):
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        result = rotate(img, 90)
        assert result.shape == (20, 10, 4)

    def test_rotate_180(self):
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        result = rotate(img, 180)
        assert result.shape == (10, 20, 4)

    def test_rotate_270(self):
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        result = rotate(img, 270)
        assert result.shape == (20, 10, 4)

    def test_rotate_invalid_angle(self):
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        with pytest.raises(ValueError):
            rotate(img, 45)


class TestPixelFormats:
    """Test all supported pixel formats."""

    def test_grayscale_u8(self):
        img = np.zeros((10, 20, 1), dtype=np.uint8)
        img[2, 5] = [128]
        result = rotate_90_cw(img)
        assert result.shape == (20, 10, 1)
        assert result[5, 7, 0] == 128

    def test_rgb_u8(self):
        img = np.zeros((10, 20, 3), dtype=np.uint8)
        img[2, 5] = [100, 150, 200]
        result = rotate_90_cw(img)
        assert result.shape == (20, 10, 3)
        assert np.array_equal(result[5, 7], [100, 150, 200])

    def test_rgba_u8(self):
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        img[2, 5] = [100, 150, 200, 255]
        result = rotate_90_cw(img)
        assert result.shape == (20, 10, 4)
        assert np.array_equal(result[5, 7], [100, 150, 200, 255])

    def test_grayscale_f32(self):
        img = np.zeros((10, 20, 1), dtype=np.float32)
        img[2, 5] = [0.5]
        result = rotate_90_cw_f32(img)
        assert result.shape == (20, 10, 1)
        assert np.isclose(result[5, 7, 0], 0.5)

    def test_rgb_f32(self):
        img = np.zeros((10, 20, 3), dtype=np.float32)
        img[2, 5] = [0.25, 0.5, 0.75]
        result = rotate_90_cw_f32(img)
        assert result.shape == (20, 10, 3)
        assert np.allclose(result[5, 7], [0.25, 0.5, 0.75])

    def test_rgba_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        img[2, 5] = [0.25, 0.5, 0.75, 1.0]
        result = rotate_90_cw_f32(img)
        assert result.shape == (20, 10, 4)
        assert np.allclose(result[5, 7], [0.25, 0.5, 0.75, 1.0])


class TestF32Functions:
    """Test f32 versions of all functions."""

    def test_rotate_90_cw_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        result = rotate_90_cw_f32(img)
        assert result.shape == (20, 10, 4)
        assert result.dtype == np.float32

    def test_rotate_180_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        result = rotate_180_f32(img)
        assert result.shape == (10, 20, 4)
        assert result.dtype == np.float32

    def test_rotate_270_cw_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        result = rotate_270_cw_f32(img)
        assert result.shape == (20, 10, 4)
        assert result.dtype == np.float32

    def test_rotate_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        result = rotate_f32(img, 90)
        assert result.shape == (20, 10, 4)
        assert result.dtype == np.float32

    def test_flip_horizontal_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        result = flip_horizontal_f32(img)
        assert result.shape == (10, 20, 4)
        assert result.dtype == np.float32

    def test_flip_vertical_f32(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        result = flip_vertical_f32(img)
        assert result.shape == (10, 20, 4)
        assert result.dtype == np.float32


class TestValidation:
    """Test input validation."""

    def test_invalid_channels(self):
        img = np.zeros((10, 20, 2), dtype=np.uint8)
        with pytest.raises(ValueError):
            rotate_90_cw(img)

    def test_invalid_dtype_u8_function(self):
        img = np.zeros((10, 20, 4), dtype=np.float32)
        with pytest.raises(ValueError):
            rotate_90_cw(img)  # u8 function with f32 data

    def test_invalid_dtype_f32_function(self):
        img = np.zeros((10, 20, 4), dtype=np.uint8)
        with pytest.raises(ValueError):
            rotate_90_cw_f32(img)  # f32 function with u8 data

    def test_invalid_ndim(self):
        img = np.zeros((10, 20), dtype=np.uint8)
        with pytest.raises(ValueError):
            rotate_90_cw(img)
