"""Document management API endpoints with proper URL hierarchy.

All document-scoped operations use the URL pattern:
/api/sessions/{session}/documents/{doc}/...

Resource selection supports:
- UUID: Specific resource by ID
- "current": Active/selected resource
- Integer: Index (0-based)
- String: Name match
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from ..sessions import session_manager


router = APIRouter(tags=["documents"])


# --- Helper Functions ---


def _resolve_session_id(session_id: str) -> str:
    """Resolve session_id, treating 'current' as the most recent session.

    Args:
        session_id: Either a specific session ID or 'current' for most recent.

    Returns:
        The resolved session ID.

    Raises:
        HTTPException: If session not found or no active sessions.
    """
    if session_id == "current":
        session = session_manager.get_most_recent()
        if not session:
            raise HTTPException(status_code=404, detail="No active sessions")
        return session.id

    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session_id


def _parse_document_param(doc: str) -> str | int:
    """Parse document parameter - can be ID, name, or index.

    Returns int if numeric index, str otherwise (ID or name or "current").
    """
    if doc == "current":
        return "current"
    try:
        return int(doc)
    except ValueError:
        return doc


def _parse_layer_param(layer: str) -> str | int:
    """Parse layer parameter - can be ID, name, or index.

    Returns int if numeric index, str otherwise (ID or name).
    """
    try:
        return int(layer)
    except ValueError:
        return layer


# --- Request/Response Models ---


class DocumentCreateRequest(BaseModel):
    """Request body for creating a new document."""

    width: int = 800
    height: int = 600
    name: str = "Untitled"


class DocumentUpdateRequest(BaseModel):
    """Request body for updating a document."""

    name: str | None = None
    width: int | None = None
    height: int | None = None


class LayerCreateRequest(BaseModel):
    """Request body for creating a new layer."""

    name: str | None = None
    type: str = "raster"


class LayerUpdateRequest(BaseModel):
    """Request body for updating a layer."""

    name: str | None = None
    opacity: float | None = None
    blend_mode: str | None = None
    visible: bool | None = None
    locked: bool | None = None


class LayerMoveRequest(BaseModel):
    """Request body for moving a layer."""

    to_index: int


class GroupCreateRequest(BaseModel):
    """Request body for creating a group."""

    name: str | None = None


class GroupFromLayersRequest(BaseModel):
    """Request body for creating a group from layers."""

    layer_ids: list[str]
    name: str | None = None


class MoveToGroupRequest(BaseModel):
    """Request body for moving a layer to a group."""

    group_id: str


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


class EffectAddRequest(BaseModel):
    """Request body for adding a layer effect."""

    effect_type: str
    params: dict[str, Any] = {}


class EffectUpdateRequest(BaseModel):
    """Request body for updating a layer effect."""

    params: dict[str, Any]


class SelectionSetRequest(BaseModel):
    """Request body for setting selection."""

    x: int
    y: int
    width: int
    height: int


class ViewSetRequest(BaseModel):
    """Request body for setting view."""

    zoom: float | None = None
    pan_x: float | None = None
    pan_y: float | None = None


class ColorSetRequest(BaseModel):
    """Request body for setting color."""

    color: str


# --- Document Management Endpoints ---


@router.get("/sessions/{session_id}/documents")
async def list_documents(session_id: str) -> dict:
    """List all documents in a session.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)

    return {
        "documents": [doc.to_summary() for doc in session.state.documents],
        "active_document_id": session.state.active_document_id,
        "session_id": resolved_id,
    }


@router.post("/sessions/{session_id}/documents")
async def create_document(session_id: str, request: DocumentCreateRequest) -> dict:
    """Create a new document.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(
        resolved_id,
        "new_document",
        {"width": request.width, "height": request.height, "name": request.name},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to create document"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


@router.get("/sessions/{session_id}/documents/{doc}")
async def get_document(session_id: str, doc: str) -> dict:
    """Get document details.

    Use 'current' as session_id/doc to use the active session/document.
    Document can be specified by UUID, name, or index.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)
    doc_param = _parse_document_param(doc)

    # Resolve document
    document = None
    if doc_param == "current":
        document = session.state.get_active_document()
    elif isinstance(doc_param, int):
        if 0 <= doc_param < len(session.state.documents):
            document = session.state.documents[doc_param]
    else:
        # Try by ID first, then by name
        for d in session.state.documents:
            if d.id == doc_param:
                document = d
                break
        if not document:
            for d in session.state.documents:
                if d.name == doc_param:
                    document = d
                    break

    if not document:
        raise HTTPException(status_code=404, detail=f"Document '{doc}' not found")

    return {
        **document.to_detail(),
        "session_id": resolved_id,
    }


