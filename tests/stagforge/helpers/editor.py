"""EditorTestHelper - Main helper class for Slopstag UI testing."""

import time
import base64
import json
from typing import Optional, Dict, Any, List, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class EditorTestHelper:
    """
    Main helper class for interacting with the Slopstag editor in tests.

    Provides unified methods for:
    - Waiting for editor to load
    - Accessing Vue component state
    - Executing JavaScript in the browser
    - Mouse interactions on canvas
    - Keyboard shortcuts
    """

    def __init__(self, driver: WebDriver, base_url: str = "http://127.0.0.1:8080"):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 15)
        self._canvas_rect = None

    def navigate_to_editor(self):
        """Navigate to the editor page and wait for it to load."""
        self.driver.get(self.base_url)
        self.wait_for_editor()
        return self

    def wait_for_editor(self, timeout: float = 15):
        """Wait for the editor to fully load."""
        self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "editor-root"))
        )
        # Wait for Vue to mount and initialize
        self.wait.until(lambda d: self.execute_js("return window.__stagforge_app__ !== undefined"))
        # Wait for layer stack to be ready
        self.wait.until(lambda d: self.get_layer_count() > 0)
        time.sleep(0.3)  # Small delay for any remaining initialization
        return self

    def execute_js(self, script: str, *args) -> Any:
        """Execute JavaScript in the browser and return the result."""
        return self.driver.execute_script(script, *args)

    def get_vue_data(self, property_path: str) -> Any:
        """
        Get a property from the Vue component.

        Args:
            property_path: Dot-separated path to property (e.g., "currentToolId", "layers.length")
        """
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            if (!root || !root.__vue_app__) return null;
            const vm = root.__vue_app__._instance?.proxy;
            if (!vm) return null;
            return vm.{property_path};
        """)

    def get_app_state(self) -> Dict[str, Any]:
        """Get the full app state object."""
        return self.execute_js("""
            const root = document.querySelector('.editor-root');
            if (!root || !root.__vue_app__) return null;
            const vm = root.__vue_app__._instance?.proxy;
            if (!vm) return null;
            const app = vm.getState();
            if (!app) return null;
            return {
                width: app.layerStack?.width,
                height: app.layerStack?.height,
                layerCount: app.layerStack?.layers?.length,
                zoom: app.renderer?.zoom,
                currentTool: app.toolManager?.currentTool?.constructor?.id
            };
        """)

    # ===== Canvas Interaction =====

    def get_canvas_element(self):
        """Get the main canvas element."""
        return self.driver.find_element(By.ID, "main-canvas")

    def get_canvas_rect(self) -> Dict[str, float]:
        """Get the canvas bounding rect (cached)."""
        if self._canvas_rect is None:
            canvas = self.get_canvas_element()
            rect = canvas.rect
            self._canvas_rect = {
                'x': rect['x'],
                'y': rect['y'],
                'width': rect['width'],
                'height': rect['height']
            }
        return self._canvas_rect

    def invalidate_canvas_rect(self):
        """Clear cached canvas rect (call after resize/zoom)."""
        self._canvas_rect = None

    def doc_to_screen(self, doc_x: float, doc_y: float) -> Tuple[float, float]:
        """Convert document coordinates to screen coordinates."""
        result = self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();
            if (!app?.renderer) return null;
            return app.renderer.canvasToScreen({doc_x}, {doc_y});
        """)
        if result:
            canvas_rect = self.get_canvas_rect()
            return (result['x'] + canvas_rect['x'], result['y'] + canvas_rect['y'])
        return (doc_x, doc_y)

    def click_at_doc(self, doc_x: float, doc_y: float, button: str = 'left'):
        """Click at document coordinates."""
        screen_x, screen_y = self.doc_to_screen(doc_x, doc_y)
        canvas = self.get_canvas_element()
        canvas_rect = self.get_canvas_rect()

        # Calculate offset from canvas top-left
        offset_x = screen_x - canvas_rect['x']
        offset_y = screen_y - canvas_rect['y']

        actions = ActionChains(self.driver)
        actions.move_to_element_with_offset(canvas, offset_x, offset_y)
        if button == 'left':
            actions.click()
        elif button == 'right':
            actions.context_click()
        actions.perform()
        return self

    def alt_click_at_doc(self, doc_x: float, doc_y: float):
        """Alt+click at document coordinates (used for clone stamp source, etc.)."""
        screen_x, screen_y = self.doc_to_screen(doc_x, doc_y)
        canvas = self.get_canvas_element()
        canvas_rect = self.get_canvas_rect()

        offset_x = screen_x - canvas_rect['x']
        offset_y = screen_y - canvas_rect['y']

        actions = ActionChains(self.driver)
        actions.key_down(Keys.ALT)
        actions.move_to_element_with_offset(canvas, offset_x, offset_y)
        actions.click()
        actions.key_up(Keys.ALT)
        actions.perform()
        return self

    def drag_at_doc(self, start_x: float, start_y: float, end_x: float, end_y: float,
                    steps: int = 10):
        """Drag from start to end in document coordinates."""
        canvas = self.get_canvas_element()
        canvas_rect = self.get_canvas_rect()

        start_screen = self.doc_to_screen(start_x, start_y)
        end_screen = self.doc_to_screen(end_x, end_y)

        start_offset_x = start_screen[0] - canvas_rect['x']
        start_offset_y = start_screen[1] - canvas_rect['y']
        end_offset_x = end_screen[0] - canvas_rect['x']
        end_offset_y = end_screen[1] - canvas_rect['y']

        actions = ActionChains(self.driver)
        actions.move_to_element_with_offset(canvas, start_offset_x, start_offset_y)
        actions.click_and_hold()

        # Move in steps for smooth drag
        for i in range(1, steps + 1):
            t = i / steps
            x = start_offset_x + (end_offset_x - start_offset_x) * t
            y = start_offset_y + (end_offset_y - start_offset_y) * t
            actions.move_to_element_with_offset(canvas, x, y)

        actions.release()
        actions.perform()
        time.sleep(0.1)  # Allow for render
        return self

    def draw_stroke(self, points: List[Tuple[float, float]]):
        """Draw a stroke through multiple points in document coordinates."""
        if len(points) < 2:
            return self

        canvas = self.get_canvas_element()
        canvas_rect = self.get_canvas_rect()

        actions = ActionChains(self.driver)

        # Move to first point and press
        first_screen = self.doc_to_screen(points[0][0], points[0][1])
        first_offset_x = first_screen[0] - canvas_rect['x']
        first_offset_y = first_screen[1] - canvas_rect['y']
        actions.move_to_element_with_offset(canvas, first_offset_x, first_offset_y)
        actions.click_and_hold()

        # Move through remaining points
        for x, y in points[1:]:
            screen = self.doc_to_screen(x, y)
            offset_x = screen[0] - canvas_rect['x']
            offset_y = screen[1] - canvas_rect['y']
            actions.move_to_element_with_offset(canvas, offset_x, offset_y)

        actions.release()
        actions.perform()
        time.sleep(0.1)
        return self

    # ===== Tool Selection =====

    def select_tool(self, tool_id: str):
        """Select a tool by ID."""
        self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();
            app?.toolManager?.select('{tool_id}');
        """)
        time.sleep(0.1)
        return self

    def get_current_tool(self) -> str:
        """Get the current tool ID."""
        return self.get_vue_data("currentToolId")

    def set_tool_property(self, prop_id: str, value: Any):
        """Set a tool property."""
        value_json = json.dumps(value)
        self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            vm?.updateToolProperty('{prop_id}', {value_json});
        """)
        return self

    # ===== Keyboard Shortcuts =====

    def press_key(self, key: str, ctrl: bool = False, shift: bool = False, alt: bool = False):
        """Press a key combination."""
        canvas = self.get_canvas_element()
        actions = ActionChains(self.driver)

        if ctrl:
            actions.key_down(Keys.CONTROL)
        if shift:
            actions.key_down(Keys.SHIFT)
        if alt:
            actions.key_down(Keys.ALT)

        actions.send_keys_to_element(canvas, key)

        if alt:
            actions.key_up(Keys.ALT)
        if shift:
            actions.key_up(Keys.SHIFT)
        if ctrl:
            actions.key_up(Keys.CONTROL)

        actions.perform()
        time.sleep(0.1)
        return self

    def undo(self):
        """Undo the last action."""
        return self.press_key('z', ctrl=True)

    def redo(self):
        """Redo the last undone action."""
        return self.press_key('y', ctrl=True)

    def copy(self):
        """Copy selection."""
        return self.press_key('c', ctrl=True)

    def cut(self):
        """Cut selection."""
        return self.press_key('x', ctrl=True)

    def paste(self):
        """Paste clipboard."""
        return self.press_key('v', ctrl=True)

    def select_all(self):
        """Select all."""
        return self.press_key('a', ctrl=True)

    def deselect(self):
        """Deselect."""
        return self.press_key('d', ctrl=True)

    def delete_selection(self):
        """Delete selection content."""
        return self.press_key(Keys.DELETE)

    # ===== Layer Operations =====

    def get_layer_count(self) -> int:
        """Get the number of layers."""
        return self.execute_js("""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();
            return app?.layerStack?.layers?.length || 0;
        """) or 0

    def get_active_layer_id(self) -> Optional[str]:
        """Get the active layer ID."""
        return self.get_vue_data("activeLayerId")

    def get_layer_info(self, index: int = None, layer_id: str = None) -> Optional[Dict]:
        """Get layer information by index or ID."""
        if layer_id:
            return self.execute_js(f"""
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
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
            """)
        elif index is not None:
            return self.execute_js(f"""
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
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
            """)
        return None

    def add_layer(self, name: str = None, width: int = None, height: int = None,
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
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();
            const layer = app?.layerStack?.addLayer({options_json});
            vm?.updateLayerList();
            return layer?.id;
        """)

    def select_layer(self, index: int = None, layer_id: str = None):
        """Select a layer by index or ID."""
        if layer_id:
            self.execute_js(f"""
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                const layer = app?.layerStack?.getLayerById('{layer_id}');
                if (layer) app?.layerStack?.setActiveLayer(layer);
            """)
        elif index is not None:
            self.execute_js(f"""
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                app?.layerStack?.setActiveLayerByIndex({index});
            """)
        return self

    def delete_layer(self, layer_id: str = None):
        """Delete a layer by ID (or active layer if no ID given)."""
        if layer_id:
            self.execute_js(f"""
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                app?.layerStack?.removeLayer('{layer_id}');
                vm?.updateLayerList();
            """)
        else:
            self.execute_js("""
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                vm?.deleteLayer();
            """)
        return self

    # ===== Selection Operations =====

    def get_selection(self) -> Optional[Dict]:
        """Get the current selection rectangle."""
        return self.execute_js("""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            return vm?.getSelection();
        """)

    def set_selection(self, x: int, y: int, width: int, height: int):
        """Set a rectangular selection."""
        self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();
            const selTool = app?.toolManager?.tools?.get('selection');
            selTool?.setSelection({{x: {x}, y: {y}, width: {width}, height: {height}}});
        """)
        return self

    def clear_selection(self):
        """Clear the current selection."""
        self.execute_js("""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();
            const selTool = app?.toolManager?.tools?.get('selection');
            selTool?.clearSelection();
        """)
        return self

    # ===== Color Operations =====

    def set_foreground_color(self, color: str):
        """Set the foreground color (hex string like '#FF0000')."""
        self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            vm?.setForegroundColor('{color}');
        """)
        return self

    def set_background_color(self, color: str):
        """Set the background color."""
        self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            vm?.setBackgroundColor('{color}');
        """)
        return self

    def get_foreground_color(self) -> str:
        """Get the current foreground color."""
        return self.get_vue_data("fgColor")

    def get_background_color(self) -> str:
        """Get the current background color."""
        return self.get_vue_data("bgColor")

    # ===== Document Operations =====

    def get_document_size(self) -> Tuple[int, int]:
        """Get document width and height."""
        state = self.get_app_state()
        return (state.get('width', 800), state.get('height', 600))

    def new_document(self, width: int, height: int):
        """Create a new document."""
        self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            vm?.newDocument({width}, {height});
        """)
        self.invalidate_canvas_rect()
        time.sleep(0.2)
        return self

    # ===== Browser Console =====

    def get_browser_logs(self) -> List[Dict]:
        """Get browser console logs."""
        return self.driver.get_log("browser")

    def print_errors(self):
        """Print any JavaScript errors from the console."""
        logs = self.get_browser_logs()
        errors = [log for log in logs if log["level"] in ("SEVERE", "WARNING")]
        if errors:
            print("\n=== Browser Console Errors ===")
            for error in errors:
                print(f"  [{error['level']}] {error['message']}")
            print("==============================\n")
        return errors

    # ===== Waiting =====

    def wait(self, seconds: float):
        """Wait for a number of seconds."""
        time.sleep(seconds)
        return self

    def wait_for_render(self):
        """Wait for the next render cycle."""
        time.sleep(0.1)
        return self

    # ===== Document Export/Import for Parity Testing =====

    def export_document(self) -> Dict[str, Any]:
        """Export the current document as JSON for parity testing."""
        return self.execute_js("""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            return vm?.exportDocument();
        """)

    def import_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import a document from JSON."""
        doc_json = json.dumps(document_data)
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            return vm?.importDocument({doc_json});
        """)

    def get_layer_image_data(self, layer_id: str = None) -> Dict[str, Any]:
        """Get layer image as RGBA bytes (base64 encoded).

        Returns dict with: data (base64), width, height
        """
        layer_arg = f"'{layer_id}'" if layer_id else "null"
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            return vm?.getImageData({layer_arg});
        """)

    def get_composite_image_data(self) -> Dict[str, Any]:
        """Get flattened composite image as RGBA bytes (base64 encoded)."""
        return self.get_layer_image_data(None)

    # ===== Text Layer Creation =====

    def create_text_layer(self, text: str, x: int, y: int,
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
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();

            // Import TextLayer if available
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
        """)

    def create_text_layer_with_runs(self, runs: List[Dict], x: int, y: int,
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
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();

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
        """)

    # ===== Vector Layer Creation =====

    def create_vector_layer(self, shapes: List[Dict], width: int = None,
                            height: int = None) -> str:
        """Create a vector layer with shapes and return its ID."""
        options = {'shapes': shapes}
        if width:
            options['width'] = width
        if height:
            options['height'] = height
        options_json = json.dumps(options)
        return self.execute_js(f"""
            const root = document.querySelector('.editor-root');
            const vm = root.__vue_app__._instance?.proxy;
            const app = vm?.getState();

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
        """)
