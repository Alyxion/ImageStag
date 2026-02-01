"""Image rotation and mirroring filters with Rust backend.

Provides exact 90-degree rotation and mirroring operations for images.

## Supported Formats

All functions support 1, 3, or 4 channel images in both u8 and f32:
- Grayscale: (H, W, 1)
- RGB: (H, W, 3)
- RGBA: (H, W, 4)

## Rotation Direction

All rotations are clockwise (CW):
- 90° CW: (x, y) -> (H - 1 - y, x)
- 180°: (x, y) -> (W - 1 - x, H - 1 - y)
- 270° CW (90° CCW): (x, y) -> (y, W - 1 - x)

Usage:
    from imagestag.filters.rotate import rotate_90_cw, rotate_180, flip_horizontal

    # Rotate 90 degrees clockwise
    rotated = rotate_90_cw(image)  # (H, W, C) -> (W, H, C)

    # Rotate 180 degrees
    rotated = rotate_180(image)  # same dimensions

    # Mirror horizontally
    mirrored = flip_horizontal(image)  # same dimensions
"""
import numpy as np

from imagestag import imagestag_rust


# ============================================================================
# 8-bit (u8) Functions
# ============================================================================

def rotate_90_cw(image: np.ndarray) -> np.ndarray:
    """Rotate image 90 degrees clockwise (u8).

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4

    Returns:
        Rotated uint8 array (W, H, C) - note dimensions are swapped
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8, got {image.dtype}")
    return imagestag_rust.rotate_90_cw(image)


def rotate_180(image: np.ndarray) -> np.ndarray:
    """Rotate image 180 degrees (u8).

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4

    Returns:
        Rotated uint8 array (H, W, C) - same dimensions
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8, got {image.dtype}")
    return imagestag_rust.rotate_180(image)


def rotate_270_cw(image: np.ndarray) -> np.ndarray:
    """Rotate image 270 degrees clockwise (90 counter-clockwise) (u8).

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4

    Returns:
        Rotated uint8 array (W, H, C) - note dimensions are swapped
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8, got {image.dtype}")
    return imagestag_rust.rotate_270_cw(image)


def rotate(image: np.ndarray, degrees: int) -> np.ndarray:
    """Rotate image by specified degrees (90, 180, or 270) (u8).

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4
        degrees: Rotation angle (must be 90, 180, or 270)

    Returns:
        Rotated uint8 array. For 90/270, dimensions are swapped.

    Raises:
        ValueError: If degrees is not 90, 180, or 270.
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8, got {image.dtype}")
    if degrees not in (90, 180, 270):
        raise ValueError(f"Degrees must be 90, 180, or 270, got {degrees}")
    return imagestag_rust.rotate(image, degrees)


def flip_horizontal(image: np.ndarray) -> np.ndarray:
    """Flip image horizontally (mirror left-right) (u8).

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4

    Returns:
        Flipped uint8 array (H, W, C) - same dimensions
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8, got {image.dtype}")
    return imagestag_rust.flip_horizontal(image)


def flip_vertical(image: np.ndarray) -> np.ndarray:
    """Flip image vertically (mirror top-bottom) (u8).

    Args:
        image: uint8 array (H, W, C) where C is 1, 3, or 4

    Returns:
        Flipped uint8 array (H, W, C) - same dimensions
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8, got {image.dtype}")
    return imagestag_rust.flip_vertical(image)


# ============================================================================
# Float (f32) Functions
# ============================================================================

def rotate_90_cw_f32(image: np.ndarray) -> np.ndarray:
    """Rotate image 90 degrees clockwise (f32).

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, C is 1, 3, or 4

    Returns:
        Rotated float32 array (W, H, C)
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32, got {image.dtype}")
    return imagestag_rust.rotate_90_cw_f32(image)


def rotate_180_f32(image: np.ndarray) -> np.ndarray:
    """Rotate image 180 degrees (f32).

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, C is 1, 3, or 4

    Returns:
        Rotated float32 array (H, W, C)
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32, got {image.dtype}")
    return imagestag_rust.rotate_180_f32(image)


def rotate_270_cw_f32(image: np.ndarray) -> np.ndarray:
    """Rotate image 270 degrees clockwise (90 counter-clockwise) (f32).

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, C is 1, 3, or 4

    Returns:
        Rotated float32 array (W, H, C)
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32, got {image.dtype}")
    return imagestag_rust.rotate_270_cw_f32(image)


def rotate_f32(image: np.ndarray, degrees: int) -> np.ndarray:
    """Rotate image by specified degrees (90, 180, or 270) (f32).

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, C is 1, 3, or 4
        degrees: Rotation angle (must be 90, 180, or 270)

    Returns:
        Rotated float32 array. For 90/270, dimensions are swapped.
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32, got {image.dtype}")
    if degrees not in (90, 180, 270):
        raise ValueError(f"Degrees must be 90, 180, or 270, got {degrees}")
    return imagestag_rust.rotate_f32(image, degrees)


def flip_horizontal_f32(image: np.ndarray) -> np.ndarray:
    """Flip image horizontally (mirror left-right) (f32).

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, C is 1, 3, or 4

    Returns:
        Flipped float32 array (H, W, C)
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32, got {image.dtype}")
    return imagestag_rust.flip_horizontal_f32(image)


def flip_vertical_f32(image: np.ndarray) -> np.ndarray:
    """Flip image vertically (mirror top-bottom) (f32).

    Args:
        image: float32 array (H, W, C) with values 0.0-1.0, C is 1, 3, or 4

    Returns:
        Flipped float32 array (H, W, C)
    """
    if image.ndim != 3 or image.shape[2] not in (1, 3, 4):
        raise ValueError(f"Expected (H, W, C) with C in [1, 3, 4], got {image.shape}")
    if image.dtype != np.float32:
        raise ValueError(f"Expected float32, got {image.dtype}")
    return imagestag_rust.flip_vertical_f32(image)
