"""Image comparison utilities for parity testing.

Provides functions to compare Python and JavaScript outputs and
generate visual diff reports.

All comparisons are done in normalized float space (0.0-1.0) to allow
comparing u8 and f32 outputs fairly.
"""
import numpy as np
from pathlib import Path
from PIL import Image
from io import BytesIO
from typing import NamedTuple

from .config import get_output_path, get_comparison_path, Platform, LOSSLESS
from .constants import DEFAULT_TOLERANCE


class ComparisonResult(NamedTuple):
    """Result of comparing two images."""
    match: bool
    diff_ratio: float
    diff_count: int
    total_pixels: int
    message: str
    max_diff: float = 0.0  # Maximum per-channel difference in normalized space


def normalize_to_float(image: np.ndarray) -> np.ndarray:
    """Normalize image to float32 in range [0.0, 1.0].

    Handles:
    - uint8 (0-255) -> divide by 255
    - uint16 (0-4095 or 0-65535) -> divide by max value
    - float32/float64 (already 0.0-1.0) -> pass through

    Args:
        image: Input image array

    Returns:
        float32 array with values in [0.0, 1.0]
    """
    if image.dtype == np.uint8:
        return image.astype(np.float32) / 255.0
    elif image.dtype == np.uint16:
        # Check if 12-bit (0-4095) or 16-bit (0-65535)
        max_val = image.max()
        if max_val <= 4095:
            # 12-bit values (from f32 pipeline)
            return image.astype(np.float32) / 4095.0
        else:
            # Full 16-bit values
            return image.astype(np.float32) / 65535.0
    elif image.dtype in (np.float32, np.float64):
        return image.astype(np.float32)
    else:
        raise ValueError(f"Unsupported dtype for normalization: {image.dtype}")


def load_test_image(
    category: str,
    name: str,
    test_case: str,
    platform: Platform,
) -> np.ndarray | None:
    """Load a test result image.

    Args:
        category: Test category
        name: Filter/effect name
        test_case: Test case identifier
        platform: Platform ("python" or "js")

    Returns:
        numpy array with original channel count (1, 3, or 4), or None if file doesn't exist
    """
    path = get_output_path(category, name, test_case, platform)

    # For f32 tests (16-bit), prefer PNG format which preserves depth
    # (AVIF doesn't reliably support 16-bit across platforms)
    is_f32_test = test_case.endswith('_f32') or name.endswith('_f32')
    if is_f32_test:
        png_path = path.with_suffix('.png')
        if png_path.exists():
            return _load_png_16bit(png_path)

    # Check for raw RGBA format first (primary format for parity testing)
    if path.suffix == '.rgba':
        if path.exists():
            return _load_rgba_file(path)
        # Also check without suffix change for other formats
    elif path.suffix == '.avif':
        if path.exists():
            return _load_avif_file(path)
    elif path.suffix == '.png' and path.exists():
        # PNG files may be 16-bit - use cv2 to preserve depth and channels
        return _load_png_16bit(path)
    elif path.exists():
        # Standard image formats (WebP, etc.) - preserve channel count
        img = Image.open(path)
        return np.array(img)

    # Try RGBA format
    rgba_path = path.with_suffix('.rgba')
    if rgba_path.exists():
        return _load_rgba_file(rgba_path)

    # Try AVIF fallback (use pillow_heif for true lossless support)
    avif_path = path.with_suffix('.avif')
    if avif_path.exists():
        return _load_avif_file(avif_path)

    # Try PNG fallback - use cv2 to preserve 16-bit depth and channels
    png_path = path.with_suffix('.png')
    if png_path.exists():
        return _load_png_16bit(png_path)

    return None


def _load_rgba_file(path: Path) -> np.ndarray:
    """Load raw RGBA file format (used by JS Node.js tests).

    Format: 4-byte width (LE) + 4-byte height (LE) + raw RGBA bytes
    """
    with open(path, 'rb') as f:
        data = f.read()

    width = int.from_bytes(data[0:4], 'little')
    height = int.from_bytes(data[4:8], 'little')
    pixels = np.frombuffer(data[8:], dtype=np.uint8)
    return pixels.reshape((height, width, 4))


