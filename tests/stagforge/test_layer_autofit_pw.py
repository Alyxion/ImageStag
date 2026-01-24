"""Tests for pixel layer auto-fit behavior.

Key Requirements:
1. New empty layers should have size 0x0 (not document size)
2. After any pixel operation, layer bounds auto-fit to content (pixels with alpha > 0)
3. Layer offset adjusts to the top-left of content bounding box
4. Cutting/deleting all content should result in 0x0 layer

This behavior mirrors VectorLayer auto-fit but for raster/pixel layers.
"""

import pytest
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


class TestNewLayerSize:
    """Tests for initial layer size behavior."""

    async def test_new_empty_layer_has_zero_size(self, helpers: TestHelpers):
        """New empty layer should have 0x0 size, not document size."""
        await helpers.new_document(800, 600)

        # Background layer should span full document
        bg_info = await helpers.editor.get_layer_info(index=0)
        assert bg_info['width'] == 800, f"Background width should be 800, got {bg_info['width']}"
        assert bg_info['height'] == 600, f"Background height should be 600, got {bg_info['height']}"

        # Create new empty layer
        layer_id = await helpers.layers.create_layer(name="Empty Layer")
        layer_info = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Empty layer should have 0x0 size
        assert layer_info['width'] == 0, \
            f"Empty layer width should be 0, got {layer_info['width']}"
        assert layer_info['height'] == 0, \
            f"Empty layer height should be 0, got {layer_info['height']}"

    async def test_new_layer_has_zero_offset(self, helpers: TestHelpers):
        """New empty layer should have 0,0 offset."""
        await helpers.new_document(800, 600)

        layer_id = await helpers.layers.create_layer()
        layer_info = await helpers.editor.get_layer_info(layer_id=layer_id)

        assert layer_info['offsetX'] == 0, f"Offset X should be 0, got {layer_info['offsetX']}"
        assert layer_info['offsetY'] == 0, f"Offset Y should be 0, got {layer_info['offsetY']}"


