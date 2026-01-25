"""Color science filters with Rust backend.

This module provides HSL-based color adjustments:
- Hue Shift
- Vibrance
- Color Balance

## Input Format

These filters operate on **numpy RGBA arrays only**:
- Shape: (height, width, 4) - always 4 channels (RGBA)
- u8: dtype=np.uint8, values 0-255
- f32: dtype=np.float32, values 0.0-1.0

ImageStag's `Image` class can convert from other formats (PIL, OpenCV BGR/BGRA,
numpy RGB) to RGBA before applying filters.

## Bit Depth Support

- **u8 (8-bit)**: Values 0-255, standard for web/display
- **f32 (float)**: Values 0.0-1.0, for HDR/linear workflows

Both versions use identical Rust implementations for cross-platform parity.

Usage:
    from imagestag.filters.color_science import hue_shift, vibrance, color_balance

    result = hue_shift(rgba_image, degrees=45.0)
    result = vibrance(rgba_image, amount=0.5)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ============================================================================
# RGB <-> HSL Conversion Helpers (for Python fallback)
# ============================================================================

def _rgb_to_hsl(r: float, g: float, b: float) -> tuple:
    """Convert RGB (0-1) to HSL (0-1)."""
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    l = (max_c + min_c) / 2.0

    if max_c == min_c:
        h = s = 0.0
    else:
        d = max_c - min_c
        s = d / (2.0 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)

        if max_c == r:
            h = (g - b) / d + (6.0 if g < b else 0.0)
        elif max_c == g:
            h = (b - r) / d + 2.0
        else:
            h = (r - g) / d + 4.0
        h /= 6.0

    return h, s, l


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple:
    """Convert HSL (0-1) to RGB (0-1)."""
    if s == 0.0:
        return l, l, l

    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    r = hue_to_rgb(p, q, h + 1/3)
    g = hue_to_rgb(p, q, h)
    b = hue_to_rgb(p, q, h - 1/3)

    return r, g, b


# ============================================================================
# Hue Shift
# ============================================================================

def hue_shift(image: np.ndarray, degrees: float = 0.0) -> np.ndarray:
    """Shift image hue (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)
        degrees: Hue rotation in degrees (0-360)

    Returns:
        Hue-shifted RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.hue_shift(image, degrees)

    # Pure Python fallback
    h, w = image.shape[:2]
    result = image.copy()
    shift = (degrees % 360.0) / 360.0

    for y in range(h):
        for x in range(w):
            r, g, b = image[y, x, :3] / 255.0
            hue, sat, light = _rgb_to_hsl(r, g, b)
            hue = (hue + shift) % 1.0
            r, g, b = _hsl_to_rgb(hue, sat, light)
            result[y, x, 0] = int(np.clip(r * 255, 0, 255))
            result[y, x, 1] = int(np.clip(g * 255, 0, 255))
            result[y, x, 2] = int(np.clip(b * 255, 0, 255))

    return result


