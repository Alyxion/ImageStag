"""Noise filters with Rust backend.

This module provides noise manipulation filters:
- Add Noise (Gaussian or uniform)
- Median (noise reduction)
- Denoise (non-local means)

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
    from imagestag.filters.noise_filters import add_noise, median, denoise

    result = add_noise(image, amount=0.1, gaussian=True)
    result = median(image, radius=2)
    result = denoise(image, strength=0.5)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


def _validate_image(image: np.ndarray, expected_dtype: type, name: str) -> None:
    """Validate image shape and dtype."""
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected image (H, W, 1|3|4), got shape {image.shape}")
    if image.dtype != expected_dtype:
        raise ValueError(f"Expected {expected_dtype} dtype, got {image.dtype}")


# ============================================================================
# Add Noise
# ============================================================================

def add_noise(
    image: np.ndarray,
    amount: float = 0.1,
    gaussian: bool = True,
    monochrome: bool = False,
    seed: int = 0,
) -> np.ndarray:
    """Add noise to image (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        amount: Noise intensity (0.0-1.0)
        gaussian: Use Gaussian noise (True) or uniform noise (False)
        monochrome: Apply same noise to all channels (grayscale noise)
        seed: Random seed for reproducibility (0 = random)

    Returns:
        Noisy uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "add_noise")

    if HAS_RUST:
        return imagestag_rust.add_noise(image, amount, gaussian, monochrome, seed)

    # Pure Python fallback
    rng = np.random.default_rng(seed if seed > 0 else None)
    h, w, c = image.shape
    color_channels = 3 if c == 4 else c

    if gaussian:
        noise_scale = amount * 128
        if monochrome:
            noise = rng.normal(0, noise_scale, (h, w, 1)).astype(np.float32)
            noise = np.repeat(noise, color_channels, axis=2)
        else:
            noise = rng.normal(0, noise_scale, (h, w, color_channels)).astype(np.float32)
    else:
        noise_range = amount * 255
        if monochrome:
            noise = rng.uniform(-noise_range, noise_range, (h, w, 1)).astype(np.float32)
            noise = np.repeat(noise, color_channels, axis=2)
        else:
            noise = rng.uniform(-noise_range, noise_range, (h, w, color_channels)).astype(np.float32)

    result = image.astype(np.float32)
    result[:, :, :color_channels] += noise
    result = np.clip(result, 0, 255).astype(np.uint8)
    return result


def add_noise_f32(
    image: np.ndarray,
    amount: float = 0.1,
    gaussian: bool = True,
    monochrome: bool = False,
    seed: int = 0,
) -> np.ndarray:
    """Add noise to image (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        amount: Noise intensity (0.0-1.0)
        gaussian: Use Gaussian noise (True) or uniform noise (False)
        monochrome: Apply same noise to all channels (grayscale noise)
        seed: Random seed for reproducibility (0 = random)

    Returns:
        Noisy float32 array with same channel count
    """
    _validate_image(image, np.float32, "add_noise_f32")

    if HAS_RUST:
        return imagestag_rust.add_noise_f32(image, amount, gaussian, monochrome, seed)

    # Pure Python fallback
    rng = np.random.default_rng(seed if seed > 0 else None)
    h, w, c = image.shape
    color_channels = 3 if c == 4 else c

    if gaussian:
        noise_scale = amount * 0.5
        if monochrome:
            noise = rng.normal(0, noise_scale, (h, w, 1)).astype(np.float32)
            noise = np.repeat(noise, color_channels, axis=2)
        else:
            noise = rng.normal(0, noise_scale, (h, w, color_channels)).astype(np.float32)
    else:
        if monochrome:
            noise = rng.uniform(-amount, amount, (h, w, 1)).astype(np.float32)
            noise = np.repeat(noise, color_channels, axis=2)
        else:
            noise = rng.uniform(-amount, amount, (h, w, color_channels)).astype(np.float32)

    result = image.copy()
    result[:, :, :color_channels] = np.clip(result[:, :, :color_channels] + noise, 0.0, 1.0)
    return result


# ============================================================================
# Median Filter
# ============================================================================

def median(image: np.ndarray, radius: int = 1) -> np.ndarray:
    """Apply median filter for noise reduction (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        radius: Filter radius (1 = 3x3 window, 2 = 5x5, etc.)

    Returns:
        Filtered uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "median")

    if HAS_RUST:
        return imagestag_rust.median(image, radius)

    # Pure Python fallback using scipy
    from scipy.ndimage import median_filter
    h, w, c = image.shape
    color_channels = 3 if c == 4 else c
    size = 2 * radius + 1

    result = image.copy()
    for ch in range(color_channels):
        result[:, :, ch] = median_filter(image[:, :, ch], size=size)
    return result


def median_f32(image: np.ndarray, radius: int = 1) -> np.ndarray:
    """Apply median filter for noise reduction (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Filter radius (1 = 3x3 window, 2 = 5x5, etc.)

    Returns:
        Filtered float32 array with same channel count
    """
    _validate_image(image, np.float32, "median_f32")

    if HAS_RUST:
        return imagestag_rust.median_f32(image, radius)

    # Pure Python fallback using scipy
    from scipy.ndimage import median_filter
    h, w, c = image.shape
    color_channels = 3 if c == 4 else c
    size = 2 * radius + 1

    result = image.copy()
    for ch in range(color_channels):
        result[:, :, ch] = median_filter(image[:, :, ch], size=size)
    return result


# ============================================================================
# Denoise (Non-local Means)
# ============================================================================

def denoise(image: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """Apply denoising filter (u8).

    Uses a simplified non-local means approach that averages
    nearby pixels based on color similarity.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        strength: Denoising strength (0.0-1.0)

    Returns:
        Denoised uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "denoise")

    if HAS_RUST:
        return imagestag_rust.denoise(image, strength)

    # Pure Python fallback - simple bilateral-like filter
    from scipy.ndimage import gaussian_filter
    h, w, c = image.shape
    color_channels = 3 if c == 4 else c
    sigma = 1.0 + strength * 2.0

    result = image.copy()
    for ch in range(color_channels):
        result[:, :, ch] = gaussian_filter(image[:, :, ch].astype(np.float32), sigma=sigma).astype(np.uint8)
    return result


def denoise_f32(image: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """Apply denoising filter (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        strength: Denoising strength (0.0-1.0)

    Returns:
        Denoised float32 array with same channel count
    """
    _validate_image(image, np.float32, "denoise_f32")

    if HAS_RUST:
        return imagestag_rust.denoise_f32(image, strength)

    # Pure Python fallback
    from scipy.ndimage import gaussian_filter
    h, w, c = image.shape
    color_channels = 3 if c == 4 else c
    sigma = 1.0 + strength * 2.0

    result = image.copy()
    for ch in range(color_channels):
        result[:, :, ch] = gaussian_filter(image[:, :, ch], sigma=sigma)
    return result


__all__ = [
    'add_noise', 'add_noise_f32',
    'median', 'median_f32',
    'denoise', 'denoise_f32',
    'HAS_RUST',
]
