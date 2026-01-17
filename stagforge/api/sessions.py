"""Session management API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from ..sessions import session_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


class ToolExecuteRequest(BaseModel):
    """Request body for tool execution."""

    action: str
    params: dict[str, Any] = {}


class CommandRequest(BaseModel):
    """Request body for command execution."""

    command: str
    params: dict[str, Any] = {}


class DocumentImportRequest(BaseModel):
    """Request body for document import."""

    document: dict[str, Any]


class ConfigSetRequest(BaseModel):
    """Request body for setting config value."""

    path: str
    value: Any


class EffectAddRequest(BaseModel):
    """Request body for adding a layer effect."""

    effect_type: str
    params: dict[str, Any] = {}


class EffectUpdateRequest(BaseModel):
    """Request body for updating a layer effect."""

    params: dict[str, Any]


@router.get("")
async def list_sessions() -> dict:
    """List all active editor sessions."""
    sessions = session_manager.get_all()
    return {"sessions": [s.to_summary() for s in sessions]}


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get detailed information about a session."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_detail()


@router.get("/{session_id}/image")
async def get_session_image(session_id: str) -> Response:
    """Get the flattened composite image as raw RGBA bytes."""
    rgba_bytes, metadata = await session_manager.get_image(session_id)

    if rgba_bytes is None:
        raise HTTPException(
            status_code=404 if "not found" in metadata.get("error", "").lower() else 500,
            detail=metadata.get("error", "Failed to get image"),
        )

    return Response(
        content=rgba_bytes,
        media_type="application/octet-stream",
        headers={
            "X-Image-Width": str(metadata.get("width", 0)),
            "X-Image-Height": str(metadata.get("height", 0)),
        },
    )


@router.get("/{session_id}/layers/{layer_id}")
async def get_layer_image(session_id: str, layer_id: str) -> Response:
    """Get a specific layer's image data as raw RGBA bytes."""
    rgba_bytes, metadata = await session_manager.get_image(session_id, layer_id)

    if rgba_bytes is None:
        raise HTTPException(
            status_code=404 if "not found" in metadata.get("error", "").lower() else 500,
            detail=metadata.get("error", "Failed to get layer image"),
        )

    return Response(
        content=rgba_bytes,
        media_type="application/octet-stream",
        headers={
            "X-Image-Width": str(metadata.get("width", 0)),
            "X-Image-Height": str(metadata.get("height", 0)),
            "X-Layer-Name": metadata.get("layer_name", ""),
            "X-Layer-Opacity": str(metadata.get("layer_opacity", 1.0)),
            "X-Layer-Blend-Mode": metadata.get("layer_blend_mode", "normal"),
        },
    )


@router.post("/{session_id}/tools/{tool_id}/execute")
async def execute_tool(
    session_id: str,
    tool_id: str,
    request: ToolExecuteRequest,
) -> dict:
    """Execute a tool action on a session.

    Supported tools and actions:
    - brush: stroke (points, size, color)
    - eraser: stroke (points, size)
    - shape: draw (type, start, end, fill, stroke)
    - fill: fill (point, color, tolerance)
    - move: translate (dx, dy)
    """
    result = await session_manager.execute_tool(
        session_id,
        tool_id,
        request.action,
        request.params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Tool execution failed"),
        )

    return result


@router.post("/{session_id}/command")
async def execute_command(
    session_id: str,
    request: CommandRequest,
) -> dict:
    """Execute an editor command on a session.

    Supported commands:
    - undo, redo
    - new_layer, delete_layer, duplicate_layer, merge_down, flatten
    - set_foreground_color (color), set_background_color (color)
    - select_tool (tool_id)
    - apply_filter (filter_id, params)
    - new_document (width, height)
    """
    result = await session_manager.execute_command(
        session_id,
        request.command,
        request.params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Command execution failed"),
        )

    return result


@router.get("/{session_id}/document/export")
async def export_document(session_id: str) -> dict:
    """Export the full document as JSON for cross-platform transfer.

    Returns the complete document structure including all layers,
    their content (raster as PNG data URLs, text/vector as data),
    and document metadata.
    """
    document, metadata = await session_manager.export_document(session_id)

    if document is None:
        raise HTTPException(
            status_code=404 if "not found" in metadata.get("error", "").lower() else 500,
            detail=metadata.get("error", "Failed to export document"),
        )

    return {"document": document}


