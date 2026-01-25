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
    from skimage import filters
    threshold_val = params.get("threshold_val", 128)

    gray = _ensure_grayscale(image)
    # Use manual threshold (not Otsu)
    result = np.where(gray >= threshold_val, 255, 0).astype(np.uint8)
    return _output_to_rgba(result, image)


def _skimage_solarize(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage solarize."""
    from skimage import exposure
    threshold = params.get("threshold", 128)
    # SKImage solarize uses 0-1 threshold
    threshold_normalized = threshold / 255.0

    channels = image.shape[2] if image.ndim == 3 else 1
    img_float = image.astype(np.float32) / 255.0

    if channels == 4:
        rgb = exposure.solarize(img_float[:, :, :3], threshold_normalized)
        result = (rgb * 255).astype(np.uint8)
        return np.dstack([result, image[:, :, 3]])

    result = exposure.solarize(img_float, threshold_normalized)
    return (result * 255).astype(np.uint8)


def _skimage_gamma(image: np.ndarray, params: dict) -> np.ndarray:
    """SKImage gamma correction."""
    from skimage import exposure
    gamma_value = params.get("gamma_value", 1.0)

    channels = image.shape[2] if image.ndim == 3 else 1
    img_float = image.astype(np.float32) / 255.0

    if channels == 4:
        rgb = exposure.adjust_gamma(img_float[:, :, :3], gamma_value)
        result = (rgb * 255).astype(np.uint8)
        return np.dstack([result, image[:, :, 3]])

    result = exposure.adjust_gamma(img_float, gamma_value)
    return (result * 255).astype(np.uint8)


# Register SKImage implementations
_skimage_filters["grayscale"] = _skimage_grayscale
_skimage_filters["gaussian_blur"] = _skimage_gaussian_blur
_skimage_filters["sobel"] = _skimage_sobel
_skimage_filters["laplacian"] = _skimage_laplacian
_skimage_filters["median"] = _skimage_median
_skimage_filters["dilate"] = _skimage_dilate
_skimage_filters["erode"] = _skimage_erode
_skimage_filters["invert"] = _skimage_invert
_skimage_filters["threshold"] = _skimage_threshold
_skimage_filters["solarize"] = _skimage_solarize
_skimage_filters["gamma"] = _skimage_gamma


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
) -> Path:
    """Save a reference filter output to disk.

    Args:
        image: Output image (uint8)
        category: "filters" or "layer_effects"
        filter_name: Filter name
        test_id: Test case ID
        library: "opencv" or "skimage"
        output_dir: Output directory (defaults to tmp/parity)

    Returns:
        Path to saved file
    """
    from .config import get_test_dir

    if output_dir is None:
        output_dir = get_test_dir(category) / filter_name

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{test_id}_{library}.png"
    filepath = output_dir / filename

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
