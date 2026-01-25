"""Reference filter implementations using OpenCV and scikit-image.

This module provides reference implementations of filters using established
libraries (OpenCV and scikit-image) for comparison against ImageStag outputs.

These reference implementations are used for validation purposes only and
produce 8-bit (u8) outputs only, as these libraries don't natively support
the same 16-bit precision as ImageStag's f32 mode.

Usage:
    from imagestag.parity.reference_filters import (
        get_opencv_filter,
        get_skimage_filter,
        run_reference_comparison,
    )

    # Get reference implementations
    opencv_sobel = get_opencv_filter("sobel")
    skimage_sobel = get_skimage_filter("sobel")

    # Run comparison
    results = run_reference_comparison("sobel", input_image)
"""
import numpy as np
from typing import Callable, Any
from pathlib import Path

# Type for filter functions
ReferenceFilter = Callable[[np.ndarray, dict[str, Any]], np.ndarray]

# Reference implementation registries
_opencv_filters: dict[str, ReferenceFilter] = {}
_skimage_filters: dict[str, ReferenceFilter] = {}


def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale for edge detection filters."""
    if image.ndim == 2:
        return image
    if image.shape[2] == 1:
        return image[:, :, 0]
    # Use BT.709 coefficients
    if image.shape[2] >= 3:
        r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
        return (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(image.dtype)
    return image[:, :, 0]


def _output_to_rgba(gray: np.ndarray, original: np.ndarray) -> np.ndarray:
    """Convert grayscale result back to RGBA format matching input."""
    channels = original.shape[2] if original.ndim == 3 else 1
    if channels == 1:
        return gray.reshape(gray.shape[0], gray.shape[1], 1)
    elif channels == 3:
        return np.stack([gray, gray, gray], axis=2)
    else:  # 4 channels
        alpha = original[:, :, 3] if original.ndim == 3 else np.full(gray.shape, 255, dtype=np.uint8)
        return np.stack([gray, gray, gray, alpha], axis=2)


# =============================================================================
# OpenCV Reference Implementations
# =============================================================================

def _opencv_grayscale(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV grayscale using cv2.cvtColor."""
    import cv2
    if image.shape[2] == 1:
        return image.copy()
    # OpenCV uses BGR, so we need to handle RGB input
    if image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
        return np.stack([gray, gray, gray, image[:, :, 3]], axis=2)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return np.stack([gray, gray, gray], axis=2)


