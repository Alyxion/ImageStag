"""Document rendering.

Provides full document rendering in Python that matches the
JavaScript Renderer output exactly.
"""

import numpy as np
from PIL import Image
from typing import Any, Dict, List, Optional, Tuple
import base64
from io import BytesIO

from .text import render_text_layer
from .vector import render_vector_layer


# Blend mode implementations matching canvas globalCompositeOperation
BLEND_MODES = {
    "normal": "source-over",
    "multiply": "multiply",
    "screen": "screen",
    "overlay": "overlay",
    "darken": "darken",
    "lighten": "lighten",
    "color-dodge": "color-dodge",
    "color-burn": "color-burn",
    "hard-light": "hard-light",
    "soft-light": "soft-light",
    "difference": "difference",
    "exclusion": "exclusion",
}


def decode_png_data_url(data_url: str) -> np.ndarray:
    """Decode a PNG data URL to numpy array.

    Args:
        data_url: PNG data URL (data:image/png;base64,...)

    Returns:
        RGBA numpy array
    """
    if data_url.startswith("data:image/png;base64,"):
        base64_data = data_url[22:]
    elif data_url.startswith("data:image/"):
        # Other image format
        base64_data = data_url.split(",", 1)[1]
    else:
        base64_data = data_url

    png_bytes = base64.b64decode(base64_data)
    img = Image.open(BytesIO(png_bytes))
    img = img.convert("RGBA")
    return np.array(img)


def blend_layers(
    dst: np.ndarray,
    src: np.ndarray,
    opacity: float = 1.0,
    blend_mode: str = "normal",
    offset_x: int = 0,
    offset_y: int = 0,
) -> np.ndarray:
    """Blend source layer onto destination.

    Args:
        dst: Destination RGBA array
        src: Source RGBA array
        opacity: Layer opacity (0-1)
        blend_mode: Blend mode name
        offset_x: Source X offset in destination
        offset_y: Source Y offset in destination

    Returns:
        Blended result
    """
    result = dst.copy().astype(np.float64)
    dst_h, dst_w = dst.shape[:2]
    src_h, src_w = src.shape[:2]

    # Calculate overlap region
    x1 = max(0, offset_x)
    y1 = max(0, offset_y)
    x2 = min(dst_w, offset_x + src_w)
    y2 = min(dst_h, offset_y + src_h)

    if x1 >= x2 or y1 >= y2:
        return result.astype(np.uint8)

    # Source region
    sx1 = x1 - offset_x
    sy1 = y1 - offset_y
    sx2 = x2 - offset_x
    sy2 = y2 - offset_y

    # Get regions
    dst_region = result[y1:y2, x1:x2].astype(np.float64)
    src_region = src[sy1:sy2, sx1:sx2].astype(np.float64)

    # Apply opacity
    src_alpha = (src_region[:, :, 3:4] / 255.0) * opacity
    dst_alpha = dst_region[:, :, 3:4] / 255.0

    # Simple "source-over" compositing for now
    # TODO: Implement other blend modes
    out_alpha = src_alpha + dst_alpha * (1 - src_alpha)

    # Avoid division by zero
    out_alpha_safe = np.where(out_alpha > 0, out_alpha, 1.0)

    # Blend RGB
    out_rgb = (
        src_region[:, :, :3] * src_alpha +
        dst_region[:, :, :3] * dst_alpha * (1 - src_alpha)
    ) / out_alpha_safe

    # Combine
    result[y1:y2, x1:x2, :3] = np.clip(out_rgb, 0, 255)
    result[y1:y2, x1:x2, 3:4] = out_alpha * 255

    return result.astype(np.uint8)


def render_layer(
    layer_data: Dict[str, Any],
) -> Tuple[np.ndarray, int, int]:
    """Render a single layer to RGBA array.

    Args:
        layer_data: Serialized layer data

    Returns:
        (rgba_array, offset_x, offset_y)
    """
    layer_type = layer_data.get("type", "raster")
    offset_x = layer_data.get("offsetX", layer_data.get("x", 0))
    offset_y = layer_data.get("offsetY", layer_data.get("y", 0))

    if layer_type == "text":
        # Render text layer
        pixels = render_text_layer(layer_data)
        return pixels, offset_x, offset_y

    elif layer_type == "vector":
        # Render vector layer
        pixels = render_vector_layer(layer_data)
        return pixels, offset_x, offset_y

    else:
        # Raster layer - decode PNG
        image_data = layer_data.get("imageData", "")
        if image_data:
            pixels = decode_png_data_url(image_data)
        else:
            width = layer_data.get("width", 100)
            height = layer_data.get("height", 100)
            pixels = np.zeros((height, width, 4), dtype=np.uint8)

        return pixels, offset_x, offset_y


def render_document(
    document_data: Dict[str, Any],
    background_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
) -> np.ndarray:
    """Render a full document to RGBA array.

    This matches the JavaScript Renderer.render() output.

    Args:
        document_data: Serialized document data containing:
            - width, height: Document dimensions
            - layers: Array of layer data
        background_color: Background RGBA color

    Returns:
        RGBA numpy array of composited document
    """
    width = document_data.get("width", 800)
    height = document_data.get("height", 600)
    layers = document_data.get("layers", [])

    # Create canvas with background
    canvas = np.zeros((height, width, 4), dtype=np.uint8)
    canvas[:, :] = background_color

    # Composite layers from bottom to top
    for layer_data in layers:
        if not layer_data.get("visible", True):
            continue

        opacity = layer_data.get("opacity", 1.0)
        blend_mode = layer_data.get("blendMode", "normal")

        # Render the layer
        layer_pixels, offset_x, offset_y = render_layer(layer_data)

        # Blend onto canvas
        canvas = blend_layers(
            canvas,
            layer_pixels,
            opacity=opacity,
            blend_mode=blend_mode,
            offset_x=offset_x,
            offset_y=offset_y,
        )

    return canvas


def compute_pixel_diff(
    img1: np.ndarray,
    img2: np.ndarray,
) -> Tuple[float, np.ndarray]:
    """Compute pixel difference between two images.

    Args:
        img1: First RGBA image
        img2: Second RGBA image

    Returns:
        (diff_ratio, diff_image)
        - diff_ratio: 0.0 = identical, 1.0 = completely different
        - diff_image: Visualization of differences
    """
    if img1.shape != img2.shape:
        raise ValueError(f"Image shapes don't match: {img1.shape} vs {img2.shape}")

    # Compute per-pixel difference
    diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))

    # Max difference per pixel (sum of RGBA channels)
    max_diff_per_pixel = 255 * 4

    # Total difference
    total_diff = np.sum(diff)
    max_total = img1.shape[0] * img1.shape[1] * max_diff_per_pixel

    diff_ratio = total_diff / max_total if max_total > 0 else 0.0

    # Create diff visualization
    diff_vis = np.zeros_like(img1)
    diff_magnitude = np.sum(diff, axis=2)
    diff_vis[:, :, 0] = np.clip(diff_magnitude, 0, 255)  # Red channel shows diff
    diff_vis[:, :, 3] = 255  # Full opacity

    return diff_ratio, diff_vis


def images_match(
    img1: np.ndarray,
    img2: np.ndarray,
    tolerance: float = 0.01,
) -> bool:
    """Check if two images match within tolerance.

    Args:
        img1: First RGBA image
        img2: Second RGBA image
        tolerance: Maximum allowed difference ratio (0.01 = 99% match)

    Returns:
        True if images match within tolerance
    """
    diff_ratio, _ = compute_pixel_diff(img1, img2)
    return diff_ratio <= tolerance
