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

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ============================================================================
# 8-bit (u8) Functions
# ============================================================================

def grayscale(image: np.ndarray) -> np.ndarray:
    """Convert RGBA image to grayscale (u8).

    Uses ITU-R BT.709 luminosity coefficients:
    Y = 0.2126*R + 0.7152*G + 0.0722*B

    Args:
        image: RGBA uint8 array (H, W, 4)

    Returns:
        Grayscale RGBA uint8 array (H, W, 4) with R=G=B=luminosity
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.grayscale_rgba(image)

    # Pure Python fallback
    r = image[:, :, 0].astype(np.float32)
    g = image[:, :, 1].astype(np.float32)
    b = image[:, :, 2].astype(np.float32)
    gray = (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(np.uint8)
    result = np.stack([gray, gray, gray, image[:, :, 3]], axis=2)
    return result


# ============================================================================
# Float (f32) Functions
# ============================================================================

def grayscale_f32(image: np.ndarray) -> np.ndarray:
    """Convert RGBA image to grayscale (f32).

    Uses ITU-R BT.709 luminosity coefficients (same as u8 version).
    Input/output values are 0.0-1.0.

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0

    Returns:
        Grayscale RGBA float32 array (H, W, 4) with R=G=B=luminosity
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.grayscale_rgba_f32(image)

    # Pure Python fallback
    r = image[:, :, 0]
    g = image[:, :, 1]
    b = image[:, :, 2]
    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b
    result = np.stack([gray, gray, gray, image[:, :, 3]], axis=2)
    return result


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

    if HAS_RUST:
        return imagestag_rust.convert_u8_to_f32(image)

    return image.astype(np.float32) / 255.0


def convert_f32_to_u8(image: np.ndarray) -> np.ndarray:
    """Convert f32 image (0.0-1.0) to u8 (0-255).

    Args:
        image: float32 array with values 0.0-1.0

    Returns:
        uint8 array with values 0-255
    """
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.convert_f32_to_u8(image)

    return np.clip(image * 255.0, 0, 255).astype(np.uint8)


def convert_f32_to_12bit(image: np.ndarray) -> np.ndarray:
    """Convert f32 image (0.0-1.0) to 12-bit (0-4095).

    Args:
        image: float32 array with values 0.0-1.0

    Returns:
        uint16 array with values 0-4095
    """
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.convert_f32_to_12bit(image)

    return np.clip(image * 4095.0, 0, 4095).astype(np.uint16)


def convert_12bit_to_f32(image: np.ndarray) -> np.ndarray:
    """Convert 12-bit image (0-4095) to f32 (0.0-1.0).

    Args:
        image: uint16 array with values 0-4095

    Returns:
        float32 array with values 0.0-1.0
    """
    if image.dtype != np.uint16:
        raise ValueError(f"Expected uint16 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.convert_12bit_to_f32(image)

    return image.astype(np.float32) / 4095.0


__all__ = [
    'grayscale', 'grayscale_f32',
    'convert_u8_to_f32', 'convert_f32_to_u8',
    'convert_f32_to_12bit', 'convert_12bit_to_f32',
    'HAS_RUST',
]
