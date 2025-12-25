# Tests for Flip and Rotation filters
"""
Comprehensive tests for flip and rotation filters covering all backends:
- PIL (default)
- OpenCV (cv)
- NumPy (numpy/raw)

Each test verifies that the operation produces correct results
by checking specific pixel positions after transformation.
"""

import pytest
import numpy as np
from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import Flip, Rotate, Filter


# Fixture for a simple test image with known pixel values
@pytest.fixture
def test_image():
    """Create a 4x3 test image with unique colors at each position.

    Layout (row, col):
        (0,0)=Red     (0,1)=Green   (0,2)=Blue    (0,3)=White
        (1,0)=Yellow  (1,1)=Cyan    (1,2)=Magenta (1,3)=Gray
        (2,0)=Orange  (2,1)=Purple  (2,2)=Pink    (2,3)=Black
    """
    pixels = np.array([
        [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255]],     # Row 0
        [[255, 255, 0], [0, 255, 255], [255, 0, 255], [128, 128, 128]],  # Row 1
        [[255, 128, 0], [128, 0, 255], [255, 192, 203], [0, 0, 0]],    # Row 2
    ], dtype=np.uint8)
    return Image(pixels, pixel_format=PixelFormat.RGB)


@pytest.fixture
def square_image():
    """Create a 4x4 square test image for rotation tests."""
    pixels = np.array([
        [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0]],
        [[255, 0, 255], [0, 255, 255], [128, 128, 128], [255, 255, 255]],
        [[255, 128, 0], [128, 0, 255], [64, 64, 64], [192, 192, 192]],
        [[0, 128, 255], [255, 64, 128], [128, 255, 64], [0, 0, 0]],
    ], dtype=np.uint8)
    return Image(pixels, pixel_format=PixelFormat.RGB)


