"""Stylize filters with Rust backend.

This module provides artistic effect filters:
- Posterize
- Solarize
- Threshold
- Emboss

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
    from imagestag.filters.stylize import posterize, solarize, threshold, emboss

    result = posterize(rgba_image, levels=4)
    result = solarize(rgba_image, threshold=128)
    result = threshold(rgba_image, threshold=128)
    result = emboss(rgba_image, angle=135.0, depth=1.0)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ============================================================================
# Posterize
# ============================================================================

def posterize(image: np.ndarray, levels: int = 4) -> np.ndarray:
    """Reduce color levels / posterize (u8).

    Quantizes each channel to the specified number of levels.

    Args:
        image: RGBA uint8 array (H, W, 4)
        levels: Number of levels per channel (2-256)

    Returns:
        Posterized RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.posterize(image, levels)

    # Pure Python fallback
    levels = max(2, min(256, levels))
    divisor = 256 // levels
    multiplier = 255 // (levels - 1)

    result = image.copy()
    result[:, :, :3] = ((image[:, :, :3] // divisor) * multiplier).astype(np.uint8)
    return result


def posterize_f32(image: np.ndarray, levels: int = 4) -> np.ndarray:
    """Reduce color levels / posterize (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        levels: Number of levels per channel (2-256)

    Returns:
        Posterized RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.posterize_f32(image, levels)

    # Pure Python fallback
    levels = max(2, min(256, levels))
    step = 1.0 / levels

    result = image.copy()
    result[:, :, :3] = np.floor(image[:, :, :3] / step) / (levels - 1)
    result[:, :, :3] = np.clip(result[:, :, :3], 0.0, 1.0)
    return result


# ============================================================================
# Solarize
# ============================================================================

def solarize(image: np.ndarray, threshold: int = 128) -> np.ndarray:
    """Apply solarize effect (u8).

    Inverts pixels above the threshold, creating a part-negative effect.

    Args:
        image: RGBA uint8 array (H, W, 4)
        threshold: Inversion threshold (0-255)

    Returns:
        Solarized RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.solarize(image, threshold)

    # Pure Python fallback
    result = image.copy()
    mask = image[:, :, :3] >= threshold
    result[:, :, :3] = np.where(mask, 255 - image[:, :, :3], image[:, :, :3])
    return result


def solarize_f32(image: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Apply solarize effect (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        threshold: Inversion threshold (0.0-1.0)

    Returns:
        Solarized RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.solarize_f32(image, threshold)

    # Pure Python fallback
    result = image.copy()
    mask = image[:, :, :3] >= threshold
    result[:, :, :3] = np.where(mask, 1.0 - image[:, :, :3], image[:, :, :3])
    return result


# ============================================================================
# Threshold
# ============================================================================

def threshold(image: np.ndarray, threshold_val: int = 128) -> np.ndarray:
    """Apply binary threshold (u8).

    Converts to black/white based on luminance threshold.

    Args:
        image: RGBA uint8 array (H, W, 4)
        threshold_val: Luminance threshold (0-255)

    Returns:
        Thresholded RGBA uint8 array (black or white)
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.threshold(image, threshold_val)

    # Pure Python fallback
    r = image[:, :, 0].astype(np.float32)
    g = image[:, :, 1].astype(np.float32)
    b = image[:, :, 2].astype(np.float32)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    white = (lum >= threshold_val).astype(np.uint8) * 255
    result = np.stack([white, white, white, image[:, :, 3]], axis=2)
    return result


def threshold_f32(image: np.ndarray, threshold_val: float = 0.5) -> np.ndarray:
    """Apply binary threshold (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        threshold_val: Luminance threshold (0.0-1.0)

    Returns:
        Thresholded RGBA float32 array (0.0 or 1.0)
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.threshold_f32(image, threshold_val)

    # Pure Python fallback
    r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    white = (lum >= threshold_val).astype(np.float32)
    result = np.stack([white, white, white, image[:, :, 3]], axis=2)
    return result


# ============================================================================
# Emboss
# ============================================================================

def emboss(image: np.ndarray, angle: float = 135.0, depth: float = 1.0) -> np.ndarray:
    """Apply emboss effect (u8).

    Creates a 3D embossed appearance using directional lighting.

    Args:
        image: RGBA uint8 array (H, W, 4)
        angle: Light angle in degrees (0-360), 135 = upper-left
        depth: Emboss depth/strength (0.1-10.0)

    Returns:
        Embossed RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.emboss(image, angle, depth)

    # Pure Python fallback using 3x3 emboss kernel
    import math
    rad = math.radians(angle)
    dx = math.cos(rad) * depth
    dy = math.sin(rad) * depth

    # Build emboss kernel based on angle
    kernel = np.array([
        [-dy - dx, -dy, -dy + dx],
        [-dx, 1, dx],
        [dy - dx, dy, dy + dx]
    ], dtype=np.float32)

    h, w = image.shape[:2]
    result = np.zeros_like(image)

    # Convert to grayscale for processing
    gray = (0.2126 * image[:, :, 0].astype(np.float32) +
            0.7152 * image[:, :, 1].astype(np.float32) +
            0.0722 * image[:, :, 2].astype(np.float32))

    # Apply convolution
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            val = 128.0
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    val += gray[y + ky, x + kx] * kernel[ky + 1, kx + 1]
            val = np.clip(val, 0, 255)
            result[y, x, 0] = result[y, x, 1] = result[y, x, 2] = int(val)

    result[:, :, 3] = image[:, :, 3]
    return result


def emboss_f32(image: np.ndarray, angle: float = 135.0, depth: float = 1.0) -> np.ndarray:
    """Apply emboss effect (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        angle: Light angle in degrees (0-360), 135 = upper-left
        depth: Emboss depth/strength (0.1-10.0)

    Returns:
        Embossed RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.emboss_f32(image, angle, depth)

    # Pure Python fallback
    import math
    rad = math.radians(angle)
    dx = math.cos(rad) * depth
    dy = math.sin(rad) * depth

    kernel = np.array([
        [-dy - dx, -dy, -dy + dx],
        [-dx, 1, dx],
        [dy - dx, dy, dy + dx]
    ], dtype=np.float32)

    h, w = image.shape[:2]
    result = np.zeros_like(image)

    gray = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            val = 0.5
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    val += gray[y + ky, x + kx] * kernel[ky + 1, kx + 1]
            val = np.clip(val, 0.0, 1.0)
            result[y, x, 0] = result[y, x, 1] = result[y, x, 2] = val

    result[:, :, 3] = image[:, :, 3]
    return result


__all__ = [
    'posterize', 'posterize_f32',
    'solarize', 'solarize_f32',
    'threshold', 'threshold_f32',
    'emboss', 'emboss_f32',
    'HAS_RUST',
]