@router.delete("/sessions/{session_id}/documents/{doc}")
async def close_document(session_id: str, doc: str) -> dict:
    """Close a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "close_document",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to close document"),
        )

    return {"success": True, "session_id": resolved_id}


@router.put("/sessions/{session_id}/documents/{doc}")
async def update_document(
    session_id: str, doc: str, request: DocumentUpdateRequest
) -> dict:
    """Update document properties (rename, resize).

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    params = {"document_id": doc_param}
    if request.name is not None:
        params["name"] = request.name
    if request.width is not None:
        params["width"] = request.width
    if request.height is not None:
        params["height"] = request.height

    result = await session_manager.execute_command(
        resolved_id,
        "update_document",
        params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to update document"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/activate")
async def activate_document(session_id: str, doc: str) -> dict:
    """Set a document as the active document.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "activate_document",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to activate document"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Image Retrieval ---


@router.get("/sessions/{session_id}/documents/{doc}/image")
async def get_document_image(
    session_id: str,
    doc: str,
    format: str = "webp",
    bg: str | None = None,
) -> Response:
    """Get the composite image (all visible layers merged).

    Use 'current' as session_id/doc to use the active session/document.

    Args:
        session_id: Session ID or 'current'
        doc: Document ID, name, index, or 'current'
        format: Output format - 'webp' (default), 'avif', 'png'
        bg: Background color (e.g., '#FFFFFF') or omit for transparent
    """
    if format not in ("webp", "avif", "png"):
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")

    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    data_bytes, metadata = await session_manager.get_image(
        resolved_id, document_id=doc_param, format=format, bg=bg
    )

    if data_bytes is None:
        raise HTTPException(
            status_code=500,
            detail=metadata.get("error", "Failed to get image"),
        )

    content_type = metadata.get("content_type", "image/webp")

    return Response(
        content=data_bytes,
        media_type=content_type,
        headers={
            "X-Width": str(metadata.get("width", 0)),
            "X-Height": str(metadata.get("height", 0)),
            "X-Session-Id": resolved_id,
            "X-Document-Id": metadata.get("document_id", ""),
            "X-Document-Name": metadata.get("document_name", ""),
        },
    )


# --- Document Export/Import ---


@router.get("/sessions/{session_id}/documents/{doc}/export")
async def export_document(session_id: str, doc: str) -> dict:
    """Export the full document as JSON for cross-platform transfer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    document, metadata = await session_manager.export_document(
        resolved_id, document_id=doc_param
    )

    if document is None:
        raise HTTPException(
            status_code=500,
            detail=metadata.get("error", "Failed to export document"),
        )

    return {"document": document, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/import")
async def import_document(
    session_id: str, doc: str, request: DocumentImportRequest
) -> dict:
    """Import a full document from JSON.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.import_document(
        resolved_id,
        request.document,
        document_id=doc_param,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to import document"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Layer Management ---


@router.get("/sessions/{session_id}/documents/{doc}/layers")
async def list_layers(session_id: str, doc: str) -> dict:
    """List all layers in a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)
    doc_param = _parse_document_param(doc)

    # Resolve document
    document = None
    if doc_param == "current":
        document = session.state.get_active_document()
    elif isinstance(doc_param, int):
        if 0 <= doc_param < len(session.state.documents):
            document = session.state.documents[doc_param]
    else:
        for d in session.state.documents:
            if d.id == doc_param or d.name == doc_param:
                document = d
                break

    if not document:
        raise HTTPException(status_code=404, detail=f"Document '{doc}' not found")

    return {
        "layers": [layer.to_dict() for layer in document.layers],
        "active_layer_id": document.active_layer_id,
        "document_id": document.id,
        "session_id": resolved_id,
    }


