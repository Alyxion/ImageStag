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


# ============================================================================
# Sepia
# ============================================================================

def sepia(image: np.ndarray, intensity: float = 1.0) -> np.ndarray:
    """Apply sepia tone effect (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        intensity: Sepia intensity (0.0 = no effect, 1.0 = full sepia)

    Returns:
        Sepia-toned uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "sepia")
    return imagestag_rust.sepia(image, intensity)


def sepia_f32(image: np.ndarray, intensity: float = 1.0) -> np.ndarray:
    """Apply sepia tone effect (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        intensity: Sepia intensity (0.0 = no effect, 1.0 = full sepia)

    Returns:
        Sepia-toned float32 array with same channel count
    """
    _validate_image(image, np.float32, "sepia_f32")
    return imagestag_rust.sepia_f32(image, intensity)


# ============================================================================
# Temperature
# ============================================================================

def temperature(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust color temperature (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: Temperature shift (-1.0 = cool/blue, 1.0 = warm/orange)

    Returns:
        Temperature-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "temperature")
    return imagestag_rust.temperature(image, amount)


def temperature_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust color temperature (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: Temperature shift (-1.0 = cool/blue, 1.0 = warm/orange)

    Returns:
        Temperature-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "temperature_f32")
    return imagestag_rust.temperature_f32(image, amount)


# ============================================================================
# Channel Mixer
# ============================================================================

def channel_mixer(image: np.ndarray, r_src: int = 0, g_src: int = 1, b_src: int = 2) -> np.ndarray:
    """Remap color channels (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        r_src: Source channel index for red output (0=R, 1=G, 2=B)
        g_src: Source channel index for green output (0=R, 1=G, 2=B)
        b_src: Source channel index for blue output (0=R, 1=G, 2=B)

    Returns:
        Channel-remapped uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "channel_mixer")
    return imagestag_rust.channel_mixer(image, r_src, g_src, b_src)


def channel_mixer_f32(image: np.ndarray, r_src: int = 0, g_src: int = 1, b_src: int = 2) -> np.ndarray:
    """Remap color channels (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        r_src: Source channel index for red output (0=R, 1=G, 2=B)
        g_src: Source channel index for green output (0=R, 1=G, 2=B)
        b_src: Source channel index for blue output (0=R, 1=G, 2=B)

    Returns:
        Channel-remapped float32 array with same channel count
    """
    _validate_image(image, np.float32, "channel_mixer_f32")
    return imagestag_rust.channel_mixer_f32(image, r_src, g_src, b_src)


__all__ = [
    'hue_shift', 'hue_shift_f32',
    'vibrance', 'vibrance_f32',
    'color_balance', 'color_balance_f32',
    'sepia', 'sepia_f32',
    'temperature', 'temperature_f32',
    'channel_mixer', 'channel_mixer_f32',
]
