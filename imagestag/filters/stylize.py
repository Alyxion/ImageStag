"""Stylize filters with Rust backend.

This module provides artistic effect filters:
- Posterize
- Solarize
- Threshold
- Emboss

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
    from imagestag.filters.stylize import posterize, solarize, threshold, emboss

    result = posterize(rgba_image, levels=4)
    result = solarize(rgba_image, threshold=128)
    result = threshold(rgba_image, threshold=128)
    result = emboss(rgba_image, angle=135.0, depth=1.0)
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
# Posterize
# ============================================================================

def posterize(image: np.ndarray, levels: int = 4) -> np.ndarray:
    """Reduce color levels / posterize (u8).

    Quantizes each channel to the specified number of levels.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        levels: Number of levels per channel (2-256)

    Returns:
        Posterized uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "posterize")
    return imagestag_rust.posterize(image, levels)


def posterize_f32(image: np.ndarray, levels: int = 4) -> np.ndarray:
    """Reduce color levels / posterize (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        levels: Number of levels per channel (2-256)

    Returns:
        Posterized float32 array with same channel count
    """
    _validate_image(image, np.float32, "posterize_f32")
    return imagestag_rust.posterize_f32(image, levels)


# ============================================================================
# Solarize
# ============================================================================

def solarize(image: np.ndarray, threshold: int = 128) -> np.ndarray:
    """Apply solarize effect (u8).

    Inverts pixels above the threshold, creating a part-negative effect.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        threshold: Inversion threshold (0-255)

    Returns:
        Solarized uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "solarize")
    return imagestag_rust.solarize(image, threshold)


def solarize_f32(image: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Apply solarize effect (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        threshold: Inversion threshold (0.0-1.0)

    Returns:
        Solarized float32 array with same channel count
    """
    _validate_image(image, np.float32, "solarize_f32")
    return imagestag_rust.solarize_f32(image, threshold)


# ============================================================================
# Threshold
# ============================================================================

def threshold(image: np.ndarray, threshold_val: int = 128) -> np.ndarray:
    """Apply binary threshold (u8).

    Converts to black/white based on luminance threshold.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        threshold_val: Luminance threshold (0-255)

    Returns:
        Thresholded uint8 array (black or white)
    """
    _validate_image(image, np.uint8, "threshold")
    return imagestag_rust.threshold(image, threshold_val)


def threshold_f32(image: np.ndarray, threshold_val: float = 0.5) -> np.ndarray:
    """Apply binary threshold (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        threshold_val: Luminance threshold (0.0-1.0)

    Returns:
        Thresholded float32 array (0.0 or 1.0)
    """
    _validate_image(image, np.float32, "threshold_f32")
    return imagestag_rust.threshold_f32(image, threshold_val)


# ============================================================================
# Emboss
# ============================================================================

def emboss(image: np.ndarray, angle: float = 135.0, depth: float = 1.0) -> np.ndarray:
    """Apply emboss effect (u8).

    Creates a 3D embossed appearance using directional lighting.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        angle: Light angle in degrees (0-360), 135 = upper-left
        depth: Emboss depth/strength (0.1-10.0)

    Returns:
        Embossed uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "emboss")
    return imagestag_rust.emboss(image, angle, depth)


def emboss_f32(image: np.ndarray, angle: float = 135.0, depth: float = 1.0) -> np.ndarray:
    """Apply emboss effect (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        angle: Light angle in degrees (0-360), 135 = upper-left
        depth: Emboss depth/strength (0.1-10.0)

    Returns:
        Embossed float32 array with same channel count
    """
    _validate_image(image, np.float32, "emboss_f32")
    return imagestag_rust.emboss_f32(image, angle, depth)


__all__ = [
    'posterize', 'posterize_f32',
    'solarize', 'solarize_f32',
    'threshold', 'threshold_f32',
    'emboss', 'emboss_f32',
]
