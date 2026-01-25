"""Sharpen and blur filters with Rust backend.

This module provides sharpening and related spatial filters:
- Sharpen
- Unsharp Mask
- High Pass
- Motion Blur

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
    from imagestag.filters.sharpen_filters import sharpen, unsharp_mask, high_pass

    result = sharpen(rgba_image, amount=1.0)
    result = unsharp_mask(rgba_image, amount=1.5, radius=2.0, threshold=5)
    result = high_pass(rgba_image, radius=3.0)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ============================================================================
# Sharpen
# ============================================================================

def sharpen(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Sharpen image using convolution (u8).

    Uses a 3x3 sharpening kernel.

    Args:
        image: RGBA uint8 array (H, W, 4)
        amount: Sharpening strength (0.0-10.0), 1.0 = standard

    Returns:
        Sharpened RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.sharpen(image, amount)

    # Pure Python fallback using 3x3 sharpen kernel
    # kernel = [0, -1, 0, -1, 5, -1, 0, -1, 0] for amount=1.0
    center = 1.0 + 4.0 * amount
    edge = -amount

    h, w = image.shape[:2]
    result = image.copy().astype(np.float32)

    for c in range(3):
        channel = image[:, :, c].astype(np.float32)
        output = np.zeros((h, w), dtype=np.float32)

        for y in range(1, h - 1):
            for x in range(1, w - 1):
                val = (
                    channel[y - 1, x] * edge +
                    channel[y + 1, x] * edge +
                    channel[y, x - 1] * edge +
                    channel[y, x + 1] * edge +
                    channel[y, x] * center
                )
                output[y, x] = val

        # Copy edges
        output[0, :] = channel[0, :]
        output[-1, :] = channel[-1, :]
        output[:, 0] = channel[:, 0]
        output[:, -1] = channel[:, -1]

        result[:, :, c] = np.clip(output, 0, 255)

    return result.astype(np.uint8)


def sharpen_f32(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Sharpen image using convolution (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        amount: Sharpening strength (0.0-10.0), 1.0 = standard

    Returns:
        Sharpened RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.sharpen_f32(image, amount)

    # Pure Python fallback
    center = 1.0 + 4.0 * amount
    edge = -amount

    h, w = image.shape[:2]
    result = image.copy()

    for c in range(3):
        channel = image[:, :, c]
        output = np.zeros((h, w), dtype=np.float32)

        for y in range(1, h - 1):
            for x in range(1, w - 1):
                val = (
                    channel[y - 1, x] * edge +
                    channel[y + 1, x] * edge +
                    channel[y, x - 1] * edge +
                    channel[y, x + 1] * edge +
                    channel[y, x] * center
                )
                output[y, x] = val

        output[0, :] = channel[0, :]
        output[-1, :] = channel[-1, :]
        output[:, 0] = channel[:, 0]
        output[:, -1] = channel[:, -1]

        result[:, :, c] = np.clip(output, 0.0, 1.0)

    return result


# ============================================================================
# Unsharp Mask
# ============================================================================

def _gaussian_blur_channel(channel: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur to a single channel (Python fallback)."""
    if sigma <= 0:
        return channel.copy()

    # Build 1D Gaussian kernel
    radius = int(np.ceil(sigma * 3))
    size = radius * 2 + 1
    kernel = np.exp(-np.arange(-radius, radius + 1) ** 2 / (2 * sigma ** 2))
    kernel = kernel / kernel.sum()

    # Separable convolution
    h, w = channel.shape

    # Horizontal pass
    temp = np.zeros_like(channel)
    for y in range(h):
        for x in range(w):
            val = 0.0
            for k in range(-radius, radius + 1):
                sx = min(max(x + k, 0), w - 1)
                val += channel[y, sx] * kernel[k + radius]
            temp[y, x] = val

    # Vertical pass
    result = np.zeros_like(channel)
    for y in range(h):
        for x in range(w):
            val = 0.0
            for k in range(-radius, radius + 1):
                sy = min(max(y + k, 0), h - 1)
                val += temp[sy, x] * kernel[k + radius]
            result[y, x] = val

    return result


