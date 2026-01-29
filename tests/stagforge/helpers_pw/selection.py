"""SelectionHelper - Selection operations for Stagforge testing with Playwright."""

import asyncio
from typing import Optional, Dict, Tuple

from .editor import EditorTestHelper


class SelectionHelper:
    """
    Helper class for selection operations in tests.

    Provides methods for:
    - Creating and manipulating selections
    - Selection verification
    - Clipboard operations with selections
    """

    def __init__(self, editor: EditorTestHelper):
        self.editor = editor

    # ===== Selection Creation =====

    async def select_rect(self, x: float, y: float, width: float, height: float):
        """
        Create a rectangular selection by mouse drag.

        Args:
            x, y: Top-left corner in document coordinates
            width, height: Size of selection
        """
        await self.editor.select_tool('selection')
        await self.editor.drag_at_doc(x, y, x + width, y + height)
        await asyncio.sleep(0.1)
        return self

    async def select_rect_api(self, x: float, y: float, width: float, height: float):
        """Create a rectangular selection via API (faster, more precise)."""
        await self.editor.set_selection(int(x), int(y), int(width), int(height))
        return self

    async def select_all(self):
        """Select the entire document."""
        await self.editor.select_all()
        return self

    async def clear_selection(self):
        """Clear the current selection."""
        await self.editor.clear_selection()
        return self

    async def deselect(self):
        """Deselect (same as clear_selection, uses keyboard shortcut)."""
        await self.editor.deselect()
        return self

    # ===== Selection via Magic Wand =====

    async def select_by_color(self, x: float, y: float, tolerance: int = 32,
                              contiguous: bool = True):
        """
        Select by color similarity using magic wand.

        Args:
            x, y: Point to start selection (document coordinates)
            tolerance: Color tolerance 0-255
            contiguous: Only select connected pixels if True
        """
        await self.editor.select_tool('magicwand')
        await self.editor.set_tool_property('tolerance', tolerance)
        await self.editor.set_tool_property('contiguous', contiguous)
        await self.editor.click_at_doc(x, y)
        await asyncio.sleep(0.1)
        return self

    # ===== Selection via Lasso =====

    async def lasso_select(self, points: list):
        """
        Create a freeform selection using the lasso tool.

        Args:
            points: List of (x, y) coordinates forming the selection boundary
        """
        if len(points) < 3:
            return self

        await self.editor.select_tool('lasso')
        await self.editor.draw_stroke(points + [points[0]])  # Close the loop
        await asyncio.sleep(0.1)
        return self

    # ===== Selection State =====

    async def get_selection(self) -> Optional[Dict]:
        """Get the current selection rectangle."""
        return await self.editor.get_selection()

    async def has_selection(self) -> bool:
        """Check if there is an active selection."""
        sel = await self.get_selection()
        return sel is not None and sel.get('width', 0) > 0 and sel.get('height', 0) > 0

    async def get_selection_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get selection bounds as (x, y, width, height) tuple."""
        sel = await self.get_selection()
        if not sel:
            return None
        return (sel.get('x', 0), sel.get('y', 0),
                sel.get('width', 0), sel.get('height', 0))

    async def get_selection_size(self) -> Tuple[int, int]:
        """Get selection width and height."""
        sel = await self.get_selection()
        if not sel:
            return (0, 0)
        return (sel.get('width', 0), sel.get('height', 0))

    async def get_selection_position(self) -> Tuple[int, int]:
        """Get selection top-left position."""
        sel = await self.get_selection()
        if not sel:
            return (0, 0)
        return (sel.get('x', 0), sel.get('y', 0))

    # ===== Selection Operations =====

    async def delete_selection_content(self):
        """Delete the content within the selection (make transparent)."""
        await self.editor.delete_selection()
        return self

    async def invert_selection(self):
        """Invert the selection (select everything not currently selected)."""
        await self.editor.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                const app = vm?.getState?.() || vm;
                const selTool = app?.toolManager?.tools?.get('selection');
                selTool?.invertSelection?.();
            })()
        """)
        return self

    async def expand_selection(self, pixels: int):
        """Expand the selection by a number of pixels."""
        sel = await self.get_selection()
        if sel:
            new_x = max(0, sel['x'] - pixels)
            new_y = max(0, sel['y'] - pixels)
            new_w = sel['width'] + 2 * pixels
            new_h = sel['height'] + 2 * pixels
            await self.select_rect_api(new_x, new_y, new_w, new_h)
        return self

    async def contract_selection(self, pixels: int):
        """Contract the selection by a number of pixels."""
        sel = await self.get_selection()
        if sel:
            new_x = sel['x'] + pixels
            new_y = sel['y'] + pixels
            new_w = max(1, sel['width'] - 2 * pixels)
            new_h = max(1, sel['height'] - 2 * pixels)
            await self.select_rect_api(new_x, new_y, new_w, new_h)
        return self

    # ===== Clipboard with Selection =====

    async def copy(self):
        """Copy the selection to clipboard."""
        await self.editor.copy()
        return self

    async def cut(self):
        """Cut the selection to clipboard."""
        await self.editor.cut()
        return self

    async def paste(self):
        """Paste from clipboard (creates new layer)."""
        await self.editor.paste()
        return self

    async def paste_in_place(self):
        """Paste from clipboard at original position."""
        await self.editor.press_key('v', ctrl=True, shift=True)
        return self

    async def copy_merged(self):
        """Copy merged (all visible layers within selection)."""
        await self.editor.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                const app = vm?.getState?.() || vm;
                const sel = vm?.getSelection?.();
                app?.clipboard?.copyMerged(sel);
            })()
        """)
        return self

    async def has_clipboard_content(self) -> bool:
        """Check if clipboard has content."""
        result = await self.editor.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                const app = vm?.getState?.() || vm;
                return app?.clipboard?.hasContent() || false;
            })()
        """)
        return result or False

    async def get_clipboard_info(self) -> Optional[Dict]:
        """Get info about clipboard content."""
        return await self.editor.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                const app = vm?.getState?.() || vm;
                return app?.clipboard?.getInfo();
            })()
        """)

    # ===== Selection Verification =====

    async def assert_selection_exists(self) -> bool:
        """Assert that a selection exists."""
        has_sel = await self.has_selection()
        assert has_sel, "Expected a selection, but none exists"
        return True

    async def assert_no_selection(self) -> bool:
        """Assert that no selection exists."""
        has_sel = await self.has_selection()
        assert not has_sel, "Expected no selection, but one exists"
        return True

    async def assert_selection_bounds(self, expected: Tuple[int, int, int, int],
                                      tolerance: int = 0) -> bool:
        """
        Assert that selection bounds match expected values.

        Args:
            expected: (x, y, width, height) tuple
            tolerance: Allowed difference in pixels
        """
        actual = await self.get_selection_bounds()
        assert actual is not None, "No selection exists"

        for i, (a, e) in enumerate(zip(actual, expected)):
            assert abs(a - e) <= tolerance, \
                f"Selection bounds mismatch at index {i}: expected {e}, got {a}"
        return True

    async def assert_selection_size(self, expected_width: int, expected_height: int,
                                    tolerance: int = 0) -> bool:
        """Assert that selection size matches expected values."""
        w, h = await self.get_selection_size()
        assert abs(w - expected_width) <= tolerance, \
            f"Selection width: expected {expected_width}, got {w}"
        assert abs(h - expected_height) <= tolerance, \
            f"Selection height: expected {expected_height}, got {h}"
        return True

    async def assert_selection_position(self, expected_x: int, expected_y: int,
                                        tolerance: int = 0) -> bool:
        """Assert that selection position matches expected values."""
        x, y = await self.get_selection_position()
        assert abs(x - expected_x) <= tolerance, \
            f"Selection x: expected {expected_x}, got {x}"
        assert abs(y - expected_y) <= tolerance, \
            f"Selection y: expected {expected_y}, got {y}"
        return True

    # ===== Convenience Methods for Testing Offset Layers =====

    async def select_layer_content(self, layer_id: str = None):
        """
        Select the entire content area of a layer (its bounds in document coords).

        Args:
            layer_id: Layer to select, or None for active layer
        """
        info = await self.editor.get_layer_info(layer_id=layer_id)
        if info:
            x = info.get('offsetX', 0)
            y = info.get('offsetY', 0)
            w = info.get('width', 0)
            h = info.get('height', 0)
            await self.select_rect_api(x, y, w, h)
        return self

    async def select_partial_layer(self, layer_id: str, margin: int = 10):
        """
        Select a portion of a layer, leaving a margin.

        Args:
            layer_id: Layer to select
            margin: Pixels to leave around selection
        """
        info = await self.editor.get_layer_info(layer_id=layer_id)
        if info:
            x = info.get('offsetX', 0) + margin
            y = info.get('offsetY', 0) + margin
            w = max(1, info.get('width', 0) - 2 * margin)
            h = max(1, info.get('height', 0) - 2 * margin)
            await self.select_rect_api(x, y, w, h)
        return self