def _opencv_gaussian_blur(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV Gaussian blur."""
    import cv2
    sigma = params.get("sigma", 1.0)
    # ksize=0 means auto-calculate from sigma
    return cv2.GaussianBlur(image, (0, 0), sigma)


def _opencv_box_blur(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV box blur."""
    import cv2
    radius = params.get("radius", 1)
    ksize = 2 * radius + 1
    return cv2.blur(image, (ksize, ksize))


def _opencv_sobel(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV Sobel edge detection."""
    import cv2
    direction = params.get("direction", "both")
    gray = _ensure_grayscale(image).astype(np.float32)

    if direction == "h":
        result = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        result = np.abs(result)
    elif direction == "v":
        result = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        result = np.abs(result)
    else:  # both
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        result = np.sqrt(sobel_x**2 + sobel_y**2)

    # Normalize and convert to u8
    result = np.clip(result, 0, 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _opencv_laplacian(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV Laplacian edge detection."""
    import cv2
    kernel_size = params.get("kernel_size", 3)
    gray = _ensure_grayscale(image).astype(np.float32)

    result = cv2.Laplacian(gray, cv2.CV_32F, ksize=kernel_size)
    result = np.abs(result)
    result = np.clip(result, 0, 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _opencv_median(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV median filter."""
    import cv2
    radius = params.get("radius", 1)
    ksize = 2 * radius + 1
    # OpenCV medianBlur requires odd ksize >= 1
    if ksize < 1:
        ksize = 1
    if ksize % 2 == 0:
        ksize += 1
    return cv2.medianBlur(image, ksize)


def _opencv_dilate(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV dilation."""
    import cv2
    radius = params.get("radius", 1.0)
    size = max(1, int(2 * radius + 1))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        # Process RGB only, preserve alpha
        rgb = cv2.dilate(image[:, :, :3], kernel)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.dilate(image, kernel)


def _opencv_erode(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV erosion."""
    import cv2
    radius = params.get("radius", 1.0)
    size = max(1, int(2 * radius + 1))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.erode(image[:, :, :3], kernel)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.erode(image, kernel)


def _opencv_sharpen(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV sharpen using kernel convolution."""
    import cv2
    amount = params.get("amount", 1.0)

    # Sharpen kernel: center = 1 + 4*amount, edges = -amount
    kernel = np.array([
        [0, -amount, 0],
        [-amount, 1 + 4*amount, -amount],
        [0, -amount, 0]
    ], dtype=np.float32)

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.filter2D(image[:, :, :3], -1, kernel)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.filter2D(image, -1, kernel)


def _opencv_threshold(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV binary threshold."""
    import cv2
    threshold_val = params.get("threshold_val", 128)
    gray = _ensure_grayscale(image)
    _, result = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY)
    return _output_to_rgba(result, image)


def _opencv_invert(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV invert."""
    import cv2
    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.bitwise_not(image[:, :, :3])
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.bitwise_not(image)


def _opencv_brightness(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV brightness adjustment."""
    amount = params.get("amount", 0.0)
    offset = int(amount * 255)
    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = image[:, :, :3].astype(np.int16) + offset
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        return np.dstack([rgb, image[:, :, 3]])
    result = image.astype(np.int16) + offset
    return np.clip(result, 0, 255).astype(np.uint8)


def _opencv_contrast(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV contrast adjustment (matching ImageStag formula)."""
    amount = params.get("amount", 0.0)
    # ImageStag uses steeper curve for positive amounts
    factor = 1.0 + amount * 3.0 if amount >= 0 else 1.0 + amount
    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32)
        rgb = (rgb - 127.5) * factor + 127.5
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        return np.dstack([rgb, image[:, :, 3]])
    result = image.astype(np.float32)
    result = (result - 127.5) * factor + 127.5
    return np.clip(result, 0, 255).astype(np.uint8)


def _opencv_saturation(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV saturation adjustment (matching ImageStag luminosity-based formula)."""
    amount = params.get("amount", 0.0)
    channels = image.shape[2] if image.ndim == 3 else 1
    if channels < 3:
        return image.copy()

    factor = 1.0 + amount
    # BT.709 luminosity coefficients (same as ImageStag)
    LUMA_R, LUMA_G, LUMA_B = 0.2126, 0.7152, 0.0722

    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32)
        alpha = image[:, :, 3]
    else:
        rgb = image.astype(np.float32)
        alpha = None

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = LUMA_R * r + LUMA_G * g + LUMA_B * b

    new_r = np.clip(gray + (r - gray) * factor, 0, 255).astype(np.uint8)
    new_g = np.clip(gray + (g - gray) * factor, 0, 255).astype(np.uint8)
    new_b = np.clip(gray + (b - gray) * factor, 0, 255).astype(np.uint8)

    result = np.stack([new_r, new_g, new_b], axis=2)
    if alpha is not None:
        return np.dstack([result, alpha])
    return result


def _opencv_gamma(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV gamma correction."""
    import cv2
    gamma_value = params.get("gamma_value", 1.0)
    inv_gamma = 1.0 / gamma_value
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.LUT(image[:, :, :3], table)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.LUT(image, table)


def _opencv_exposure(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV exposure adjustment."""
    exposure_val = params.get("exposure_val", 0.0)
    offset = params.get("offset", 0.0)
    gamma_val = params.get("gamma_val", 1.0)

    multiplier = 2.0 ** exposure_val
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32) / 255.0
        rgb = rgb * multiplier + offset
        if gamma_val != 1.0:
            rgb = np.power(np.clip(rgb, 0, 1), 1.0 / gamma_val)
        rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)
        return np.dstack([rgb, image[:, :, 3]])

    result = image.astype(np.float32) / 255.0
    result = result * multiplier + offset
    if gamma_val != 1.0:
        result = np.power(np.clip(result, 0, 1), 1.0 / gamma_val)
    return np.clip(result * 255, 0, 255).astype(np.uint8)


def _opencv_hue_shift(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV hue shift via HSV."""
    import cv2
    degrees = params.get("degrees", 0.0)
    channels = image.shape[2] if image.ndim == 3 else 1
    if channels < 3:
        return image.copy()

    if channels == 4:
        rgb = image[:, :, :3]
        alpha = image[:, :, 3]
    else:
        rgb = image
        alpha = None

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + degrees / 2) % 180  # OpenCV uses 0-180 for hue
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    if alpha is not None:
        return np.dstack([result, alpha])
    return result


def _opencv_posterize(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV posterize."""
    levels = params.get("levels", 4)
    divisor = 256 // levels
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels == 4:
        rgb = (image[:, :, :3] // divisor) * divisor
        return np.dstack([rgb.astype(np.uint8), image[:, :, 3]])
    return ((image // divisor) * divisor).astype(np.uint8)


def _opencv_solarize(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV solarize."""
    threshold_val = params.get("threshold", 128)
    channels = image.shape[2] if image.ndim == 3 else 1
    result = image.copy()

    if channels == 4:
        mask = result[:, :, :3] >= threshold_val
        result[:, :, :3] = np.where(mask, 255 - result[:, :, :3], result[:, :, :3])
    else:
        mask = result >= threshold_val
        result = np.where(mask, 255 - result, result)
    return result


def _opencv_emboss(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV emboss using kernel convolution."""
    import cv2
    angle = params.get("angle", 135.0)
    depth = params.get("depth", 1.0)

    # Simple emboss kernel based on angle
    rad = np.radians(angle)
    dx, dy = np.cos(rad), np.sin(rad)
    kernel = np.array([
        [-depth * dy, -depth, -depth * dx],
        [-1, 1, 1],
        [depth * dx, depth, depth * dy]
    ], dtype=np.float32)

    channels = image.shape[2] if image.ndim == 3 else 1
    gray = _ensure_grayscale(image)
    result = cv2.filter2D(gray.astype(np.float32), -1, kernel)
    result = np.clip(result + 128, 0, 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _opencv_unsharp_mask(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV unsharp mask."""
    import cv2
    amount = params.get("amount", 1.0)
    radius = params.get("radius", 2.0)
    threshold = params.get("threshold", 0)

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32)
        blurred = cv2.GaussianBlur(rgb, (0, 0), radius)
        sharpened = rgb + amount * (rgb - blurred)
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        return np.dstack([sharpened, image[:, :, 3]])

    img_float = image.astype(np.float32)
    blurred = cv2.GaussianBlur(img_float, (0, 0), radius)
    sharpened = img_float + amount * (img_float - blurred)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def _opencv_high_pass(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV high pass filter."""
    import cv2
    radius = params.get("radius", 3.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32)
        blurred = cv2.GaussianBlur(rgb, (0, 0), radius)
        high_pass = rgb - blurred + 128
        high_pass = np.clip(high_pass, 0, 255).astype(np.uint8)
        return np.dstack([high_pass, image[:, :, 3]])

    img_float = image.astype(np.float32)
    blurred = cv2.GaussianBlur(img_float, (0, 0), radius)
    high_pass = img_float - blurred + 128
    return np.clip(high_pass, 0, 255).astype(np.uint8)


def _opencv_motion_blur(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV motion blur."""
    import cv2
    angle = params.get("angle", 45.0)
    distance = int(params.get("distance", 10.0))

    # Create motion blur kernel
    kernel = np.zeros((distance, distance))
    center = distance // 2
    rad = np.radians(angle)
    for i in range(distance):
        x = int(center + (i - center) * np.cos(rad))
        y = int(center + (i - center) * np.sin(rad))
        if 0 <= x < distance and 0 <= y < distance:
            kernel[y, x] = 1
    kernel /= kernel.sum() if kernel.sum() > 0 else 1

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.filter2D(image[:, :, :3], -1, kernel)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.filter2D(image, -1, kernel)


def _opencv_find_edges(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV find edges using Canny."""
    import cv2
    gray = _ensure_grayscale(image)
    edges = cv2.Canny(gray, 50, 150)
    return _output_to_rgba(edges, image)


def _opencv_add_noise(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV add noise."""
    amount = params.get("amount", 0.1)
    gaussian = params.get("gaussian", True)
    monochrome = params.get("monochrome", False)
    seed = params.get("seed", None)

    if seed is not None:
        np.random.seed(seed)

    channels = image.shape[2] if image.ndim == 3 else 1
    h, w = image.shape[:2]

    if gaussian:
        if monochrome:
            noise = np.random.normal(0, amount * 255, (h, w))
            noise = np.stack([noise] * min(channels, 3), axis=2)
        else:
            noise = np.random.normal(0, amount * 255, (h, w, min(channels, 3)))
    else:
        if monochrome:
            noise = np.random.uniform(-amount * 255, amount * 255, (h, w))
            noise = np.stack([noise] * min(channels, 3), axis=2)
        else:
            noise = np.random.uniform(-amount * 255, amount * 255, (h, w, min(channels, 3)))

    if channels == 4:
        result = image[:, :, :3].astype(np.float32) + noise
        result = np.clip(result, 0, 255).astype(np.uint8)
        return np.dstack([result, image[:, :, 3]])

    result = image.astype(np.float32) + noise.reshape(image.shape)
    return np.clip(result, 0, 255).astype(np.uint8)


def _opencv_denoise(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV denoise using fastNlMeansDenoising."""
    import cv2
    strength = params.get("strength", 0.5)
    h = strength * 20  # Map 0-1 to 0-20 filter strength

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.fastNlMeansDenoisingColored(image[:, :, :3], None, h, h, 7, 21)
        return np.dstack([rgb, image[:, :, 3]])
    elif channels == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)
    else:
        return cv2.fastNlMeansDenoising(image, None, h, 7, 21)


def _opencv_levels(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV levels adjustment."""
    import cv2
    in_black = params.get("in_black", 0)
    in_white = params.get("in_white", 255)
    out_black = params.get("out_black", 0)
    out_white = params.get("out_white", 255)
    gamma = params.get("gamma", 1.0)

    # Create lookup table
    lut = np.zeros(256, dtype=np.uint8)
    for i in range(256):
        # Normalize to input range
        v = (i - in_black) / max(in_white - in_black, 1)
        v = np.clip(v, 0, 1)
        # Apply gamma
        v = np.power(v, 1.0 / gamma)
        # Map to output range
        v = out_black + v * (out_white - out_black)
        lut[i] = int(np.clip(v, 0, 255))

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.LUT(image[:, :, :3], lut)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.LUT(image, lut)


def _opencv_auto_levels(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV auto levels."""
    clip_percent = params.get("clip_percent", 0.01)

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = image[:, :, :3]
    else:
        rgb = image

    result = np.zeros_like(rgb)
    for c in range(min(channels, 3)):
        channel = rgb[:, :, c] if rgb.ndim == 3 else rgb
        hist, _ = np.histogram(channel.flatten(), 256, [0, 256])
        cumsum = np.cumsum(hist)
        total = cumsum[-1]

        # Find black and white points
        black = 0
        white = 255
        for i in range(256):
            if cumsum[i] >= total * clip_percent:
                black = i
                break
        for i in range(255, -1, -1):
            if cumsum[i] <= total * (1 - clip_percent):
                white = i
                break

        # Apply levels
        scale = 255.0 / max(white - black, 1)
        if rgb.ndim == 3:
            result[:, :, c] = np.clip((channel.astype(np.float32) - black) * scale, 0, 255).astype(np.uint8)
        else:
            result = np.clip((channel.astype(np.float32) - black) * scale, 0, 255).astype(np.uint8)

    if channels == 4:
        return np.dstack([result, image[:, :, 3]])
    return result


def _opencv_curves(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV curves using spline interpolation."""
    import cv2
    from scipy import interpolate
    points = params.get("points", [(0, 0), (1, 1)])

    # Create spline from control points
    x = [p[0] for p in points]
    y = [p[1] for p in points]

    if len(points) < 2:
        return image.copy()

    # Create lookup table
    if len(points) == 2:
        # Linear interpolation
        f = interpolate.interp1d(x, y, fill_value="extrapolate")
    else:
        # Cubic spline
        f = interpolate.PchipInterpolator(x, y, extrapolate=True)

    lut = np.array([int(np.clip(f(i / 255.0) * 255, 0, 255)) for i in range(256)], dtype=np.uint8)

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.LUT(image[:, :, :3], lut)
        return np.dstack([rgb, image[:, :, 3]])
    return cv2.LUT(image, lut)


def _opencv_vibrance(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV vibrance (smart saturation)."""
    import cv2
    amount = params.get("amount", 0.0)
    channels = image.shape[2] if image.ndim == 3 else 1
    if channels < 3:
        return image.copy()

    if channels == 4:
        rgb = image[:, :, :3]
        alpha = image[:, :, 3]
    else:
        rgb = image
        alpha = None

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    # Vibrance increases saturation more for less saturated pixels
    sat = hsv[:, :, 1] / 255.0
    adjustment = amount * (1 - sat)  # Less saturated = more boost
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.0 + adjustment), 0, 255)
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    if alpha is not None:
        return np.dstack([result, alpha])
    return result


def _opencv_color_balance(image: np.ndarray, params: dict) -> np.ndarray:
    """OpenCV color balance adjustment."""
    shadows = params.get("shadows", [0.0, 0.0, 0.0])
    midtones = params.get("midtones", [0.0, 0.0, 0.0])
    highlights = params.get("highlights", [0.0, 0.0, 0.0])

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels < 3:
        return image.copy()

    result = image.astype(np.float32)

    for c in range(3):
        channel = result[:, :, c] / 255.0

        # Apply adjustments based on luminance ranges
        # Shadows: darks (0-0.33), Midtones: mids (0.33-0.66), Highlights: lights (0.66-1.0)
        shadow_mask = np.clip(1.0 - channel * 3, 0, 1)
        mid_mask = 1.0 - np.abs(channel - 0.5) * 4
        mid_mask = np.clip(mid_mask, 0, 1)
        highlight_mask = np.clip(channel * 3 - 2, 0, 1)

        adjustment = (
            shadows[c] * shadow_mask +
            midtones[c] * mid_mask +
            highlights[c] * highlight_mask
        )

        result[:, :, c] = np.clip((channel + adjustment) * 255, 0, 255)

    result = result.astype(np.uint8)
    return result


# Register OpenCV implementations
_opencv_filters["grayscale"] = _opencv_grayscale
_opencv_filters["gaussian_blur"] = _opencv_gaussian_blur
_opencv_filters["box_blur"] = _opencv_box_blur
_opencv_filters["sobel"] = _opencv_sobel
_opencv_filters["laplacian"] = _opencv_laplacian
_opencv_filters["median"] = _opencv_median
_opencv_filters["dilate"] = _opencv_dilate
_opencv_filters["erode"] = _opencv_erode
_opencv_filters["sharpen"] = _opencv_sharpen
_opencv_filters["threshold"] = _opencv_threshold
_opencv_filters["invert"] = _opencv_invert
_opencv_filters["brightness"] = _opencv_brightness
_opencv_filters["contrast"] = _opencv_contrast
_opencv_filters["saturation"] = _opencv_saturation
_opencv_filters["gamma"] = _opencv_gamma
_opencv_filters["exposure"] = _opencv_exposure
_opencv_filters["hue_shift"] = _opencv_hue_shift
_opencv_filters["posterize"] = _opencv_posterize
_opencv_filters["solarize"] = _opencv_solarize
_opencv_filters["emboss"] = _opencv_emboss
_opencv_filters["unsharp_mask"] = _opencv_unsharp_mask
_opencv_filters["high_pass"] = _opencv_high_pass
_opencv_filters["motion_blur"] = _opencv_motion_blur
_opencv_filters["find_edges"] = _opencv_find_edges
_opencv_filters["add_noise"] = _opencv_add_noise
_opencv_filters["denoise"] = _opencv_denoise
_opencv_filters["levels"] = _opencv_levels
_opencv_filters["auto_levels"] = _opencv_auto_levels
_opencv_filters["curves"] = _opencv_curves
_opencv_filters["vibrance"] = _opencv_vibrance
_opencv_filters["color_balance"] = _opencv_color_balance


# =============================================================================
# scikit-image Reference Implementations
# =============================================================================

def _skimage_grayscale(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage grayscale using color.rgb2gray."""
    from skimage import color
    if image.shape[2] == 1:
        return image.copy()

    # rgb2gray expects float input, returns float 0-1
    img_float = image[:, :, :3].astype(np.float32) / 255.0
    gray = color.rgb2gray(img_float)
    gray_u8 = (gray * 255).astype(np.uint8)

    if image.shape[2] == 4:
        return np.stack([gray_u8, gray_u8, gray_u8, image[:, :, 3]], axis=2)
    return np.stack([gray_u8, gray_u8, gray_u8], axis=2)


def _skimage_gaussian_blur(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage Gaussian blur."""
    from skimage import filters
    sigma = params.get("sigma", 1.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        channel = image[:, :, c].astype(np.float32) / 255.0
        blurred = filters.gaussian(channel, sigma=sigma)
        result[:, :, c] = (blurred * 255).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_sobel(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage Sobel edge detection."""
    from skimage import filters
    direction = params.get("direction", "both")

    gray = _ensure_grayscale(image).astype(np.float32) / 255.0

    if direction == "h":
        result = np.abs(filters.sobel_h(gray))
    elif direction == "v":
        result = np.abs(filters.sobel_v(gray))
    else:  # both
        result = filters.sobel(gray)

    # SKImage returns 0-1, convert to u8
    result = (np.clip(result, 0, 1) * 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _skimage_laplacian(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage Laplacian edge detection."""
    from skimage import filters
    kernel_size = params.get("kernel_size", 3)

    gray = _ensure_grayscale(image).astype(np.float32) / 255.0
    result = np.abs(filters.laplace(gray, ksize=kernel_size))

    # Normalize to 0-255
    if result.max() > 0:
        result = result / result.max()
    result = (result * 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _skimage_median(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage median filter."""
    from skimage import filters
    from skimage.morphology import disk
    radius = params.get("radius", 1)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    selem = disk(radius)
    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        result[:, :, c] = filters.median(image[:, :, c], selem)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_dilate(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage dilation."""
    from skimage import morphology
    radius = params.get("radius", 1.0)
    selem = morphology.disk(max(1, int(radius)))

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        result[:, :, c] = morphology.dilation(image[:, :, c], selem)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_erode(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage erosion."""
    from skimage import morphology
    radius = params.get("radius", 1.0)
    selem = morphology.disk(max(1, int(radius)))

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        result[:, :, c] = morphology.erosion(image[:, :, c], selem)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_invert(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage invert."""
    from skimage import util
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels == 4:
        rgb = util.invert(image[:, :, :3])
        return np.dstack([rgb, image[:, :, 3]])
    return util.invert(image)


def _skimage_threshold(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage threshold."""
    threshold_val = params.get("threshold_val", 128)

    gray = _ensure_grayscale(image)
    # Use >= to include the threshold value (more intuitive behavior)
    result = np.where(gray >= threshold_val, 255, 0).astype(np.uint8)
    return _output_to_rgba(result, image)


def _skimage_solarize(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage solarize - manual implementation as skimage.exposure.solarize may not exist."""
    threshold = params.get("threshold", 128)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = image.copy()

    # Solarize: invert pixels above threshold
    if channels == 4:
        mask = result[:, :, :3] >= threshold
        result[:, :, :3] = np.where(mask, 255 - result[:, :, :3], result[:, :, :3])
    else:
        mask = result >= threshold
        result = np.where(mask, 255 - result, result)

    return result


def _skimage_gamma(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage gamma correction (matching ImageStag: output = input^(1/gamma))."""
    gamma_value = params.get("gamma_value", 1.0)
    # ImageStag uses gamma CORRECTION: output = input^(1/gamma)
    # skimage.adjust_gamma uses: output = input^gamma
    # So we use 1/gamma to match ImageStag
    inv_gamma = 1.0 / gamma_value

    channels = image.shape[2] if image.ndim == 3 else 1
    img_float = image.astype(np.float32) / 255.0

    if channels == 4:
        rgb = np.power(img_float[:, :, :3], inv_gamma)
        result = (rgb * 255).astype(np.uint8)
        return np.dstack([result, image[:, :, 3]])

    result = np.power(img_float, inv_gamma)
    return (result * 255).astype(np.uint8)


def _skimage_box_blur(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage box blur using uniform filter."""
    from scipy import ndimage
    radius = params.get("radius", 1)
    size = 2 * radius + 1

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        result[:, :, c] = ndimage.uniform_filter(image[:, :, c].astype(np.float32), size=size).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_sharpen(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage sharpen using unsharp mask."""
    from skimage import filters
    amount = params.get("amount", 1.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        channel = image[:, :, c].astype(np.float32) / 255.0
        blurred = filters.gaussian(channel, sigma=1.0)
        sharpened = channel + amount * (channel - blurred)
        result[:, :, c] = (np.clip(sharpened, 0, 1) * 255).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_brightness(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage brightness adjustment."""
    amount = params.get("amount", 0.0)
    offset = int(amount * 255)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = image.astype(np.int16)

    if channels == 4:
        result[:, :, :3] += offset
        result = np.clip(result, 0, 255).astype(np.uint8)
    else:
        result += offset
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def _skimage_contrast(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage contrast adjustment (matching ImageStag formula)."""
    amount = params.get("amount", 0.0)
    # ImageStag uses steeper curve for positive amounts
    factor = 1.0 + amount * 3.0 if amount >= 0 else 1.0 + amount

    channels = image.shape[2] if image.ndim == 3 else 1
    result = image.astype(np.float32)

    if channels == 4:
        result[:, :, :3] = (result[:, :, :3] - 127.5) * factor + 127.5
        result = np.clip(result, 0, 255).astype(np.uint8)
    else:
        result = (result - 127.5) * factor + 127.5
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def _skimage_saturation(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage saturation adjustment (matching ImageStag luminosity-based formula)."""
    amount = params.get("amount", 0.0)
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels < 3:
        return image.copy()

    factor = 1.0 + amount
    # BT.709 luminosity coefficients (same as ImageStag)
    LUMA_R, LUMA_G, LUMA_B = 0.2126, 0.7152, 0.0722

    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32)
        alpha = image[:, :, 3]
    else:
        rgb = image.astype(np.float32)
        alpha = None

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = LUMA_R * r + LUMA_G * g + LUMA_B * b

    new_r = np.clip(gray + (r - gray) * factor, 0, 255).astype(np.uint8)
    new_g = np.clip(gray + (g - gray) * factor, 0, 255).astype(np.uint8)
    new_b = np.clip(gray + (b - gray) * factor, 0, 255).astype(np.uint8)

    result = np.stack([new_r, new_g, new_b], axis=2)
    if alpha is not None:
        return np.dstack([result, alpha])
    return result


def _skimage_exposure(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage exposure adjustment."""
    exposure_val = params.get("exposure_val", 0.0)
    offset = params.get("offset", 0.0)
    gamma_val = params.get("gamma_val", 1.0)

    multiplier = 2.0 ** exposure_val
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels == 4:
        rgb = image[:, :, :3].astype(np.float32) / 255.0
        rgb = rgb * multiplier + offset
        if gamma_val != 1.0:
            rgb = np.power(np.clip(rgb, 0, 1), 1.0 / gamma_val)
        rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        return np.dstack([rgb, image[:, :, 3]])

    result = image.astype(np.float32) / 255.0
    result = result * multiplier + offset
    if gamma_val != 1.0:
        result = np.power(np.clip(result, 0, 1), 1.0 / gamma_val)
    return (np.clip(result, 0, 1) * 255).astype(np.uint8)


def _skimage_hue_shift(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage hue shift via HSV."""
    from skimage import color
    degrees = params.get("degrees", 0.0)
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels < 3:
        return image.copy()

    if channels == 4:
        rgb = image[:, :, :3]
        alpha = image[:, :, 3]
    else:
        rgb = image
        alpha = None

    hsv = color.rgb2hsv(rgb.astype(np.float32) / 255.0)
    hsv[:, :, 0] = (hsv[:, :, 0] + degrees / 360.0) % 1.0
    result = (color.hsv2rgb(hsv) * 255).astype(np.uint8)

    if alpha is not None:
        return np.dstack([result, alpha])
    return result


def _skimage_posterize(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage posterize."""
    levels = params.get("levels", 4)
    divisor = 256 // levels

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 4:
        rgb = (image[:, :, :3] // divisor) * divisor
        return np.dstack([rgb.astype(np.uint8), image[:, :, 3]])
    return ((image // divisor) * divisor).astype(np.uint8)


def _skimage_emboss(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage emboss using convolution."""
    from scipy import ndimage
    angle = params.get("angle", 135.0)
    depth = params.get("depth", 1.0)

    rad = np.radians(angle)
    dx, dy = np.cos(rad), np.sin(rad)
    kernel = np.array([
        [-depth * dy, -depth, -depth * dx],
        [-1, 1, 1],
        [depth * dx, depth, depth * dy]
    ], dtype=np.float32)

    gray = _ensure_grayscale(image).astype(np.float32)
    result = ndimage.convolve(gray, kernel)
    result = np.clip(result + 128, 0, 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _skimage_unsharp_mask(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage unsharp mask."""
    from skimage import filters
    amount = params.get("amount", 1.0)
    radius = params.get("radius", 2.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        channel = image[:, :, c].astype(np.float32) / 255.0
        blurred = filters.gaussian(channel, sigma=radius)
        sharpened = channel + amount * (channel - blurred)
        result[:, :, c] = (np.clip(sharpened, 0, 1) * 255).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_high_pass(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage high pass filter."""
    from skimage import filters
    radius = params.get("radius", 3.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        # Work in 0-1 range for skimage
        channel = image[:, :, c].astype(np.float32) / 255.0
        blurred = filters.gaussian(channel, sigma=radius)
        # High pass = original - blurred, centered at 0.5 (128 in u8)
        high_pass = (channel - blurred + 0.5) * 255.0
        result[:, :, c] = np.clip(high_pass, 0, 255).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_motion_blur(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage motion blur."""
    from scipy import ndimage
    angle = params.get("angle", 45.0)
    distance = int(params.get("distance", 10.0))

    # Create motion blur kernel
    kernel = np.zeros((distance, distance))
    center = distance // 2
    rad = np.radians(angle)
    for i in range(distance):
        x = int(center + (i - center) * np.cos(rad))
        y = int(center + (i - center) * np.sin(rad))
        if 0 <= x < distance and 0 <= y < distance:
            kernel[y, x] = 1
    kernel /= kernel.sum() if kernel.sum() > 0 else 1

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        result[:, :, c] = ndimage.convolve(image[:, :, c].astype(np.float32), kernel).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_find_edges(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage find edges using Canny."""
    from skimage import feature
    gray = _ensure_grayscale(image).astype(np.float32) / 255.0
    edges = feature.canny(gray, sigma=1.0)
    result = (edges * 255).astype(np.uint8)
    return _output_to_rgba(result, image)


def _skimage_add_noise(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage add noise."""
    from skimage import util
    amount = params.get("amount", 0.1)
    gaussian = params.get("gaussian", True)
    monochrome = params.get("monochrome", False)
    seed = params.get("seed", None)

    # Set random state (seed is set externally, not passed to random_noise)
    if seed is not None:
        np.random.seed(seed)
        rng = np.random.default_rng(seed)
    else:
        rng = None

    channels = image.shape[2] if image.ndim == 3 else 1
    h, w = image.shape[:2]

    # skimage noise works on 0-1 range
    img_float = image.astype(np.float32) / 255.0

    if gaussian:
        if channels == 4:
            rgb = img_float[:, :, :3]
            # Use rng parameter instead of seed
            noisy = util.random_noise(rgb, mode='gaussian', var=amount**2, rng=rng)
            result = (noisy * 255).astype(np.uint8)
            return np.dstack([result, image[:, :, 3]])
        else:
            noisy = util.random_noise(img_float, mode='gaussian', var=amount**2, rng=rng)
            return (noisy * 255).astype(np.uint8)
    else:
        # Uniform noise
        if channels == 4:
            noise = np.random.uniform(-amount, amount, (h, w, 3))
            result = img_float[:, :, :3] + noise
            result = (np.clip(result, 0, 1) * 255).astype(np.uint8)
            return np.dstack([result, image[:, :, 3]])
        else:
            noise = np.random.uniform(-amount, amount, image.shape)
            result = img_float + noise
            return (np.clip(result, 0, 1) * 255).astype(np.uint8)


def _skimage_denoise(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage denoise using TV denoising."""
    from skimage import restoration
    strength = params.get("strength", 0.5)
    weight = strength * 0.1  # Map to reasonable TV weight

    channels = image.shape[2] if image.ndim == 3 else 1
    img_float = image.astype(np.float32) / 255.0

    if channels == 4:
        rgb = img_float[:, :, :3]
        denoised = restoration.denoise_tv_chambolle(rgb, weight=weight, channel_axis=2)
        result = (denoised * 255).astype(np.uint8)
        return np.dstack([result, image[:, :, 3]])
    elif channels == 3:
        denoised = restoration.denoise_tv_chambolle(img_float, weight=weight, channel_axis=2)
        return (denoised * 255).astype(np.uint8)
    else:
        denoised = restoration.denoise_tv_chambolle(img_float, weight=weight)
        return (denoised * 255).astype(np.uint8)


def _skimage_levels(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage levels adjustment."""
    in_black = params.get("in_black", 0)
    in_white = params.get("in_white", 255)
    out_black = params.get("out_black", 0)
    out_white = params.get("out_white", 255)
    gamma = params.get("gamma", 1.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        channel = image[:, :, c].astype(np.float32)
        # Normalize to input range
        v = (channel - in_black) / max(in_white - in_black, 1)
        v = np.clip(v, 0, 1)
        # Apply gamma
        v = np.power(v, 1.0 / gamma)
        # Map to output range
        v = out_black + v * (out_white - out_black)
        result[:, :, c] = np.clip(v, 0, 255).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_auto_levels(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage auto levels."""
    from skimage import exposure
    clip_percent = params.get("clip_percent", 0.01)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        channel = image[:, :, c]
        # Rescale intensity with percentile clipping
        p_low, p_high = np.percentile(channel, (clip_percent * 100, (1 - clip_percent) * 100))
        result[:, :, c] = np.clip((channel.astype(np.float32) - p_low) * 255.0 / max(p_high - p_low, 1), 0, 255).astype(np.uint8)

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_curves(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage curves using spline interpolation."""
    from scipy import interpolate
    points = params.get("points", [(0, 0), (1, 1)])

    x = [p[0] for p in points]
    y = [p[1] for p in points]

    if len(points) < 2:
        return image.copy()

    # Create lookup table
    if len(points) == 2:
        f = interpolate.interp1d(x, y, fill_value="extrapolate")
    else:
        f = interpolate.PchipInterpolator(x, y, extrapolate=True)

    lut = np.array([int(np.clip(f(i / 255.0) * 255, 0, 255)) for i in range(256)], dtype=np.uint8)

    channels = image.shape[2] if image.ndim == 3 else 1
    result = np.zeros_like(image)

    color_channels = 3 if channels == 4 else channels
    for c in range(color_channels):
        result[:, :, c] = lut[image[:, :, c]]

    if channels == 4:
        result[:, :, 3] = image[:, :, 3]

    return result


def _skimage_vibrance(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage vibrance (smart saturation)."""
    from skimage import color
    amount = params.get("amount", 0.0)
    channels = image.shape[2] if image.ndim == 3 else 1

    if channels < 3:
        return image.copy()

    if channels == 4:
        rgb = image[:, :, :3]
        alpha = image[:, :, 3]
    else:
        rgb = image
        alpha = None

    hsv = color.rgb2hsv(rgb.astype(np.float32) / 255.0)
    # Vibrance increases saturation more for less saturated pixels
    sat = hsv[:, :, 1]
    adjustment = amount * (1 - sat)
    hsv[:, :, 1] = np.clip(sat * (1.0 + adjustment), 0, 1)
    result = (color.hsv2rgb(hsv) * 255).astype(np.uint8)

    if alpha is not None:
        return np.dstack([result, alpha])
    return result


def _skimage_color_balance(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage color balance adjustment."""
    shadows = params.get("shadows", [0.0, 0.0, 0.0])
    midtones = params.get("midtones", [0.0, 0.0, 0.0])
    highlights = params.get("highlights", [0.0, 0.0, 0.0])

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels < 3:
        return image.copy()

    result = image.astype(np.float32)

    for c in range(3):
        channel = result[:, :, c] / 255.0

        # Apply adjustments based on luminance ranges
        shadow_mask = np.clip(1.0 - channel * 3, 0, 1)
        mid_mask = 1.0 - np.abs(channel - 0.5) * 4
        mid_mask = np.clip(mid_mask, 0, 1)
        highlight_mask = np.clip(channel * 3 - 2, 0, 1)

        adjustment = (
            shadows[c] * shadow_mask +
            midtones[c] * mid_mask +
            highlights[c] * highlight_mask
        )

        result[:, :, c] = np.clip((channel + adjustment) * 255, 0, 255)

    result = result.astype(np.uint8)
    return result


# Register SKImage implementations
_skimage_filters["grayscale"] = _skimage_grayscale
_skimage_filters["gaussian_blur"] = _skimage_gaussian_blur
_skimage_filters["box_blur"] = _skimage_box_blur
_skimage_filters["sobel"] = _skimage_sobel
_skimage_filters["laplacian"] = _skimage_laplacian
_skimage_filters["median"] = _skimage_median
_skimage_filters["dilate"] = _skimage_dilate
_skimage_filters["erode"] = _skimage_erode
_skimage_filters["sharpen"] = _skimage_sharpen
_skimage_filters["invert"] = _skimage_invert
_skimage_filters["threshold"] = _skimage_threshold
_skimage_filters["solarize"] = _skimage_solarize
_skimage_filters["gamma"] = _skimage_gamma
_skimage_filters["brightness"] = _skimage_brightness
_skimage_filters["contrast"] = _skimage_contrast
_skimage_filters["saturation"] = _skimage_saturation
_skimage_filters["exposure"] = _skimage_exposure
_skimage_filters["hue_shift"] = _skimage_hue_shift
_skimage_filters["posterize"] = _skimage_posterize
_skimage_filters["emboss"] = _skimage_emboss
_skimage_filters["unsharp_mask"] = _skimage_unsharp_mask
_skimage_filters["high_pass"] = _skimage_high_pass
_skimage_filters["motion_blur"] = _skimage_motion_blur
_skimage_filters["find_edges"] = _skimage_find_edges
_skimage_filters["add_noise"] = _skimage_add_noise
_skimage_filters["denoise"] = _skimage_denoise
_skimage_filters["levels"] = _skimage_levels
_skimage_filters["auto_levels"] = _skimage_auto_levels
_skimage_filters["curves"] = _skimage_curves
_skimage_filters["vibrance"] = _skimage_vibrance
_skimage_filters["color_balance"] = _skimage_color_balance


# =============================================================================
# Public API
# =============================================================================

def get_opencv_filter(name: str) -> ReferenceFilter | None:
    """Get an OpenCV reference filter by name.

    Args:
        name: Filter name

    Returns:
        Reference filter function or None if not available
    """
    return _opencv_filters.get(name)


def get_skimage_filter(name: str) -> ReferenceFilter | None:
    """Get a scikit-image reference filter by name.

    Args:
        name: Filter name

    Returns:
        Reference filter function or None if not available
    """
    return _skimage_filters.get(name)


def list_opencv_filters() -> list[str]:
    """List all available OpenCV reference filters."""
    return list(_opencv_filters.keys())


def list_skimage_filters() -> list[str]:
    """List all available scikit-image reference filters."""
    return list(_skimage_filters.keys())


def run_reference_filter(
    name: str,
    image: np.ndarray,
    params: dict[str, Any] | None = None,
    library: str = "opencv",
) -> np.ndarray | None:
    """Run a reference filter on an image.

    Args:
        name: Filter name
        image: Input image (uint8)
        params: Filter parameters
        library: "opencv" or "skimage"

    Returns:
        Filtered image or None if filter not available
    """
    params = params or {}

    if library == "opencv":
        func = get_opencv_filter(name)
    elif library == "skimage":
        func = get_skimage_filter(name)
    else:
        raise ValueError(f"Unknown library: {library}")

    if func is None:
        return None

    return func(image, params)


def save_reference_output(
    image: np.ndarray,
    category: str,
    filter_name: str,
    test_id: str,
    library: str,
    output_dir: Path | None = None,
    input_image: np.ndarray | None = None,
) -> Path:
    """Save a reference filter output to disk with side-by-side comparison.

    Creates a 2x width image with [original | output] for easy visual comparison.

    Naming convention: {filter_name}_{test_id}_{library}.png
    All outputs are flat in the category directory (no subdirs).

    Args:
        image: Output image (uint8)
        category: "filters" or "layer_effects"
        filter_name: Filter name
        test_id: Test case ID
        library: "opencv" or "skimage"
        output_dir: Output directory (defaults to tmp/parity/{category})
        input_image: Original input image for side-by-side display (optional)

    Returns:
        Path to saved file
    """
    from .config import get_test_dir

    if output_dir is None:
        output_dir = get_test_dir() / category

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{filter_name}_{test_id}_{library}.png"
    filepath = output_dir / filename

    # Create side-by-side image if input_image is provided
    if input_image is not None:
        from .comparison import _create_side_by_side
        image = _create_side_by_side(input_image, image, "u8")

    from PIL import Image
    pil_img = Image.fromarray(image)
    pil_img.save(filepath)

    return filepath


def run_reference_comparison(
    filter_name: str,
    input_image: np.ndarray,
    params: dict[str, Any] | None = None,
) -> dict[str, np.ndarray | None]:
    """Run both OpenCV and SKImage reference implementations.

    Args:
        filter_name: Filter name
        input_image: Input image (uint8)
        params: Filter parameters

    Returns:
        Dict with "opencv" and "skimage" outputs (None if not available)
    """
    return {
        "opencv": run_reference_filter(filter_name, input_image, params, "opencv"),
        "skimage": run_reference_filter(filter_name, input_image, params, "skimage"),
    }


__all__ = [
    "get_opencv_filter",
    "get_skimage_filter",
    "list_opencv_filters",
    "list_skimage_filters",
    "run_reference_filter",
    "save_reference_output",
    "run_reference_comparison",
]