class TestBrushStrokeAutoFit:
    """Tests for layer auto-fit after brush strokes."""

    async def test_brush_dot_creates_correctly_sized_layer(self, helpers: TestHelpers):
        """Single brush dot should create layer sized to fit the dot."""
        await helpers.new_document(800, 600)

        layer_id = await helpers.layers.create_layer(name="Test Layer")

        # Verify initially 0x0
        info_before = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info_before['width'] == 0
        assert info_before['height'] == 0

        # Draw a brush dot at (80, 80) with radius 30 (size=60)
        brush_size = 60
        await helpers.tools.brush_dot(80, 80, color='#FF0000', size=brush_size)

        # Get layer info after drawing
        info_after = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should be approximately brush_size x brush_size
        # Allow some tolerance for antialiasing
        expected_size = brush_size
        tolerance = 10

        assert abs(info_after['width'] - expected_size) <= tolerance, \
            f"Width should be ~{expected_size}, got {info_after['width']}"
        assert abs(info_after['height'] - expected_size) <= tolerance, \
            f"Height should be ~{expected_size}, got {info_after['height']}"

        # Offset should be approximately (80 - 30, 80 - 30) = (50, 50)
        expected_offset = 80 - brush_size // 2
        assert abs(info_after['offsetX'] - expected_offset) <= tolerance, \
            f"Offset X should be ~{expected_offset}, got {info_after['offsetX']}"
        assert abs(info_after['offsetY'] - expected_offset) <= tolerance, \
            f"Offset Y should be ~{expected_offset}, got {info_after['offsetY']}"

    async def test_brush_stroke_creates_correctly_sized_layer(self, helpers: TestHelpers):
        """Brush stroke should create layer sized to fit the stroke path."""
        await helpers.new_document(800, 600)

        layer_id = await helpers.layers.create_layer(name="Stroke Layer")

        # Draw horizontal stroke from (100, 200) to (300, 200) with size 20
        brush_size = 20
        await helpers.tools.brush_stroke(
            [(100, 200), (300, 200)],
            color='#00FF00',
            size=brush_size
        )

        info = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Width should be ~200 (stroke length) + brush_size for ends
        # Height should be ~brush_size
        expected_width = 200 + brush_size
        expected_height = brush_size
        tolerance = 15

        assert abs(info['width'] - expected_width) <= tolerance, \
            f"Width should be ~{expected_width}, got {info['width']}"
        assert abs(info['height'] - expected_height) <= tolerance, \
            f"Height should be ~{expected_height}, got {info['height']}"

        # Offset X should be ~100 - brush_size/2
        # Offset Y should be ~200 - brush_size/2
        expected_offset_x = 100 - brush_size // 2
        expected_offset_y = 200 - brush_size // 2

        assert abs(info['offsetX'] - expected_offset_x) <= tolerance, \
            f"Offset X should be ~{expected_offset_x}, got {info['offsetX']}"
        assert abs(info['offsetY'] - expected_offset_y) <= tolerance, \
            f"Offset Y should be ~{expected_offset_y}, got {info['offsetY']}"

    async def test_multiple_strokes_expand_layer(self, helpers: TestHelpers):
        """Multiple strokes should expand layer to fit all content."""
        await helpers.new_document(800, 600)

        layer_id = await helpers.layers.create_layer(name="Multi Stroke")

        brush_size = 20

        # First stroke at top-left area
        await helpers.tools.brush_dot(100, 100, color='#FF0000', size=brush_size)

        info1 = await helpers.editor.get_layer_info(layer_id=layer_id)
        initial_width = info1['width']
        initial_height = info1['height']

        # Second stroke at bottom-right area
        await helpers.tools.brush_dot(400, 300, color='#FF0000', size=brush_size)

        info2 = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should now span from ~(90,90) to ~(410,310)
        # Width should be ~320, Height should be ~220
        assert info2['width'] > initial_width, \
            f"Width should increase from {initial_width} to cover both strokes"
        assert info2['height'] > initial_height, \
            f"Height should increase from {initial_height} to cover both strokes"

        expected_width = (400 + brush_size // 2) - (100 - brush_size // 2)
        expected_height = (300 + brush_size // 2) - (100 - brush_size // 2)
        tolerance = 20

        assert abs(info2['width'] - expected_width) <= tolerance, \
            f"Width should be ~{expected_width}, got {info2['width']}"
        assert abs(info2['height'] - expected_height) <= tolerance, \
            f"Height should be ~{expected_height}, got {info2['height']}"


class TestEraserAutoFit:
    """Tests for layer auto-fit after eraser operations."""

    async def test_eraser_shrinks_layer_bounds(self, helpers: TestHelpers):
        """Erasing content should shrink layer to remaining content."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Erase Test")

        # Draw two dots
        await helpers.tools.brush_dot(100, 100, color='#FF0000', size=40)
        await helpers.tools.brush_dot(300, 100, color='#FF0000', size=40)

        info_before = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Erase the right dot completely
        await helpers.tools.eraser_stroke([(300, 100)], size=60)

        info_after = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should shrink to just contain the left dot
        assert info_after['width'] < info_before['width'], \
            f"Width should shrink after erasing. Before: {info_before['width']}, after: {info_after['width']}"

    async def test_erasing_all_content_results_in_zero_size(self, helpers: TestHelpers):
        """Erasing all content should result in 0x0 layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Erase All")

        # Draw a single dot
        await helpers.tools.brush_dot(200, 200, color='#FF0000', size=40)

        info_before = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info_before['width'] > 0, "Should have content before erasing"

        # Erase the dot completely
        await helpers.tools.eraser_stroke([(200, 200)], size=80)

        info_after = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should be 0x0
        assert info_after['width'] == 0, \
            f"Width should be 0 after erasing all content, got {info_after['width']}"
        assert info_after['height'] == 0, \
            f"Height should be 0 after erasing all content, got {info_after['height']}"


class TestCutAutoFit:
    """Tests for layer auto-fit after cut/delete operations."""

    async def test_cut_selection_shrinks_layer(self, helpers: TestHelpers):
        """Cutting a selection should shrink layer to remaining content."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Cut Test")

        # Draw two separate areas
        await helpers.tools.brush_dot(100, 100, color='#0000FF', size=50)
        await helpers.tools.brush_dot(300, 100, color='#0000FF', size=50)

        info_before = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Select and cut the right area
        await helpers.selection.select_rect_api(270, 70, 60, 60)
        await helpers.selection.cut()

        # Select the layer again (cut creates new layer)
        await helpers.layers.select_by_id(layer_id)
        info_after = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should shrink to just the left dot
        assert info_after['width'] < info_before['width'], \
            "Width should shrink after cutting right portion"

    async def test_cut_all_content_results_in_zero_size(self, helpers: TestHelpers):
        """Cutting all content should result in 0x0 layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Cut All")

        # Draw content
        await helpers.tools.brush_dot(200, 200, color='#FF00FF', size=60)

        # Select all content and cut
        await helpers.selection.select_rect_api(160, 160, 80, 80)
        await helpers.selection.cut()

        # Select the original layer
        await helpers.layers.select_by_id(layer_id)
        info_after = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should be 0x0
        assert info_after['width'] == 0, \
            f"Width should be 0 after cutting all content, got {info_after['width']}"
        assert info_after['height'] == 0, \
            f"Height should be 0 after cutting all content, got {info_after['height']}"

    async def test_delete_selection_shrinks_layer(self, helpers: TestHelpers):
        """Deleting selection content should shrink layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Delete Test")

        # Draw content using brush strokes to create pixel data (not vector shapes)
        # Create a filled area with multiple brush strokes
        # Strokes from x=60 to x=340 with size 25 (radius 12.5)
        # Content extends from x=47.5 to x=352.5 approximately
        for y in range(60, 240, 20):
            await helpers.tools.brush_stroke(
                [(60, y), (340, y)],
                color='#FFFF00',
                size=25
            )

        info_before = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info_before['width'] > 0, f"Layer should have content, got width {info_before['width']}"

        # Delete right portion - selection must extend beyond the brush content
        # to fully remove the right half. Brush extends to x~353, so select x=200-400
        await helpers.selection.select_rect_api(200, 40, 200, 220)
        await helpers.selection.delete_selection_content()

        # Wait for async operations
        await helpers.editor.wait(0.2)

        info_after = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Width should roughly halve (content was ~47 to ~353, now ~47 to ~200)
        # Original width ~306, expected after ~153
        assert info_after['width'] < info_before['width'] * 0.7, \
            f"Width should significantly shrink. Before: {info_before['width']}, after: {info_after['width']}"


class TestUndoRedoPreservesAutoFit:
    """Tests for undo/redo with auto-fit layers."""

    async def test_undo_restores_previous_layer_bounds(self, helpers: TestHelpers):
        """Undo should restore previous layer size and offset."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Undo Test")

        # Draw first dot
        await helpers.tools.brush_dot(100, 100, color='#FF0000', size=40)
        info_after_first = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Draw second dot (expands layer)
        await helpers.tools.brush_dot(300, 300, color='#FF0000', size=40)
        info_after_second = await helpers.editor.get_layer_info(layer_id=layer_id)

        assert info_after_second['width'] > info_after_first['width'], \
            "Layer should expand after second dot"

        # Undo second dot
        await helpers.undo()

        info_after_undo = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Should restore to first dot bounds
        assert abs(info_after_undo['width'] - info_after_first['width']) <= 2, \
            f"Undo should restore width. Expected ~{info_after_first['width']}, got {info_after_undo['width']}"
        assert abs(info_after_undo['height'] - info_after_first['height']) <= 2, \
            f"Undo should restore height. Expected ~{info_after_first['height']}, got {info_after_undo['height']}"

    async def test_redo_restores_expanded_bounds(self, helpers: TestHelpers):
        """Redo should restore expanded layer bounds."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Redo Test")

        # Draw and expand
        await helpers.tools.brush_dot(100, 100, color='#00FF00', size=40)
        await helpers.tools.brush_dot(300, 300, color='#00FF00', size=40)
        info_expanded = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Undo
        await helpers.undo()

        # Redo
        await helpers.redo()

        info_after_redo = await helpers.editor.get_layer_info(layer_id=layer_id)

        assert abs(info_after_redo['width'] - info_expanded['width']) <= 2, \
            f"Redo should restore width. Expected ~{info_expanded['width']}, got {info_after_redo['width']}"


class TestAutoFitEdgeCases:
    """Edge cases for auto-fit behavior."""

    async def test_content_at_document_edge(self, helpers: TestHelpers):
        """Content at document edge should work correctly."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Edge Test")

        # Draw at edge - with size 40 (radius 20), center at (10, 10)
        # The brush extends from (-10, -10) to (30, 30)
        brush_size = 40
        brush_radius = brush_size // 2
        center_x, center_y = 10, 10
        await helpers.tools.brush_dot(center_x, center_y, color='#FF0000', size=brush_size)

        info = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should contain the brush content (may extend outside document)
        # Layer offset should be approximately center - radius
        expected_offset = center_x - brush_radius
        tolerance = 5

        assert abs(info['offsetX'] - expected_offset) <= tolerance, \
            f"Offset X should be ~{expected_offset}, got {info['offsetX']}"
        assert abs(info['offsetY'] - expected_offset) <= tolerance, \
            f"Offset Y should be ~{expected_offset}, got {info['offsetY']}"

        # Layer should have content
        assert info['width'] > 0, f"Width should be > 0, got {info['width']}"
        assert info['height'] > 0, f"Height should be > 0, got {info['height']}"

    async def test_very_small_content(self, helpers: TestHelpers):
        """Very small content (1-2 pixels) should still auto-fit."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Small Test")

        # Draw with size 1 (single pixel)
        await helpers.tools.brush_dot(200, 200, color='#FF0000', size=1)

        info = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Should have very small dimensions
        assert info['width'] >= 1, "Width should be at least 1"
        assert info['height'] >= 1, "Height should be at least 1"
        assert info['width'] <= 10, f"Width should be small, got {info['width']}"
        assert info['height'] <= 10, f"Height should be small, got {info['height']}"

    async def test_diagonal_stroke_autofit(self, helpers: TestHelpers):
        """Diagonal stroke should create appropriately sized layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(name="Diagonal")

        brush_size = 20

        # Draw diagonal from (50, 50) to (350, 350)
        await helpers.tools.brush_stroke(
            [(50, 50), (350, 350)],
            color='#0000FF',
            size=brush_size
        )

        info = await helpers.editor.get_layer_info(layer_id=layer_id)

        # Layer should span diagonally
        expected_span = 300 + brush_size
        tolerance = 20

        assert abs(info['width'] - expected_span) <= tolerance, \
            f"Width should be ~{expected_span}, got {info['width']}"
        assert abs(info['height'] - expected_span) <= tolerance, \
            f"Height should be ~{expected_span}, got {info['height']}"


class TestBackgroundLayerBehavior:
    """Tests for background layer auto-fit behavior."""

    async def test_background_layer_initially_full_size(self, helpers: TestHelpers):
        """Background layer starts at full document size (filled with white)."""
        await helpers.new_document(800, 600)

        # Get background layer info
        bg_info = await helpers.editor.get_layer_info(index=0)

        # Background should be full document size (filled with white)
        assert bg_info['width'] == 800
        assert bg_info['height'] == 600

    async def test_background_layer_autofits_after_erasing(self, helpers: TestHelpers):
        """Background layer should auto-fit after erasing content."""
        await helpers.new_document(800, 600)

        # Get background layer info
        bg_info = await helpers.editor.get_layer_info(index=0)
        assert bg_info['width'] == 800
        assert bg_info['height'] == 600

        # Erase some content - all layers auto-fit now
        await helpers.tools.eraser_stroke([(100, 100), (200, 200)], size=50)

        bg_info_after = await helpers.editor.get_layer_info(index=0)

        # Background layer should auto-fit like any other layer
        # With a diagonal erase through the middle, the layer bounds
        # should still cover most of the document
        assert bg_info_after['width'] > 0, "Layer should have content"
        assert bg_info_after['height'] > 0, "Layer should have content"
