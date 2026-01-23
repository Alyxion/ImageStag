"""Tests for clipboard operations (copy, cut, paste) with different layer offsets.

Playwright-based tests.

Testing Principles:
- Copy/paste should preserve exact pixel content (same checksum)
- Cut should remove exact selection area from source
- Pasted layer dimensions should match clipboard content exactly
- Paste in place should restore exact original position
"""

import pytest
from .helpers_pw import TestHelpers, approx_rect_pixels


pytestmark = pytest.mark.asyncio


class TestCopy:
    """Tests for copy operations."""

    async def test_copy_entire_layer_has_correct_size(self, helpers: TestHelpers):
        """Test copying entire layer produces correct clipboard size."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF0000')
        await helpers.selection.select_all()
        await helpers.selection.copy()

        assert await helpers.selection.has_clipboard_content()
        info = await helpers.selection.get_clipboard_info()

        # Clipboard should be exact document size
        assert info['width'] == 200, f"Clipboard width should be 200, got {info['width']}"
        assert info['height'] == 200, f"Clipboard height should be 200, got {info['height']}"

    async def test_copy_selection_has_exact_size(self, helpers: TestHelpers):
        """Test copying selection produces exact clipboard size."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#00FF00')
        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.copy()

        info = await helpers.selection.get_clipboard_info()

        assert info['width'] == 80, f"Clipboard width should be 80, got {info['width']}"
        assert info['height'] == 60, f"Clipboard height should be 60, got {info['height']}"

    async def test_copy_from_offset_layer_correct_source_position(self, helpers: TestHelpers):
        """Test copy from offset layer records correct source position."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#FF0000',
            width=100, height=100,
            offset_x=150, offset_y=150
        )

        await helpers.selection.select_rect_api(170, 170, 50, 50)
        await helpers.selection.copy()

        info = await helpers.selection.get_clipboard_info()

        assert info['sourceX'] == 170, f"Source X should be 170, got {info['sourceX']}"
        assert info['sourceY'] == 170, f"Source Y should be 170, got {info['sourceY']}"
        assert info['width'] == 50
        assert info['height'] == 50


class TestPaste:
    """Tests for paste operations."""

    async def test_paste_creates_exactly_one_layer(self, helpers: TestHelpers):
        """Test paste creates exactly one new layer."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF0000')
        initial_count = await helpers.editor.get_layer_count()

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.copy()
        await helpers.selection.paste()

        new_count = await helpers.editor.get_layer_count()
        assert new_count == initial_count + 1, \
            f"Should add exactly 1 layer. Initial: {initial_count}, after: {new_count}"

    async def test_pasted_layer_exact_size(self, helpers: TestHelpers):
        """Test pasted layer has exact clipboard dimensions."""
        await helpers.new_document(400, 400)

        await helpers.layers.fill_layer_with_color('#0000FF')
        await helpers.selection.select_rect_api(100, 100, 100, 80)
        await helpers.selection.copy()
        await helpers.selection.paste()

        layer_info = await helpers.editor.get_layer_info()

        assert layer_info['width'] == 100, f"Layer width should be 100, got {layer_info['width']}"
        assert layer_info['height'] == 80, f"Layer height should be 80, got {layer_info['height']}"

    async def test_paste_preserves_pixel_content(self, helpers: TestHelpers):
        """Test paste preserves exact pixel content (matching checksum)."""
        await helpers.new_document(200, 200)

        await helpers.tools.draw_filled_rect(50, 50, 60, 40, color='#FF0000')
        await helpers.tools.draw_filled_circle(80, 70, 10, color='#0000FF')

        await helpers.selection.select_rect_api(50, 50, 60, 40)
        original_checksum = await helpers.pixels.compute_checksum(region=(50, 50, 60, 40))

        await helpers.selection.copy()
        await helpers.selection.paste()

        pasted_layer_id = await helpers.editor.get_active_layer_id()
        pasted_checksum = await helpers.pixels.compute_checksum(layer_id=pasted_layer_id)

        assert pasted_checksum == original_checksum, \
            "Pasted content should have identical checksum"

    async def test_paste_in_place_exact_position(self, helpers: TestHelpers):
        """Test paste in place restores exact original position."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#0000FF',
            width=80, height=80,
            offset_x=200, offset_y=200
        )

        await helpers.selection.select_rect_api(200, 200, 80, 80)
        await helpers.selection.copy()
        await helpers.selection.paste_in_place()

        new_layer = await helpers.editor.get_layer_info()

        assert new_layer['offsetX'] == 200, f"Offset X should be 200, got {new_layer['offsetX']}"
        assert new_layer['offsetY'] == 200, f"Offset Y should be 200, got {new_layer['offsetY']}"


class TestCut:
    """Tests for cut operations."""

    async def test_cut_removes_exact_selection_area(self, helpers: TestHelpers):
        """Test cut removes exactly the selection area pixels."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF0000')
        initial_pixels = 200 * 200

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.cut()

        remaining = await helpers.pixels.count_non_transparent_pixels()
        removed = initial_pixels - remaining
        expected_removed = 80 * 60

        assert abs(removed - expected_removed) <= 50, \
            f"Cut should remove exactly {expected_removed} pixels, removed {removed}"

    async def test_cut_from_offset_layer_removes_correct_area(self, helpers: TestHelpers):
        """Test cut from offset layer removes pixels only in overlap region."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#00FF00',
            width=100, height=100,
            offset_x=150, offset_y=150
        )

        initial_pixels = 100 * 100

        # Cut 40x40 region from layer
        await helpers.selection.select_rect_api(180, 180, 40, 40)
        await helpers.selection.cut()

        remaining = await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)
        removed = initial_pixels - remaining
        expected_removed = 40 * 40

        assert abs(removed - expected_removed) <= 100, \
            f"Cut should remove ~{expected_removed} pixels, removed {removed}"

    async def test_cut_outside_offset_layer_removes_nothing(self, helpers: TestHelpers):
        """Test cut outside offset layer doesn't affect it."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#0000FF',
            width=80, height=80,
            offset_x=300, offset_y=300
        )

        initial_pixels = 80 * 80

        await helpers.selection.select_rect_api(50, 50, 100, 100)
        await helpers.selection.cut()

        remaining = await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)

        assert remaining == initial_pixels, \
            f"Layer should have exactly {initial_pixels} pixels, got {remaining}"


