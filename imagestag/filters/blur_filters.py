"""Blur filters with Rust backend.

This module provides RGBA-aware blur operations:
- Gaussian Blur
- Box Blur

## Supported Formats

All filters accept numpy arrays with 1, 3, or 4 channels:

| Format | Shape | Type | Description |
|--------|-------|------|-------------|
| Grayscale8 | (H, W, 1) | uint8 | Single channel, 0-255 |
| Grayscale float | (H, W, 1) | float32 | Single channel, 0.0-1.0 |
| RGB8 | (H, W, 3) | uint8 | 3 channels, 0-255 |
| RGB float | (H, W, 3) | float32 | 3 channels, 0.0-1.0 |
| RGBA8 | (H, W, 4) | uint8 | 4 channels, 0-255 |
| RGBA float | (H, W, 4) | float32 | 4 channels, 0.0-1.0 |

## Bit Depth Support

- **u8 (8-bit)**: Values 0-255, standard for web/display
- **f32 (float)**: Values 0.0-1.0, for HDR/linear workflows

Usage:
    from imagestag.filters.blur_filters import gaussian_blur, box_blur

    result = gaussian_blur(image, sigma=2.0)
    result = box_blur(image, radius=3)
"""
import numpy as np

import imagestag_rust


def _validate_image(image: np.ndarray, expected_dtype: type, name: str) -> None:
    """Validate image shape and dtype."""
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")
    if image.dtype != expected_dtype:
        raise ValueError(f"Expected {expected_dtype} dtype, got {image.dtype}")


# ============================================================================
# Gaussian Blur
# ============================================================================

def gaussian_blur(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Apply Gaussian blur (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        sigma: Blur radius in standard deviations (0.1-100.0)

    Returns:
        Blurred uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "gaussian_blur")
    return imagestag_rust.gaussian_blur_rgba(image, sigma)


def gaussian_blur_f32(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Apply Gaussian blur (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        sigma: Blur radius in standard deviations (0.1-100.0)

    Returns:
        Blurred float32 array with same channel count
    """
    _validate_image(image, np.float32, "gaussian_blur_f32")
    return imagestag_rust.gaussian_blur_rgba_f32(image, sigma)


# ============================================================================
# Box Blur
# ============================================================================

def box_blur(image: np.ndarray, radius: int = 1) -> np.ndarray:
    """Apply box blur (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Blur radius in pixels (1-100)

    Returns:
        Blurred uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "box_blur")
    return imagestag_rust.box_blur_rgba(image, radius)


def box_blur_f32(image: np.ndarray, radius: int = 1) -> np.ndarray:
    """Apply box blur (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Blur radius in pixels (1-100)

    Returns:
        Blurred float32 array with same channel count
    """
    _validate_image(image, np.float32, "box_blur_f32")
    return imagestag_rust.box_blur_rgba_f32(image, radius)


__all__ = [
    'gaussian_blur', 'gaussian_blur_f32',
    'box_blur', 'box_blur_f32',
]
