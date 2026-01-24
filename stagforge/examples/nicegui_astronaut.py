"""Sample NiceGUI app: Fullscreen app with isolated Stagforge editor.

This example demonstrates how to embed Stagforge in a NiceGUI application
with isolated mode enabled. The editor loads the skimage astronaut image.

Run:
    poetry run python stagforge/examples/nicegui_astronaut.py

Then open http://localhost:8080 in your browser.
"""
import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def log(msg):
    """Log with timestamp and thread info."""
    tid = threading.current_thread().name
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tid}] {msg}", flush=True)

from fastapi import Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from nicegui import app, ui
from skimage import data

# Mount Stagforge API and static files
from stagforge.app import create_api_app

STAGFORGE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = STAGFORGE_DIR / "templates"
CANVAS_EDITOR_JS = STAGFORGE_DIR / "canvas_editor.js"

# Mount the API
api_app = create_api_app()
app.mount("/api", api_app)

# Templates for editor page
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def parse_bool(value: str, default: bool = True) -> bool:
    """Parse boolean query parameter, defaulting to True if not specified."""
    if value is None:
        return default
    return value.lower() not in ('false', '0', 'no', 'off')


# Serve editor page at /editor for iframe embedding
@app.get("/editor", response_class=HTMLResponse)
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
    # Tool groups (comma-separated)
    visible_tool_groups: str = None,
    hidden_tool_groups: str = None,
):
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

    # Debug: log received parameters
    log(f"editor_page: show_navigator={show_navigator}→{p_show_navigator}, show_layers={show_layers}→{p_show_layers}, show_history={show_history}→{p_show_history}")

    # Parse tool group lists
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
        "visible_tool_groups": visible_groups,
        "hidden_tool_groups": hidden_groups,
    })

# Serve canvas_editor.js from stagforge root
@app.get("/static/js/canvas_editor.js")
async def serve_canvas_editor():
    return FileResponse(
        CANVAS_EDITOR_JS,
        media_type="application/javascript",
    )

# Serve static files for the editor (AFTER specific routes)
app.add_static_files("/static", STAGFORGE_DIR / "frontend")

# Import the editor component (after mounting routes)
from stagforge.nicegui import StagforgeEditor

# Global references
editor_ref = None

# Thread pool for blocking HTTP requests (avoids deadlock)
_executor = ThreadPoolExecutor(max_workers=2)

# Editor configuration state (will be set from UI before opening editor)
editor_config = {
    "show_menu": True,
    "show_navigator": True,
    "show_layers": True,
    "show_tool_properties": True,
    "show_bottom_bar": True,
    "show_history": True,
    "show_toolbar": True,
    "visible_tool_groups": None,  # None = all, or list of group IDs
    "hidden_tool_groups": [],     # List of group IDs to hide
}


async def open_editor():
    """Open isolated editor with astronaut image and current config."""
    global editor_ref

    # Get the astronaut image as a numpy array (512, 512, 3) uint8
    astronaut = data.astronaut()

    with ui.dialog().props('maximized persistent') as dialog:
        with ui.card().classes('w-full h-full p-0'):
            # Header bar
            with ui.row().classes('w-full items-center p-2 bg-gray-800 gap-2'):
                ui.label('Isolated Editor - Astronaut').classes('text-white text-xl flex-grow')
                ui.button('Load Astronaut', on_click=load_astronaut, icon='image').classes('mr-2')
                ui.button('Get Image', on_click=get_result, icon='download').classes('mr-2')
                ui.button('Close', on_click=dialog.close, icon='close')

            # Editor iframe - document sized for astronaut (512x512), UI larger
            editor_ref = StagforgeEditor(
                width=1200,
                height=800,
                doc_width=512,   # Astronaut is 512x512
                doc_height=512,
                isolated=True,
                initial_image=astronaut,
                # UI configuration from settings
                show_menu=editor_config["show_menu"],
                show_navigator=editor_config["show_navigator"],
                show_layers=editor_config["show_layers"],
                show_tool_properties=editor_config["show_tool_properties"],
                show_bottom_bar=editor_config["show_bottom_bar"],
                show_history=editor_config["show_history"],
                show_toolbar=editor_config["show_toolbar"],
                visible_tool_groups=editor_config["visible_tool_groups"],
                hidden_tool_groups=editor_config["hidden_tool_groups"],
            ).classes('flex-grow')

    dialog.open()


async def load_astronaut():
    """Manually load the astronaut image into the editor."""
    log("load_astronaut() CALLED - button clicked")
    if not editor_ref:
        ui.notify('No editor open', type='warning')
        return

    try:
        log("load_astronaut() submitting to executor...")
        loop = asyncio.get_event_loop()
        log(f"load_astronaut() got loop: {loop}")
        future = loop.run_in_executor(_executor, editor_ref.load_initial_image)
        log(f"load_astronaut() future created: {future}")
        log("load_astronaut() awaiting future...")
        success = await future
        log(f"load_astronaut() future returned: {success}")
        if success:
            ui.notify('Astronaut loaded!', type='positive')
        else:
            ui.notify('Failed to load image', type='negative')
    except Exception as e:
        log(f"load_astronaut() EXCEPTION: {e}")
        ui.notify(f'Error: {e}', type='negative')


