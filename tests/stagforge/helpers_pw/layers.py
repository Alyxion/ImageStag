"""LayerHelper - Layer operations for Stagforge testing with Playwright."""

import asyncio
from typing import Optional, Dict, List, Tuple

from .editor import EditorTestHelper


class LayerHelper:
    """
    Helper class for layer management in tests.

    Provides methods for:
    - Creating layers with specific properties
    - Layer manipulation (move, resize, duplicate)
    - Layer state verification
    - Offset layer testing utilities
    """

    def __init__(self, editor: EditorTestHelper):
        self.editor = editor

    # ===== Layer Creation =====

    async def create_layer(self, name: str = None, width: int = None, height: int = None,
                           offset_x: int = 0, offset_y: int = 0,
                           select: bool = True) -> str:
        """
        Create a new layer with specified properties.

        Args:
            name: Layer name
            width: Layer width (defaults to document width)
            height: Layer height (defaults to document height)
            offset_x: X offset in document
            offset_y: Y offset in document
            select: Whether to select the new layer

        Returns:
            ID of the new layer
        """
        layer_id = await self.editor.add_layer(name=name, width=width, height=height,
                                               offset_x=offset_x, offset_y=offset_y)
        if select and layer_id:
            await self.editor.select_layer(layer_id=layer_id)
        return layer_id

    async def create_offset_layer(self, offset_x: int, offset_y: int,
                                  width: int = 100, height: int = 100,
                                  name: str = None) -> str:
        """
        Create a layer at a specific offset (for testing coordinate transforms).

        Args:
            offset_x, offset_y: Position in document
            width, height: Layer size
            name: Layer name (auto-generated if None)

        Returns:
            ID of the new layer
        """
        if name is None:
            name = f"Layer@({offset_x},{offset_y})"
        return await self.create_layer(name=name, width=width, height=height,
                                       offset_x=offset_x, offset_y=offset_y)

    async def create_filled_layer(self, color: str, width: int = None, height: int = None,
                                  offset_x: int = 0, offset_y: int = 0,
                                  name: str = None) -> str:
        """
        Create a layer filled with a solid color.

        Args:
            color: Fill color (hex string like '#FF0000')
            width, height: Layer size
            offset_x, offset_y: Position
            name: Layer name

        Returns:
            ID of the new layer
        """
        layer_id = await self.create_layer(name=name, width=width, height=height,
                                           offset_x=offset_x, offset_y=offset_y)

        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.ctx.fillStyle = '{color}';
                        layer.ctx.fillRect(0, 0, layer.width, layer.height);
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)

        return layer_id

    # ===== Layer Selection =====

    async def select_by_index(self, index: int):
        """Select a layer by its index in the stack."""
        await self.editor.select_layer(index=index)
        return self

    async def select_by_id(self, layer_id: str):
        """Select a layer by ID."""
        await self.editor.select_layer(layer_id=layer_id)
        return self

    async def select_topmost(self):
        """Select the topmost layer."""
        count = await self.editor.get_layer_count()
        if count > 0:
            await self.select_by_index(count - 1)
        return self

    async def select_bottommost(self):
        """Select the bottommost (background) layer."""
        await self.select_by_index(0)
        return self

    # ===== Layer Properties =====

    async def get_layer_offset(self, layer_id: str = None) -> Tuple[int, int]:
        """
        Get the offset of a layer.

        Args:
            layer_id: Layer ID, or None for active layer

        Returns:
            (offsetX, offsetY) tuple
        """
        info = await self.editor.get_layer_info(layer_id=layer_id)
        if info:
            return (info.get('offsetX', 0), info.get('offsetY', 0))
        return (0, 0)

    async def get_layer_size(self, layer_id: str = None) -> Tuple[int, int]:
        """
        Get the size of a layer.

        Args:
            layer_id: Layer ID, or None for active layer

        Returns:
            (width, height) tuple
        """
        info = await self.editor.get_layer_info(layer_id=layer_id)
        if info:
            return (info.get('width', 0), info.get('height', 0))
        return (0, 0)

    async def get_layer_bounds(self, layer_id: str = None) -> Tuple[int, int, int, int]:
        """
        Get the bounds of a layer in document coordinates.

        Returns:
            (x, y, width, height) tuple
        """
        info = await self.editor.get_layer_info(layer_id=layer_id)
        if info:
            return (
                info.get('offsetX', 0),
                info.get('offsetY', 0),
                info.get('width', 0),
                info.get('height', 0)
            )
        return (0, 0, 0, 0)

    async def set_layer_offset(self, offset_x: int, offset_y: int, layer_id: str = None):
        """
        Set the offset of a layer.

        Args:
            offset_x, offset_y: New offset
            layer_id: Layer ID, or None for active layer
        """
        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.offsetX = {offset_x};
                        layer.offsetY = {offset_y};
                        app?.renderer?.requestRender();
                        vm?.updateLayerList();
                    }}
                }})()
            """)
        else:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getActiveLayer();
                    if (layer) {{
                        layer.offsetX = {offset_x};
                        layer.offsetY = {offset_y};
                        app?.renderer?.requestRender();
                        vm?.updateLayerList();
                    }}
                }})()
            """)
        return self

    async def set_layer_opacity(self, opacity: float, layer_id: str = None):
        """
        Set layer opacity.

        Args:
            opacity: Opacity value 0.0-1.0
            layer_id: Layer ID, or None for active layer
        """
        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.opacity = {opacity};
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        else:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getActiveLayer();
                    if (layer) {{
                        layer.opacity = {opacity};
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        return self

    async def set_layer_visibility(self, visible: bool, layer_id: str = None):
        """Set layer visibility."""
        visible_str = 'true' if visible else 'false'
        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.visible = {visible_str};
                        app?.renderer?.requestRender();
                        vm?.updateLayerList();
                    }}
                }})()
            """)
        else:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getActiveLayer();
                    if (layer) {{
                        layer.visible = {visible_str};
                        app?.renderer?.requestRender();
                        vm?.updateLayerList();
                    }}
                }})()
            """)
        return self

    # ===== Layer Operations =====

    async def duplicate_layer(self, layer_id: str = None) -> Optional[str]:
        """
        Duplicate a layer.

        Args:
            layer_id: Layer to duplicate, or None for active layer

        Returns:
            ID of the new duplicate layer
        """
        if layer_id:
            await self.select_by_id(layer_id)

        return await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                vm?.duplicateLayer();
                // Get the new active layer (the duplicate)
                return vm?.activeLayerId;
            })()
        """)

    async def merge_down(self, layer_id: str = None):
        """
        Merge layer with the one below it.

        Args:
            layer_id: Layer to merge, or None for active layer
        """
        if layer_id:
            await self.select_by_id(layer_id)

        await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                vm?.mergeDown();
            })()
        """)
        return self

    async def flatten_all(self):
        """Flatten all layers into one."""
        await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                vm?.flattenAll();
            })()
        """)
        return self

    async def delete_layer(self, layer_id: str = None):
        """
        Delete a layer.

        Args:
            layer_id: Layer to delete, or None for active layer
        """
        await self.editor.delete_layer(layer_id)
        return self

    async def clear_layer(self, layer_id: str = None):
        """
        Clear all content from a layer.

        Args:
            layer_id: Layer to clear, or None for active layer
        """
        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.ctx.clearRect(0, 0, layer.width, layer.height);
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        else:
            await self.editor.execute_js("""
                (() => {
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getActiveLayer();
                    if (layer) {
                        layer.ctx.clearRect(0, 0, layer.width, layer.height);
                        app?.renderer?.requestRender();
                    }
                })()
            """)
        return self

    # ===== Layer Reordering =====

    async def move_layer_up(self, layer_id: str = None):
        """Move a layer up in the stack."""
        if layer_id:
            await self.select_by_id(layer_id)

        await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                const layer = app?.layerStack?.getActiveLayer();
                if (layer) {
                    app?.layerStack?.moveLayerUp(layer);
                    vm?.updateLayerList();
                }
            })()
        """)
        return self

    async def move_layer_down(self, layer_id: str = None):
        """Move a layer down in the stack."""
        if layer_id:
            await self.select_by_id(layer_id)

        await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                const layer = app?.layerStack?.getActiveLayer();
                if (layer) {
                    app?.layerStack?.moveLayerDown(layer);
                    vm?.updateLayerList();
                }
            })()
        """)
        return self

    async def move_layer_to_top(self, layer_id: str = None):
        """Move a layer to the top of the stack."""
        if layer_id:
            await self.select_by_id(layer_id)

        await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                const layer = app?.layerStack?.getActiveLayer();
                if (layer) {
                    app?.layerStack?.moveLayerToTop(layer);
                    vm?.updateLayerList();
                }
            })()
        """)
        return self

    async def move_layer_to_bottom(self, layer_id: str = None):
        """Move a layer to the bottom of the stack."""
        if layer_id:
            await self.select_by_id(layer_id)

        await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                const layer = app?.layerStack?.getActiveLayer();
                if (layer) {
                    app?.layerStack?.moveLayerToBottom(layer);
                    vm?.updateLayerList();
                }
            })()
        """)
        return self

    # ===== Layer State Verification =====

    async def get_all_layers(self) -> List[Dict]:
        """Get information about all layers."""
        result = await self.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root.__vue_app__._instance?.proxy;
                const app = vm?.getState();
                if (!app?.layerStack?.layers) return [];
                return app.layerStack.layers.map(layer => ({
                    id: layer.id,
                    name: layer.name,
                    width: layer.width,
                    height: layer.height,
                    offsetX: layer.offsetX,
                    offsetY: layer.offsetY,
                    opacity: layer.opacity,
                    visible: layer.visible,
                    locked: layer.locked
                }));
            })()
        """)
        return result or []

    async def layer_exists(self, layer_id: str) -> bool:
        """Check if a layer exists."""
        info = await self.editor.get_layer_info(layer_id=layer_id)
        return info is not None

    async def layer_is_active(self, layer_id: str) -> bool:
        """Check if a layer is the active layer."""
        active_id = await self.editor.get_active_layer_id()
        return active_id == layer_id

    async def assert_layer_count(self, expected_count: int) -> bool:
        """Assert that the layer count matches expected value."""
        actual = await self.editor.get_layer_count()
        assert actual == expected_count, f"Expected {expected_count} layers, got {actual}"
        return True

    async def assert_layer_bounds(self, layer_id: str, expected_bounds: Tuple[int, int, int, int],
                                  tolerance: int = 0) -> bool:
        """Assert that a layer's bounds match expected values."""
        actual = await self.get_layer_bounds(layer_id)
        for i, (a, e) in enumerate(zip(actual, expected_bounds)):
            assert abs(a - e) <= tolerance, \
                f"Layer bounds mismatch at index {i}: expected {e}, got {a}"
        return True

    # ===== Content Operations =====

    async def fill_layer_with_color(self, color: str, layer_id: str = None):
        """
        Fill an entire layer with a color.

        Args:
            color: Hex color string
            layer_id: Layer to fill, or None for active layer
        """
        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.ctx.fillStyle = '{color}';
                        layer.ctx.fillRect(0, 0, layer.width, layer.height);
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        else:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getActiveLayer();
                    if (layer) {{
                        layer.ctx.fillStyle = '{color}';
                        layer.ctx.fillRect(0, 0, layer.width, layer.height);
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        return self

    async def draw_rect_on_layer(self, x: int, y: int, width: int, height: int,
                                 color: str, layer_id: str = None):
        """
        Draw a rectangle directly on a layer's canvas (layer coordinates).

        Args:
            x, y: Position in LAYER canvas coordinates (not document)
            width, height: Size of rectangle
            color: Fill color
            layer_id: Layer to draw on, or None for active layer
        """
        if layer_id:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (layer) {{
                        layer.ctx.fillStyle = '{color}';
                        layer.ctx.fillRect({x}, {y}, {width}, {height});
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        else:
            await self.editor.execute_js(f"""
                (() => {{
                    const root = document.querySelector('.editor-root');
                    const vm = root.__vue_app__._instance?.proxy;
                    const app = vm?.getState();
                    const layer = app?.layerStack?.getActiveLayer();
                    if (layer) {{
                        layer.ctx.fillStyle = '{color}';
                        layer.ctx.fillRect({x}, {y}, {width}, {height});
                        app?.renderer?.requestRender();
                    }}
                }})()
            """)
        return self
