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

import imagestag_rust


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


# ============================================================================
# Morphology Open
# ============================================================================

def morphology_open(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Morphological opening - erosion then dilation (u8).

    Removes small bright spots while preserving shape and size.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Opened uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "morphology_open")
    return imagestag_rust.morphology_open(image, radius)


def morphology_open_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Morphological opening (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Opened float32 array with same channel count
    """
    _validate_image(image, np.float32, "morphology_open_f32")
    return imagestag_rust.morphology_open_f32(image, radius)


# ============================================================================
# Morphology Close
# ============================================================================

def morphology_close(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Morphological closing - dilation then erosion (u8).

    Fills small dark holes while preserving shape and size.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Closed uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "morphology_close")
    return imagestag_rust.morphology_close(image, radius)


def morphology_close_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Morphological closing (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Closed float32 array with same channel count
    """
    _validate_image(image, np.float32, "morphology_close_f32")
    return imagestag_rust.morphology_close_f32(image, radius)


# ============================================================================
# Morphology Gradient
# ============================================================================

def morphology_gradient(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Morphological gradient - dilation minus erosion (u8).

    Produces an outline of the object boundaries.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Gradient uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "morphology_gradient")
    return imagestag_rust.morphology_gradient(image, radius)


def morphology_gradient_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Morphological gradient (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Gradient float32 array with same channel count
    """
    _validate_image(image, np.float32, "morphology_gradient_f32")
    return imagestag_rust.morphology_gradient_f32(image, radius)


# ============================================================================
# Top Hat
# ============================================================================

def tophat(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Top-hat transform - input minus opening (u8).

    Extracts small bright elements on dark background.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Top-hat uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "tophat")
    return imagestag_rust.tophat(image, radius)


def tophat_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Top-hat transform (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Top-hat float32 array with same channel count
    """
    _validate_image(image, np.float32, "tophat_f32")
    return imagestag_rust.tophat_f32(image, radius)


# ============================================================================
# Black Hat
# ============================================================================

def blackhat(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Black-hat transform - closing minus input (u8).

    Extracts small dark elements on bright background.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Black-hat uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "blackhat")
    return imagestag_rust.blackhat(image, radius)


def blackhat_f32(image: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Black-hat transform (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Structuring element radius in pixels (0.5-100.0)

    Returns:
        Black-hat float32 array with same channel count
    """
    _validate_image(image, np.float32, "blackhat_f32")
    return imagestag_rust.blackhat_f32(image, radius)


__all__ = [
    'dilate', 'dilate_f32',
    'erode', 'erode_f32',
    'morphology_open', 'morphology_open_f32',
    'morphology_close', 'morphology_close_f32',
    'morphology_gradient', 'morphology_gradient_f32',
    'tophat', 'tophat_f32',
    'blackhat', 'blackhat_f32',
]