async def get_result():
    """Retrieve edited image from the editor."""
    if not editor_ref:
        ui.notify('No editor open', type='warning')
        return

    try:
        img_bytes = await editor_ref.get_merged_image('png')

        # Save to temp file
        output_path = '/tmp/astronaut_edited.png'
        with open(output_path, 'wb') as f:
            f.write(img_bytes)

        ui.notify(f'Saved: {len(img_bytes):,} bytes to {output_path}', type='positive')

    except Exception as e:
        ui.notify(f'Error: {e}', type='negative')


@ui.page('/')
def main():
    """Main page with configuration options and button to open editor."""
    # All available tool groups for selection
    ALL_TOOL_GROUPS = list(StagforgeEditor.TOOL_GROUPS.keys())

    with ui.column().classes('w-full min-h-screen p-8'):
        ui.label('Stagforge NiceGUI Demo').classes('text-3xl mb-4')
        ui.label('Configure the editor below, then click to open.').classes('mb-6 text-gray-600')

        with ui.row().classes('gap-8 flex-wrap'):
            # Left column: UI visibility options
            with ui.card().classes('p-4'):
                ui.label('Panel Visibility').classes('text-lg font-bold mb-2')

                ui.checkbox('Menu Bar (File/Edit/View)').bind_value(editor_config, 'show_menu')
                ui.checkbox('Navigator').bind_value(editor_config, 'show_navigator')
                ui.checkbox('Layers Panel').bind_value(editor_config, 'show_layers')
                ui.checkbox('Tool Properties').bind_value(editor_config, 'show_tool_properties')
                ui.checkbox('History Panel').bind_value(editor_config, 'show_history')
                ui.checkbox('Bottom Status Bar').bind_value(editor_config, 'show_bottom_bar')
                ui.checkbox('Toolbar (Tools Panel)').bind_value(editor_config, 'show_toolbar')

            # Right column: Tool category selection
            with ui.card().classes('p-4'):
                ui.label('Tool Categories').classes('text-lg font-bold mb-2')
                ui.label('Select which tool groups to show:').classes('text-sm text-gray-500 mb-2')

                # Use a select for visible groups (multi-select)
                tool_options = {group: f"{group}: {desc}" for group, desc in StagforgeEditor.TOOL_GROUPS.items()}

                def update_hidden_groups(selected: list):
                    """Update hidden groups based on selection."""
                    if selected is None or len(selected) == 0:
                        # Nothing selected = show all
                        editor_config["visible_tool_groups"] = None
                        editor_config["hidden_tool_groups"] = []
                    else:
                        # Show only selected groups
                        editor_config["visible_tool_groups"] = list(selected)
                        editor_config["hidden_tool_groups"] = []

                ui.select(
                    options=tool_options,
                    multiple=True,
                    label='Visible Tool Groups (empty = all)',
                ).classes('w-64').on('update:model-value', lambda e: update_hidden_groups(e.args))

                ui.label('Common presets:').classes('text-sm text-gray-500 mt-4')

                def set_drawing_only():
                    editor_config["visible_tool_groups"] = ["brush", "eraser", "fill", "eyedropper"]
                    editor_config["hidden_tool_groups"] = []

                def set_selection_only():
                    editor_config["visible_tool_groups"] = ["selection", "freeform", "quicksel", "move"]
                    editor_config["hidden_tool_groups"] = []

                def set_all_tools():
                    editor_config["visible_tool_groups"] = None
                    editor_config["hidden_tool_groups"] = []

                with ui.row().classes('gap-2'):
                    ui.button('Drawing Only', on_click=set_drawing_only).props('size=sm')
                    ui.button('Selection Only', on_click=set_selection_only).props('size=sm')
                    ui.button('All Tools', on_click=set_all_tools).props('size=sm')

        # Open editor button
        ui.button('Open Isolated Editor', on_click=open_editor, icon='edit').classes('text-xl mt-6')

        # Features info
        with ui.expansion('Features', icon='info').classes('mt-8 w-full max-w-2xl'):
            ui.markdown('''
- **Isolated mode**: No auto-save, fresh document each time
- **Initial image**: Astronaut from skimage (512x512) loaded automatically
- **Export**: Click "Get Image" to save the edited result
- **Configurable UI**: Toggle panels and tool visibility before opening
- **Tool Categories**: Show only specific tool groups for simplified interfaces
            ''')


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, title='Stagforge NiceGUI Demo', show=False)