def _load_avif_file(path: Path, as_12bit: bool = False) -> np.ndarray:
    """Load AVIF file with support for both pillow_heif and standard encoders.

    Args:
        path: Path to AVIF file
        as_12bit: If True, load as 12-bit uint16 (for f32 test outputs)

    Tries Pillow first (works with sharp/libvips AVIFs), then falls back
    to pillow_heif for files created with matrix_coefficients=0.
    Preserves original channel count (3 for RGB, 4 for RGBA).
    """
    import pillow_heif

    if as_12bit:
        # Load as 16-bit using pillow_heif with convert_hdr_to_8bit=False
        # This preserves 10/12-bit precision instead of converting to 8-bit
        heif_file = pillow_heif.open_heif(str(path), convert_hdr_to_8bit=False)
        info = heif_file.info
        bit_depth = info.get('bit_depth', 8)

        if '16' in heif_file.mode:
            # 10/12-bit file loaded in 16-bit mode
            # Data is in 0-65535 range, scale to 12-bit (0-4095)
            height, width = heif_file.size[1], heif_file.size[0]
            channels = 4 if 'A' in heif_file.mode else 3
            arr = np.frombuffer(heif_file.data, dtype=np.uint16).reshape((height, width, channels))
            # Scale from 16-bit (0-65535) to 12-bit (0-4095)
            return (arr.astype(np.uint32) * 4095 // 65535).astype(np.uint16)
        elif bit_depth > 8:
            # Fallback: loaded as 8-bit despite bit_depth > 8
            pil_img = heif_file.to_pillow()
            # Preserve original mode (RGB or RGBA)
            arr = np.array(pil_img)
            # Scale 8-bit (0-255) to 12-bit (0-4095)
            return (arr.astype(np.uint16) * 4095 // 255).astype(np.uint16)
        else:
            # 8-bit file, convert to 12-bit range
            pil_img = heif_file.to_pillow()
            # Preserve original mode (RGB or RGBA)
            arr = np.array(pil_img)
            return (arr.astype(np.uint16) * 4095 // 255).astype(np.uint16)

    # Standard 8-bit loading - preserve channel count
    # Try Pillow first (works with most AVIF encoders including sharp)
    try:
        img = Image.open(path)
        # Preserve original mode (RGB or RGBA) - don't convert
        return np.array(img)
    except Exception:
        pass

    # Fall back to pillow_heif for special cases (matrix_coefficients=0)
    heif_file = pillow_heif.open_heif(str(path))
    pil_img = heif_file.to_pillow()
    # Preserve original mode (RGB or RGBA)
    return np.array(pil_img)


def _save_rgba_file(path: Path, image: np.ndarray) -> None:
    """Save image as raw RGBA file format.

    Format: 4-byte width (LE) + 4-byte height (LE) + raw RGBA bytes
    """
    height, width = image.shape[:2]
    header = np.array([width, height], dtype=np.uint32).tobytes()
    rgba_data = image.astype(np.uint8).tobytes()

    with open(path, 'wb') as f:
        f.write(header + rgba_data)


def _save_avif_lossless(path: Path, image: np.ndarray) -> None:
    """Save image as truly lossless 8-bit AVIF using pillow_heif.

    Uses matrix_coefficients=0 to stay in RGB color space (no YCbCr conversion).
    This is required for exact pixel-perfect round-trips.

    Supports 3-channel (RGB) or 4-channel (RGBA) images.
    """
    import pillow_heif

    channels = image.shape[2] if image.ndim == 3 else 1
    if channels == 3:
        mode = 'RGB'
    elif channels == 4:
        mode = 'RGBA'
    else:
        # For grayscale, convert to RGB
        if channels == 1:
            image = np.repeat(image, 3, axis=2)
            mode = 'RGB'
        else:
            raise ValueError(f"Unsupported channel count: {channels}")

    heif_file = pillow_heif.from_bytes(
        mode=mode,
        size=(image.shape[1], image.shape[0]),
        data=image.astype(np.uint8).tobytes()
    )

    heif_file.save(
        str(path),
        quality=-1,  # lossless
        chroma=444,  # no chroma subsampling
        matrix_coefficients=0  # RGB, not YCbCr - key for true lossless!
    )


def _load_png_16bit(path: Path) -> np.ndarray:
    """Load 16-bit PNG file using cv2.

    cv2 can read 16-bit PNG (PIL converts to 8-bit).
    Data is stored as 16-bit (0-65535), scaled back to 12-bit (0-4095).

    Returns:
        uint16 array with 12-bit values (0-4095), preserving original channel count
    """
    import cv2

    # cv2.IMREAD_UNCHANGED preserves 16-bit depth, alpha channel, and channel count
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    if img is None:
        raise ValueError(f"Failed to load PNG: {path}")

    # Convert BGR(A) to RGB(A) based on channel count
    if img.ndim == 2:
        # Grayscale - add channel dimension
        img = img[:, :, np.newaxis]
    elif img.shape[2] == 3:
        # BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    elif img.shape[2] == 4:
        # BGRA to RGBA
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)

    # Scale 16-bit (0-65535) to 12-bit (0-4095)
    if img.dtype == np.uint16:
        return (img.astype(np.uint32) * 4095 // 65535).astype(np.uint16)
    else:
        # 8-bit PNG, scale to 12-bit
        return (img.astype(np.uint16) * 4095 // 255).astype(np.uint16)


def _save_png_16bit(path: Path, image: np.ndarray) -> None:
    """Save image as 16-bit PNG using cv2.

    For storing float data with higher precision than 8-bit.
    Input should be uint16 with values 0-4095 (12-bit range).
    Values are scaled to 16-bit (0-65535) for PNG storage.

    Supports 1-channel (grayscale), 3-channel (RGB), or 4-channel (RGBA).
    """
    import cv2

    # Ensure input is uint16
    if image.dtype != np.uint16:
        raise ValueError(f"Expected uint16 for 16-bit PNG, got {image.dtype}")

    # Scale 12-bit (0-4095) to 16-bit (0-65535)
    scaled = (image.astype(np.uint32) * 65535 // 4095).astype(np.uint16)

    # cv2 expects BGR(A) format, so convert based on channel count
    channels = scaled.shape[2] if scaled.ndim == 3 else 1
    if channels == 1:
        # Grayscale - squeeze the channel dimension
        out = scaled[:, :, 0] if scaled.ndim == 3 else scaled
    elif channels == 3:
        # RGB to BGR
        out = cv2.cvtColor(scaled, cv2.COLOR_RGB2BGR)
    elif channels == 4:
        # RGBA to BGRA
        out = cv2.cvtColor(scaled, cv2.COLOR_RGBA2BGRA)
    else:
        raise ValueError(f"Unsupported channel count: {channels}")

    cv2.imwrite(str(path), out)


def save_test_image(
    image: np.ndarray,
    category: str,
    name: str,
    test_case: str,
    platform: Platform,
    quality: int = 80,
    lossless: bool | None = None,
    bit_depth: str = "u8",
) -> Path:
    """Save a test result image.

    Args:
        image: RGBA numpy array (uint8 for 8-bit, uint16 for 12-bit)
        category: Test category
        name: Filter/effect name
        test_case: Test case identifier
        platform: Platform ("python" or "js")
        quality: AVIF/WebP quality (1-100), ignored if lossless=True
        lossless: Use lossless compression (defaults to config.LOSSLESS)
        bit_depth: "u8" for 8-bit or "f32" for 12-bit storage

    Returns:
        Path to saved file
    """
    if lossless is None:
        lossless = LOSSLESS

    # For f32 bit depth, use PNG 16-bit (cross-platform compatible)
    if bit_depth == "f32" and image.dtype == np.uint16:
        path = get_output_path(category, name, test_case, platform, format="png")
        _save_png_16bit(path, image)
        return path

    path = get_output_path(category, name, test_case, platform)

    # Raw RGBA format (for JS compatibility in Node.js)
    if path.suffix == '.rgba':
        _save_rgba_file(path, image)
        return path

    try:
        if path.suffix == '.avif':
            if lossless:
                # True lossless 8-bit AVIF with matrix_coefficients=0
                _save_avif_lossless(path, image)
            else:
                # Lossy AVIF via Pillow
                pil_img = Image.fromarray(image)
                pil_img.save(path, format='AVIF', quality=quality)
        elif path.suffix == '.webp':
            pil_img = Image.fromarray(image)
            if lossless:
                pil_img.save(path, format='WebP', lossless=True)
            else:
                pil_img.save(path, format='WebP', quality=quality)
        else:
            # PNG is always lossless
            pil_img = Image.fromarray(image)
            pil_img.save(path, format='PNG')
    except Exception:
        # Fall back to PNG if AVIF/WebP not available
        png_path = path.with_suffix('.png')
        pil_img = Image.fromarray(image)
        pil_img.save(png_path, format='PNG')
        return png_path

    return path


def compute_pixel_diff(
    img1: np.ndarray,
    img2: np.ndarray,
    tolerance: float = DEFAULT_TOLERANCE,
) -> tuple[float, np.ndarray, float]:
    """Compute pixel difference between two images in normalized float space.

    Both images are normalized to float [0.0, 1.0] before comparison, allowing
    fair comparison between u8 and f32 outputs.

    Args:
        img1: First image (any dtype: uint8, uint16, float32)
        img2: Second image (any dtype: uint8, uint16, float32)
        tolerance: Maximum allowed per-channel difference in [0.0, 1.0] space

    Returns:
        Tuple of (diff_ratio, diff_mask, max_diff)
        - diff_ratio: Fraction of pixels that differ (0.0 to 1.0)
        - diff_mask: Boolean array where True = pixel differs
        - max_diff: Maximum per-channel difference found (in normalized space)
    """
    if img1.shape != img2.shape:
        raise ValueError(
            f"Image shapes don't match: {img1.shape} vs {img2.shape}"
        )

    # Normalize both images to float [0.0, 1.0]
    img1_norm = normalize_to_float(img1)
    img2_norm = normalize_to_float(img2)

    # Compute per-channel difference in float space
    diff = np.abs(img1_norm - img2_norm)

    # Maximum difference across all channels and pixels
    max_diff = float(diff.max())

    # A pixel is "different" if ANY channel differs by more than tolerance
    diff_mask = np.any(diff > tolerance, axis=2)

    total_pixels = diff_mask.size
    diff_count = np.sum(diff_mask)
    diff_ratio = diff_count / total_pixels

    return diff_ratio, diff_mask, max_diff


def compare_outputs(
    category: str,
    name: str,
    test_case: str,
    tolerance: float = DEFAULT_TOLERANCE,
) -> ComparisonResult:
    """Compare Python and JavaScript outputs for a test case.

    Comparison is done in normalized float space [0.0, 1.0] to allow
    fair comparison between u8 and f32 outputs.

    Args:
        category: Test category
        name: Filter/effect name
        test_case: Test case identifier
        tolerance: Maximum allowed per-channel difference in [0.0, 1.0] space
                  (e.g., 0.001 means max 0.1% difference per channel)

    Returns:
        ComparisonResult with match status and details
    """
    py_img = load_test_image(category, name, test_case, "python")
    js_img = load_test_image(category, name, test_case, "js")

    if py_img is None and js_img is None:
        return ComparisonResult(
            match=False,
            diff_ratio=1.0,
            diff_count=0,
            total_pixels=0,
            message="Neither Python nor JS output found"
        )

    if py_img is None:
        return ComparisonResult(
            match=False,
            diff_ratio=1.0,
            diff_count=0,
            total_pixels=js_img.shape[0] * js_img.shape[1],
            message="Python output not found"
        )

    if js_img is None:
        return ComparisonResult(
            match=False,
            diff_ratio=1.0,
            diff_count=0,
            total_pixels=py_img.shape[0] * py_img.shape[1],
            message="JavaScript output not found"
        )

    if py_img.shape != js_img.shape:
        return ComparisonResult(
            match=False,
            diff_ratio=1.0,
            diff_count=0,
            total_pixels=0,
            message=f"Shape mismatch: Python {py_img.shape} vs JS {js_img.shape}"
        )

    diff_ratio, diff_mask, max_diff = compute_pixel_diff(py_img, js_img, tolerance)
    total_pixels = diff_mask.size
    diff_count = int(np.sum(diff_mask))

    match = diff_ratio <= tolerance

    if match:
        message = f"PASS: {diff_ratio*100:.4f}% pixels differ, max_diff={max_diff:.6f}"
    else:
        message = f"FAIL: {diff_ratio*100:.4f}% pixels differ (max_diff={max_diff:.6f}) exceeds tolerance={tolerance}"

    return ComparisonResult(
        match=match,
        diff_ratio=diff_ratio,
        diff_count=diff_count,
        total_pixels=total_pixels,
        message=message,
        max_diff=max_diff
    )


def save_comparison_image(
    category: str,
    name: str,
    test_case: str,
    tolerance: float = DEFAULT_TOLERANCE,
) -> Path | None:
    """Save a visual comparison image showing Python, JS, and diff.

    Args:
        category: Test category
        name: Filter/effect name
        test_case: Test case identifier
        tolerance: Minimum normalized difference to highlight

    Returns:
        Path to saved comparison image, or None if outputs missing
    """
    py_img = load_test_image(category, name, test_case, "python")
    js_img = load_test_image(category, name, test_case, "js")

    if py_img is None or js_img is None:
        return None

    if py_img.shape != js_img.shape:
        return None

    h, w = py_img.shape[:2]

    # Compute diff mask in normalized space
    _, diff_mask, _ = compute_pixel_diff(py_img, js_img, tolerance)

    # For visualization, convert images to uint8 if needed
    if py_img.dtype != np.uint8:
        py_img = (normalize_to_float(py_img) * 255).astype(np.uint8)
    if js_img.dtype != np.uint8:
        js_img = (normalize_to_float(js_img) * 255).astype(np.uint8)

    # Create diff visualization (red = different, transparent = same)
    diff_img = np.zeros((h, w, 4), dtype=np.uint8)
    diff_img[diff_mask] = [255, 0, 0, 255]  # Red for differences
    diff_img[~diff_mask] = [0, 0, 0, 0]     # Transparent for same

    # Create side-by-side: [Python | JS | Diff overlay on checkerboard]
    gap = 10
    combined_w = w * 3 + gap * 2
    combined = np.zeros((h, combined_w, 4), dtype=np.uint8)

    # Gray background
    combined[:, :, :3] = 128
    combined[:, :, 3] = 255

    # Add labels area at top
    label_h = 20
    full_h = h + label_h
    full_img = np.zeros((full_h, combined_w, 4), dtype=np.uint8)
    full_img[:, :, :3] = 64  # Dark gray header
    full_img[:, :, 3] = 255

    # Copy images
    full_img[label_h:, 0:w] = py_img
    full_img[label_h:, w+gap:2*w+gap] = js_img

    # Create checkerboard background for diff view
    checker = np.zeros((h, w, 4), dtype=np.uint8)
    checker_size = 8
    for y in range(0, h, checker_size):
        for x in range(0, w, checker_size):
            is_light = ((y // checker_size) + (x // checker_size)) % 2 == 0
            color = 200 if is_light else 150
            y_end = min(y + checker_size, h)
            x_end = min(x + checker_size, w)
            checker[y:y_end, x:x_end, :3] = color
            checker[y:y_end, x:x_end, 3] = 255

    # Overlay diff on checkerboard (blend where diff is set)
    diff_view = checker.copy()
    alpha = diff_img[:, :, 3:4] / 255.0
    diff_view[:, :, :3] = (
        diff_img[:, :, :3] * alpha +
        checker[:, :, :3] * (1 - alpha)
    ).astype(np.uint8)

    full_img[label_h:, 2*w+2*gap:] = diff_view

    # Save
    path = get_comparison_path(category, name, test_case)
    pil_img = Image.fromarray(full_img)
    pil_img.save(path, format='PNG')

    return path


def images_match(
    img1: np.ndarray,
    img2: np.ndarray,
    tolerance: float = DEFAULT_TOLERANCE,
) -> bool:
    """Check if two images match within tolerance.

    Comparison is done in normalized float space [0.0, 1.0].

    Args:
        img1: First image (any dtype: uint8, uint16, float32)
        img2: Second image (any dtype: uint8, uint16, float32)
        tolerance: Maximum allowed per-channel difference in [0.0, 1.0] space

    Returns:
        True if images match within tolerance
    """
    if img1.shape != img2.shape:
        return False

    diff_ratio, _, _ = compute_pixel_diff(img1, img2, tolerance)
    return diff_ratio <= tolerance


__all__ = [
    'ComparisonResult',
    'normalize_to_float',
    'load_test_image',
    'save_test_image',
    'compute_pixel_diff',
    'compare_outputs',
    'save_comparison_image',
    'images_match',
]