@router.post("/sessions/{session_id}/documents/{doc}/layers")
async def create_layer(
    session_id: str, doc: str, request: LayerCreateRequest
) -> dict:
    """Create a new layer in a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    params = {"document_id": doc_param}
    if request.name:
        params["name"] = request.name
    if request.type:
        params["type"] = request.type

    result = await session_manager.execute_command(
        resolved_id,
        "new_layer",
        params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to create layer"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


@router.get("/sessions/{session_id}/documents/{doc}/layers/{layer}")
async def get_layer(session_id: str, doc: str, layer: str) -> dict:
    """Get layer details.

    Use 'current' as session_id/doc to use the active session/document.
    Layer can be specified by UUID, name, or index.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    # Resolve document
    document = None
    if doc_param == "current":
        document = session.state.get_active_document()
    elif isinstance(doc_param, int):
        if 0 <= doc_param < len(session.state.documents):
            document = session.state.documents[doc_param]
    else:
        for d in session.state.documents:
            if d.id == doc_param or d.name == doc_param:
                document = d
                break

    if not document:
        raise HTTPException(status_code=404, detail=f"Document '{doc}' not found")

    # Resolve layer
    layer_info = None
    if isinstance(layer_param, int):
        if 0 <= layer_param < len(document.layers):
            layer_info = document.layers[layer_param]
    else:
        for l in document.layers:
            if l.id == layer_param or l.name == layer_param:
                layer_info = l
                break

    if not layer_info:
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found")

    return {
        **layer_info.to_dict(),
        "document_id": document.id,
        "session_id": resolved_id,
    }


@router.put("/sessions/{session_id}/documents/{doc}/layers/{layer}")
async def update_layer(
    session_id: str, doc: str, layer: str, request: LayerUpdateRequest
) -> dict:
    """Update layer properties.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    params = {"document_id": doc_param, "layer_id": layer_param}
    if request.name is not None:
        params["name"] = request.name
    if request.opacity is not None:
        params["opacity"] = request.opacity
    if request.blend_mode is not None:
        params["blend_mode"] = request.blend_mode
    if request.visible is not None:
        params["visible"] = request.visible
    if request.locked is not None:
        params["locked"] = request.locked

    result = await session_manager.execute_command(
        resolved_id,
        "update_layer",
        params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to update layer"),
        )

    return {"success": True, "session_id": resolved_id}


@router.delete("/sessions/{session_id}/documents/{doc}/layers/{layer}")
async def delete_layer(session_id: str, doc: str, layer: str) -> dict:
    """Delete a layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.execute_command(
        resolved_id,
        "delete_layer",
        {"document_id": doc_param, "layer_id": layer_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to delete layer"),
        )

    return {"success": True, "session_id": resolved_id}


@router.get("/sessions/{session_id}/documents/{doc}/layers/{layer}/image")
async def get_layer_image(
    session_id: str,
    doc: str,
    layer: str,
    format: str = "webp",
    bg: str | None = None,
) -> Response:
    """Get a specific layer's data.

    Use 'current' as session_id/doc to use the active session/document.

    Args:
        session_id: Session ID or 'current'
        doc: Document ID, name, index, or 'current'
        layer: Layer ID, name, index, or 'current'
        format: Output format - 'webp' (default), 'avif', 'png' for raster;
                'svg', 'json' for vector layers
        bg: Background color (e.g., '#FFFFFF') or omit for transparent
    """
    valid_formats = ("webp", "avif", "png", "svg", "json")
    if format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")

    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    data_bytes, metadata = await session_manager.get_data(
        resolved_id,
        layer_id=layer_param,
        document_id=doc_param,
        format=format,
        bg=bg,
    )

    if data_bytes is None:
        error_msg = metadata.get("error", "Failed to get layer data").lower()
        if "not found" in error_msg:
            status_code = 404
        elif "cannot export" in error_msg or "unsupported" in error_msg:
            status_code = 400  # Bad request - unsupported operation
        else:
            status_code = 500
        raise HTTPException(
            status_code=status_code,
            detail=metadata.get("error", "Failed to get layer data"),
        )

    content_type = metadata.get("content_type", "image/webp")

    return Response(
        content=data_bytes,
        media_type=content_type,
        headers={
            "X-Width": str(metadata.get("width", 0)),
            "X-Height": str(metadata.get("height", 0)),
            "X-Layer-Id": metadata.get("layer_id", ""),
            "X-Layer-Name": metadata.get("layer_name", ""),
            "X-Layer-Type": metadata.get("layer_type", ""),
            "X-Data-Type": metadata.get("data_type", ""),
            "X-Session-Id": resolved_id,
            "X-Document-Id": metadata.get("document_id", ""),
            "X-Document-Name": metadata.get("document_name", ""),
        },
    )


@router.post("/sessions/{session_id}/documents/{doc}/layers/{layer}/duplicate")
async def duplicate_layer(session_id: str, doc: str, layer: str) -> dict:
    """Duplicate a layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.execute_command(
        resolved_id,
        "duplicate_layer",
        {"document_id": doc_param, "layer_id": layer_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to duplicate layer"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


@router.post("/sessions/{session_id}/documents/{doc}/layers/{layer}/move")
async def move_layer(
    session_id: str, doc: str, layer: str, request: LayerMoveRequest
) -> dict:
    """Move a layer to a new position.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.execute_command(
        resolved_id,
        "move_layer",
        {
            "document_id": doc_param,
            "layer_id": layer_param,
            "to_index": request.to_index,
        },
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to move layer"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/layers/{layer}/merge-down")
async def merge_layer_down(session_id: str, doc: str, layer: str) -> dict:
    """Merge a layer with the one below it.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.execute_command(
        resolved_id,
        "merge_down",
        {"document_id": doc_param, "layer_id": layer_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to merge layer"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Layer Effects ---


@router.get("/sessions/{session_id}/documents/{doc}/layers/{layer}/effects")
async def list_layer_effects(session_id: str, doc: str, layer: str) -> dict:
    """List all effects on a layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    effects, metadata = await session_manager.get_layer_effects(
        resolved_id, layer_param, document_id=doc_param
    )

    if effects is None:
        raise HTTPException(
            status_code=404 if "not found" in metadata.get("error", "").lower() else 500,
            detail=metadata.get("error", "Failed to get effects"),
        )

    return {
        "effects": effects,
        "layer_id": str(layer_param),
        "session_id": resolved_id,
    }


@router.post("/sessions/{session_id}/documents/{doc}/layers/{layer}/effects")
async def add_layer_effect(
    session_id: str, doc: str, layer: str, request: EffectAddRequest
) -> dict:
    """Add an effect to a layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.add_layer_effect(
        resolved_id,
        layer_param,
        request.effect_type,
        request.params,
        document_id=doc_param,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to add effect"),
        )

    return {"success": True, "session_id": resolved_id, "result": result}


@router.put("/sessions/{session_id}/documents/{doc}/layers/{layer}/effects/{effect_id}")
async def update_layer_effect(
    session_id: str, doc: str, layer: str, effect_id: str, request: EffectUpdateRequest
) -> dict:
    """Update an effect's parameters.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.update_layer_effect(
        resolved_id,
        layer_param,
        effect_id,
        request.params,
        document_id=doc_param,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to update effect"),
        )

    return {"success": True, "session_id": resolved_id}


