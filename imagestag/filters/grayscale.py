"""Grayscale filter with Rust backend.

This module provides a high-performance grayscale conversion using
ITU-R BT.709 luminosity coefficients.

Usage:
    from imagestag.filters.grayscale import grayscale

    # Convert RGBA numpy array
    result = grayscale(rgba_image)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


def grayscale(image: np.ndarray) -> np.ndarray:
    """Convert RGBA image to grayscale.

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


__all__ = ['grayscale', 'HAS_RUST']
