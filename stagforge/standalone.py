"""Standalone FastAPI entry point for Stagforge.

Run without NiceGUI:
    poetry run python -m stagforge.standalone

Environment variables:
    STAGFORGE_PORT: Port to run on (default: 8080)
"""
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from .app import create_api_app
from imagestag.api import create_api as create_imgstag_api

STAGFORGE_DIR = Path(__file__).parent
FRONTEND_DIR = STAGFORGE_DIR / "frontend"
TEMPLATES_DIR = STAGFORGE_DIR / "templates"
CANVAS_EDITOR_JS = STAGFORGE_DIR / "canvas_editor.js"


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Disable caching for development hot-reload."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Disable caching for JS/CSS files
        if any(request.url.path.endswith(ext) for ext in ('.js', '.css')):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response


def create_standalone_app() -> FastAPI:
    """Create standalone FastAPI application with editor UI."""
    app = FastAPI(title="Stagforge Image Editor")

    # Add no-cache middleware for development
    app.add_middleware(NoCacheMiddleware)

    # Mount API
    api_app = create_api_app()
    app.mount("/api", api_app)

    # Mount ImageStag API at /imgstag/
    imgstag_api = create_imgstag_api()
    app.mount("/imgstag", imgstag_api)

    # Serve canvas_editor.js from stagforge root (NiceGUI component)
    # This must be defined BEFORE the static files mount to take precedence
    @app.get("/static/js/canvas_editor.js")
    async def serve_canvas_editor():
        """Serve the canvas editor Vue component."""
        return FileResponse(
            CANVAS_EDITOR_JS,
            media_type="application/javascript",
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            }
        )

    # Static files
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    # Templates
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    def parse_bool(value: str, default: bool = True) -> bool:
        """Parse boolean query parameter."""
        if value is None:
            return default
        return value.lower() not in ('false', '0', 'no', 'off')

    @app.get("/", response_class=HTMLResponse)
    async def editor_page(
        request: Request,
        session_id: str = None,
        isolated: str = None,
        empty: str = None,
        width: int = 800,
        height: int = 600,
        # UI visibility options (as strings for reliable parsing)
        show_menu: str = None,
        show_navigator: str = None,
        show_layers: str = None,
        show_tool_properties: str = None,
        show_bottom_bar: str = None,
        show_history: str = None,
        show_toolbar: str = None,
        show_document_tabs: str = None,
        # Tool groups (comma-separated for query params)
        visible_tool_groups: str = None,
        hidden_tool_groups: str = None,
    ):
        """Serve the editor HTML page.

        Args:
            request: FastAPI request
            session_id: Optional session ID (generated if not provided)
            isolated: If True, disable auto-save/restore (for embedded use)
            empty: If True, create document with no layers
            width: Document width in pixels
            height: Document height in pixels
            show_menu: Show the File/Edit/View menu bar
            show_navigator: Show the navigator panel
            show_layers: Show the layers panel
            show_tool_properties: Show tool properties/ribbon
            show_bottom_bar: Show the status bar
            show_history: Show the history panel
            show_toolbar: Show the tools panel
            show_document_tabs: Show document tabs for multi-document support
            visible_tool_groups: Comma-separated list of tool groups to show
            hidden_tool_groups: Comma-separated list of tool groups to hide
        """
        # Parse booleans explicitly
        is_isolated = parse_bool(isolated, False)
        is_empty = parse_bool(empty, False)
        p_show_menu = parse_bool(show_menu, True)
        p_show_navigator = parse_bool(show_navigator, True)
        p_show_layers = parse_bool(show_layers, True)
        p_show_tool_properties = parse_bool(show_tool_properties, True)
        p_show_bottom_bar = parse_bool(show_bottom_bar, True)
        p_show_history = parse_bool(show_history, True)
        p_show_toolbar = parse_bool(show_toolbar, True)
        p_show_document_tabs = parse_bool(show_document_tabs, True)

        # Parse tool group lists from comma-separated strings
        visible_groups = visible_tool_groups.split(",") if visible_tool_groups else None
        hidden_groups = hidden_tool_groups.split(",") if hidden_tool_groups else []

        return templates.TemplateResponse("editor.html", {
            "request": request,
            "session_id": session_id or str(uuid.uuid4()),
            "isolated": is_isolated,
            "empty": is_empty,
            "width": width,
            "height": height,
            "show_menu": p_show_menu,
            "show_navigator": p_show_navigator,
            "show_layers": p_show_layers,
            "show_tool_properties": p_show_tool_properties,
            "show_bottom_bar": p_show_bottom_bar,
            "show_history": p_show_history,
            "show_toolbar": p_show_toolbar,
            "show_document_tabs": p_show_document_tabs,
            "visible_tool_groups": visible_groups,
            "hidden_tool_groups": hidden_groups,
        })

    return app


# Create the app instance for uvicorn
app = create_standalone_app()


def main():
    """Run the standalone server."""
    import uvicorn

    port = int(os.environ.get("STAGFORGE_PORT", "8080"))
    uvicorn.run(
        "stagforge.standalone:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[str(STAGFORGE_DIR)],
    )


if __name__ == "__main__":
    main()
