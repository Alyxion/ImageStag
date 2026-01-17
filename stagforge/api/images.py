"""Image source API endpoints."""

import json
import struct

import numpy as np
from fastapi import APIRouter, HTTPException, Response

from ..images.providers import image_providers

router = APIRouter()


@router.get("/sources")
async def list_sources():
    """List all available image sources."""
    sources = []
    for source_id, provider in image_providers.items():
        sources.append(
            {
                "id": source_id,
                "name": provider.name,
                "description": provider.description,
                "images": provider.list_images(),
            }
        )
    return {"sources": sources}


@router.get("/{source_id}")
async def list_source_images(source_id: str):
    """List all images in a source."""
    if source_id not in image_providers:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

    provider = image_providers[source_id]
    return {"images": provider.list_images()}


@router.get("/{source_id}/{image_id}")
async def get_image(source_id: str, image_id: str):
    """Get a sample image as raw RGBA data.

    Response format:
    - First 4 bytes: metadata length (uint32, little-endian)
    - Next N bytes: JSON metadata {"width": int, "height": int, "name": str, ...}
    - Remaining bytes: raw RGBA pixel data
    """
    if source_id not in image_providers:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

    provider = image_providers[source_id]

    try:
        image, metadata = provider.get_image(image_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")

    # Ensure RGBA format
    if image.ndim == 2:  # Grayscale
        image = np.stack([image, image, image, np.full_like(image, 255)], axis=-1)
    elif image.shape[2] == 3:  # RGB
        alpha = np.full((image.shape[0], image.shape[1], 1), 255, dtype=np.uint8)
        image = np.concatenate([image, alpha], axis=-1)

    # Build response metadata
    response_metadata = {
        "width": image.shape[1],
        "height": image.shape[0],
        **metadata,
    }
    metadata_json = json.dumps(response_metadata).encode("utf-8")

    # Pack response: [4 bytes length][metadata][rgba data]
    response_data = struct.pack("<I", len(metadata_json)) + metadata_json + image.tobytes()

    return Response(content=response_data, media_type="application/octet-stream")
