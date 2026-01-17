"""Test helpers for Stagforge UI testing."""

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
        helpers = TestHelpers(driver)
        helpers.navigate_to_editor()
        helpers.tools.brush_stroke([(100, 100), (200, 200)])
        checksum = helpers.pixels.compute_checksum()
    """

    def __init__(self, driver, base_url: str = "http://127.0.0.1:8081"):
        self.editor = EditorTestHelper(driver, base_url)
        self.pixels = PixelHelper(self.editor)
        self.tools = ToolHelper(self.editor)
        self.layers = LayerHelper(self.editor)
        self.selection = SelectionHelper(self.editor)

    def navigate_to_editor(self):
        """Navigate to editor and initialize all helpers."""
        self.editor.navigate_to_editor()
        return self

    def wait_for_render(self):
        """Wait for render cycle."""
        self.editor.wait_for_render()
        return self

    # Delegate common methods to editor
    def new_document(self, width: int, height: int):
        self.editor.new_document(width, height)
        return self

    def undo(self):
        self.editor.undo()
        return self

    def redo(self):
        self.editor.redo()
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
