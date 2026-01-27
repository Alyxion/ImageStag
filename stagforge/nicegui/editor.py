"""NiceGUI wrapper for embedding Stagforge editor.

This module provides the StagforgeEditor component for embedding the Stagforge
image editor in NiceGUI applications with isolated mode support.

Example usage:
    from stagforge.nicegui import StagforgeEditor
    from skimage import data

    # Create isolated editor with initial image
    editor = StagforgeEditor(
        width=800,
        height=600,
        isolated=True,
        initial_image=data.astronaut(),  # numpy array
    )

    # Get the edited image
    result = await editor.get_merged_image('png')
"""
import uuid
import base64
import io
import threading
import time
from typing import Optional, Union

import numpy as np
from nicegui import ui
from nicegui.element import Element


def log(msg):
    """Log with timestamp and thread info."""
    tid = threading.current_thread().name
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tid}] [editor.py] {msg}", flush=True)


class StagforgeEditor(Element):
    """Embeddable Stagforge editor component with isolated mode support.

    The editor is embedded as an iframe pointing to the standalone Stagforge server.
    In isolated mode, auto-save is disabled to prevent cross-session interference.

    Args:
        width: Editor iframe width in pixels
        height: Editor iframe height in pixels
        doc_width: Document canvas width (default: same as width)
        doc_height: Document canvas height (default: same as height)
        isolated: If True, disable auto-save/restore (for embedded use)
        initial_image: Optional image to load (bytes or numpy array)
        server_url: Base URL of the Stagforge server (default: current host)
        show_menu: Show the File/Edit/View menu bar
        show_navigator: Show the navigator panel
        show_layers: Show the layers panel
        show_tool_properties: Show tool properties/ribbon
        show_bottom_bar: Show the status bar
        show_history: Show the history panel
        show_toolbar: Show the tools panel
        show_document_tabs: Show document tabs for multi-document support
        visible_tool_groups: List of tool group IDs to show (None = all)
        hidden_tool_groups: List of tool group IDs to hide
    """

    # Tool group constants for easy reference
    TOOL_GROUPS = {
        "selection": "Selection tools (marquee)",
        "freeform": "Freeform selection (lasso)",
        "quicksel": "Quick selection (magic wand)",
        "move": "Move tool",
        "crop": "Crop tool",
        "hand": "Hand/pan tool",
        "brush": "Brush tools (brush, pencil, spray)",
        "eraser": "Eraser tool",
        "stamp": "Clone stamp",
        "retouch": "Retouching (smudge, blur, sharpen)",
        "dodge": "Dodge/burn/sponge",
        "pen": "Pen/vector tools",
        "shapes": "Shape tools (rect, circle, polygon, line)",
        "fill": "Fill/gradient",
        "text": "Text tool",
        "eyedropper": "Eyedropper/color picker",
    }

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        doc_width: int = None,
        doc_height: int = None,
        isolated: bool = False,
        initial_image: Optional[Union[bytes, np.ndarray]] = None,
        server_url: str = "",
        # UI visibility options
        show_menu: bool = True,
        show_navigator: bool = True,
        show_layers: bool = True,
        show_tool_properties: bool = True,
        show_bottom_bar: bool = True,
        show_history: bool = True,
        show_toolbar: bool = True,
        show_document_tabs: bool = True,
        # Tool category filtering
        visible_tool_groups: Optional[list] = None,
        hidden_tool_groups: Optional[list] = None,
        # Backend mode: "on" (default), "offline" (no filters), "off" (no connection)
        backend_mode: str = "on",
    ) -> None:
        super().__init__("iframe")
        self.session_id = str(uuid.uuid4())
        self._isolated = isolated
        self._initial_image = initial_image
        self._server_url = server_url
        self._width = width
        self._height = height

        # Document dimensions default to editor size
        canvas_width = doc_width if doc_width is not None else width
        canvas_height = doc_height if doc_height is not None else height

        # Build URL with query parameters
        # Use /editor path for NiceGUI embedding (avoids conflict with NiceGUI's / route)
        params = [
            f"session_id={self.session_id}",
            f"width={canvas_width}",
            f"height={canvas_height}",
        ]
        if isolated:
            params.append("isolated=true")
        if initial_image is not None:
            params.append("empty=true")  # Start empty, we'll add the image layer via API

        # UI visibility params
        if not show_menu:
            params.append("show_menu=false")
        if not show_navigator:
            params.append("show_navigator=false")
        if not show_layers:
            params.append("show_layers=false")
        if not show_tool_properties:
            params.append("show_tool_properties=false")
        if not show_bottom_bar:
            params.append("show_bottom_bar=false")
        if not show_history:
            params.append("show_history=false")
        if not show_toolbar:
            params.append("show_toolbar=false")
        if not show_document_tabs:
            params.append("show_document_tabs=false")

        # Tool group filtering (ensure all items are strings)
        if visible_tool_groups is not None:
            # Handle case where items might be dicts or other types
            groups = [str(g) if isinstance(g, str) else str(g.get('id', g)) if isinstance(g, dict) else str(g) for g in visible_tool_groups]
            params.append(f"visible_tool_groups={','.join(groups)}")
        if hidden_tool_groups:
            groups = [str(g) if isinstance(g, str) else str(g.get('id', g)) if isinstance(g, dict) else str(g) for g in hidden_tool_groups]
            params.append(f"hidden_tool_groups={','.join(groups)}")

        # Backend mode
        if backend_mode and backend_mode != "on":
            params.append(f"backend={backend_mode}")

        url = f"{server_url}/editor?{'&'.join(params)}"
        self._props['src'] = url
        self._props['style'] = f'width:{width}px;height:{height}px;border:none;'
        self._props['allow'] = 'clipboard-read; clipboard-write'

    def load_initial_image(self) -> bool:
        """Load initial image via the import API.

        Call this after the editor is ready.

        Returns:
            True if successful, False otherwise
        """
        log("load_initial_image() CALLED")
        if self._initial_image is None:
            log("load_initial_image() no initial image, returning True")
            return True

        import requests

        try:
            log("load_initial_image() converting image to base64...")
            if isinstance(self._initial_image, np.ndarray):
                # Convert numpy array to PNG bytes
                from PIL import Image
                img = Image.fromarray(self._initial_image)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                b64 = base64.b64encode(buf.getvalue()).decode()
                content_type = "image/png"
                log(f"load_initial_image() converted numpy array, b64 len={len(b64)}")
            else:
                # Assume bytes - try to detect format
                b64 = base64.b64encode(self._initial_image).decode()
                content_type = "image/png"
                log(f"load_initial_image() converted bytes, b64 len={len(b64)}")

            # Import via layer import API (synchronous)
            base_url = self._server_url or "http://localhost:8080"
            url = f"{base_url}/api/sessions/{self.session_id}/documents/current/layers/import"
            log(f"load_initial_image() POST {url}")
            log(f"load_initial_image() making request NOW...")
            resp = requests.post(
                url,
                json={
                    "data": b64,
                    "content_type": content_type,
                    "name": "Imported Image",
                },
                timeout=30.0,
            )
            log(f"load_initial_image() response received: {resp.status_code}")
            resp.raise_for_status()
            log("load_initial_image() SUCCESS")
            return True

        except Exception as e:
            log(f"load_initial_image() EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def get_merged_image(self, format: str = 'png') -> bytes:
        """Get flattened image from all visible layers.

        Args:
            format: Image format ('png', 'webp', 'avif')

        Returns:
            Image bytes in the requested format
        """
        import httpx

        base_url = self._server_url or "http://localhost:8080"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            resp = await client.get(
                f"/api/sessions/{self.session_id}/documents/current/image",
                params={"format": format}
            )
            resp.raise_for_status()
            return resp.content

    async def get_layer_image(self, layer_id: str, format: str = 'png') -> bytes:
        """Get image from a specific layer.

        Args:
            layer_id: The layer ID to get image from
            format: Image format ('png', 'webp', 'avif')

        Returns:
            Image bytes in the requested format
        """
        import httpx

        base_url = self._server_url or "http://localhost:8080"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            resp = await client.get(
                f"/api/sessions/{self.session_id}/documents/current/layers/{layer_id}/image",
                params={"format": format}
            )
            resp.raise_for_status()
            return resp.content

    async def get_document_json(self) -> dict:
        """Export the current document as JSON.

        Returns:
            Document data as a dictionary
        """
        import httpx

        base_url = self._server_url or "http://localhost:8080"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            resp = await client.post(
                f"/api/sessions/{self.session_id}/document/export"
            )
            resp.raise_for_status()
            return resp.json()

    async def load_document_json(self, document_data: dict) -> None:
        """Import a document from JSON.

        Args:
            document_data: Document data dictionary
        """
        import httpx

        base_url = self._server_url or "http://localhost:8080"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            await client.post(
                f"/api/sessions/{self.session_id}/document/import",
                json=document_data
            )
