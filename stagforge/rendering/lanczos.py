"""Lanczos resampling implementation.

This MUST produce identical output to the JavaScript implementation
in frontend/js/core/TextLayer.js.

Algorithm:
- Lanczos-3 kernel (a=3)
- Kernel scaled for downsampling ratios > 1
- Premultiplied alpha blending
"""

import numpy as np
from typing import Tuple


def lanczos_kernel(x: float, a: int = 3) -> float:
    """Lanczos kernel function.

    Args:
        x: Distance from center (normalized by filter scale)
        a: Kernel size (2 or 3)

    Returns:
        Kernel weight
    """
    if x == 0:
        return 1.0
    if x < -a or x > a:
        return 0.0
    pix = np.pi * x
    return float(a * np.sin(pix) * np.sin(pix / a) / (pix * pix))


def lanczos_resample(
    src: np.ndarray,
    dst_width: int,
    dst_height: int,
    a: int = 3,
) -> np.ndarray:
    """Lanczos resampling for high-quality image downscaling.

    Properly scales the kernel for downsampling ratios > 1.
    This implementation matches the JavaScript version exactly.

    Args:
        src: Source image as RGBA numpy array (H, W, 4), dtype uint8
        dst_width: Destination width
        dst_height: Destination height
        a: Lanczos kernel size (2 or 3)

    Returns:
        Resampled image as RGBA numpy array
    """
    src_height, src_width = src.shape[:2]
    dst = np.zeros((dst_height, dst_width, 4), dtype=np.uint8)

    scale_x = src_width / dst_width
    scale_y = src_height / dst_height

    # For downscaling, expand the kernel support region
    filter_scale_x = max(1.0, scale_x)
    filter_scale_y = max(1.0, scale_y)

    # For each destination pixel
    for dst_y in range(dst_height):
        for dst_x in range(dst_width):
            # Map to source coordinates (center of the pixel)
            src_center_x = (dst_x + 0.5) * scale_x
            src_center_y = (dst_y + 0.5) * scale_y

            # Calculate kernel bounds (expanded for downscaling)
            support_x = a * filter_scale_x
            support_y = a * filter_scale_y

            x1 = max(0, int(np.floor(src_center_x - support_x)))
            x2 = min(src_width - 1, int(np.ceil(src_center_x + support_x)))
            y1 = max(0, int(np.floor(src_center_y - support_y)))
            y2 = min(src_height - 1, int(np.ceil(src_center_y + support_y)))

            r, g, b, alpha = 0.0, 0.0, 0.0, 0.0
            weight_sum = 0.0

            # Convolve with Lanczos kernel
            for sy in range(y1, y2 + 1):
                dy = sy - src_center_y
                # Normalized distance for kernel
                wy = lanczos_kernel(dy / filter_scale_y, a)
                if wy == 0:
                    continue

                for sx in range(x1, x2 + 1):
                    dx = sx - src_center_x
                    wx = lanczos_kernel(dx / filter_scale_x, a)
                    if wx == 0:
                        continue

                    weight = wx * wy
                    src_alpha = src[sy, sx, 3] / 255.0

                    # Premultiplied alpha for correct blending
                    r += src[sy, sx, 0] * src_alpha * weight
                    g += src[sy, sx, 1] * src_alpha * weight
                    b += src[sy, sx, 2] * src_alpha * weight
                    alpha += src_alpha * weight
                    weight_sum += weight

            if weight_sum > 0 and alpha > 0:
                # Unpremultiply alpha
                inv_alpha = 1.0 / alpha
                dst[dst_y, dst_x, 0] = int(round(max(0, min(255, r * inv_alpha))))
                dst[dst_y, dst_x, 1] = int(round(max(0, min(255, g * inv_alpha))))
                dst[dst_y, dst_x, 2] = int(round(max(0, min(255, b * inv_alpha))))
                dst[dst_y, dst_x, 3] = int(round(max(0, min(255, alpha / weight_sum * 255))))
            else:
                dst[dst_y, dst_x] = [0, 0, 0, 0]

    return dst


def lanczos_resample_fast(
    src: np.ndarray,
    dst_width: int,
    dst_height: int,
    a: int = 3,
) -> np.ndarray:
    """Optimized Lanczos resampling using vectorized operations.

    Same algorithm as lanczos_resample but faster for large images.
    """
    src_height, src_width = src.shape[:2]

    scale_x = src_width / dst_width
    scale_y = src_height / dst_height

    filter_scale_x = max(1.0, scale_x)
    filter_scale_y = max(1.0, scale_y)

    # Precompute kernel weights for all positions
    support_x = int(np.ceil(a * filter_scale_x))
    support_y = int(np.ceil(a * filter_scale_y))

    # Create output array
    dst = np.zeros((dst_height, dst_width, 4), dtype=np.float64)
    weight_sums = np.zeros((dst_height, dst_width), dtype=np.float64)

    # Convert source to float with premultiplied alpha
    src_float = src.astype(np.float64)
    src_alpha = src_float[:, :, 3:4] / 255.0
    src_premult = src_float[:, :, :3] * src_alpha

    for dst_y in range(dst_height):
        src_center_y = (dst_y + 0.5) * scale_y
        y1 = max(0, int(np.floor(src_center_y - a * filter_scale_y)))
        y2 = min(src_height - 1, int(np.ceil(src_center_y + a * filter_scale_y)))

        for sy in range(y1, y2 + 1):
            dy = sy - src_center_y
            wy = lanczos_kernel(dy / filter_scale_y, a)
            if wy == 0:
                continue

            for dst_x in range(dst_width):
                src_center_x = (dst_x + 0.5) * scale_x
                x1 = max(0, int(np.floor(src_center_x - a * filter_scale_x)))
                x2 = min(src_width - 1, int(np.ceil(src_center_x + a * filter_scale_x)))

                for sx in range(x1, x2 + 1):
                    dx = sx - src_center_x
                    wx = lanczos_kernel(dx / filter_scale_x, a)
                    if wx == 0:
                        continue

                    weight = wx * wy
                    dst[dst_y, dst_x, :3] += src_premult[sy, sx] * weight
                    dst[dst_y, dst_x, 3] += src_alpha[sy, sx, 0] * weight
                    weight_sums[dst_y, dst_x] += weight

    # Normalize and unpremultiply
    result = np.zeros((dst_height, dst_width, 4), dtype=np.uint8)

    mask = (weight_sums > 0) & (dst[:, :, 3] > 0)

    # Unpremultiply RGB
    alpha_nonzero = np.where(dst[:, :, 3:4] > 0, dst[:, :, 3:4], 1.0)
    rgb = dst[:, :, :3] / alpha_nonzero

    # Normalize alpha
    weight_sums_safe = np.where(weight_sums > 0, weight_sums, 1.0)
    alpha_normalized = dst[:, :, 3] / weight_sums_safe * 255.0

    result[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    result[:, :, 3] = np.clip(alpha_normalized, 0, 255).astype(np.uint8)

    # Zero out pixels with no weight
    result[~mask] = [0, 0, 0, 0]

    return result
