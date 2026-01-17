"""Filter API endpoints."""

import base64
import io
import json
import struct
from functools import lru_cache

import numpy as np
from fastapi import APIRouter, HTTPException, Request, Response
from PIL import Image

from ..filters.registry import filter_registry

router = APIRouter()

# Cache for filter previews - stores base64 PNG data
_preview_cache: dict[str, str] = {}

# Sample image for filter previews (96x96 with various features to show filter effects)
@lru_cache(maxsize=1)
def _get_sample_image() -> np.ndarray:
    """Generate a sample image for filter previews.

    Creates a 96x96 RGBA image with:
    - Gradient background
    - Some geometric shapes
    - Areas of different colors for demonstrating color effects
    """
    size = 96
    img = np.zeros((size, size, 4), dtype=np.uint8)

    # Create a gradient background (blue to orange)
    for y in range(size):
        for x in range(size):
            t = x / size
            r = int(50 + 180 * t)
            g = int(100 + 80 * (1 - abs(t - 0.5) * 2))
            b = int(200 * (1 - t))
            img[y, x] = [r, g, b, 255]

    # Add a white circle in the center
    cy, cx = size // 2, size // 2
    radius = size // 4
    for y in range(size):
        for x in range(size):
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < radius:
                img[y, x] = [255, 255, 255, 255]
            elif dist < radius + 2:
                # Soft edge
                alpha = 1 - (dist - radius) / 2
                img[y, x] = [
                    int(255 * alpha + img[y, x, 0] * (1 - alpha)),
                    int(255 * alpha + img[y, x, 1] * (1 - alpha)),
                    int(255 * alpha + img[y, x, 2] * (1 - alpha)),
                    255,
                ]

    # Add a dark rectangle in corner
    img[10:30, 10:40] = [40, 40, 50, 255]

    # Add colored squares
    img[70:90, 10:30] = [255, 50, 50, 255]  # Red
    img[70:90, 35:55] = [50, 255, 50, 255]  # Green
    img[70:90, 60:80] = [50, 50, 255, 255]  # Blue

    return img


@router.get("")
async def list_filters():
    """List all available filters with their parameters."""
    filters = []
    for filter_id, filter_class in filter_registry.items():
        filters.append(
            {
                "id": filter_id,
                "name": filter_class.name,
                "description": filter_class.description,
                "category": filter_class.category,
                "params": filter_class.get_params_schema(),
            }
        )
    return {"filters": filters}


@router.get("/{filter_id}")
async def get_filter_info(filter_id: str):
    """Get detailed information about a specific filter."""
    if filter_id not in filter_registry:
        raise HTTPException(status_code=404, detail=f"Filter not found: {filter_id}")

    filter_class = filter_registry[filter_id]
    return {
        "id": filter_id,
        "name": filter_class.name,
        "description": filter_class.description,
        "category": filter_class.category,
        "params": filter_class.get_params_schema(),
    }


@router.post("/{filter_id}")
async def apply_filter(filter_id: str, request: Request):
    """Apply a filter to raw image data.

    Request format:
    - First 4 bytes: metadata length (uint32, little-endian)
    - Next N bytes: JSON metadata {"width": int, "height": int, "params": {...}}
    - Remaining bytes: raw RGBA pixel data

    Response:
    - Raw RGBA pixel data (same dimensions as input)
    """
    import numpy as np

    if filter_id not in filter_registry:
        raise HTTPException(status_code=404, detail=f"Filter not found: {filter_id}")

    # Read raw body
    body = await request.body()

    if len(body) < 4:
        raise HTTPException(status_code=400, detail="Request body too short")

    # Parse metadata
    metadata_length = struct.unpack("<I", body[:4])[0]
    if len(body) < 4 + metadata_length:
        raise HTTPException(status_code=400, detail="Invalid metadata length")

    metadata_json = body[4 : 4 + metadata_length].decode("utf-8")
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON metadata: {e}")

    width = metadata.get("width")
    height = metadata.get("height")
    params = metadata.get("params", {})

    if not width or not height:
        raise HTTPException(status_code=400, detail="Missing width or height in metadata")

    # Extract RGBA data
    rgba_data = body[4 + metadata_length :]
    expected_size = width * height * 4
    if len(rgba_data) != expected_size:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image data size. Expected {expected_size}, got {len(rgba_data)}",
        )

    # Convert to numpy array
    image = np.frombuffer(rgba_data, dtype=np.uint8).reshape((height, width, 4)).copy()

    # Apply filter
    filter_instance = filter_registry[filter_id]()
    try:
        result = filter_instance.apply(image, **params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filter error: {e!s}")

    # Ensure result is correct format
    if result.shape != image.shape:
        raise HTTPException(status_code=500, detail="Filter produced invalid output dimensions")

    # Return raw RGBA bytes
    return Response(content=result.tobytes(), media_type="application/octet-stream")


@router.get("/{filter_id}/preview")
async def get_filter_preview(filter_id: str):
    """Get a preview thumbnail of a filter applied to a sample image.

    Returns a JSON object with a base64-encoded PNG thumbnail showing
    the filter effect on a sample image. Results are cached for performance.
    """
    if filter_id not in filter_registry:
        raise HTTPException(status_code=404, detail=f"Filter not found: {filter_id}")

    # Check cache first
    if filter_id in _preview_cache:
        return {"preview": _preview_cache[filter_id]}

    # Get sample image
    sample = _get_sample_image().copy()

    # Apply filter with default parameters
    filter_instance = filter_registry[filter_id]()
    try:
        result = filter_instance.apply(sample)
    except Exception as e:
        # If filter fails with defaults, return sample image as preview
        print(f"Filter preview error for {filter_id}: {e}")
        result = sample

    # Ensure result is valid
    if result is None or result.shape != sample.shape:
        result = sample

    # Convert to PNG and base64 encode
    pil_img = Image.fromarray(result)
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    buffer.seek(0)
    base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
    data_url = f"data:image/png;base64,{base64_data}"

    # Cache the result
    _preview_cache[filter_id] = data_url

    return {"preview": data_url}


@router.get("/previews/all")
async def get_all_filter_previews():
    """Get preview thumbnails for all filters.

    Returns a JSON object mapping filter IDs to base64-encoded PNG thumbnails.
    This is useful for loading all previews at once.
    """
    previews = {}

    for filter_id in filter_registry:
        # Check cache first
        if filter_id in _preview_cache:
            previews[filter_id] = _preview_cache[filter_id]
            continue

        # Get sample image
        sample = _get_sample_image().copy()

        # Apply filter with default parameters
        filter_instance = filter_registry[filter_id]()
        try:
            result = filter_instance.apply(sample)
        except Exception:
            result = sample

        # Ensure result is valid
        if result is None or result.shape != sample.shape:
            result = sample

        # Convert to PNG and base64 encode
        pil_img = Image.fromarray(result)
        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        buffer.seek(0)
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{base64_data}"

        # Cache and add to result
        _preview_cache[filter_id] = data_url
        previews[filter_id] = data_url

    return {"previews": previews}
