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

from imagestag import imagestag_rust


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
    return imagestag_rust.add_noise(image, amount, gaussian, monochrome, seed)


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
    return imagestag_rust.add_noise_f32(image, amount, gaussian, monochrome, seed)


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
    return imagestag_rust.median(image, radius)


def median_f32(image: np.ndarray, radius: int = 1) -> np.ndarray:
    """Apply median filter for noise reduction (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        radius: Filter radius (1 = 3x3 window, 2 = 5x5, etc.)

    Returns:
        Filtered float32 array with same channel count
    """
    _validate_image(image, np.float32, "median_f32")
    return imagestag_rust.median_f32(image, radius)


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
    return imagestag_rust.denoise(image, strength)


def denoise_f32(image: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """Apply denoising filter (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        strength: Denoising strength (0.0-1.0)

    Returns:
        Denoised float32 array with same channel count
    """
    _validate_image(image, np.float32, "denoise_f32")
    return imagestag_rust.denoise_f32(image, strength)


__all__ = [
    'add_noise', 'add_noise_f32',
    'median', 'median_f32',
    'denoise', 'denoise_f32',
]