@router.post("/{session_id}/document/import")
async def import_document(
    session_id: str,
    request: DocumentImportRequest,
) -> dict:
    """Import a full document from JSON.

    Replaces the current document with the imported one.
    Supports all layer types: raster, text, vector.
    """
    result = await session_manager.import_document(
        session_id,
        request.document,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to import document"),
        )

    return result


@router.get("/{session_id}/config")
async def get_config(session_id: str, path: str | None = None) -> dict:
    """Get UIConfig settings for a session.

    Query params:
        path: Optional dot-separated config path (e.g., 'rendering.vectorSVGRendering')
              If not provided, returns the full config.

    Returns:
        The config value or full config object.

    Example paths:
        - rendering.vectorSVGRendering (bool)
        - rendering.vectorSupersampleLevel (int: 1-4)
        - rendering.vectorAntialiasing (bool)
        - mode (str: 'desktop', 'tablet', 'limited')
        - desktopMode, tabletMode, limitedMode (objects)
    """
    config, metadata = await session_manager.get_config(session_id, path)

    if config is None:
        raise HTTPException(
            status_code=404 if "not found" in metadata.get("error", "").lower() else 500,
            detail=metadata.get("error", "Failed to get config"),
        )

    return {"config": config, "path": path}


@router.put("/{session_id}/config")
async def set_config(session_id: str, request: ConfigSetRequest) -> dict:
    """Set a UIConfig setting for a session.

    Request body:
        path: Dot-separated config path (e.g., 'rendering.vectorSupersampleLevel')
        value: The value to set

    Example:
        {"path": "rendering.vectorSupersampleLevel", "value": 3}
        {"path": "rendering.vectorAntialiasing", "value": false}
        {"path": "mode", "value": "tablet"}
    """
    result = await session_manager.set_config(
        session_id,
        request.path,
        request.value,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to set config"),
        )

    return result


# Layer Effects API


@router.get("/{session_id}/layers/{layer_id}/effects")
async def list_layer_effects(session_id: str, layer_id: str) -> dict:
    """List all effects on a layer.

    Returns:
        List of effect objects with type, id, enabled, and parameters.
    """
    effects, metadata = await session_manager.get_layer_effects(session_id, layer_id)

    if effects is None:
        raise HTTPException(
            status_code=404 if "not found" in metadata.get("error", "").lower() else 500,
            detail=metadata.get("error", "Failed to get effects"),
        )

    return {"effects": effects, "layer_id": layer_id}


@router.post("/{session_id}/layers/{layer_id}/effects")
async def add_layer_effect(
    session_id: str,
    layer_id: str,
    request: EffectAddRequest,
) -> dict:
    """Add an effect to a layer.

    Available effect types:
    - dropShadow: Drop shadow (offsetX, offsetY, blur, spread, color, colorOpacity)
    - innerShadow: Inner shadow (offsetX, offsetY, blur, choke, color, colorOpacity)
    - outerGlow: Outer glow (blur, spread, color, colorOpacity)
    - innerGlow: Inner glow (blur, choke, color, colorOpacity, source)
    - bevelEmboss: Bevel & Emboss (style, depth, direction, size, soften, angle, altitude, etc.)
    - stroke: Stroke (size, position, color, colorOpacity)
    - colorOverlay: Color overlay (color)

    All effects also accept: enabled (bool), blendMode (str), opacity (float)
    """
    result = await session_manager.add_layer_effect(
        session_id,
        layer_id,
        request.effect_type,
        request.params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to add effect"),
        )

    return result


@router.put("/{session_id}/layers/{layer_id}/effects/{effect_id}")
async def update_layer_effect(
    session_id: str,
    layer_id: str,
    effect_id: str,
    request: EffectUpdateRequest,
) -> dict:
    """Update an effect's parameters.

    Params can include any effect-specific parameters plus:
    - enabled: bool
    - blendMode: str
    - opacity: float
    """
    result = await session_manager.update_layer_effect(
        session_id,
        layer_id,
        effect_id,
        request.params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to update effect"),
        )

    return result


@router.delete("/{session_id}/layers/{layer_id}/effects/{effect_id}")
async def remove_layer_effect(
    session_id: str,
    layer_id: str,
    effect_id: str,
) -> dict:
    """Remove an effect from a layer."""
    result = await session_manager.remove_layer_effect(
        session_id,
        layer_id,
        effect_id,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to remove effect"),
        )

    return result
