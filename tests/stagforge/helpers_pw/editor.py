"""EditorTestHelper - Main helper class for Stagforge UI testing with Playwright."""

import asyncio
import json
from typing import Optional, Dict, Any, List, Tuple
from playwright.async_api import Page, expect


class EditorTestHelper:
    """
    Main helper class for interacting with the Stagforge editor in tests.

    Provides unified methods for:
    - Waiting for editor to load
    - Accessing Vue component state
    - Executing JavaScript in the browser
    - Mouse interactions on canvas
    - Keyboard shortcuts
    """

    def __init__(self, page: Page, base_url: str = "http://127.0.0.1:8080"):
        self.page = page
        self.base_url = base_url
        self._canvas_rect = None

    async def navigate_to_editor(self):
        """Navigate to the editor page and wait for it to load."""
        await self.page.goto(self.base_url)
        await self.wait_for_editor()
        return self

    async def wait_for_editor(self, timeout: float = 15000):
        """Wait for the editor to fully load (does not require a document to be open)."""
        # Wait for editor root
        await self.page.wait_for_selector(".editor-root", timeout=timeout)

        # Wait for app to be exposed globally (may or may not have a document)
        await self.page.wait_for_function(
            """() => {
                const app = window.__stagforge_app__;
                return app && app.documentManager && app.renderer;
            }""",
            timeout=timeout
        )

        # Small delay for any remaining initialization
        await asyncio.sleep(0.3)
        return self

    async def execute_js(self, script: str) -> Any:
        """Execute JavaScript in the browser and return the result."""
        return await self.page.evaluate(script)

    async def get_vue_data(self, property_path: str) -> Any:
        """
        Get a property from the Vue component.

        Args:
            property_path: Dot-separated path to property (e.g., "currentToolId", "layers.length")
        """
        return await self.execute_js(f"""
            (() => {{
                const vm = window.__stagforge_app__;
                if (!vm) return null;
                return vm.{property_path};
            }})()
        """)

    async def get_app_state(self) -> Dict[str, Any]:
        """Get the full app state object."""
        return await self.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                if (!vm) return null;
                const app = vm.getState?.() || vm;
                if (!app) return null;
                return {
                    width: app.layerStack?.width,
                    height: app.layerStack?.height,
                    layerCount: app.layerStack?.layers?.length,
                    zoom: app.renderer?.zoom,
                    currentTool: app.toolManager?.currentTool?.constructor?.id
                };
            })()
        """)

    # ===== Canvas Interaction =====

    async def get_canvas_element(self):
        """Get the main canvas element."""
        return self.page.locator("#main-canvas")

    async def get_canvas_rect(self) -> Dict[str, float]:
        """Get the canvas bounding rect (cached)."""
        if self._canvas_rect is None:
            canvas = await self.get_canvas_element()
            box = await canvas.bounding_box()
            self._canvas_rect = {
                'x': box['x'],
                'y': box['y'],
                'width': box['width'],
                'height': box['height']
            }
        return self._canvas_rect

    def invalidate_canvas_rect(self):
        """Clear cached canvas rect (call after resize/zoom)."""
        self._canvas_rect = None

    async def doc_to_screen(self, doc_x: float, doc_y: float) -> Tuple[float, float]:
        """Convert document coordinates to screen coordinates."""
        result = await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                if (!app?.renderer) return null;
                return app.renderer.canvasToScreen({doc_x}, {doc_y});
            }})()
        """)
        if result:
            canvas_rect = await self.get_canvas_rect()
            return (result['x'] + canvas_rect['x'], result['y'] + canvas_rect['y'])
        return (doc_x, doc_y)

    async def click_at_doc(self, doc_x: float, doc_y: float, button: str = 'left'):
        """Click at document coordinates."""
        screen_x, screen_y = await self.doc_to_screen(doc_x, doc_y)
        await self.page.mouse.click(screen_x, screen_y, button=button)
        return self

    async def alt_click_at_doc(self, doc_x: float, doc_y: float):
        """Alt+click at document coordinates (used for clone stamp source, etc.)."""
        screen_x, screen_y = await self.doc_to_screen(doc_x, doc_y)
        await self.page.keyboard.down('Alt')
        await self.page.mouse.click(screen_x, screen_y)
        await self.page.keyboard.up('Alt')
        return self

    async def drag_at_doc(self, start_x: float, start_y: float, end_x: float, end_y: float,
                          steps: int = 10):
        """Drag from start to end in document coordinates."""
        start_screen = await self.doc_to_screen(start_x, start_y)
        end_screen = await self.doc_to_screen(end_x, end_y)

        # Move to start position
        await self.page.mouse.move(start_screen[0], start_screen[1])
        await self.page.mouse.down()

        # Move in steps for smooth drag
        for i in range(1, steps + 1):
            t = i / steps
            x = start_screen[0] + (end_screen[0] - start_screen[0]) * t
            y = start_screen[1] + (end_screen[1] - start_screen[1]) * t
            await self.page.mouse.move(x, y)

        await self.page.mouse.up()
        await asyncio.sleep(0.1)  # Allow for render
        return self

    async def draw_stroke(self, points: List[Tuple[float, float]]):
        """Draw a stroke through multiple points in document coordinates."""
        if len(points) < 1:
            return self

        # Handle single-point strokes (e.g., dots)
        if len(points) == 1:
            screen = await self.doc_to_screen(points[0][0], points[0][1])
            await self.page.mouse.move(screen[0], screen[1])
            await self.page.mouse.down()
            await self.page.mouse.up()
            await asyncio.sleep(0.1)
            return self

        # Move to first point and press
        first_screen = await self.doc_to_screen(points[0][0], points[0][1])
        await self.page.mouse.move(first_screen[0], first_screen[1])
        await self.page.mouse.down()

        # Move through remaining points
        for x, y in points[1:]:
            screen = await self.doc_to_screen(x, y)
            await self.page.mouse.move(screen[0], screen[1])

        await self.page.mouse.up()
        await asyncio.sleep(0.1)
        return self

    # ===== Tool Selection =====

    async def select_tool(self, tool_id: str):
        """Select a tool by ID."""
        await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                app?.toolManager?.select('{tool_id}');
            }})()
        """)
        await asyncio.sleep(0.1)
        return self

    async def get_current_tool(self) -> str:
        """Get the current tool ID."""
        return await self.get_vue_data("currentToolId")

    async def set_tool_property(self, prop_id: str, value: Any):
        """Set a tool property."""
        value_json = json.dumps(value)
        await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const tool = app?.toolManager?.currentTool;
                if (tool && tool.setProperty) {{
                    tool.setProperty('{prop_id}', {value_json});
                }}
            }})()
        """)
        return self

    # ===== Keyboard Shortcuts =====

    async def press_key(self, key: str, ctrl: bool = False, shift: bool = False, alt: bool = False):
        """Press a key combination."""
        modifiers = []
        if ctrl:
            modifiers.append('Control')
        if shift:
            modifiers.append('Shift')
        if alt:
            modifiers.append('Alt')

        # Focus the canvas first
        canvas = await self.get_canvas_element()
        await canvas.focus()

        if modifiers:
            key_combo = '+'.join(modifiers + [key])
            await self.page.keyboard.press(key_combo)
        else:
            await self.page.keyboard.press(key)

        await asyncio.sleep(0.1)
        return self

    async def undo(self):
        """Undo the last action."""
        return await self.press_key('z', ctrl=True)

    async def redo(self):
        """Redo the last undone action."""
        return await self.press_key('y', ctrl=True)

    async def copy(self):
        """Copy selection."""
        return await self.press_key('c', ctrl=True)

    async def cut(self):
        """Cut selection."""
        return await self.press_key('x', ctrl=True)

    async def paste(self):
        """Paste clipboard."""
        return await self.press_key('v', ctrl=True)

    async def select_all(self):
        """Select all."""
        return await self.press_key('a', ctrl=True)

    async def deselect(self):
        """Deselect."""
        return await self.press_key('d', ctrl=True)

    async def delete_selection(self):
        """Delete selection content."""
        return await self.press_key('Delete')

    async def fill_with_fg_color(self):
        """Fill selection (or layer) with foreground color."""
        await self.execute_js("""
            (() => {
                // __stagforge_app__ is the app state, __stagforge_vm__ is the Vue component
                const app = window.__stagforge_app__;
                const vm = window.__stagforge_vm__;
                if (!vm || !app) return;

                const fgColor = app?.foregroundColor || '#000000';

                // fillSelectionWithColor is a Vue component method
                if (vm.fillSelectionWithColor) {
                    vm.fillSelectionWithColor(fgColor);
                }
            })()
        """)
        await asyncio.sleep(0.1)
        return self

    async def fill_with_bg_color(self):
        """Fill selection (or layer) with background color."""
        await self.execute_js("""
            (() => {
                // __stagforge_app__ is the app state, __stagforge_vm__ is the Vue component
                const app = window.__stagforge_app__;
                const vm = window.__stagforge_vm__;
                if (!vm || !app) return;

                const bgColor = app?.backgroundColor || '#FFFFFF';

                // fillSelectionWithColor is a Vue component method
                if (vm.fillSelectionWithColor) {
                    vm.fillSelectionWithColor(bgColor);
                }
            })()
        """)
        await asyncio.sleep(0.1)
        return self

    # ===== Layer Operations =====

    async def get_layer_count(self) -> int:
        """Get the number of layers."""
        result = await self.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                return app?.layerStack?.layers?.length || 0;
            })()
        """)
        return result or 0

    async def get_active_layer_id(self) -> Optional[str]:
        """Get the active layer ID."""
        return await self.get_vue_data("activeLayerId")

    async def get_layer_info(self, index: int = None, layer_id: str = None) -> Optional[Dict]:
        """Get layer information by index or ID."""
        if layer_id:
            return await self.execute_js(f"""
                (() => {{
                    const app = window.__stagforge_app__;
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (!layer) return null;
                    return {{
                        id: layer.id,
                        name: layer.name,
                        width: layer.width,
                        height: layer.height,
                        offsetX: layer.offsetX,
                        offsetY: layer.offsetY,
                        opacity: layer.opacity,
                        visible: layer.visible,
                        locked: layer.locked
                    }};
                }})()
            """)
        elif index is not None:
            return await self.execute_js(f"""
                (() => {{
                    const app = window.__stagforge_app__;
                    const layer = app?.layerStack?.layers?.[{index}];
                    if (!layer) return null;
                    return {{
                        id: layer.id,
                        name: layer.name,
                        width: layer.width,
                        height: layer.height,
                        offsetX: layer.offsetX,
                        offsetY: layer.offsetY,
                        opacity: layer.opacity,
                        visible: layer.visible,
                        locked: layer.locked
                    }};
                }})()
            """)
        else:
            # Get active layer info
            return await self.execute_js("""
                (() => {
                    const app = window.__stagforge_app__;
                    const layer = app?.layerStack?.getActiveLayer();
                    if (!layer) return null;
                    return {
                        id: layer.id,
                        name: layer.name,
                        width: layer.width,
                        height: layer.height,
                        offsetX: layer.offsetX,
                        offsetY: layer.offsetY,
                        opacity: layer.opacity,
                        visible: layer.visible,
                        locked: layer.locked
                    };
                })()
            """)

    async def add_layer(self, name: str = None, width: int = None, height: int = None,
                        offset_x: int = 0, offset_y: int = 0) -> str:
        """Add a new layer and return its ID."""
        options = {'offsetX': offset_x, 'offsetY': offset_y}
        if name:
            options['name'] = name
        if width:
            options['width'] = width
        if height:
            options['height'] = height

        options_json = json.dumps(options)
        return await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.addLayer({options_json});
                return layer?.id;
            }})()
        """)

    async def select_layer(self, index: int = None, layer_id: str = None):
        """Select a layer by index or ID."""
        if layer_id:
            await self.execute_js(f"""
                (() => {{
                    const app = window.__stagforge_app__;
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) app?.layerStack?.setActiveLayer(layer);
                }})()
            """)
        elif index is not None:
            await self.execute_js(f"""
                (() => {{
                    const app = window.__stagforge_app__;
                    app?.layerStack?.setActiveLayerByIndex({index});
                }})()
            """)
        return self

    async def delete_layer(self, layer_id: str = None):
        """Delete a layer by ID (or active layer if no ID given)."""
        if layer_id:
            await self.execute_js(f"""
                (() => {{
                    const app = window.__stagforge_app__;
                    app?.layerStack?.removeLayer('{layer_id}');
                    vm?.updateLayerList();
                }})()
            """)
        else:
            await self.execute_js("""
                (() => {
                    const app = window.__stagforge_app__;
                    const activeLayer = app?.layerStack?.getActiveLayer();
                    if (activeLayer) {
                        app.layerStack.removeLayer(activeLayer.id);
                    }
                })()
            """)
        return self

    # ===== Selection Operations =====

    async def get_selection(self) -> Optional[Dict]:
        """Get the current selection rectangle."""
        return await self.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const selTool = app?.toolManager?.tools?.get('selection');
                return selTool?.getSelection() || null;
            })()
        """)

    async def set_selection(self, x: int, y: int, width: int, height: int):
        """Set a rectangular selection."""
        await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const selTool = app?.toolManager?.tools?.get('selection');
                selTool?.setSelection({{x: {x}, y: {y}, width: {width}, height: {height}}});
            }})()
        """)
        return self

    async def clear_selection(self):
        """Clear the current selection."""
        await self.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const selTool = app?.toolManager?.tools?.get('selection');
                selTool?.clearSelection();
            })()
        """)
        return self

    # ===== Color Operations =====

    async def set_foreground_color(self, color: str):
        """Set the foreground color (hex string like '#FF0000')."""
        await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                if (app) app.foregroundColor = '{color}';
            }})()
        """)
        return self

    async def set_background_color(self, color: str):
        """Set the background color."""
        await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                if (app) app.backgroundColor = '{color}';
            }})()
        """)
        return self

    async def get_foreground_color(self) -> str:
        """Get the current foreground color."""
        return await self.execute_js("window.__stagforge_app__?.foregroundColor")

    async def get_background_color(self) -> str:
        """Get the current background color."""
        return await self.execute_js("window.__stagforge_app__?.backgroundColor")

    # ===== Document Operations =====

    async def get_document_size(self) -> Tuple[int, int]:
        """Get document width and height."""
        state = await self.get_app_state()
        return (state.get('width', 800), state.get('height', 600))

    async def new_document(self, width: int, height: int):
        """Create a new document and wait for it to be ready."""
        await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                if (app && app.documentManager) {{
                    app.documentManager.createDocument({{
                        width: {width},
                        height: {height},
                        name: 'Untitled',
                        activate: true
                    }});
                }}
            }})()
        """)
        self.invalidate_canvas_rect()
        # Wait for document to be ready with layers
        await self.page.wait_for_function(
            """() => {
                const app = window.__stagforge_app__;
                return app && app.layerStack && app.layerStack.layers && app.layerStack.layers.length > 0;
            }""",
            timeout=5000
        )
        await asyncio.sleep(0.1)
        return self

    # ===== Waiting =====

    async def wait(self, seconds: float):
        """Wait for a number of seconds."""
        await asyncio.sleep(seconds)
        return self

    async def wait_for_render(self):
        """Wait for the next render cycle."""
        await asyncio.sleep(0.1)
        return self

    # ===== Document Export/Import for Parity Testing =====

    async def export_document(self) -> Dict[str, Any]:
        """Export the current document as JSON for parity testing."""
        return await self.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                return vm?.exportDocument?.();
            })()
        """)

    async def import_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import a document from JSON."""
        doc_json = json.dumps(document_data)
        return await self.execute_js(f"""
            (() => {{
                const vm = window.__stagforge_app__;
                return vm?.importDocument?.({doc_json});
            }})()
        """)

    async def get_layer_image_data(self, layer_id: str = None) -> Dict[str, Any]:
        """Get layer image as RGBA bytes (base64 encoded).

        Returns dict with: data (base64), width, height
        """
        layer_arg = f"'{layer_id}'" if layer_id else "null"
        return await self.execute_js(f"""
            (() => {{
                const vm = window.__stagforge_app__;
                return vm?.getImageData?.({layer_arg});
            }})()
        """)

    async def get_composite_image_data(self) -> Dict[str, Any]:
        """Get flattened composite image as RGBA bytes (base64 encoded)."""
        return await self.get_layer_image_data(None)

    # ===== Text Layer Creation =====

    async def create_text_layer(self, text: str, x: int, y: int,
                                font_size: int = 24, font_family: str = "Arial",
                                color: str = "#000000", **kwargs) -> str:
        """Create a text layer and return its ID."""
        options = {
            'text': text,
            'x': x,
            'y': y,
            'fontSize': font_size,
            'fontFamily': font_family,
            'color': color,
            **kwargs
        }
        options_json = json.dumps(options)
        return await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;

                const TextLayer = window.TextLayer;
                if (!TextLayer) return null;

                const options = {options_json};
                const layer = new TextLayer({{
                    name: 'Text: ' + options.text.substring(0, 20),
                    offsetX: options.x,
                    offsetY: options.y,
                    fontSize: options.fontSize,
                    fontFamily: options.fontFamily,
                    color: options.color,
                    runs: [{{ text: options.text }}],
                    docWidth: app.layerStack.width,
                    docHeight: app.layerStack.height,
                }});

                app.layerStack.addLayer(layer);
                vm?.updateLayerList();
                return layer.id;
            }})()
        """)

    async def create_text_layer_with_runs(self, runs: List[Dict], x: int, y: int,
                                          font_size: int = 24, **kwargs) -> str:
        """Create a text layer with styled runs."""
        options = {
            'runs': runs,
            'x': x,
            'y': y,
            'fontSize': font_size,
            **kwargs
        }
        options_json = json.dumps(options)
        return await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;

                const TextLayer = window.TextLayer;
                if (!TextLayer) return null;

                const options = {options_json};
                const layer = new TextLayer({{
                    name: 'Rich Text',
                    offsetX: options.x,
                    offsetY: options.y,
                    fontSize: options.fontSize,
                    runs: options.runs,
                    docWidth: app.layerStack.width,
                    docHeight: app.layerStack.height,
                }});

                app.layerStack.addLayer(layer);
                vm?.updateLayerList();
                return layer.id;
            }})()
        """)

    # ===== Vector Layer Creation =====

    async def create_vector_layer(self, shapes: List[Dict], width: int = None,
                                  height: int = None) -> str:
        """Create a vector layer with shapes and return its ID."""
        options = {'shapes': shapes}
        if width:
            options['width'] = width
        if height:
            options['height'] = height
        options_json = json.dumps(options)
        return await self.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;

                const VectorLayer = window.VectorLayer;
                if (!VectorLayer) return null;

                const options = {options_json};
                const layer = new VectorLayer({{
                    name: 'Vector Layer',
                    width: options.width || app.layerStack.width,
                    height: options.height || app.layerStack.height,
                }});

                // Add shapes
                for (const shapeData of options.shapes) {{
                    const shape = layer.createShape(shapeData.type, shapeData);
                    if (shape) layer.addShape(shape);
                }}

                app.layerStack.addLayer(layer);
                vm?.updateLayerList();
                return layer.id;
            }})()
        """)
