"""Stagforge Image Editor - NiceGUI entry point."""

from pathlib import Path
from typing import Optional

from nicegui import app, ui
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import APIRouter
from fastapi.responses import JSONResponse


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
async def index(mode: str = None):
    """Main editor page.

    Args:
        mode: Optional UI mode override via query param (?mode=desktop|tablet|limited)
    """
    # Add stylesheet
    ui.add_head_html('<link rel="stylesheet" href="/static/css/main.css">')

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
    editor = CanvasEditor(width=800, height=600, api_base="/api").classes("w-full h-full")

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
    ui.run(
        host="0.0.0.0",
        port=8080,
        title="Stagforge Image Editor",
        reload=True,
        show=False,
        uvicorn_reload_includes="*.py,*.js,*.css,*.html",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