class TestCutPasteCycle:
    """Tests for cut-paste roundtrip."""

    async def test_cut_paste_preserves_checksum(self, helpers: TestHelpers):
        """Test cut then paste produces identical pixel content."""
        await helpers.new_document(200, 200)

        await helpers.tools.draw_filled_rect(60, 60, 50, 50, color='#FF0000')
        await helpers.tools.draw_filled_circle(85, 85, 15, color='#0000FF')

        await helpers.selection.select_rect_api(60, 60, 50, 50)
        original_checksum = await helpers.pixels.compute_checksum(region=(60, 60, 50, 50))

        await helpers.selection.cut()
        await helpers.selection.paste()

        new_layer_id = await helpers.editor.get_active_layer_id()
        pasted_checksum = await helpers.pixels.compute_checksum(layer_id=new_layer_id)

        assert pasted_checksum == original_checksum, \
            "Cut-paste should preserve exact pixel content"

    async def test_cut_paste_in_place_restores_position(self, helpers: TestHelpers):
        """Test cut then paste in place creates layer at original position."""
        await helpers.new_document(300, 300)

        await helpers.tools.draw_filled_rect(100, 100, 60, 60, color='#FF00FF')

        await helpers.selection.select_rect_api(100, 100, 60, 60)
        await helpers.selection.cut()
        await helpers.selection.paste_in_place()

        layer_info = await helpers.editor.get_layer_info()

        assert layer_info['offsetX'] == 100, f"Offset X should be 100, got {layer_info['offsetX']}"
        assert layer_info['offsetY'] == 100, f"Offset Y should be 100, got {layer_info['offsetY']}"
        assert layer_info['width'] == 60
        assert layer_info['height'] == 60


