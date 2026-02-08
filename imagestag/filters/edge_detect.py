"""Edge detection filters with Rust backend.

This module provides edge detection filters:
- Sobel (horizontal, vertical, or combined)
- Laplacian
- Find Edges (combined edge detection)

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

Note: Edge detection filters may produce different value ranges for u8 vs f32
due to different normalization strategies. The u8 version maps to 0-255 while
f32 uses normalized 0.0-1.0 output.

Usage:
    from imagestag.filters.edge_detect import sobel, laplacian, find_edges

    result = sobel(rgba_image, direction="both")
    result = laplacian(rgba_image, kernel_size=3)
    result = find_edges(rgba_image)
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
# Sobel
# ============================================================================

def sobel(image: np.ndarray, direction: str = "both", kernel_size: int = 3) -> np.ndarray:
    """Apply Sobel edge detection (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        direction: "h" (horizontal), "v" (vertical), or "both" (combined)
        kernel_size: 3, 5, or 7 for kernel size

    Returns:
        Edge-detected uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "sobel")
    if direction not in ("h", "v", "both"):
        raise ValueError(f"Direction must be 'h', 'v', or 'both', got {direction}")
    if kernel_size not in (3, 5, 7):
        raise ValueError(f"Kernel size must be 3, 5, or 7, got {kernel_size}")
    return imagestag_rust.sobel(image, direction, kernel_size)


def sobel_f32(image: np.ndarray, direction: str = "both", kernel_size: int = 3) -> np.ndarray:
    """Apply Sobel edge detection (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        direction: "h" (horizontal), "v" (vertical), or "both" (combined)
        kernel_size: 3, 5, or 7 for kernel size

    Returns:
        Edge-detected float32 array with same channel count
    """
    _validate_image(image, np.float32, "sobel_f32")
    if direction not in ("h", "v", "both"):
        raise ValueError(f"Direction must be 'h', 'v', or 'both', got {direction}")
    if kernel_size not in (3, 5, 7):
        raise ValueError(f"Kernel size must be 3, 5, or 7, got {kernel_size}")
    return imagestag_rust.sobel_f32(image, direction, kernel_size)


# ============================================================================
# Laplacian
# ============================================================================

def laplacian(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Apply Laplacian edge detection (u8).

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        kernel_size: 3, 5, or 7 for kernel size

    Returns:
        Edge-detected uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "laplacian")
    if kernel_size not in (3, 5, 7):
        raise ValueError(f"Kernel size must be 3, 5, or 7, got {kernel_size}")
    return imagestag_rust.laplacian(image, kernel_size)


def laplacian_f32(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Apply Laplacian edge detection (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        kernel_size: 3, 5, or 7 for kernel size

    Returns:
        Edge-detected float32 array with same channel count
    """
    _validate_image(image, np.float32, "laplacian_f32")
    if kernel_size not in (3, 5, 7):
        raise ValueError(f"Kernel size must be 3, 5, or 7, got {kernel_size}")
    return imagestag_rust.laplacian_f32(image, kernel_size)


# ============================================================================
# Find Edges
# ============================================================================

def find_edges(image: np.ndarray, sigma: float = 1.0,
               low_threshold: float = 0.1, high_threshold: float = 0.2) -> np.ndarray:
    """Find all edges in image (u8).

    Uses Canny edge detection with configurable parameters.

    Args:
        image: uint8 array with 1, 3, or 4 channels (H, W, C)
        sigma: Gaussian blur sigma (default 1.0)
        low_threshold: Low hysteresis threshold (default 0.1)
        high_threshold: High hysteresis threshold (default 0.2)

    Returns:
        Edge-detected uint8 array with same channel count
    """
    _validate_image(image, np.uint8, "find_edges")
    return imagestag_rust.find_edges(image, sigma, low_threshold, high_threshold)


def find_edges_f32(image: np.ndarray, sigma: float = 1.0,
                   low_threshold: float = 0.1, high_threshold: float = 0.2) -> np.ndarray:
    """Find all edges in image (f32).

    Args:
        image: float32 array with 1, 3, or 4 channels (H, W, C), values 0.0-1.0
        sigma: Gaussian blur sigma (default 1.0)
        low_threshold: Low hysteresis threshold (default 0.1)
        high_threshold: High hysteresis threshold (default 0.2)

    Returns:
        Edge-detected float32 array with same channel count
    """
    _validate_image(image, np.float32, "find_edges_f32")
    return imagestag_rust.find_edges_f32(image, sigma, low_threshold, high_threshold)


__all__ = [
    'sobel', 'sobel_f32',
    'laplacian', 'laplacian_f32',
    'find_edges', 'find_edges_f32',
]
