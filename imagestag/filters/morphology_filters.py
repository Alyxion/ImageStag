"""Morphology filters with Rust backend.

This module provides morphological operations:
- Dilate (expand bright regions)
- Erode (shrink bright regions)

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
    from imagestag.filters.morphology_filters import dilate, erode

    result = dilate(image, radius=2.0)
    result = erode(image, radius=2.0)
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
# Dilate
# ============================================================================

def dilate(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Dilate image - expand bright regions (u8).

    Takes the maximum value in the neighborhood, making bright
    regions grow and dark regions shrink.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Dilation radius in pixels (0.5-100.0)

    Returns:
        Dilated uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "dilate")
    return imagestag_rust.dilate(image, radius)


def dilate_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Dilate image - expand bright regions (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Dilation radius in pixels (0.5-100.0)

    Returns:
        Dilated float32 array with same channel count
    """
    _validate_image(image, np.float32, "dilate_f32")
    return imagestag_rust.dilate_f32(image, radius)


# ============================================================================
# Erode
# ============================================================================

def erode(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Erode image - shrink bright regions (u8).

    Takes the minimum value in the neighborhood, making dark
    regions grow and bright regions shrink.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Erosion radius in pixels (0.5-100.0)

    Returns:
        Eroded uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "erode")
    return imagestag_rust.erode(image, radius)


def erode_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Erode image - shrink bright regions (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Erosion radius in pixels (0.5-100.0)

    Returns:
        Eroded float32 array with same channel count
    """
    _validate_image(image, np.float32, "erode_f32")
    return imagestag_rust.erode_f32(image, radius)


__all__ = [
    'dilate', 'dilate_f32',
    'erode', 'erode_f32',
]