class TestCopyMerged:
    """Tests for copy merged functionality."""

    async def test_copy_merged_combines_visible_layers(self, helpers: TestHelpers):
        """Test copy merged combines all visible layers."""
        await helpers.new_document(200, 200)

        # Bottom layer: red
        await helpers.layers.fill_layer_with_color('#FF0000')

        # Top layer: blue circle
        layer_id = await helpers.layers.create_layer()
        await helpers.tools.draw_filled_circle(100, 100, 40, color='#0000FF')

        await helpers.selection.select_all()
        await helpers.selection.copy_merged()

        assert await helpers.selection.has_clipboard_content()
        info = await helpers.selection.get_clipboard_info()

        assert info['width'] == 200
        assert info['height'] == 200

    async def test_copy_merged_includes_offset_layers(self, helpers: TestHelpers):
        """Test copy merged includes content from offset layers."""
        await helpers.new_document(400, 400)

        # Background: yellow
        await helpers.layers.fill_layer_with_color('#FFFF00')

        # Offset layer: cyan
        layer_id = await helpers.layers.create_filled_layer(
            '#00FFFF',
            width=100, height=100,
            offset_x=150, offset_y=150
        )

        # Copy merged from region including offset layer
        await helpers.selection.select_rect_api(100, 100, 200, 200)
        await helpers.selection.copy_merged()

        info = await helpers.selection.get_clipboard_info()

        assert info['width'] == 200
        assert info['height'] == 200


class TestClipboardUndoRedo:
    """Tests for undo/redo with clipboard operations - exact restoration."""

    async def test_undo_cut_restores_exact_pixels(self, helpers: TestHelpers):
        """Test undo cut restores exact original pixel count."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF0000')
        initial_pixels = await helpers.pixels.count_non_transparent_pixels()
        initial_checksum = await helpers.pixels.compute_checksum()
        assert initial_pixels == 200 * 200

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.cut()

        after_cut = await helpers.pixels.count_non_transparent_pixels()
        assert after_cut < initial_pixels

        await helpers.undo()
        after_undo = await helpers.pixels.count_non_transparent_pixels()
        after_undo_checksum = await helpers.pixels.compute_checksum()

        assert after_undo == initial_pixels, \
            f"Undo should restore exact {initial_pixels} pixels, got {after_undo}"
        assert after_undo_checksum == initial_checksum, \
            "Undo should restore identical pixel data"

    async def test_undo_paste_removes_layer(self, helpers: TestHelpers):
        """Test undo paste removes the pasted layer exactly."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#00FF00')
        initial_count = await helpers.editor.get_layer_count()

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.copy()
        await helpers.selection.paste()

        after_paste = await helpers.editor.get_layer_count()
        assert after_paste == initial_count + 1

        await helpers.undo()
        after_undo = await helpers.editor.get_layer_count()

        assert after_undo == initial_count, \
            f"Undo should restore layer count to {initial_count}, got {after_undo}"

    async def test_undo_delete_selection_restores_exact_content(self, helpers: TestHelpers):
        """Test undo delete restores exact pixel content."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#0000FF')
        initial_checksum = await helpers.pixels.compute_checksum()

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.delete_selection_content()

        after_delete_checksum = await helpers.pixels.compute_checksum()
        assert after_delete_checksum != initial_checksum

        await helpers.undo()
        after_undo_checksum = await helpers.pixels.compute_checksum()

        assert after_undo_checksum == initial_checksum, \
            "Undo should restore identical pixel data"

    async def test_redo_cut_removes_exact_pixels_again(self, helpers: TestHelpers):
        """Test redo cut removes same pixels as original cut."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF00FF')

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.cut()
        after_cut_checksum = await helpers.pixels.compute_checksum()

        await helpers.undo()
        await helpers.redo()
        after_redo_checksum = await helpers.pixels.compute_checksum()

        assert after_redo_checksum == after_cut_checksum, \
            "Redo should produce identical result to original cut"
