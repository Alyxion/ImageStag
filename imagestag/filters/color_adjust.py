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

Channel count is inferred from array shape. Filters process only the
channels present, avoiding unnecessary work on unused alpha.

Note: Saturation is a no-op for grayscale images (requires RGB).

ImageStag's `Image` class handles conversion from other formats (PIL,
OpenCV BGR/BGRA) before passing to these filters.

## Bit Depth Support

- **u8 (8-bit)**: Values 0-255, standard for web/display
- **f32 (float)**: Values 0.0-1.0, for HDR/linear workflows

Usage:
    from imagestag.filters.color_adjust import brightness, contrast

    # Any supported format
    result = brightness(grayscale_image, amount=0.2)  # (H, W, 1)
    result = brightness(rgb_image, amount=0.2)        # (H, W, 3)
    result = brightness(rgba_image, amount=0.2)       # (H, W, 4)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


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
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.brightness(image, amount)

    # Pure Python fallback
    channels = image.shape[2]
    color_channels = 3 if channels == 4 else channels
    offset = int(amount * 255)
    result = image.astype(np.int16)
    result[:, :, :color_channels] += offset
    result = np.clip(result, 0, 255).astype(np.uint8)
    return result


def brightness_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust image brightness (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: -1.0 (black) to 1.0 (white), 0.0 = no change

    Returns:
        Brightness-adjusted float32 array with same channel count
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.brightness_f32(image, amount)

    # Pure Python fallback
    channels = image.shape[2]
    color_channels = 3 if channels == 4 else channels
    result = image.copy()
    result[:, :, :color_channels] = np.clip(result[:, :, :color_channels] + amount, 0.0, 1.0)
    return result


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
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.contrast(image, amount)

    # Pure Python fallback
    channels = image.shape[2]
    color_channels = 3 if channels == 4 else channels
    factor = (1.0 + amount) / (1.0 - amount) if amount < 1.0 else 255.0
    result = image.astype(np.float32)
    result[:, :, :color_channels] = (result[:, :, :color_channels] - 128) * factor + 128
    result = np.clip(result, 0, 255).astype(np.uint8)
    return result


def contrast_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust image contrast (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: -1.0 (gray) to 1.0 (max contrast), 0.0 = no change

    Returns:
        Contrast-adjusted float32 array with same channel count
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.contrast_f32(image, amount)

    # Pure Python fallback
    channels = image.shape[2]
    color_channels = 3 if channels == 4 else channels
    factor = (1.0 + amount) / (1.0 - amount) if amount < 1.0 else 255.0
    result = image.copy()
    result[:, :, :color_channels] = np.clip((result[:, :, :color_channels] - 0.5) * factor + 0.5, 0.0, 1.0)
    return result


# ============================================================================
# Saturation
# ============================================================================

def saturation(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust color saturation (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)
        amount: -1.0 (grayscale) to 1.0 (max saturation), 0.0 = no change

    Returns:
        Saturation-adjusted RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.saturation(image, amount)

    # Pure Python fallback - linear interpolation with grayscale
    factor = amount + 1.0
    r = image[:, :, 0].astype(np.float32)
    g = image[:, :, 1].astype(np.float32)
    b = image[:, :, 2].astype(np.float32)
    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b

    result = image.copy()
    result[:, :, 0] = np.clip(gray + (r - gray) * factor, 0, 255).astype(np.uint8)
    result[:, :, 1] = np.clip(gray + (g - gray) * factor, 0, 255).astype(np.uint8)
    result[:, :, 2] = np.clip(gray + (b - gray) * factor, 0, 255).astype(np.uint8)
    return result


def saturation_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust color saturation (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        amount: -1.0 (grayscale) to 1.0 (max saturation), 0.0 = no change

    Returns:
        Saturation-adjusted RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.saturation_f32(image, amount)

    # Pure Python fallback
    factor = amount + 1.0
    r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b

    result = image.copy()
    result[:, :, 0] = np.clip(gray + (r - gray) * factor, 0.0, 1.0)
    result[:, :, 1] = np.clip(gray + (g - gray) * factor, 0.0, 1.0)
    result[:, :, 2] = np.clip(gray + (b - gray) * factor, 0.0, 1.0)
    return result


# ============================================================================
# Gamma
# ============================================================================

def gamma(image: np.ndarray, gamma_value: float = 1.0) -> np.ndarray:
    """Apply gamma correction (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)
        gamma_value: Gamma value (0.1-10.0), 1.0 = no change
                     <1.0 brightens, >1.0 darkens

    Returns:
        Gamma-corrected RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.gamma(image, gamma_value)

    # Pure Python fallback using lookup table
    inv_gamma = 1.0 / gamma_value
    lut = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8)
    result = image.copy()
    result[:, :, :3] = lut[image[:, :, :3]]
    return result


def gamma_f32(image: np.ndarray, gamma_value: float = 1.0) -> np.ndarray:
    """Apply gamma correction (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        gamma_value: Gamma value (0.1-10.0), 1.0 = no change

    Returns:
        Gamma-corrected RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.gamma_f32(image, gamma_value)

    # Pure Python fallback
    inv_gamma = 1.0 / gamma_value
    result = image.copy()
    result[:, :, :3] = np.power(np.clip(result[:, :, :3], 0.0, 1.0), inv_gamma)
    return result


# ============================================================================
# Exposure
# ============================================================================

def exposure(image: np.ndarray, exposure_val: float = 0.0,
             offset: float = 0.0, gamma_val: float = 1.0) -> np.ndarray:
    """Adjust exposure (u8).

    Applies: (pixel * 2^exposure + offset) ^ (1/gamma)

    Args:
        image: RGBA uint8 array (H, W, 4)
        exposure_val: Exposure adjustment in stops (-5.0 to 5.0)
        offset: Black level offset (-0.5 to 0.5)
        gamma_val: Gamma correction (0.1-10.0)

    Returns:
        Exposure-adjusted RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.exposure(image, exposure_val, offset, gamma_val)

    # Pure Python fallback
    multiplier = 2.0 ** exposure_val
    inv_gamma = 1.0 / gamma_val
    result = image.astype(np.float32) / 255.0
    result[:, :, :3] = result[:, :, :3] * multiplier + offset
    result[:, :, :3] = np.power(np.clip(result[:, :, :3], 0.0, 1.0), inv_gamma)
    result = (np.clip(result, 0.0, 1.0) * 255).astype(np.uint8)
    return result


def exposure_f32(image: np.ndarray, exposure_val: float = 0.0,
                 offset: float = 0.0, gamma_val: float = 1.0) -> np.ndarray:
    """Adjust exposure (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        exposure_val: Exposure adjustment in stops (-5.0 to 5.0)
        offset: Black level offset (-0.5 to 0.5)
        gamma_val: Gamma correction (0.1-10.0)

    Returns:
        Exposure-adjusted RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.exposure_f32(image, exposure_val, offset, gamma_val)

    # Pure Python fallback
    multiplier = 2.0 ** exposure_val
    inv_gamma = 1.0 / gamma_val
    result = image.copy()
    result[:, :, :3] = result[:, :, :3] * multiplier + offset
    result[:, :, :3] = np.power(np.clip(result[:, :, :3], 0.0, 1.0), inv_gamma)
    return result


# ============================================================================
# Invert
# ============================================================================

def invert(image: np.ndarray) -> np.ndarray:
    """Invert image colors (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)

    Returns:
        Inverted RGBA uint8 array (alpha preserved)
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.invert(image)

    # Pure Python fallback
    result = image.copy()
    result[:, :, :3] = 255 - result[:, :, :3]
    return result


def invert_f32(image: np.ndarray) -> np.ndarray:
    """Invert image colors (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0

    Returns:
        Inverted RGBA float32 array (alpha preserved)
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.invert_f32(image)

    # Pure Python fallback
    result = image.copy()
    result[:, :, :3] = 1.0 - result[:, :, :3]
    return result


__all__ = [
    'brightness', 'brightness_f32',
    'contrast', 'contrast_f32',
    'saturation', 'saturation_f32',
    'gamma', 'gamma_f32',
    'exposure', 'exposure_f32',
    'invert', 'invert_f32',
    'HAS_RUST',
]
