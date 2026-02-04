"""Levels and curves filters with Rust backend.

This module provides tonal adjustment filters:
- Levels (input/output range mapping with gamma)
- Curves (spline-based tonal adjustment)
- Auto Levels (histogram stretch)

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
    from imagestag.filters.levels_curves import levels, curves, auto_levels

    result = levels(image, in_black=20, in_white=240)
    result = curves(image, points=[(0, 0), (0.25, 0.2), (0.75, 0.8), (1, 1)])
    result = auto_levels(image, clip_percent=0.5)
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
# Levels
# ============================================================================

def levels(image: np.ndarray,
           in_black: int = 0,
           in_white: int = 255,
           out_black: int = 0,
           out_white: int = 255,
           gamma: float = 1.0) -> np.ndarray:
    """Apply levels adjustment (u8).

    Maps input range [in_black, in_white] to output range [out_black, out_white]
    with optional gamma correction.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        in_black: Input black point (0-255)
        in_white: Input white point (0-255)
        out_black: Output black point (0-255)
        out_white: Output white point (0-255)
        gamma: Gamma correction (0.1-10.0), 1.0 = linear

    Returns:
        Levels-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "levels")
    return imagestag_rust.levels(image, in_black, in_white, out_black, out_white, gamma)


def levels_f32(image: np.ndarray,
               in_black: float = 0.0,
               in_white: float = 1.0,
               out_black: float = 0.0,
               out_white: float = 1.0,
               gamma: float = 1.0) -> np.ndarray:
    """Apply levels adjustment (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        in_black: Input black point (0.0-1.0)
        in_white: Input white point (0.0-1.0)
        out_black: Output black point (0.0-1.0)
        out_white: Output white point (0.0-1.0)
        gamma: Gamma correction (0.1-10.0), 1.0 = linear

    Returns:
        Levels-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "levels_f32")
    return imagestag_rust.levels_f32(image, in_black, in_white, out_black, out_white, gamma)


# ============================================================================
# Curves
# ============================================================================

def curves(image: np.ndarray, points: list) -> np.ndarray:
    """Apply curves adjustment (u8).

    Uses Catmull-Rom spline interpolation through control points.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        points: List of (input, output) tuples, values 0.0-1.0
                Example: [(0, 0), (0.25, 0.2), (0.75, 0.8), (1, 1)]

    Returns:
        Curves-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "curves")
    return imagestag_rust.curves(image, points)


def curves_f32(image: np.ndarray, points: list) -> np.ndarray:
    """Apply curves adjustment (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        points: List of (input, output) tuples, values 0.0-1.0
                Example: [(0, 0), (0.25, 0.2), (0.75, 0.8), (1, 1)]

    Returns:
        Curves-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "curves_f32")
    return imagestag_rust.curves_f32(image, points)


# ============================================================================
# Auto Levels
# ============================================================================

def auto_levels(image: np.ndarray, clip_percent: float = 0.0) -> np.ndarray:
    """Apply auto levels / histogram stretch (u8).

    Automatically stretches the histogram to use the full 0-255 range.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        clip_percent: Percentage to clip from each end (0.0-50.0)
                      Higher values ignore outliers for more robust results

    Returns:
        Auto-leveled uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "auto_levels")
    return imagestag_rust.auto_levels(image, clip_percent)


def auto_levels_f32(image: np.ndarray, clip_percent: float = 0.0) -> np.ndarray:
    """Apply auto levels / histogram stretch (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        clip_percent: Percentage to clip from each end (0.0-50.0)

    Returns:
        Auto-leveled float32 array with same channel count
    """
    _validate_image(image, np.float32, "auto_levels_f32")
    return imagestag_rust.auto_levels_f32(image, clip_percent)


__all__ = [
    'levels', 'levels_f32',
    'curves', 'curves_f32',
    'auto_levels', 'auto_levels_f32',
]
