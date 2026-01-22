"""Main API router."""

from fastapi import APIRouter

from stagforge.sessions import session_manager

from .browser import router as browser_router
from .data_cache import data_cache
from .documents import router as documents_router
from .effects import router as effects_router
from .filters import router as filters_router
from .images import router as images_router
from .rendering import router as rendering_router
from .sessions import router as sessions_router
from .tools import router as tools_router
from .upload import router as upload_router

api_router = APIRouter()


@api_router.on_event("startup")
async def startup_event():
    """Start background tasks on API startup."""
    data_cache.start()
    session_manager.start_cleanup_task()


@api_router.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on API shutdown."""
    data_cache.stop()
    session_manager.stop_cleanup_task()


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


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
api_router.include_router(upload_router)
