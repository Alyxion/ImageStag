"""Levels and curves filters with Rust backend.

This module provides tonal adjustment filters:
- Levels (input/output range mapping with gamma)
- Curves (spline-based tonal adjustment)
- Auto Levels (histogram stretch)

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
    from imagestag.filters.levels_curves import levels, curves, auto_levels

    result = levels(rgba_image, in_black=20, in_white=240)
    result = curves(rgba_image, points=[(0, 0), (0.25, 0.2), (0.75, 0.8), (1, 1)])
    result = auto_levels(rgba_image, clip_percent=0.5)
"""
import numpy as np

try:
    from imagestag import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ============================================================================
# Levels
# ============================================================================

def levels(image: np.ndarray,
           in_black: int = 0,
           in_white: int = 255,
           out_black: int = 0,
           out_white: int = 255,
           gamma: float = 1.0) -> np.ndarray:
    """Apply levels adjustment (u8).

    Maps input range [in_black, in_white] to output range [out_black, out_white]
    with optional gamma correction.

    Args:
        image: RGBA uint8 array (H, W, 4)
        in_black: Input black point (0-255)
        in_white: Input white point (0-255)
        out_black: Output black point (0-255)
        out_white: Output white point (0-255)
        gamma: Gamma correction (0.1-10.0), 1.0 = linear

    Returns:
        Levels-adjusted RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.levels(image, in_black, in_white, out_black, out_white, gamma)

    # Pure Python fallback
    in_range = max(in_white - in_black, 1)
    out_range = out_white - out_black
    inv_gamma = 1.0 / gamma

    result = image.astype(np.float32)
    for c in range(3):
        normalized = (result[:, :, c] - in_black) / in_range
        normalized = np.clip(normalized, 0.0, 1.0)
        gamma_corrected = np.power(normalized, inv_gamma)
        result[:, :, c] = gamma_corrected * out_range + out_black

    return np.clip(result, 0, 255).astype(np.uint8)


def levels_f32(image: np.ndarray,
               in_black: float = 0.0,
               in_white: float = 1.0,
               out_black: float = 0.0,
               out_white: float = 1.0,
               gamma: float = 1.0) -> np.ndarray:
    """Apply levels adjustment (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        in_black: Input black point (0.0-1.0)
        in_white: Input white point (0.0-1.0)
        out_black: Output black point (0.0-1.0)
        out_white: Output white point (0.0-1.0)
        gamma: Gamma correction (0.1-10.0), 1.0 = linear

    Returns:
        Levels-adjusted RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.levels_f32(image, in_black, in_white, out_black, out_white, gamma)

    # Pure Python fallback
    in_range = max(in_white - in_black, 0.001)
    out_range = out_white - out_black
    inv_gamma = 1.0 / gamma

    result = image.copy()
    for c in range(3):
        normalized = (result[:, :, c] - in_black) / in_range
        normalized = np.clip(normalized, 0.0, 1.0)
        gamma_corrected = np.power(normalized, inv_gamma)
        result[:, :, c] = np.clip(gamma_corrected * out_range + out_black, 0.0, 1.0)

    return result


# ============================================================================
# Curves
# ============================================================================

def _catmull_rom_spline(points: list, t: float) -> float:
    """Evaluate Catmull-Rom spline at t."""
    if not points:
        return t

    # Add implicit endpoints if needed
    pts = list(points)
    if pts[0][0] > 0:
        pts.insert(0, (0.0, 0.0))
    if pts[-1][0] < 1:
        pts.append((1.0, 1.0))

    # Find segment
    for i in range(len(pts) - 1):
        if pts[i][0] <= t <= pts[i + 1][0]:
            # Get 4 control points
            p0 = pts[max(i - 1, 0)]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[min(i + 2, len(pts) - 1)]

            # Normalize t to segment
            seg_range = p2[0] - p1[0]
            if seg_range < 0.001:
                return p1[1]
            local_t = (t - p1[0]) / seg_range

            # Catmull-Rom coefficients
            t2 = local_t * local_t
            t3 = t2 * local_t

            result = 0.5 * (
                (2 * p1[1]) +
                (-p0[1] + p2[1]) * local_t +
                (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
            )
            return max(0.0, min(1.0, result))

    return t


def curves(image: np.ndarray, points: list) -> np.ndarray:
    """Apply curves adjustment (u8).

    Uses Catmull-Rom spline interpolation through control points.

    Args:
        image: RGBA uint8 array (H, W, 4)
        points: List of (input, output) tuples, values 0-255
                Example: [(0, 0), (64, 50), (192, 210), (255, 255)]

    Returns:
        Curves-adjusted RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        # Convert to 0-255 format for Rust
        return imagestag_rust.curves(image, points)

    # Pure Python fallback - build LUT
    # Convert points to 0-1 range
    norm_points = [(p[0] / 255.0, p[1] / 255.0) for p in points]
    lut = np.array([
        int(_catmull_rom_spline(norm_points, i / 255.0) * 255)
        for i in range(256)
    ], dtype=np.uint8)

    result = image.copy()
    result[:, :, :3] = lut[image[:, :, :3]]
    return result


def curves_f32(image: np.ndarray, points: list) -> np.ndarray:
    """Apply curves adjustment (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        points: List of (input, output) tuples, values 0.0-1.0
                Example: [(0, 0), (0.25, 0.2), (0.75, 0.8), (1, 1)]

    Returns:
        Curves-adjusted RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.curves_f32(image, points)

    # Pure Python fallback
    h, w = image.shape[:2]
    result = image.copy()

    for y in range(h):
        for x in range(w):
            for c in range(3):
                v = image[y, x, c]
                result[y, x, c] = _catmull_rom_spline(points, v)

    return result


# ============================================================================
# Auto Levels
# ============================================================================

def auto_levels(image: np.ndarray, clip_percent: float = 0.0) -> np.ndarray:
    """Apply auto levels / histogram stretch (u8).

    Automatically stretches the histogram to use the full 0-255 range.

    Args:
        image: RGBA uint8 array (H, W, 4)
        clip_percent: Percentage to clip from each end (0.0-50.0)
                      Higher values ignore outliers for more robust results

    Returns:
        Auto-leveled RGBA uint8 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.uint8:
        raise ValueError(f"Expected uint8 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.auto_levels(image, clip_percent)

    # Pure Python fallback
    result = image.copy()
    clip = clip_percent / 100.0

    for c in range(3):
        channel = image[:, :, c].flatten()

        if clip > 0:
            low = np.percentile(channel, clip * 100)
            high = np.percentile(channel, (1 - clip) * 100)
        else:
            low = channel.min()
            high = channel.max()

        if high > low:
            scale = 255.0 / (high - low)
            result[:, :, c] = np.clip((image[:, :, c].astype(np.float32) - low) * scale, 0, 255).astype(np.uint8)

    return result


def auto_levels_f32(image: np.ndarray, clip_percent: float = 0.0) -> np.ndarray:
    """Apply auto levels / histogram stretch (f32).

    Args:
        image: RGBA float32 array (H, W, 4) with values 0.0-1.0
        clip_percent: Percentage to clip from each end (0.0-50.0)

    Returns:
        Auto-leveled RGBA float32 array
    """
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Expected RGBA image (H, W, 4), got shape {image.shape}")

    if image.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {image.dtype}")

    if HAS_RUST:
        return imagestag_rust.auto_levels_f32(image, clip_percent)

    # Pure Python fallback
    result = image.copy()
    clip = clip_percent / 100.0

    for c in range(3):
        channel = image[:, :, c].flatten()

        if clip > 0:
            low = np.percentile(channel, clip * 100)
            high = np.percentile(channel, (1 - clip) * 100)
        else:
            low = channel.min()
            high = channel.max()

        if high > low:
            scale = 1.0 / (high - low)
            result[:, :, c] = np.clip((image[:, :, c] - low) * scale, 0.0, 1.0)

    return result


__all__ = [
    'levels', 'levels_f32',
    'curves', 'curves_f32',
    'auto_levels', 'auto_levels_f32',
    'HAS_RUST',
]