@router.delete(
    "/sessions/{session_id}/documents/{doc}/layers/{layer}/effects/{effect_id}"
)
async def remove_layer_effect(
    session_id: str, doc: str, layer: str, effect_id: str
) -> dict:
    """Remove an effect from a layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.remove_layer_effect(
        resolved_id,
        layer_param,
        effect_id,
        document_id=doc_param,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to remove effect"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Tool Execution ---


@router.post("/sessions/{session_id}/documents/{doc}/tools/{tool_id}/execute")
async def execute_tool(
    session_id: str, doc: str, tool_id: str, request: ToolExecuteRequest
) -> dict:
    """Execute a tool action on a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_tool(
        resolved_id,
        tool_id,
        request.action,
        {**request.params, "document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Tool execution failed"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


# --- Command Execution ---


@router.post("/sessions/{session_id}/documents/{doc}/command")
async def execute_command(
    session_id: str, doc: str, request: CommandRequest
) -> dict:
    """Execute an editor command on a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        request.command,
        {**request.params, "document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Command execution failed"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


# --- History ---


@router.get("/sessions/{session_id}/documents/{doc}/history")
async def get_history_state(session_id: str, doc: str) -> dict:
    """Get history state for a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "get_history_state",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to get history state"),
        )

    return {
        "history": result.get("result", {}),
        "session_id": resolved_id,
    }


@router.post("/sessions/{session_id}/documents/{doc}/history/undo")
async def undo(session_id: str, doc: str) -> dict:
    """Undo the last action in a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "undo",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to undo"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/history/redo")
async def redo(session_id: str, doc: str) -> dict:
    """Redo the last undone action in a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "redo",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to redo"),
        )

    return {"success": True, "session_id": resolved_id}


