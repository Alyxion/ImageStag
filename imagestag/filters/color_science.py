"""Color science filters with Rust backend.

This module provides HSL-based color adjustments:
- Hue Shift
- Vibrance
- Color Balance

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
    from imagestag.filters.color_science import hue_shift, vibrance, color_balance

    result = hue_shift(image, degrees=45.0)
    result = vibrance(image, amount=0.5)
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
# Hue Shift
# ============================================================================

def hue_shift(image: np.ndarray, degrees: float = 0.0) -> np.ndarray:
    """Shift image hue (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        degrees: Hue rotation in degrees (-180 to 180)

    Returns:
        Hue-shifted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "hue_shift")
    return imagestag_rust.hue_shift(image, degrees)


def hue_shift_f32(image: np.ndarray, degrees: float = 0.0) -> np.ndarray:
    """Shift image hue (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        degrees: Hue rotation in degrees (-180 to 180)

    Returns:
        Hue-shifted float32 array with same channel count
    """
    _validate_image(image, np.float32, "hue_shift_f32")
    return imagestag_rust.hue_shift_f32(image, degrees)


# ============================================================================
# Vibrance
# ============================================================================

def vibrance(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust vibrance - smart saturation (u8).

    Unlike saturation, vibrance boosts less-saturated colors more,
    preserving already-vibrant colors (especially skin tones).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: -1.0 (desaturate) to 1.0 (boost), 0.0 = no change

    Returns:
        Vibrance-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "vibrance")
    return imagestag_rust.vibrance(image, amount)


def vibrance_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust vibrance - smart saturation (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: -1.0 (desaturate) to 1.0 (boost), 0.0 = no change

    Returns:
        Vibrance-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "vibrance_f32")
    return imagestag_rust.vibrance_f32(image, amount)


# ============================================================================
# Color Balance
# ============================================================================

def color_balance(image: np.ndarray,
                  shadows: tuple = (0.0, 0.0, 0.0),
                  midtones: tuple = (0.0, 0.0, 0.0),
                  highlights: tuple = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Adjust color balance for shadows, midtones, highlights (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        shadows: RGB adjustments for shadows (-1.0 to 1.0 each)
        midtones: RGB adjustments for midtones (-1.0 to 1.0 each)
        highlights: RGB adjustments for highlights (-1.0 to 1.0 each)

    Returns:
        Color-balanced uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "color_balance")
    return imagestag_rust.color_balance(
        image,
        list(shadows),
        list(midtones),
        list(highlights)
    )


def color_balance_f32(image: np.ndarray,
                      shadows: tuple = (0.0, 0.0, 0.0),
                      midtones: tuple = (0.0, 0.0, 0.0),
                      highlights: tuple = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Adjust color balance for shadows, midtones, highlights (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        shadows: RGB adjustments for shadows (-1.0 to 1.0 each)
        midtones: RGB adjustments for midtones (-1.0 to 1.0 each)
        highlights: RGB adjustments for highlights (-1.0 to 1.0 each)

    Returns:
        Color-balanced float32 array with same channel count
    """
    _validate_image(image, np.float32, "color_balance_f32")
    return imagestag_rust.color_balance_f32(
        image,
        list(shadows),
        list(midtones),
        list(highlights)
    )


__all__ = [
    'hue_shift', 'hue_shift_f32',
    'vibrance', 'vibrance_f32',
    'color_balance', 'color_balance_f32',
]
