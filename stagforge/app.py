"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import api_router
from .config import settings
from .filters.registry import load_builtin_filters
from .images.providers import load_providers
from .plugins.manager import load_plugins


def create_api_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Load filters and providers synchronously at creation time
    # (Lifespan doesn't work for mounted sub-applications in NiceGUI)
    load_builtin_filters()
    load_providers()
    load_plugins(settings.PLUGINS_DIR)

    app = FastAPI(
        title="Slopstag Image Editor API",
        description="Backend API for Python image processing filters",
        version="0.1.0",
    )

    # CORS (for development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router)

    return app