def unsharp_mask(image: np.ndarray, amount: float = 1.0,
                 radius: float = 1.0, threshold: int = 0) -> np.ndarray:
    """Apply unsharp mask sharpening (u8).

    Subtracts a blurred version to enhance edges.

    Args:
        image: RGBA uint8 array (H, W, 4)
        amount: Sharpening amount (0.0-10.0)
        radius: Blur radius in pixels (0.1-100.0)
        threshold: Minimum difference to sharpen (0-255)

    Returns:
        Sharpened RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.unsharp_mask(image, amount, radius, threshold)

    # Pure Python fallback
    result = image.copy().astype(np.float32)

    for c in range(3):
        original = image[:, :, c].astype(np.float32)
        blurred = _gaussian_blur_channel(original, radius)

        diff = original - blurred
        mask = np.abs(diff) >= threshold
        sharpened = original + diff * amount * mask

        result[:, :, c] = np.clip(sharpened, 0, 255)

    return result.astype(np.uint8)


def unsharp_mask_f32(image: np.ndarray, amount: float = 1.0,
                     radius: float = 1.0, threshold: float = 0.0) -> np.ndarray:
    """Apply unsharp mask sharpening (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        amount: Sharpening amount (0.0-10.0)
        radius: Blur radius in pixels (0.1-100.0)
        threshold: Minimum difference to sharpen (0.0-1.0)

    Returns:
        Sharpened RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.unsharp_mask_f32(image, amount, radius, threshold)

    # Pure Python fallback
    result = image.copy()

    for c in range(3):
        original = image[:, :, c]
        blurred = _gaussian_blur_channel(original, radius)

        diff = original - blurred
        mask = np.abs(diff) >= threshold
        sharpened = original + diff * amount * mask

        result[:, :, c] = np.clip(sharpened, 0.0, 1.0)

    return result


# ============================================================================
# High Pass
# ============================================================================

def high_pass(image: np.ndarray, radius: float = 3.0) -> np.ndarray:
    """Apply high-pass filter (u8).

    Extracts edges and fine details by subtracting blurred image.
    Result is centered at 128 (gray).

    Args:
        image: RGBA uint8 array (H, W, 4)
        radius: Blur radius in pixels (0.1-100.0)

    Returns:
        High-pass filtered RGBA uint8 array (gray = no detail)
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.high_pass(image, radius)

    # Pure Python fallback
    result = np.zeros_like(image, dtype=np.float32)

    for c in range(3):
        original = image[:, :, c].astype(np.float32)
        blurred = _gaussian_blur_channel(original, radius)
        result[:, :, c] = (original - blurred) + 128

    result[:, :, :3] = np.clip(result[:, :, :3], 0, 255)
    result[:, :, 3] = image[:, :, 3]
    return result.astype(np.uint8)


def high_pass_f32(image: np.ndarray, radius: float = 3.0) -> np.ndarray:
    """Apply high-pass filter (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        radius: Blur radius in pixels (0.1-100.0)

    Returns:
        High-pass filtered RGBA float32 array (0.5 = no detail)
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.high_pass_f32(image, radius)

    # Pure Python fallback
    result = np.zeros_like(image)

    for c in range(3):
        original = image[:, :, c]
        blurred = _gaussian_blur_channel(original, radius)
        result[:, :, c] = np.clip((original - blurred) + 0.5, 0.0, 1.0)

    result[:, :, 3] = image[:, :, 3]
    return result


# ============================================================================
# Motion Blur
# ============================================================================

def motion_blur(image: np.ndarray, angle: float = 0.0,
                distance: float = 10.0) -> np.ndarray:
    """Apply motion blur (u8).

    Simulates camera motion during exposure.

    Args:
        image: RGBA uint8 array (H, W, 4)
        angle: Motion direction in degrees (0 = horizontal right)
        distance: Blur distance in pixels (1-100)

    Returns:
        Motion-blurred RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.motion_blur(image, angle, distance)

    # Pure Python fallback
    import math
    rad = math.radians(angle)
    dx = math.cos(rad)
    dy = math.sin(rad)

    length = int(distance)
    if length < 1:
        return image.copy()

    h, w = image.shape[:2]
    result = np.zeros_like(image, dtype=np.float32)

    for c in range(3):
        channel = image[:, :, c].astype(np.float32)

        for y in range(h):
            for x in range(w):
                total = 0.0
                count = 0
                for i in range(-length // 2, length // 2 + 1):
                    sx = int(x + i * dx)
                    sy = int(y + i * dy)
                    if 0 <= sx < w and 0 <= sy < h:
                        total += channel[sy, sx]
                        count += 1
                result[y, x, c] = total / count if count > 0 else channel[y, x]

    result[:, :, 3] = image[:, :, 3]
    return np.clip(result, 0, 255).astype(np.uint8)


def motion_blur_f32(image: np.ndarray, angle: float = 0.0,
                    distance: float = 10.0) -> np.ndarray:
    """Apply motion blur (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        angle: Motion direction in degrees (0 = horizontal right)
        distance: Blur distance in pixels (1-100)

    Returns:
        Motion-blurred RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.motion_blur_f32(image, angle, distance)

    # Pure Python fallback
    import math
    rad = math.radians(angle)
    dx = math.cos(rad)
    dy = math.sin(rad)

    length = int(distance)
    if length < 1:
        return image.copy()

    h, w = image.shape[:2]
    result = np.zeros_like(image)

    for c in range(3):
        channel = image[:, :, c]

        for y in range(h):
            for x in range(w):
                total = 0.0
                count = 0
                for i in range(-length // 2, length // 2 + 1):
                    sx = int(x + i * dx)
                    sy = int(y + i * dy)
                    if 0 <= sx < w and 0 <= sy < h:
                        total += channel[sy, sx]
                        count += 1
                result[y, x, c] = total / count if count > 0 else channel[y, x]

    result[:, :, 3] = image[:, :, 3]
    return result


__all__ = [
    'sharpen', 'sharpen_f32',
    'unsharp_mask', 'unsharp_mask_f32',
    'high_pass', 'high_pass_f32',
    'motion_blur', 'motion_blur_f32',
    'HAS_RUST',
]
