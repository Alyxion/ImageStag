"""ImageStag API - mountable FastAPI application."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .samples import router as samples_router

IMAGESTAG_DIR = Path(__file__).parent.parent


def create_api() -> FastAPI:
    """Create the ImageStag API application.

    Mount at /imgstag/ in your app:
        from imagestag.api import create_api
        app.mount("/imgstag", create_api())

    Serves both the REST API and static JS/WASM files for browser use.
    """
    api = FastAPI(title="ImageStag API", docs_url="/docs")
    api.include_router(samples_router)

    # Serve JS/WASM files for browser-side filter and effect execution
    api.mount("/filters", StaticFiles(directory=IMAGESTAG_DIR / "filters"), name="filters")
    api.mount("/layer_effects", StaticFiles(directory=IMAGESTAG_DIR / "layer_effects"), name="layer_effects")
    api.mount("/wasm", StaticFiles(directory=IMAGESTAG_DIR / "wasm"), name="wasm")

    return api


__all__ = ['create_api']
