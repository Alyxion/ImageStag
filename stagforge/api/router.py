"""Main API router."""

from fastapi import APIRouter

from .filters import router as filters_router
from .images import router as images_router
from .sessions import router as sessions_router
from .rendering import router as rendering_router

api_router = APIRouter()


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# Mount sub-routers
api_router.include_router(filters_router, prefix="/filters", tags=["filters"])
api_router.include_router(images_router, prefix="/images", tags=["images"])
api_router.include_router(sessions_router)
api_router.include_router(rendering_router)
