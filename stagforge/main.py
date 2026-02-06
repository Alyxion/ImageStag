"""Stagforge Image Editor - NiceGUI entry point."""

import os
from pathlib import Path
from typing import Optional

from nicegui import app, ui
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from stagforge.config import settings


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


app.add_middleware(NoCacheMiddleware)

# Import and mount FastAPI backend
from stagforge.app import create_api_app
from stagforge.canvas_editor import CanvasEditor

# Mount API routes
api_app = create_api_app()
app.mount("/api", api_app)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.add_static_files("/static", FRONTEND_DIR)

# Serve imagestag JS/WASM files for browser-side filter execution
IMAGESTAG_DIR = Path(__file__).parent.parent / "imagestag"
app.add_static_files("/imgstag", IMAGESTAG_DIR)

# Console capture JavaScript - injected into page
CONSOLE_CAPTURE_JS = """
(function() {
    if (window._consoleCaptured) return;
    window._consoleCaptured = true;
    window._consoleLogs = [];
    const maxLogs = 200;

    const originalConsole = {
        log: console.log.bind(console),
        warn: console.warn.bind(console),
        error: console.error.bind(console),
        info: console.info.bind(console)
    };

    function captureLog(level, args) {
        const entry = {
            level: level,
            timestamp: new Date().toISOString(),
            message: Array.from(args).map(arg => {
                try {
                    if (typeof arg === 'object') return JSON.stringify(arg);
                    return String(arg);
                } catch (e) {
                    return String(arg);
                }
            }).join(' ')
        };
        window._consoleLogs.push(entry);
        if (window._consoleLogs.length > maxLogs) {
            window._consoleLogs.shift();
        }
    }

    console.log = function(...args) { captureLog('log', args); originalConsole.log(...args); };
    console.warn = function(...args) { captureLog('warn', args); originalConsole.warn(...args); };
    console.error = function(...args) { captureLog('error', args); originalConsole.error(...args); };
    console.info = function(...args) { captureLog('info', args); originalConsole.info(...args); };

    window.getConsoleLogs = function(clear = false) {
        const logs = [...window._consoleLogs];
        if (clear) window._consoleLogs = [];
        return logs;
    };

    console.log('Console capture initialized');
})();
"""

# Debug router for console access
debug_router = APIRouter(prefix="/debug", tags=["debug"])


@debug_router.get("/console")
async def get_console_logs(clear: bool = False, level: Optional[str] = None):
    """
    Fetch browser console logs.

    Args:
        clear: If True, clear logs after fetching
        level: Filter by level (log, warn, error, info)

    Returns:
        JSON array of log entries
    """
    # This endpoint is called, but we need to get logs from the browser
    # The actual fetching happens via JavaScript in the browser
    return JSONResponse({
        "message": "Use /debug/console/fetch from the browser or call fetchConsoleLogs()"
    })


# Store for console logs fetched from browser
_browser_console_logs = []


def get_browser_logs():
    """Get the stored browser console logs."""
    return _browser_console_logs


app.mount("/debug", debug_router)


@ui.page("/")
async def index(mode: str = None, backend: str = None):
    """Main editor page.

    Args:
        mode: Optional UI mode override via query param (?mode=desktop|tablet|limited)
        backend: Backend mode override (?backend=on|offline|off)
    """
    # Add stylesheet
    ui.add_head_html('<link rel="stylesheet" href="/static/css/main.css">')

    # Add JSZip library for SFR file format (ZIP-based)
    ui.add_head_html('<script src="/static/js/lib/jszip.min.js"></script>')

    # Set initial UI mode - URL query param, default to desktop
    ui.add_head_html('''<script>
        (function() {
            var urlParams = new URLSearchParams(window.location.search);
            var urlMode = urlParams.get('mode');
            // Use URL param if valid, otherwise default to desktop
            var mode = (urlMode && ['desktop', 'tablet', 'limited'].includes(urlMode)) ? urlMode : 'desktop';
            document.documentElement.setAttribute('data-initial-mode', mode);
            window.__stagforgeUrlMode = mode;
        })();
    </script>''')

    # Inject console capture script
    ui.add_head_html(f'<script>{CONSOLE_CAPTURE_JS}</script>')

    # Create the canvas editor component - it handles everything
    backend_mode = (backend or 'on').lower()
    editor = CanvasEditor(width=800, height=600, api_base="/api", backend_mode=backend_mode).classes("w-full h-full")

    # Add debug button to fetch console logs (can be toggled via keyboard shortcut)
    async def fetch_and_print_logs():
        """Fetch console logs from browser and print them."""
        logs = await ui.run_javascript('window.getConsoleLogs(true)')
        if logs:
            print("\n=== Browser Console Logs ===")
            for log in logs:
                level = log.get('level', 'log').upper()
                timestamp = log.get('timestamp', '')
                message = log.get('message', '')
                print(f"[{level}] {timestamp}: {message}")
            print("============================\n")
        else:
            print("No console logs to fetch")

    # Add keyboard shortcut to fetch logs (Ctrl+Shift+L)
    async def on_key(e):
        if e.key == 'L' and e.modifiers.ctrl and e.modifiers.shift:
            await fetch_and_print_logs()

    ui.keyboard(on_key=on_key)


def main():
    """Run the application."""
    import argparse

    parser = argparse.ArgumentParser(description="Stagforge Image Editor")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help=f"HTTP port (default: {settings.PORT}, env: STAGFORGE_PORT)"
    )
    parser.add_argument(
        "--host", "-H",
        default=None,
        help=f"Host to bind to (default: {settings.HOST}, env: STAGFORGE_HOST)"
    )
    parser.add_argument(
        "--https",
        action="store_true",
        default=None,
        help="Enable HTTPS proxy (env: STAGFORGE_HTTPS_ENABLED)"
    )
    parser.add_argument(
        "--https-port", "-s",
        type=int,
        default=None,
        help=f"HTTPS proxy port (default: {settings.HTTPS_PORT}, env: STAGFORGE_HTTPS_PORT)"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload"
    )

    args = parser.parse_args()

    # Use CLI args > env vars > defaults (via settings)
    port = args.port or settings.PORT
    host = args.host or settings.HOST
    https_enabled = args.https if args.https is not None else settings.HTTPS_ENABLED
    https_port = args.https_port or settings.HTTPS_PORT

    # Start HTTPS proxy if enabled
    if https_enabled:
        from stagforge.https_proxy import start_https_proxy
        print(f"[Stagforge] Starting HTTPS proxy on port {https_port}...")
        start_https_proxy(https_port=https_port, http_port=port, host=host)

    print(f"[Stagforge] Starting HTTP server on {host}:{port}")
    if https_enabled:
        print(f"[Stagforge] HTTPS available at https://localhost:{https_port}")

    ui.run(
        host=host,
        port=port,
        title="Stagforge Image Editor",
        reload=not args.no_reload,
        show=False,
        uvicorn_reload_includes="*.py,*.js,*.css,*.html",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
