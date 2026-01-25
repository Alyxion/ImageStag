"""Edge detection filters with Rust backend.

This module provides edge detection filters:
- Sobel (horizontal, vertical, or combined)
- Laplacian
- Find Edges (combined edge detection)

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
    from imagestag.filters.edge_detect import sobel, laplacian, find_edges

    result = sobel(rgba_image, direction="both")
    result = laplacian(rgba_image, kernel_size=3)
    result = find_edges(rgba_image)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ============================================================================
# Sobel
# ============================================================================

def sobel(image: np.ndarray, direction: str = "both") -> np.ndarray:
    """Apply Sobel edge detection (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)
        direction: "h" (horizontal), "v" (vertical), or "both" (combined)

    Returns:
        Edge-detected RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if direction not in ("h", "v", "both"):
        raise ValueError(f"Direction must be 'h', 'v', or 'both', got {direction}")

    if HAS_RUST:
        return imagestag_rust.sobel(image, direction)

    # Pure Python fallback
    # Sobel kernels
    sobel_h = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_v = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)

    h, w = image.shape[:2]

    # Convert to grayscale
    gray = (0.2126 * image[:, :, 0].astype(np.float32) +
            0.7152 * image[:, :, 1].astype(np.float32) +
            0.0722 * image[:, :, 2].astype(np.float32))

    result = np.zeros((h, w), dtype=np.float32)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            gx = gy = 0.0

            if direction in ("h", "both"):
                for ky in range(-1, 2):
                    for kx in range(-1, 2):
                        gx += gray[y + ky, x + kx] * sobel_h[ky + 1, kx + 1]

            if direction in ("v", "both"):
                for ky in range(-1, 2):
                    for kx in range(-1, 2):
                        gy += gray[y + ky, x + kx] * sobel_v[ky + 1, kx + 1]

            if direction == "both":
                result[y, x] = np.sqrt(gx * gx + gy * gy)
            elif direction == "h":
                result[y, x] = abs(gx)
            else:
                result[y, x] = abs(gy)

    result = np.clip(result, 0, 255).astype(np.uint8)
    return np.stack([result, result, result, image[:, :, 3]], axis=2)


def sobel_f32(image: np.ndarray, direction: str = "both") -> np.ndarray:
    """Apply Sobel edge detection (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        direction: "h" (horizontal), "v" (vertical), or "both" (combined)

    Returns:
        Edge-detected RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if direction not in ("h", "v", "both"):
        raise ValueError(f"Direction must be 'h', 'v', or 'both', got {direction}")

    if HAS_RUST:
        return imagestag_rust.sobel_f32(image, direction)

    # Pure Python fallback
    sobel_h = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 4.0
    sobel_v = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32) / 4.0

    h, w = image.shape[:2]
    gray = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    result = np.zeros((h, w), dtype=np.float32)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            gx = gy = 0.0

            if direction in ("h", "both"):
                for ky in range(-1, 2):
                    for kx in range(-1, 2):
                        gx += gray[y + ky, x + kx] * sobel_h[ky + 1, kx + 1]

            if direction in ("v", "both"):
                for ky in range(-1, 2):
                    for kx in range(-1, 2):
                        gy += gray[y + ky, x + kx] * sobel_v[ky + 1, kx + 1]

            if direction == "both":
                result[y, x] = np.sqrt(gx * gx + gy * gy)
            elif direction == "h":
                result[y, x] = abs(gx)
            else:
                result[y, x] = abs(gy)

    result = np.clip(result, 0.0, 1.0)
    return np.stack([result, result, result, image[:, :, 3]], axis=2)


# ============================================================================
# Laplacian
# ============================================================================

def laplacian(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Apply Laplacian edge detection (u8).

    Args:
        image: RGBA uint8 array (H, W, 4)
        kernel_size: 3 or 5 for kernel size

    Returns:
        Edge-detected RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if kernel_size not in (3, 5):
        raise ValueError(f"Kernel size must be 3 or 5, got {kernel_size}")

    if HAS_RUST:
        return imagestag_rust.laplacian(image, kernel_size)

    # Pure Python fallback
    if kernel_size == 3:
        kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)
    else:  # 5x5
        kernel = np.array([
            [0, 0, -1, 0, 0],
            [0, -1, -2, -1, 0],
            [-1, -2, 16, -2, -1],
            [0, -1, -2, -1, 0],
            [0, 0, -1, 0, 0]
        ], dtype=np.float32)

    h, w = image.shape[:2]
    radius = kernel_size // 2

    gray = (0.2126 * image[:, :, 0].astype(np.float32) +
            0.7152 * image[:, :, 1].astype(np.float32) +
            0.0722 * image[:, :, 2].astype(np.float32))

    result = np.zeros((h, w), dtype=np.float32)

    for y in range(radius, h - radius):
        for x in range(radius, w - radius):
            val = 0.0
            for ky in range(-radius, radius + 1):
                for kx in range(-radius, radius + 1):
                    val += gray[y + ky, x + kx] * kernel[ky + radius, kx + radius]
            result[y, x] = abs(val)

    result = np.clip(result, 0, 255).astype(np.uint8)
    return np.stack([result, result, result, image[:, :, 3]], axis=2)


def laplacian_f32(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Apply Laplacian edge detection (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        kernel_size: 3 or 5 for kernel size

    Returns:
        Edge-detected RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if kernel_size not in (3, 5):
        raise ValueError(f"Kernel size must be 3 or 5, got {kernel_size}")

    if HAS_RUST:
        return imagestag_rust.laplacian_f32(image, kernel_size)

    # Pure Python fallback
    if kernel_size == 3:
        kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32) / 4.0
    else:
        kernel = np.array([
            [0, 0, -1, 0, 0],
            [0, -1, -2, -1, 0],
            [-1, -2, 16, -2, -1],
            [0, -1, -2, -1, 0],
            [0, 0, -1, 0, 0]
        ], dtype=np.float32) / 16.0

    h, w = image.shape[:2]
    radius = kernel_size // 2

    gray = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    result = np.zeros((h, w), dtype=np.float32)

    for y in range(radius, h - radius):
        for x in range(radius, w - radius):
            val = 0.0
            for ky in range(-radius, radius + 1):
                for kx in range(-radius, radius + 1):
                    val += gray[y + ky, x + kx] * kernel[ky + radius, kx + radius]
            result[y, x] = abs(val)

    result = np.clip(result, 0.0, 1.0)
    return np.stack([result, result, result, image[:, :, 3]], axis=2)


# ============================================================================
# Find Edges
# ============================================================================

def find_edges(image: np.ndarray) -> np.ndarray:
    """Find all edges in image (u8).

    Combines multiple edge detection methods for comprehensive edge finding.

    Args:
        image: RGBA uint8 array (H, W, 4)

    Returns:
        Edge-detected RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.find_edges(image)

    # Pure Python fallback - use Sobel with both directions
    return sobel(image, "both")


def find_edges_f32(image: np.ndarray) -> np.ndarray:
    """Find all edges in image (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0

    Returns:
        Edge-detected RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.find_edges_f32(image)

    # Pure Python fallback
    return sobel_f32(image, "both")


__all__ = [
    'sobel', 'sobel_f32',
    'laplacian', 'laplacian_f32',
    'find_edges', 'find_edges_f32',
    'HAS_RUST',
]
