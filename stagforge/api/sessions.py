"""Session management API endpoints.

Session-level operations use the URL pattern:
/api/sessions/{session}/...

Document-scoped operations are in documents.py:
/api/sessions/{session}/documents/{doc}/...
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..sessions import session_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


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


# --- Request/Response Models ---


class ColorSetRequest(BaseModel):
    """Request body for setting color."""

    color: str


class ToolSelectRequest(BaseModel):
    """Request body for selecting a tool."""

    tool_id: str


class ConfigSetRequest(BaseModel):
    """Request body for setting config value."""

    path: str
    value: Any


# --- Session Management ---


@router.get("")
async def list_sessions() -> dict:
    """List all active editor sessions, sorted by most recent activity first."""
    sessions = session_manager.get_all()
    return {"sessions": [s.to_summary() for s in sessions]}


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get detailed information about a session.

    Use 'current' as session_id to get the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)
    return session.to_detail()


@router.post("/{session_id}/heartbeat")
async def heartbeat(session_id: str) -> dict:
    """Send a heartbeat to keep the session alive.

    Sessions are automatically cleaned up after 6 seconds of no heartbeat.
    The client should send heartbeats every 5 seconds.
    """
    if session_id == "current":
        session = session_manager.get_most_recent()
        if not session:
            raise HTTPException(status_code=404, detail="No active sessions")
        session_id = session.id

    if session_manager.heartbeat(session_id):
        return {"success": True, "session_id": session_id}

    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


@router.post("/{session_id}/refresh")
async def refresh_session(session_id: str) -> dict:
    """Refresh the browser/reload the editor.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(resolved_id, "refresh", {})

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to refresh"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/{session_id}/reload-sources")
async def reload_sources(session_id: str) -> dict:
    """Reload image sources.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(resolved_id, "reload_sources", {})

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to reload sources"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Colors ---


@router.get("/{session_id}/colors")
async def get_colors(session_id: str) -> dict:
    """Get foreground/background colors and recent colors.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)

    return {
        "foreground": session.state.foreground_color,
        "background": session.state.background_color,
        "recent_colors": session.state.recent_colors,
        "session_id": resolved_id,
    }


@router.put("/{session_id}/colors/foreground")
async def set_foreground_color(session_id: str, request: ColorSetRequest) -> dict:
    """Set the foreground color.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(
        resolved_id,
        "set_foreground_color",
        {"color": request.color},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to set foreground color"),
        )

    return {"success": True, "session_id": resolved_id}


@router.put("/{session_id}/colors/background")
async def set_background_color(session_id: str, request: ColorSetRequest) -> dict:
    """Set the background color.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(
        resolved_id,
        "set_background_color",
        {"color": request.color},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to set background color"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/{session_id}/colors/swap")
async def swap_colors(session_id: str) -> dict:
    """Swap foreground and background colors.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(resolved_id, "swap_colors", {})

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to swap colors"),
        )

    return {"success": True, "session_id": resolved_id}


@router.post("/{session_id}/colors/reset")
async def reset_colors(session_id: str) -> dict:
    """Reset colors to black/white.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(resolved_id, "reset_colors", {})

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to reset colors"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Active Tool ---


@router.get("/{session_id}/active-tool")
async def get_active_tool(session_id: str) -> dict:
    """Get the currently active tool.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    session = session_manager.get(resolved_id)

    return {
        "tool_id": session.state.active_tool,
        "tool_properties": session.state.tool_properties,
        "session_id": resolved_id,
    }


@router.put("/{session_id}/active-tool")
async def set_active_tool(session_id: str, request: ToolSelectRequest) -> dict:
    """Set the active tool.

    Use 'current' as session_id to use the most recently active session.
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.execute_command(
        resolved_id,
        "select_tool",
        {"tool_id": request.tool_id},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to select tool"),
        )

    return {"success": True, "session_id": resolved_id}


# --- Config ---


@router.get("/{session_id}/config")
async def get_config(session_id: str, path: str | None = None) -> dict:
    """Get UIConfig settings for a session.

    Use 'current' as session_id to use the most recently active session.

    Query params:
        path: Optional dot-separated config path (e.g., 'rendering.vectorSVGRendering')
              If not provided, returns the full config.

    Example paths:
        - rendering.vectorSVGRendering (bool)
        - rendering.vectorSupersampleLevel (int: 1-4)
        - rendering.vectorAntialiasing (bool)
        - mode (str: 'desktop', 'tablet', 'limited')
    """
    resolved_id = _resolve_session_id(session_id)
    config, metadata = await session_manager.get_config(resolved_id, path)

    if config is None:
        raise HTTPException(
            status_code=500,
            detail=metadata.get("error", "Failed to get config"),
        )

    return {"config": config, "path": path, "session_id": resolved_id}


@router.put("/{session_id}/config")
async def set_config(session_id: str, request: ConfigSetRequest) -> dict:
    """Set a UIConfig setting for a session.

    Use 'current' as session_id to use the most recently active session.

    Request body:
        path: Dot-separated config path (e.g., 'rendering.vectorSupersampleLevel')
        value: The value to set
    """
    resolved_id = _resolve_session_id(session_id)
    result = await session_manager.set_config(
        resolved_id,
        request.path,
        request.value,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to set config"),
        )

    return {"success": True, "session_id": resolved_id}