@router.delete("/sessions/{session_id}/documents/{doc}/history")
async def clear_history(session_id: str, doc: str) -> dict:
    """Clear history for a document.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "clear_history",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to clear history"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Selection ---


@router.get("/sessions/{session_id}/documents/{doc}/selection")
async def get_selection(session_id: str, doc: str) -> dict:
    """Get the current selection bounds.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "get_selection",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to get selection"),
        )

    return {
        "selection": result.get("result", {}),
        "session_id": resolved_id,
    }


@router.put("/sessions/{session_id}/documents/{doc}/selection")
async def set_selection(
    session_id: str, doc: str, request: SelectionSetRequest
) -> dict:
    """Set the selection bounds.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "set_selection",
        {
            "document_id": doc_param,
            "x": request.x,
            "y": request.y,
            "width": request.width,
            "height": request.height,
        },
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to set selection"),
        )

    return {"success": True, "session_id": resolved_id}


@router.delete("/sessions/{session_id}/documents/{doc}/selection")
async def clear_selection(session_id: str, doc: str) -> dict:
    """Clear the selection.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "deselect",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to clear selection"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/selection/all")
async def select_all(session_id: str, doc: str) -> dict:
    """Select all.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "select_all",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to select all"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/selection/invert")
async def invert_selection(session_id: str, doc: str) -> dict:
    """Invert the selection.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "invert_selection",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to invert selection"),
        )

    return {"success": True, "session_id": resolved_id}


# --- View/Zoom ---


@router.get("/sessions/{session_id}/documents/{doc}/view")
async def get_view(session_id: str, doc: str) -> dict:
    """Get the current view state (zoom, pan).

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "get_view",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to get view"),
        )

    return {
        "view": result.get("result", {}),
        "session_id": resolved_id,
    }


@router.put("/sessions/{session_id}/documents/{doc}/view")
async def set_view(session_id: str, doc: str, request: ViewSetRequest) -> dict:
    """Set the view state (zoom, pan).

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    params = {"document_id": doc_param}
    if request.zoom is not None:
        params["zoom"] = request.zoom
    if request.pan_x is not None:
        params["pan_x"] = request.pan_x
    if request.pan_y is not None:
        params["pan_y"] = request.pan_y

    result = await session_manager.execute_command(
        resolved_id,
        "set_view",
        params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to set view"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/view/fit")
async def fit_to_window(session_id: str, doc: str) -> dict:
    """Fit the document to the window.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "fit_to_window",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to fit to window"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/view/actual")
async def zoom_actual(session_id: str, doc: str) -> dict:
    """Set zoom to 100%.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "zoom_actual",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to set zoom to 100%"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Clipboard ---


@router.get("/sessions/{session_id}/documents/{doc}/clipboard")
async def get_clipboard_info(session_id: str, doc: str) -> dict:
    """Get clipboard info (has content, dimensions).

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "get_clipboard_info",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to get clipboard info"),
        )

    return {
        "clipboard": result.get("result", {}),
        "session_id": resolved_id,
    }


@router.post("/sessions/{session_id}/documents/{doc}/clipboard/copy")
async def copy(session_id: str, doc: str) -> dict:
    """Copy from active layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "copy",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to copy"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/clipboard/copy-merged")
async def copy_merged(session_id: str, doc: str) -> dict:
    """Copy merged (all visible layers).

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "copy_merged",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to copy merged"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/clipboard/cut")
async def cut(session_id: str, doc: str) -> dict:
    """Cut from active layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "cut",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to cut"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/clipboard/paste")
async def paste(session_id: str, doc: str) -> dict:
    """Paste as new layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "paste",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to paste"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/clipboard/paste-in-place")
async def paste_in_place(session_id: str, doc: str) -> dict:
    """Paste at original position.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "paste_in_place",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to paste in place"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Flatten ---


