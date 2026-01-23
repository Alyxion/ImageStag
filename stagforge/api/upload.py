"""Upload endpoints for push-based data transfers.

The frontend POSTs data here (images, vectors, JSON, etc.),
and API endpoints wait for it to arrive.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .data_cache import data_cache


router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/{request_id}")
async def upload_data(request_id: str, request: Request) -> JSONResponse:
    """Receive pushed data from the frontend.

    The frontend calls this endpoint to deliver rendered data
    that was requested by another API endpoint.

    Request body should be the raw binary data.
    Headers:
        Content-Type: MIME type (image/webp, image/avif, image/svg+xml, application/json, etc.)
        X-Width: Width in pixels (for images)
        X-Height: Height in pixels (for images)
        X-Document-Id: Document ID
        X-Document-Name: Document name
        X-Layer-Id: Layer ID (if layer-specific)
        X-Layer-Name: Layer name (if layer-specific)
        X-Layer-Type: Layer type (raster, vector, text, group)
        X-Data-Type: Type of data (image, vector-json, svg, document-json)
    """
    # Read raw body
    body = await request.body()

    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    # Get metadata from headers
    content_type = request.headers.get("content-type", "application/octet-stream")
    metadata = {
        "width": _parse_int_header(request, "x-width"),
        "height": _parse_int_header(request, "x-height"),
        "document_id": request.headers.get("x-document-id", ""),
        "document_name": request.headers.get("x-document-name", ""),
        "layer_id": request.headers.get("x-layer-id"),
        "layer_name": request.headers.get("x-layer-name"),
        "layer_type": request.headers.get("x-layer-type"),
        "data_type": request.headers.get("x-data-type", "image"),
    }

    # Store in cache
    success, error = data_cache.store_data(
        request_id=request_id,
        data=body,
        content_type=content_type,
        metadata=metadata,
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return JSONResponse(
        content={"success": True, "size": len(body)},
        status_code=200,
    )


@router.post("/{request_id}/error")
async def upload_error(request_id: str, request: Request) -> JSONResponse:
    """Signal an error for a pending request.

    The frontend calls this when it cannot fulfill a data request
    (e.g., layer not found, invalid layer type, etc.)

    Request body should be JSON with 'error' field.
    """
    try:
        body = await request.json()
        error_msg = body.get("error", "Unknown error")
    except Exception:
        error_msg = "Unknown error"

    success, error = data_cache.signal_error(request_id, error_msg)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return JSONResponse(
        content={"success": True},
        status_code=200,
    )


@router.get("/stats")
async def get_cache_stats() -> dict:
    """Get cache statistics for monitoring."""
    return data_cache.stats


def _parse_int_header(request: Request, header: str) -> int:
    """Parse an integer header value."""
    value = request.headers.get(header)
    if value:
        try:
            return int(value)
        except ValueError:
            pass
    return 0
