"""Static document browser UI for exploring sessions, documents, and layers."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

router = APIRouter(tags=["browser"])

# Path to static browser files
BROWSER_STATIC_DIR = Path(__file__).parent / "static" / "browser"


@router.get("/browse")
async def browser_index():
    """Serve the document browser UI."""
    return FileResponse(BROWSER_STATIC_DIR / "index.html", media_type="text/html")


@router.get("/browse/")
async def browser_index_slash():
    """Serve the document browser UI (with trailing slash)."""
    return FileResponse(BROWSER_STATIC_DIR / "index.html", media_type="text/html")


@router.get("/browse/{filename:path}")
async def browser_static(filename: str):
    """Serve static files for the browser UI."""
    file_path = BROWSER_STATIC_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return FileResponse(BROWSER_STATIC_DIR / "index.html", media_type="text/html")

    # Determine content type
    suffix = file_path.suffix.lower()
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }
    content_type = content_types.get(suffix, "application/octet-stream")

    return FileResponse(file_path, media_type=content_type)
