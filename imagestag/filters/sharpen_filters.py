"""Sharpen and blur filters with Rust backend.

This module provides sharpening and related spatial filters:
- Sharpen
- Unsharp Mask
- High Pass
- Motion Blur

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
    from imagestag.filters.sharpen_filters import sharpen, unsharp_mask, high_pass

    result = sharpen(rgba_image, amount=1.0)
    result = unsharp_mask(rgba_image, amount=1.5, radius=2.0, threshold=5)
    result = high_pass(rgba_image, radius=10.0)
"""
import numpy as np

from imagestag import imagestag_rust


def _validate_image(image: np.ndarray, expected_dtype: type, name: str) -> None:
    """Validate image shape and dtype."""
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")
    if image.dtype != expected_dtype:
        raise ValueError(f"Expected {expected_dtype} dtype, got {image.dtype}")


# ============================================================================
# Sharpen
# ============================================================================

def sharpen(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Sharpen image using convolution (u8).

    Uses a 3x3 sharpening kernel.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: Sharpening strength (0.0-5.0), 1.0 = standard (100%)

    Returns:
        Sharpened uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "sharpen")
    return imagestag_rust.sharpen(image, amount)


def sharpen_f32(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Sharpen image using convolution (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: Sharpening strength (0.0-5.0), 1.0 = standard (100%)

    Returns:
        Sharpened float32 array with same channel count
    """
    _validate_image(image, np.float32, "sharpen_f32")
    return imagestag_rust.sharpen_f32(image, amount)


# ============================================================================
# Unsharp Mask
# ============================================================================

def unsharp_mask(image: np.ndarray, amount: float = 1.0,
                 radius: float = 1.0, threshold: int = 0) -> np.ndarray:
    """Apply unsharp mask sharpening (u8).

    Subtracts a blurred version to enhance edges.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: Sharpening amount (0.0-5.0), 1.0 = 100%
        radius: Blur radius in pixels (0.1-500.0)
        threshold: Minimum difference to sharpen (0-255)

    Returns:
        Sharpened uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "unsharp_mask")
    return imagestag_rust.unsharp_mask(image, amount, radius, threshold)


def unsharp_mask_f32(image: np.ndarray, amount: float = 1.0,
                     radius: float = 1.0, threshold: float = 0.0) -> np.ndarray:
    """Apply unsharp mask sharpening (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: Sharpening amount (0.0-5.0), 1.0 = 100%
        radius: Blur radius in pixels (0.1-500.0)
        threshold: Minimum difference to sharpen (0.0-1.0)

    Returns:
        Sharpened float32 array with same channel count
    """
    _validate_image(image, np.float32, "unsharp_mask_f32")
    return imagestag_rust.unsharp_mask_f32(image, amount, radius, threshold)


# ============================================================================
# High Pass
# ============================================================================

def high_pass(image: np.ndarray, radius: float = 10.0) -> np.ndarray:
    """Apply high-pass filter (u8).

    Extracts edges and fine details by subtracting blurred image.
    Result is centered at 128 (gray).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Blur radius in pixels (0.1-500.0)

    Returns:
        High-pass filtered uint8 array (gray = no detail)
    """
    _validate_image(image, np.uint8, "high_pass")
    return imagestag_rust.high_pass(image, radius)


def high_pass_f32(image: np.ndarray, radius: float = 10.0) -> np.ndarray:
    """Apply high-pass filter (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Blur radius in pixels (0.1-500.0)

    Returns:
        High-pass filtered float32 array (0.5 = no detail)
    """
    _validate_image(image, np.float32, "high_pass_f32")
    return imagestag_rust.high_pass_f32(image, radius)


# ============================================================================
# Motion Blur
# ============================================================================

def motion_blur(image: np.ndarray, angle: float = 0.0,
                distance: float = 10.0) -> np.ndarray:
    """Apply motion blur (u8).

    Simulates camera motion during exposure.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        angle: Motion direction in degrees (0-360)
        distance: Blur distance in pixels (1-1000)

    Returns:
        Motion-blurred uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "motion_blur")
    return imagestag_rust.motion_blur(image, angle, distance)


def motion_blur_f32(image: np.ndarray, angle: float = 0.0,
                    distance: float = 10.0) -> np.ndarray:
    """Apply motion blur (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        angle: Motion direction in degrees (0-360)
        distance: Blur distance in pixels (1-1000)

    Returns:
        Motion-blurred float32 array with same channel count
    """
    _validate_image(image, np.float32, "motion_blur_f32")
    return imagestag_rust.motion_blur_f32(image, angle, distance)


__all__ = [
    'sharpen', 'sharpen_f32',
    'unsharp_mask', 'unsharp_mask_f32',
    'high_pass', 'high_pass_f32',
    'motion_blur', 'motion_blur_f32',
]
