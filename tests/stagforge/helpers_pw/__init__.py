"""Playwright-based test helpers for Stagforge UI testing."""

from .editor import EditorTestHelper
from .pixels import PixelHelper
from .tools import ToolHelper
from .layers import LayerHelper
from .selection import SelectionHelper
from .assertions import (
    approx_line_pixels,
    approx_rect_pixels,
    approx_rect_outline_pixels,
    approx_circle_pixels,
    approx_ellipse_pixels,
    approx_circle_outline_pixels,
    diagonal_length,
    assert_pixel_count_in_range,
    assert_pixel_count_exact,
    assert_pixel_ratio,
)


class TestHelpers:
    """
    Convenience class that combines all helper classes.

    Usage:
        helpers = TestHelpers(page)
        await helpers.navigate_to_editor()
        await helpers.tools.brush_stroke([(100, 100), (200, 200)])
        checksum = await helpers.pixels.compute_checksum()
    """

    def __init__(self, page, base_url: str = "http://127.0.0.1:8080"):
        self.editor = EditorTestHelper(page, base_url)
        self.pixels = PixelHelper(self.editor)
        self.tools = ToolHelper(self.editor)
        self.layers = LayerHelper(self.editor)
        self.selection = SelectionHelper(self.editor)

    async def navigate_to_editor(self):
        """Navigate to editor and initialize all helpers."""
        await self.editor.navigate_to_editor()
        return self

    async def wait_for_render(self):
        """Wait for render cycle."""
        await self.editor.wait_for_render()
        return self

    # Delegate common methods to editor
    async def new_document(self, width: int, height: int):
        await self.editor.new_document(width, height)
        return self

    async def undo(self):
        await self.editor.undo()
        return self

    async def redo(self):
        await self.editor.redo()
        return self


__all__ = [
    'EditorTestHelper',
    'PixelHelper',
    'ToolHelper',
    'LayerHelper',
    'SelectionHelper',
    'TestHelpers',
    # Assertion helpers
    'approx_line_pixels',
    'approx_rect_pixels',
    'approx_rect_outline_pixels',
    'approx_circle_pixels',
    'approx_ellipse_pixels',
    'approx_circle_outline_pixels',
    'diagonal_length',
    'assert_pixel_count_in_range',
    'assert_pixel_count_exact',
    'assert_pixel_ratio',
]
