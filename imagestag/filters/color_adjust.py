"""Color adjustment filters with Rust backend.

This module provides high-performance color adjustments:
- Brightness, Contrast, Saturation
- Gamma, Exposure
- Invert

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
    from imagestag.filters.color_adjust import brightness, contrast

    result = brightness(image, amount=0.2)
    result = contrast(image, amount=0.5)
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
# Brightness
# ============================================================================

def brightness(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust image brightness (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: -1.0 (black) to 1.0 (white), 0.0 = no change

    Returns:
        Brightness-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "brightness")
    return imagestag_rust.brightness(image, amount)


def brightness_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust image brightness (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: -1.0 (black) to 1.0 (white), 0.0 = no change

    Returns:
        Brightness-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "brightness_f32")
    return imagestag_rust.brightness_f32(image, amount)


# ============================================================================
# Contrast
# ============================================================================

def contrast(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust image contrast (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: -1.0 (gray) to 1.0 (max contrast), 0.0 = no change

    Returns:
        Contrast-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "contrast")
    return imagestag_rust.contrast(image, amount)


def contrast_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust image contrast (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: -1.0 (gray) to 1.0 (max contrast), 0.0 = no change

    Returns:
        Contrast-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "contrast_f32")
    return imagestag_rust.contrast_f32(image, amount)


# ============================================================================
# Saturation
# ============================================================================

def saturation(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust color saturation (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: -1.0 (grayscale) to 1.0 (max saturation), 0.0 = no change

    Returns:
        Saturation-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "saturation")
    return imagestag_rust.saturation(image, amount)


def saturation_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust color saturation (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: -1.0 (grayscale) to 1.0 (max saturation), 0.0 = no change

    Returns:
        Saturation-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "saturation_f32")
    return imagestag_rust.saturation_f32(image, amount)


# ============================================================================
# Gamma
# ============================================================================

def gamma(image: np.ndarray, gamma_value: float = 1.0) -> np.ndarray:
    """Apply gamma correction (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        gamma_value: Gamma value (0.1-10.0), 1.0 = no change
                     <1.0 brightens, >1.0 darkens

    Returns:
        Gamma-corrected uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "gamma")
    return imagestag_rust.gamma(image, gamma_value)


def gamma_f32(image: np.ndarray, gamma_value: float = 1.0) -> np.ndarray:
    """Apply gamma correction (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        gamma_value: Gamma value (0.1-10.0), 1.0 = no change

    Returns:
        Gamma-corrected float32 array with same channel count
    """
    _validate_image(image, np.float32, "gamma_f32")
    return imagestag_rust.gamma_f32(image, gamma_value)


# ============================================================================
# Exposure
# ============================================================================

def exposure(image: np.ndarray, exposure_val: float = 0.0,
             offset: float = 0.0, gamma_val: float = 1.0) -> np.ndarray:
    """Adjust exposure (u8).

    Applies: (pixel * 2^exposure + offset) ^ (1/gamma)

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        exposure_val: Exposure adjustment in stops (-5.0 to 5.0)
        offset: Black level offset (-0.5 to 0.5)
        gamma_val: Gamma correction (0.1-10.0)

    Returns:
        Exposure-adjusted uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "exposure")
    return imagestag_rust.exposure(image, exposure_val, offset, gamma_val)


def exposure_f32(image: np.ndarray, exposure_val: float = 0.0,
                 offset: float = 0.0, gamma_val: float = 1.0) -> np.ndarray:
    """Adjust exposure (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        exposure_val: Exposure adjustment in stops (-5.0 to 5.0)
        offset: Black level offset (-0.5 to 0.5)
        gamma_val: Gamma correction (0.1-10.0)

    Returns:
        Exposure-adjusted float32 array with same channel count
    """
    _validate_image(image, np.float32, "exposure_f32")
    return imagestag_rust.exposure_f32(image, exposure_val, offset, gamma_val)


# ============================================================================
# Invert
# ============================================================================

def invert(image: np.ndarray) -> np.ndarray:
    """Invert image colors (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)

    Returns:
        Inverted uint8 array with same channel count (alpha preserved if present)
    """
    _validate_image(image, np.uint8, "invert")
    return imagestag_rust.invert(image)


def invert_f32(image: np.ndarray) -> np.ndarray:
    """Invert image colors (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0

    Returns:
        Inverted float32 array with same channel count (alpha preserved if present)
    """
    _validate_image(image, np.float32, "invert_f32")
    return imagestag_rust.invert_f32(image)


# ============================================================================
# Equalize Histogram
# ============================================================================

def equalize_histogram(image: np.ndarray) -> np.ndarray:
    """Equalize image histogram (u8).

    Spreads out intensity values to use the full range, improving contrast.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)

    Returns:
        Histogram-equalized uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "equalize_histogram")
    return imagestag_rust.equalize_histogram(image)


def equalize_histogram_f32(image: np.ndarray) -> np.ndarray:
    """Equalize image histogram (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0

    Returns:
        Histogram-equalized float32 array with same channel count
    """
    _validate_image(image, np.float32, "equalize_histogram_f32")
    return imagestag_rust.equalize_histogram_f32(image)


__all__ = [
    'brightness', 'brightness_f32',
    'contrast', 'contrast_f32',
    'saturation', 'saturation_f32',
    'gamma', 'gamma_f32',
    'exposure', 'exposure_f32',
    'invert', 'invert_f32',
    'equalize_histogram', 'equalize_histogram_f32',
]
