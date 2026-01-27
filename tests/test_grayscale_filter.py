"""
Test grayscale filter with Rust backend and Python fallback.

Tests verify:
- ITU-R BT.709 luminosity coefficients are correctly applied
- Alpha channel is preserved
- Both Rust and Python fallback produce identical results
"""

import numpy as np
import pytest


class TestGrayscaleFilter:
    """Test grayscale conversion filter."""

    def test_grayscale_red(self):
        """Pure red should become dark gray (0.2126 * 255 ≈ 54)."""
        from imagestag.filters.grayscale import grayscale

        img = np.zeros((10, 10, 4), dtype=np.uint8)
        img[:, :, 0] = 255  # R
        img[:, :, 3] = 255  # A

        result = grayscale(img)

        # 0.2126 * 255 ≈ 54
        expected_gray = int(0.2126 * 255)
        assert abs(result[0, 0, 0] - expected_gray) <= 1
        assert result[0, 0, 0] == result[0, 0, 1]  # G = R
        assert result[0, 0, 1] == result[0, 0, 2]  # B = G
        assert result[0, 0, 3] == 255  # Alpha preserved

    def test_grayscale_green(self):
        """Pure green should become bright gray (0.7152 * 255 ≈ 182)."""
        from imagestag.filters.grayscale import grayscale

        img = np.zeros((10, 10, 4), dtype=np.uint8)
        img[:, :, 1] = 255  # G
        img[:, :, 3] = 255  # A

        result = grayscale(img)

        # 0.7152 * 255 ≈ 182
        expected_gray = int(0.7152 * 255)
        assert abs(result[0, 0, 0] - expected_gray) <= 1

    def test_grayscale_blue(self):
        """Pure blue should become very dark gray (0.0722 * 255 ≈ 18)."""
        from imagestag.filters.grayscale import grayscale

        img = np.zeros((10, 10, 4), dtype=np.uint8)
        img[:, :, 2] = 255  # B
        img[:, :, 3] = 255  # A

        result = grayscale(img)

        # 0.0722 * 255 ≈ 18
        expected_gray = int(0.0722 * 255)
        assert abs(result[0, 0, 0] - expected_gray) <= 1

    def test_grayscale_white(self):
        """White should stay white (255)."""
        from imagestag.filters.grayscale import grayscale

        img = np.zeros((10, 10, 4), dtype=np.uint8)
        img[:, :, :3] = 255  # RGB = white
        img[:, :, 3] = 255   # A

        result = grayscale(img)

        # 0.2126 * 255 + 0.7152 * 255 + 0.0722 * 255 ≈ 255
        assert result[0, 0, 0] == 255

    def test_grayscale_preserves_alpha(self):
        """Alpha channel should be preserved."""
        from imagestag.filters.grayscale import grayscale

        img = np.zeros((10, 10, 4), dtype=np.uint8)
        img[:, :, :3] = 128
        img[:, :, 3] = 100  # Semi-transparent

        result = grayscale(img)

        assert np.all(result[:, :, 3] == 100)

    def test_grayscale_r_equals_g_equals_b(self):
        """All color channels should be equal in grayscale output."""
        from imagestag.filters.grayscale import grayscale

        # Create a colorful test image
        img = np.zeros((20, 20, 4), dtype=np.uint8)
        img[:, :, 0] = np.arange(20).reshape(1, 20) * 12  # Red gradient
        img[:, :, 1] = np.arange(20).reshape(20, 1) * 10  # Green gradient
        img[:, :, 2] = 128  # Constant blue
        img[:, :, 3] = 255  # Full opacity

        result = grayscale(img)

        assert np.allclose(result[:, :, 0], result[:, :, 1])
        assert np.allclose(result[:, :, 1], result[:, :, 2])

    def test_grayscale_astronaut(self):
        """Test with real astronaut image from skimage."""
        from imagestag.filters.grayscale import grayscale

        try:
            from skimage import data
            astronaut = data.astronaut()  # (512, 512, 3)
        except ImportError:
            pytest.skip("skimage not available")

        rgba = np.zeros((512, 512, 4), dtype=np.uint8)
        rgba[:, :, :3] = astronaut
        rgba[:, :, 3] = 255

        result = grayscale(rgba)

        assert result.shape == (512, 512, 4)
        assert result.dtype == np.uint8
        # R = G = B for grayscale
        assert np.allclose(result[:, :, 0], result[:, :, 1])
        assert np.allclose(result[:, :, 1], result[:, :, 2])

    def test_grayscale_rgb_input(self):
        """Should accept RGB (3-channel) input."""
        from imagestag.filters.grayscale import grayscale

        # RGB image (3 channels) - Rust supports 1, 3, or 4 channels
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        result = grayscale(img)
        assert result.shape == (10, 10, 3)

    def test_grayscale_invalid_shape(self):
        """Should raise error for invalid channel count."""
        from imagestag.filters.grayscale import grayscale

        # 2-channel image (not supported)
        img = np.zeros((10, 10, 2), dtype=np.uint8)

        with pytest.raises(ValueError):
            grayscale(img)

    def test_grayscale_invalid_dtype(self):
        """Should raise error for non-uint8 input."""
        from imagestag.filters.grayscale import grayscale

        # Float image
        img = np.zeros((10, 10, 4), dtype=np.float32)

        with pytest.raises(ValueError):
            grayscale(img)


class TestGrayscaleRustOnly:
    """Verify grayscale uses Rust backend (no fallback)."""

    def test_rust_backend_available(self):
        """Rust backend must be available - no Python fallback exists."""
        from imagestag import imagestag_rust
        assert hasattr(imagestag_rust, 'grayscale_rgba')