@router.post("/sessions/{session_id}/documents/{doc}/flatten")
async def flatten(session_id: str, doc: str) -> dict:
    """Flatten all layers.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "flatten",
        {"document_id": doc_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to flatten"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Filters ---


@router.post("/sessions/{session_id}/documents/{doc}/filters/{filter_id}/apply")
async def apply_filter(
    session_id: str, doc: str, filter_id: str, params: dict[str, Any] = {}
) -> dict:
    """Apply a filter to the active layer.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    result = await session_manager.execute_command(
        resolved_id,
        "apply_filter",
        {"document_id": doc_param, "filter_id": filter_id, "params": params},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to apply filter"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Layer Groups ---


@router.post("/sessions/{session_id}/documents/{doc}/groups")
async def create_group(
    session_id: str, doc: str, request: GroupCreateRequest
) -> dict:
    """Create an empty layer group.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    params = {"document_id": doc_param}
    if request.name:
        params["name"] = request.name

    result = await session_manager.execute_command(
        resolved_id,
        "create_group",
        params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to create group"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


@router.post("/sessions/{session_id}/documents/{doc}/groups/from-layers")
async def create_group_from_layers(
    session_id: str, doc: str, request: GroupFromLayersRequest
) -> dict:
    """Create a group from selected layers.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)

    params = {"document_id": doc_param, "layer_ids": request.layer_ids}
    if request.name:
        params["name"] = request.name

    result = await session_manager.execute_command(
        resolved_id,
        "create_group_from_layers",
        params,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to create group from layers"),
        )

    return {"success": True, "session_id": resolved_id, "result": result.get("result")}


@router.delete("/sessions/{session_id}/documents/{doc}/groups/{group}")
async def delete_group(session_id: str, doc: str, group: str) -> dict:
    """Delete/ungroup a layer group.

    Use 'current' as session_id/doc to use the active session/document.
    Children are moved out of the group, not deleted.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    group_param = _parse_layer_param(group)

    result = await session_manager.execute_command(
        resolved_id,
        "delete_group",
        {"document_id": doc_param, "group_id": group_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to delete group"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/layers/{layer}/move-to-group")
async def move_layer_to_group(
    session_id: str, doc: str, layer: str, request: MoveToGroupRequest
) -> dict:
    """Move a layer into a group.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.execute_command(
        resolved_id,
        "move_to_group",
        {
            "document_id": doc_param,
            "layer_id": layer_param,
            "group_id": request.group_id,
        },
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to move layer to group"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/sessions/{session_id}/documents/{doc}/layers/{layer}/remove-from-group")
async def remove_layer_from_group(session_id: str, doc: str, layer: str) -> dict:
    """Remove a layer from its parent group.

    Use 'current' as session_id/doc to use the active session/document.
    """
    resolved_id = _resolve_session_id(session_id)
    doc_param = _parse_document_param(doc)
    layer_param = _parse_layer_param(layer)

    result = await session_manager.execute_command(
        resolved_id,
        "remove_from_group",
        {"document_id": doc_param, "layer_id": layer_param},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to remove layer from group"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Browser Storage (OPFS) ---


@router.get("/sessions/{session_id}/storage/documents")
async def list_stored_documents(session_id: str) -> dict:
    """List all documents stored in browser OPFS storage.

    Returns documents saved by auto-save, including timestamps and metadata.
    Use 'current' as session_id to use the most recently active session.

    Response includes:
    - documents: List of stored documents with id, name, savedAt, historyIndex
    - tabId: Browser tab ID for the session
    - files: List of all files in storage (for debugging)
    """
    resolved_id = _resolve_session_id(session_id)

    result = await session_manager.execute_command(
        resolved_id,
        "list_stored_documents",
        {},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to list stored documents"),
        )

    return {
        "storage": result.get("result", {}),
        "session_id": resolved_id,
    }


@router.delete("/sessions/{session_id}/storage/documents")
async def clear_stored_documents(session_id: str) -> dict:
    """Clear all documents from browser OPFS storage.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)

    result = await session_manager.execute_command(
        resolved_id,
        "clear_stored_documents",
        {},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to clear stored documents"),
        )

    return {"success": True, "session_id": resolved_id}


@router.delete("/sessions/{session_id}/storage/documents/{doc_id}")
async def delete_stored_document(session_id: str, doc_id: str) -> dict:
    """Delete a specific document from browser OPFS storage.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)

    result = await session_manager.execute_command(
        resolved_id,
        "delete_stored_document",
        {"document_id": doc_id},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to delete stored document"),
        )

    return {"success": True, "session_id": resolved_id}
