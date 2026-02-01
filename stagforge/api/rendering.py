"""Rendering API endpoints for server-side rendering.

These endpoints enable rendering layers and documents in Python
for cross-platform parity testing.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from ..rendering import render_layer, render_document, render_text_layer
from ..rendering.document import compute_pixel_diff, images_match

router = APIRouter(prefix="/rendering", tags=["rendering"])


class LayerRenderRequest(BaseModel):
    """Request body for layer rendering."""
    layer: Dict[str, Any]
    width: int | None = None
    height: int | None = None


class DocumentRenderRequest(BaseModel):
    """Request body for document rendering."""
    document: Dict[str, Any]


class PixelDiffRequest(BaseModel):
    """Request body for pixel diff comparison."""
    image1_base64: str  # Raw RGBA bytes as base64
    image2_base64: str
    width: int
    height: int
    tolerance: float = 0.01


@router.post("/layer")
async def render_layer_endpoint(request: LayerRenderRequest) -> Response:
    """Render a single layer to RGBA bytes.

    Supports all layer types: raster, text, vector.
    Returns raw RGBA bytes for comparison testing.
    """
    try:
        layer_data = request.layer
        layer_type = layer_data.get("type", "raster")

        if layer_type == "text":
            pixels = render_text_layer(
                layer_data,
                output_width=request.width,
                output_height=request.height,
            )
        else:
            pixels, _, _ = render_layer(layer_data)

        # Return raw RGBA bytes
        rgba_bytes = pixels.tobytes()

        return Response(
            content=rgba_bytes,
            media_type="application/octet-stream",
            headers={
                "X-Image-Width": str(pixels.shape[1]),
                "X-Image-Height": str(pixels.shape[0]),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document")
async def render_document_endpoint(request: DocumentRenderRequest) -> Response:
    """Render a full document to RGBA bytes.

    Returns composited document as raw RGBA bytes.
    """
    try:
        pixels = render_document(request.document)

        rgba_bytes = pixels.tobytes()

        return Response(
            content=rgba_bytes,
            media_type="application/octet-stream",
            headers={
                "X-Image-Width": str(pixels.shape[1]),
                "X-Image-Height": str(pixels.shape[0]),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diff")
async def pixel_diff_endpoint(request: PixelDiffRequest) -> dict:
    """Compare two images and return diff metrics.

    Use this to verify JS and Python rendering match.
    """
    import base64
    import numpy as np

    try:
        # Decode images
        bytes1 = base64.b64decode(request.image1_base64)
        bytes2 = base64.b64decode(request.image2_base64)

        img1 = np.frombuffer(bytes1, dtype=np.uint8).reshape(
            (request.height, request.width, 4)
        )
        img2 = np.frombuffer(bytes2, dtype=np.uint8).reshape(
            (request.height, request.width, 4)
        )

        diff_ratio, _ = compute_pixel_diff(img1, img2)
        match = images_match(img1, img2, tolerance=request.tolerance)

        return {
            "diff_ratio": diff_ratio,
            "match": match,
            "tolerance": request.tolerance,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