def hue_shift_f32(image: np.ndarray, degrees: float = 0.0) -> np.ndarray:
    """Shift image hue (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        degrees: Hue rotation in degrees (0-360)

    Returns:
        Hue-shifted RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.hue_shift_f32(image, degrees)

    # Pure Python fallback
    h, w = image.shape[:2]
    result = image.copy()
    shift = (degrees % 360.0) / 360.0

    for y in range(h):
        for x in range(w):
            r, g, b = image[y, x, :3]
            hue, sat, light = _rgb_to_hsl(r, g, b)
            hue = (hue + shift) % 1.0
            r, g, b = _hsl_to_rgb(hue, sat, light)
            result[y, x, 0] = np.clip(r, 0.0, 1.0)
            result[y, x, 1] = np.clip(g, 0.0, 1.0)
            result[y, x, 2] = np.clip(b, 0.0, 1.0)

    return result


# ============================================================================
# Vibrance
# ============================================================================

def vibrance(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust vibrance - smart saturation (u8).

    Unlike saturation, vibrance boosts less-saturated colors more,
    preserving already-vibrant colors (especially skin tones).

    Args:
        image: RGBA uint8 array (H, W, 4)
        amount: -1.0 (desaturate) to 1.0 (boost), 0.0 = no change

    Returns:
        Vibrance-adjusted RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.vibrance(image, amount)

    # Pure Python fallback
    result = image.astype(np.float32)
    r, g, b = result[:, :, 0], result[:, :, 1], result[:, :, 2]

    # Current saturation approximation
    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    current_sat = (max_rgb - min_rgb) / (max_rgb + 1e-6)

    # Boost factor: higher for less saturated pixels
    boost = amount * (1.0 - current_sat)

    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b
    result[:, :, 0] = np.clip(gray + (r - gray) * (1.0 + boost), 0, 255)
    result[:, :, 1] = np.clip(gray + (g - gray) * (1.0 + boost), 0, 255)
    result[:, :, 2] = np.clip(gray + (b - gray) * (1.0 + boost), 0, 255)

    return result.astype(np.uint8)


def vibrance_f32(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Adjust vibrance - smart saturation (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        amount: -1.0 (desaturate) to 1.0 (boost), 0.0 = no change

    Returns:
        Vibrance-adjusted RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.vibrance_f32(image, amount)

    # Pure Python fallback
    result = image.copy()
    r, g, b = result[:, :, 0], result[:, :, 1], result[:, :, 2]

    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    current_sat = (max_rgb - min_rgb) / (max_rgb + 1e-6)

    boost = amount * (1.0 - current_sat)

    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b
    result[:, :, 0] = np.clip(gray + (r - gray) * (1.0 + boost), 0.0, 1.0)
    result[:, :, 1] = np.clip(gray + (g - gray) * (1.0 + boost), 0.0, 1.0)
    result[:, :, 2] = np.clip(gray + (b - gray) * (1.0 + boost), 0.0, 1.0)

    return result


# ============================================================================
# Color Balance
# ============================================================================

def color_balance(image: np.ndarray,
                  shadows: tuple = (0.0, 0.0, 0.0),
                  midtones: tuple = (0.0, 0.0, 0.0),
                  highlights: tuple = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Adjust color balance for shadows, midtones, highlights (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)
        shadows: RGB adjustments for shadows (-1.0 to 1.0 each)
        midtones: RGB adjustments for midtones (-1.0 to 1.0 each)
        highlights: RGB adjustments for highlights (-1.0 to 1.0 each)

    Returns:
        Color-balanced RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.color_balance(
            image,
            list(shadows),
            list(midtones),
            list(highlights)
        )

    # Pure Python fallback
    result = image.astype(np.float32)

    for c in range(3):
        channel = result[:, :, c] / 255.0

        # Shadow weight: higher for dark pixels
        shadow_weight = 1.0 - channel
        # Highlight weight: higher for bright pixels
        highlight_weight = channel
        # Midtone weight: bell curve, highest around 0.5
        midtone_weight = 1.0 - np.abs(channel - 0.5) * 2

        adjustment = (
            shadow_weight * shadows[c] +
            midtone_weight * midtones[c] +
            highlight_weight * highlights[c]
        )

        result[:, :, c] = np.clip((channel + adjustment) * 255, 0, 255)

    return result.astype(np.uint8)


def color_balance_f32(image: np.ndarray,
                      shadows: tuple = (0.0, 0.0, 0.0),
                      midtones: tuple = (0.0, 0.0, 0.0),
                      highlights: tuple = (0.0, 0.0, 0.0)) -> np.ndarray:
    """Adjust color balance for shadows, midtones, highlights (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        shadows: RGB adjustments for shadows (-1.0 to 1.0 each)
        midtones: RGB adjustments for midtones (-1.0 to 1.0 each)
        highlights: RGB adjustments for highlights (-1.0 to 1.0 each)

    Returns:
        Color-balanced RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.color_balance_f32(
            image,
            list(shadows),
            list(midtones),
            list(highlights)
        )

    # Pure Python fallback
    result = image.copy()

    for c in range(3):
        channel = result[:, :, c]

        shadow_weight = 1.0 - channel
        highlight_weight = channel
        midtone_weight = 1.0 - np.abs(channel - 0.5) * 2

        adjustment = (
            shadow_weight * shadows[c] +
            midtone_weight * midtones[c] +
            highlight_weight * highlights[c]
        )

        result[:, :, c] = np.clip(channel + adjustment, 0.0, 1.0)

    return result


__all__ = [
    'hue_shift', 'hue_shift_f32',
    'vibrance', 'vibrance_f32',
    'color_balance', 'color_balance_f32',
    'HAS_RUST',
]
