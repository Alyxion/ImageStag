"""ImageStag API - mountable FastAPI application."""
from fastapi import FastAPI
from .samples import router as samples_router


def create_api() -> FastAPI:
    """Create the ImageStag API application.

    Mount at /imgstag/ in your app:
        from imagestag.api import create_api
        app.mount("/imgstag", create_api())
    """
    api = FastAPI(title="ImageStag API", docs_url="/docs")
    api.include_router(samples_router)
    return api


__all__ = ['create_api']