class TestFlipHorizontal:
    """Test horizontal flip (mirror) with all backends."""

    def test_flip_horizontal_pil(self, test_image):
        """Test horizontal flip using PIL backend."""
        f = Flip(mode='h', backend='pil')
        result = f.apply(test_image)

        # Get result pixels
        px = result.get_pixels(PixelFormat.RGB)

        # Original row 0: Red, Green, Blue, White
        # Flipped row 0: White, Blue, Green, Red
        assert tuple(px[0, 0]) == (255, 255, 255), "Top-left should be White"
        assert tuple(px[0, 3]) == (255, 0, 0), "Top-right should be Red"

        # Dimensions should be unchanged
        assert result.width == test_image.width
        assert result.height == test_image.height

    def test_flip_horizontal_cv(self, test_image):
        """Test horizontal flip using OpenCV backend."""
        f = Flip(mode='h', backend='cv')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == (255, 255, 255), "Top-left should be White"
        assert tuple(px[0, 3]) == (255, 0, 0), "Top-right should be Red"
        assert tuple(px[2, 0]) == (0, 0, 0), "Bottom-left should be Black"
        assert tuple(px[2, 3]) == (255, 128, 0), "Bottom-right should be Orange"

    def test_flip_horizontal_numpy(self, test_image):
        """Test horizontal flip using NumPy backend."""
        f = Flip(mode='h', backend='numpy')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == (255, 255, 255), "Top-left should be White"
        assert tuple(px[0, 3]) == (255, 0, 0), "Top-right should be Red"

    def test_flip_horizontal_all_backends_consistent(self, test_image):
        """Verify all backends produce identical results."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Flip(mode='h', backend=backend)
            results[backend] = f.apply(test_image).get_pixels(PixelFormat.RGB)

        # Compare all pairs
        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"


class TestFlipVertical:
    """Test vertical flip with all backends."""

    def test_flip_vertical_pil(self, test_image):
        """Test vertical flip using PIL backend."""
        f = Flip(mode='v', backend='pil')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        # Original: Row 0 has Red at (0,0), Row 2 has Orange at (2,0)
        # Flipped: Row 0 should have Orange at (0,0), Row 2 should have Red
        assert tuple(px[0, 0]) == (255, 128, 0), "Top-left should be Orange"
        assert tuple(px[2, 0]) == (255, 0, 0), "Bottom-left should be Red"

    def test_flip_vertical_cv(self, test_image):
        """Test vertical flip using OpenCV backend."""
        f = Flip(mode='v', backend='cv')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == (255, 128, 0), "Top-left should be Orange"
        assert tuple(px[2, 0]) == (255, 0, 0), "Bottom-left should be Red"

    def test_flip_vertical_numpy(self, test_image):
        """Test vertical flip using NumPy backend."""
        f = Flip(mode='v', backend='numpy')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == (255, 128, 0), "Top-left should be Orange"
        assert tuple(px[2, 0]) == (255, 0, 0), "Bottom-left should be Red"

    def test_flip_vertical_all_backends_consistent(self, test_image):
        """Verify all backends produce identical results."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Flip(mode='v', backend=backend)
            results[backend] = f.apply(test_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"


class TestFlipBoth:
    """Test combined horizontal and vertical flip."""

    def test_flip_both_pil(self, test_image):
        """Test both flips using PIL backend (equivalent to 180° rotation)."""
        f = Flip(mode='hv', backend='pil')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        # Original (0,0)=Red should end up at (2,3)
        # Original (2,3)=Black should end up at (0,0)
        assert tuple(px[0, 0]) == (0, 0, 0), "Top-left should be Black"
        assert tuple(px[2, 3]) == (255, 0, 0), "Bottom-right should be Red"

    def test_flip_both_cv(self, test_image):
        """Test both flips using OpenCV backend."""
        f = Flip(mode='hv', backend='cv')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == (0, 0, 0), "Top-left should be Black"
        assert tuple(px[2, 3]) == (255, 0, 0), "Bottom-right should be Red"

    def test_flip_both_numpy(self, test_image):
        """Test both flips using NumPy backend."""
        f = Flip(mode='hv', backend='numpy')
        result = f.apply(test_image)

        px = result.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == (0, 0, 0), "Top-left should be Black"
        assert tuple(px[2, 3]) == (255, 0, 0), "Bottom-right should be Red"

    def test_flip_vh_order(self, test_image):
        """Test 'vh' mode is equivalent to 'hv'."""
        f_hv = Flip(mode='hv', backend='numpy')
        f_vh = Flip(mode='vh', backend='numpy')

        px_hv = f_hv.apply(test_image).get_pixels(PixelFormat.RGB)
        px_vh = f_vh.apply(test_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(px_hv, px_vh), "'hv' and 'vh' should be identical"

    def test_flip_both_all_backends_consistent(self, test_image):
        """Verify all backends produce identical results."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Flip(mode='hv', backend=backend)
            results[backend] = f.apply(test_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"


class TestFlipNoOp:
    """Test flip with no mode set (should return unchanged)."""

    def test_flip_none_returns_same(self, test_image):
        """Flip with empty mode should return original image."""
        f = Flip(mode='')
        result = f.apply(test_image)

        # Should be the same object or equivalent
        orig_px = test_image.get_pixels(PixelFormat.RGB)
        result_px = result.get_pixels(PixelFormat.RGB)
        assert np.array_equal(orig_px, result_px)


class TestRotate90:
    """Test 90° rotation with all backends."""

    def test_rotate90_ccw_pil(self, square_image):
        """Test 90° counter-clockwise rotation using PIL."""
        f = Rotate(angle=90, backend='pil')
        result = f.apply(square_image)

        # 4x4 rotated 90° CCW should still be 4x4
        assert result.width == 4
        assert result.height == 4

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        # After 90° CCW: original (0, 3) -> new (0, 0)
        # Original top-right (0, 3) = Yellow (255, 255, 0)
        assert tuple(px[0, 0]) == tuple(orig[0, 3]), "Top-right should move to top-left"

    def test_rotate90_ccw_cv(self, square_image):
        """Test 90° counter-clockwise rotation using OpenCV."""
        f = Rotate(angle=90, backend='cv')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == tuple(orig[0, 3])

    def test_rotate90_ccw_numpy(self, square_image):
        """Test 90° counter-clockwise rotation using NumPy."""
        f = Rotate(angle=90, backend='numpy')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == tuple(orig[0, 3])

    def test_rotate90_cw_pil(self, square_image):
        """Test 90° clockwise rotation using PIL (angle=-90 or 270)."""
        f = Rotate(angle=-90, backend='pil')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        # After 90° CW: original (0, 0) -> new (0, 3)
        # Original top-left (0, 0) = Red (255, 0, 0)
        assert tuple(px[0, 3]) == tuple(orig[0, 0]), "Top-left should move to top-right"
        # Original bottom-left (3, 0) -> new (0, 0)
        assert tuple(px[0, 0]) == tuple(orig[3, 0])

    def test_rotate90_cw_cv(self, square_image):
        """Test 90° clockwise rotation using OpenCV."""
        f = Rotate(angle=-90, backend='cv')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 3]) == tuple(orig[0, 0])
        assert tuple(px[0, 0]) == tuple(orig[3, 0])

    def test_rotate90_cw_numpy(self, square_image):
        """Test 90° clockwise rotation using NumPy."""
        f = Rotate(angle=-90, backend='numpy')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 3]) == tuple(orig[0, 0])
        assert tuple(px[0, 0]) == tuple(orig[3, 0])

    def test_rotate90_all_backends_consistent(self, square_image):
        """Verify all backends produce identical results for 90° CCW."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Rotate(angle=90, backend=backend)
            results[backend] = f.apply(square_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"

    def test_rotate90_cw_all_backends_consistent(self, square_image):
        """Verify all backends produce identical results for 90° CW."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Rotate(angle=-90, backend=backend)
            results[backend] = f.apply(square_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"


class TestRotate180:
    """Test 180° rotation with all backends."""

    def test_rotate180_pil(self, square_image):
        """Test 180° rotation using PIL."""
        f = Rotate(angle=180, backend='pil')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        # After 180°: (0, 0) <-> (3, 3)
        assert tuple(px[0, 0]) == tuple(orig[3, 3]), "Corners should swap"
        assert tuple(px[3, 3]) == tuple(orig[0, 0])

    def test_rotate180_cv(self, square_image):
        """Test 180° rotation using OpenCV."""
        f = Rotate(angle=180, backend='cv')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == tuple(orig[3, 3])
        assert tuple(px[3, 3]) == tuple(orig[0, 0])

    def test_rotate180_numpy(self, square_image):
        """Test 180° rotation using NumPy."""
        f = Rotate(angle=180, backend='numpy')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == tuple(orig[3, 3])
        assert tuple(px[3, 3]) == tuple(orig[0, 0])

    def test_rotate180_all_backends_consistent(self, square_image):
        """Verify all backends produce identical results."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Rotate(angle=180, backend=backend)
            results[backend] = f.apply(square_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"

    def test_rotate180_equals_flip_both(self, square_image):
        """Verify 180° rotation equals horizontal + vertical flip."""
        rotate_result = Rotate(angle=180, backend='numpy').apply(square_image)
        flip_result = Flip(mode='hv', backend='numpy').apply(square_image)

        rotate_px = rotate_result.get_pixels(PixelFormat.RGB)
        flip_px = flip_result.get_pixels(PixelFormat.RGB)

        assert np.array_equal(rotate_px, flip_px), "180° rotation should equal double flip"


class TestRotate270:
    """Test 270° rotation with all backends."""

    def test_rotate270_pil(self, square_image):
        """Test 270° rotation using PIL (same as 90° CW)."""
        f = Rotate(angle=270, backend='pil')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        # 270° CCW = 90° CW
        # Original (3, 0) -> new (0, 0)
        assert tuple(px[0, 0]) == tuple(orig[3, 0])

    def test_rotate270_cv(self, square_image):
        """Test 270° rotation using OpenCV."""
        f = Rotate(angle=270, backend='cv')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == tuple(orig[3, 0])

    def test_rotate270_numpy(self, square_image):
        """Test 270° rotation using NumPy."""
        f = Rotate(angle=270, backend='numpy')
        result = f.apply(square_image)

        px = result.get_pixels(PixelFormat.RGB)
        orig = square_image.get_pixels(PixelFormat.RGB)

        assert tuple(px[0, 0]) == tuple(orig[3, 0])

    def test_rotate270_all_backends_consistent(self, square_image):
        """Verify all backends produce identical results."""
        results = {}
        for backend in ['pil', 'cv', 'numpy']:
            f = Rotate(angle=270, backend=backend)
            results[backend] = f.apply(square_image).get_pixels(PixelFormat.RGB)

        assert np.array_equal(results['pil'], results['cv']), "PIL and CV should match"
        assert np.array_equal(results['pil'], results['numpy']), "PIL and NumPy should match"

    def test_rotate270_equals_rotate_minus90(self, square_image):
        """Verify 270° CCW equals -90° (90° CW)."""
        rotate270 = Rotate(angle=270, backend='numpy').apply(square_image)
        rotate_neg90 = Rotate(angle=-90, backend='numpy').apply(square_image)

        r270_px = rotate270.get_pixels(PixelFormat.RGB)
        r_neg90_px = rotate_neg90.get_pixels(PixelFormat.RGB)

        assert np.array_equal(r270_px, r_neg90_px), "270° should equal -90°"


class TestRotateGeneral:
    """Test general rotation filter."""

    def test_rotate_arbitrary_angle(self, square_image):
        """Test rotation with arbitrary angle."""
        f = Rotate(angle=45, expand=True)
        result = f.apply(square_image)

        # With expand=True, result should be larger
        assert result.width >= square_image.width
        assert result.height >= square_image.height

    def test_rotate_no_expand(self, square_image):
        """Test rotation without canvas expansion."""
        f = Rotate(angle=30, expand=False)
        result = f.apply(square_image)

        # Without expand, dimensions should be same
        assert result.width == square_image.width
        assert result.height == square_image.height

    def test_rotate_360_returns_same(self, square_image):
        """Test 360° rotation returns original."""
        f = Rotate(angle=360)
        result = f.apply(square_image)

        orig_px = square_image.get_pixels(PixelFormat.RGB)
        result_px = result.get_pixels(PixelFormat.RGB)

        assert np.array_equal(orig_px, result_px)

    def test_rotate_0_returns_same(self, square_image):
        """Test 0° rotation returns original."""
        f = Rotate(angle=0)
        result = f.apply(square_image)

        orig_px = square_image.get_pixels(PixelFormat.RGB)
        result_px = result.get_pixels(PixelFormat.RGB)

        assert np.array_equal(orig_px, result_px)


class TestRotationRoundTrips:
    """Test that rotations can be reversed."""

    def test_four_90_rotations_returns_original(self, square_image):
        """Four 90° rotations should return to original."""
        f = Rotate(angle=90, backend='numpy')
        result = square_image
        for _ in range(4):
            result = f.apply(result)

        orig_px = square_image.get_pixels(PixelFormat.RGB)
        result_px = result.get_pixels(PixelFormat.RGB)

        assert np.array_equal(orig_px, result_px), "4x 90° should return to original"

    def test_two_180_rotations_returns_original(self, square_image):
        """Two 180° rotations should return to original."""
        f = Rotate(angle=180, backend='numpy')
        result = f.apply(f.apply(square_image))

        orig_px = square_image.get_pixels(PixelFormat.RGB)
        result_px = result.get_pixels(PixelFormat.RGB)

        assert np.array_equal(orig_px, result_px), "2x 180° should return to original"

    def test_double_flip_returns_original(self, test_image):
        """Two horizontal flips should return to original."""
        f = Flip(mode='h', backend='numpy')
        result = f.apply(f.apply(test_image))

        orig_px = test_image.get_pixels(PixelFormat.RGB)
        result_px = result.get_pixels(PixelFormat.RGB)

        assert np.array_equal(orig_px, result_px), "2x H-flip should return to original"


class TestRectangularRotations:
    """Test rotations on non-square images."""

    def test_rotate90_rectangular(self, test_image):
        """Test 90° rotation on 4x3 image produces 3x4 result."""
        f = Rotate(angle=90, backend='numpy')
        result = f.apply(test_image)

        # 4x3 rotated 90° should be 3x4
        assert result.width == test_image.height
        assert result.height == test_image.width

    def test_rotate90_rectangular_all_backends(self, test_image):
        """Test all backends handle rectangular images correctly."""
        for backend in ['pil', 'cv', 'numpy']:
            f = Rotate(angle=90, backend=backend)
            result = f.apply(test_image)

            assert result.width == test_image.height, f"{backend}: width should equal original height"
            assert result.height == test_image.width, f"{backend}: height should equal original width"

    def test_rotate180_rectangular_preserves_dimensions(self, test_image):
        """Test 180° rotation preserves dimensions."""
        for backend in ['pil', 'cv', 'numpy']:
            f = Rotate(angle=180, backend=backend)
            result = f.apply(test_image)

            assert result.width == test_image.width, f"{backend}: width should be preserved"
            assert result.height == test_image.height, f"{backend}: height should be preserved"


class TestDSLParsing:
    """Test filter parsing from DSL strings."""

    def test_parse_flip_horizontal(self):
        """Test parsing flip filter from DSL."""
        f = Filter.parse('flip h')
        assert isinstance(f, Flip)
        assert f.mode == 'h'

    def test_parse_flip_vertical(self):
        """Test parsing vertical flip from DSL."""
        f = Filter.parse('flip v')
        assert isinstance(f, Flip)
        assert f.mode == 'v'

    def test_parse_flip_both(self):
        """Test parsing both flip from DSL."""
        f = Filter.parse('flip hv')
        assert isinstance(f, Flip)
        assert f.mode == 'hv'

    def test_parse_rotate_90(self):
        """Test parsing rotate 90 from DSL."""
        f = Filter.parse('rotate 90')
        assert isinstance(f, Rotate)
        assert f.angle == 90.0

    def test_parse_rotate_180(self):
        """Test parsing rotate 180 from DSL."""
        f = Filter.parse('rotate 180')
        assert isinstance(f, Rotate)
        assert f.angle == 180.0

    def test_parse_rotate_270(self):
        """Test parsing rotate 270 from DSL."""
        f = Filter.parse('rotate 270')
        assert isinstance(f, Rotate)
        assert f.angle == 270.0

    def test_parse_rotate_with_angle(self):
        """Test parsing general rotate with angle."""
        f = Filter.parse('rotate 45')
        assert isinstance(f, Rotate)
        assert f.angle == 45.0


class TestDSLAliases:
    """Test parameterized aliases for rotation and flip."""

    def test_rot90_alias(self):
        """Test rot90 alias produces Rotate(angle=90)."""
        f = Filter.parse('rot90')
        assert isinstance(f, Rotate)
        assert f.angle == 90.0

    def test_rot180_alias(self):
        """Test rot180 alias produces Rotate(angle=180)."""
        f = Filter.parse('rot180')
        assert isinstance(f, Rotate)
        assert f.angle == 180.0

    def test_rot270_alias(self):
        """Test rot270 alias produces Rotate(angle=270)."""
        f = Filter.parse('rot270')
        assert isinstance(f, Rotate)
        assert f.angle == 270.0

    def test_rotcw_alias(self):
        """Test rotcw alias produces Rotate(angle=-90)."""
        f = Filter.parse('rotcw')
        assert isinstance(f, Rotate)
        assert f.angle == -90.0

    def test_rotccw_alias(self):
        """Test rotccw alias produces Rotate(angle=90)."""
        f = Filter.parse('rotccw')
        assert isinstance(f, Rotate)
        assert f.angle == 90.0

    def test_mirror_alias(self):
        """Test mirror alias produces Flip(mode='h')."""
        f = Filter.parse('mirror')
        assert isinstance(f, Flip)
        assert f.mode == 'h'

    def test_fliplr_alias(self):
        """Test fliplr alias produces Flip(mode='h')."""
        f = Filter.parse('fliplr')
        assert isinstance(f, Flip)
        assert f.mode == 'h'

    def test_flipud_alias(self):
        """Test flipud alias produces Flip(mode='v')."""
        f = Filter.parse('flipud')
        assert isinstance(f, Flip)
        assert f.mode == 'v'

    def test_flipv_alias(self):
        """Test flipv alias produces Flip(mode='v')."""
        f = Filter.parse('flipv')
        assert isinstance(f, Flip)
        assert f.mode == 'v'

    def test_alias_with_override(self):
        """Test alias can have parameters overridden."""
        # rot90 defaults to angle=90, but we can override with backend
        f = Filter.parse('rot90 backend=cv')
        assert isinstance(f, Rotate)
        assert f.angle == 90.0
        assert f.backend == 'cv'
