"""Main API router."""

from fastapi import APIRouter, WebSocket

from stagforge.bridge import editor_bridge
from stagforge.sessions import session_manager

from .browser import router as browser_router
from .data_cache import data_cache
from .documents import router as documents_router
from .effects import router as effects_router
from .filters import router as filters_router
from .images import router as images_router
from .rendering import router as rendering_router
from .sessions import router as sessions_router
from .svg_samples import router as svg_samples_router
from .tools import router as tools_router
from .upload import router as upload_router
from .upload_queue import upload_queue
from imagestag.api.samples import router as imgstag_samples_router

api_router = APIRouter()


@api_router.on_event("startup")
async def startup_event():
    """Start background tasks on API startup."""
    data_cache.start()
    # Start bridge first so it's ready to accept connections
    editor_bridge.start()
    # Register hooks and sync any existing bridge sessions
    session_manager._register_bridge_hooks()
    # Start cleanup tasks
    session_manager.start_cleanup_task()
    await upload_queue.start_cleanup_task()


@api_router.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on API shutdown."""
    data_cache.stop()
    session_manager.stop_cleanup_task()
    await upload_queue.stop_cleanup_task()
    editor_bridge.stop()


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@api_router.get("/bridge/stats")
async def bridge_stats():
    """Get bridge statistics including session info and command execution times."""
    sessions = editor_bridge.get_all_sessions()
    connected_count = sum(1 for s in sessions if s.is_connected)
    return {
        "session_count": len(sessions),
        "connected_count": connected_count,
        "sessions": [
            {
                "id": s.id,
                "connected": s.is_connected,
                "connected_at": s.connected_at.isoformat() if s.connected_at else None,
                "last_heartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None,
            }
            for s in sessions
        ],
        "command_stats": editor_bridge.get_command_stats(),
    }


@api_router.post("/bridge/stats/reset")
async def reset_bridge_stats():
    """Reset command statistics."""
    editor_bridge.reset_command_stats()
    return {"status": "ok"}


@api_router.websocket("/ws/editor/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for editor bridge communication.

    Handles bidirectional communication between Python and JavaScript:
    - Python can call JS methods via editor_bridge.call()
    - JS can send events to Python via bridge.emit()
    """
    await editor_bridge.websocket_endpoint(websocket, session_id)


# Mount sub-routers
# Note: documents_router has no prefix - it defines full paths /sessions/{id}/documents/...
api_router.include_router(browser_router)
api_router.include_router(documents_router)
api_router.include_router(effects_router)
api_router.include_router(filters_router, prefix="/filters", tags=["filters"])
api_router.include_router(images_router, prefix="/images", tags=["images"])
api_router.include_router(sessions_router)
api_router.include_router(tools_router)
api_router.include_router(rendering_router)
api_router.include_router(svg_samples_router, tags=["svg-samples"])
api_router.include_router(upload_router)
api_router.include_router(imgstag_samples_router, prefix="/imgstag", tags=["imgstag-samples"])
