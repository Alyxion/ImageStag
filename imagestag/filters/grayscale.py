"""Grayscale filter with Rust backend.

This module provides a high-performance grayscale conversion using
ITU-R BT.709 luminosity coefficients.

## Bit Depth Support

- **u8 (8-bit)**: Values 0-255, standard for web/display
- **f32 (float)**: Values 0.0-1.0, for HDR/linear workflows

Both versions use identical Rust implementations.

Usage:
    from imagestag.filters.grayscale import grayscale, grayscale_f32

    # Convert RGBA numpy array (u8)
    result = grayscale(rgba_image)

    # Convert RGBA numpy array (f32)
    result_f32 = grayscale_f32(rgba_image_f32)
"""
import numpy as np

from imagestag import imagestag_rust


# ============================================================================
# 8-bit (u8) Functions
# ============================================================================

def grayscale(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale (u8).

    Uses ITU-R BT.709 luminosity coefficients:
    Y = 0.2126*R + 0.7152*G + 0.0722*B

    Supports 1, 3, or 4 channel inputs. Output has same channel count as input.

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4

    Returns:
        Grayscale uint8 array (H, W, C) with R=G=B=luminosity
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, C) with C in (1, 3, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    return imagestag_rust.grayscale_rgba(image)


# ============================================================================
# Float (f32) Functions
# ============================================================================

def grayscale_f32(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale (f32).

    Uses ITU-R BT.709 luminosity coefficients (same as u8 version).
    Input/output values are 0.0-1.0.

    Supports 1, 3, or 4 channel inputs. Output has same channel count as input.

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, where C is 1, 3, or 4

    Returns:
        Grayscale float32 array (H, W, C) with R=G=B=luminosity
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, C) with C in (1, 3, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    return imagestag_rust.grayscale_rgba_f32(image)


# ============================================================================
# Conversion Utilities
# ============================================================================

def convert_u8_to_f32(image: np.ndarray) -> np.ndarray:
    """Convert u8 image (0-255) to f32 (0.0-1.0).

    Args:
        image: uint8 array

    Returns:
        float32 array with values 0.0-1.0
    """
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    return imagestag_rust.convert_u8_to_f32(image)


def convert_f32_to_u8(image: np.ndarray) -> np.ndarray:
    """Convert f32 image (0.0-1.0) to u8 (0-255).

    Args:
        image: float32 array with values 0.0-1.0

    Returns:
        uint8 array with values 0-255
    """
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    return imagestag_rust.convert_f32_to_u8(image)


def convert_f32_to_12bit(image: np.ndarray) -> np.ndarray:
    """Convert f32 image (0.0-1.0) to 12-bit (0-4095).

    Args:
        image: float32 array with values 0.0-1.0

    Returns:
        uint16 array with values 0-4095
    """
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    return imagestag_rust.convert_f32_to_12bit(image)


def convert_12bit_to_f32(image: np.ndarray) -> np.ndarray:
    """Convert 12-bit image (0-4095) to f32 (0.0-1.0).

    Args:
        image: uint16 array with values 0-4095

    Returns:
        float32 array with values 0.0-1.0
    """
    if image.dtype != np.uint16:
        raise ValueError(f"Expected uint16 dtype, got {image.dtype}")

    return imagestag_rust.convert_12bit_to_f32(image)


__all__ = [
    'grayscale', 'grayscale_f32',
    'convert_u8_to_f32', 'convert_f32_to_u8',
    'convert_f32_to_12bit', 'convert_12bit_to_f32',
]
