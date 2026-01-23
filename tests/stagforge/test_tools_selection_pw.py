"""Tests for selection tools with different layer offsets - Playwright version.

Testing Principles:
- Selection bounds should match exactly what was requested (clamped to document)
- Delete operations should remove exact selection area pixels
- Magic wand selection area depends on color region size
"""

import math
import pytest
from .helpers_pw import TestHelpers, approx_rect_pixels


pytestmark = pytest.mark.asyncio


class TestRectangularSelection:
    """Tests for the rectangular selection tool."""

    async def test_create_selection_exact_bounds(self, helpers: TestHelpers):
        """Test creating a selection has exact requested bounds."""
        await helpers.new_document(200, 200)

        await helpers.selection.select_rect(50, 50, 80, 60)

        assert await helpers.selection.has_selection()
        bounds = await helpers.selection.get_selection_bounds()

        # Selection bounds should be exact (within 2px for drag precision)
        assert abs(bounds[0] - 50) <= 2, f"Selection x: expected ~50, got {bounds[0]}"
        assert abs(bounds[1] - 50) <= 2, f"Selection y: expected ~50, got {bounds[1]}"
        assert abs(bounds[2] - 80) <= 2, f"Selection width: expected ~80, got {bounds[2]}"
        assert abs(bounds[3] - 60) <= 2, f"Selection height: expected ~60, got {bounds[3]}"

    async def test_selection_api_gives_exact_bounds(self, helpers: TestHelpers):
        """Test API selection gives exactly requested bounds."""
        await helpers.new_document(200, 200)

        await helpers.selection.select_rect_api(30, 40, 50, 60)

        bounds = await helpers.selection.get_selection_bounds()
        # API should be exact
        assert bounds == (30, 40, 50, 60), f"Expected exact (30, 40, 50, 60), got {bounds}"

    async def test_selection_clamped_to_document(self, helpers: TestHelpers):
        """Test selection extending beyond document is clamped."""
        await helpers.new_document(200, 200)

        # Request selection extending beyond bounds
        await helpers.selection.select_rect_api(-50, -50, 300, 300)

        bounds = await helpers.selection.get_selection_bounds()

        # Should be clamped to (0, 0, 200, 200)
        assert bounds[0] == 0, f"x should be clamped to 0, got {bounds[0]}"
        assert bounds[1] == 0, f"y should be clamped to 0, got {bounds[1]}"
        assert bounds[0] + bounds[2] <= 200, f"Right edge should be <= 200"
        assert bounds[1] + bounds[3] <= 200, f"Bottom edge should be <= 200"

    async def test_select_all_covers_entire_document(self, helpers: TestHelpers):
        """Test select all produces exact document-sized selection."""
        await helpers.new_document(200, 200)

        await helpers.selection.select_all()

        bounds = await helpers.selection.get_selection_bounds()
        assert bounds == (0, 0, 200, 200), f"Select all should be (0, 0, 200, 200), got {bounds}"

    async def test_clear_selection_removes_selection(self, helpers: TestHelpers):
        """Test clear selection completely removes selection."""
        await helpers.new_document(200, 200)

        await helpers.selection.select_rect_api(50, 50, 80, 60)
        assert await helpers.selection.has_selection()

        await helpers.selection.clear_selection()
        assert not await helpers.selection.has_selection(), "Selection should be cleared"


class TestSelectionDelete:
    """Tests for deleting selection content."""

    async def test_delete_selection_removes_exact_area(self, helpers: TestHelpers):
        """Test deleting selection removes exactly the selected pixels."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF0000')
        initial_pixels = 200 * 200  # 40000

        # Select and delete 80x60 region
        await helpers.selection.select_rect_api(50, 50, 80, 60)
        await helpers.selection.delete_selection_content()

        remaining = await helpers.pixels.count_non_transparent_pixels()
        deleted = initial_pixels - remaining
        expected_deleted = 80 * 60  # 4800

        # Delete should be exact (within small tolerance for edge effects)
        assert abs(deleted - expected_deleted) <= 50, \
            f"Should delete exactly {expected_deleted} pixels, deleted {deleted}"

    async def test_delete_on_offset_layer_removes_correct_area(self, helpers: TestHelpers):
        """Test delete on offset layer removes pixels in correct region."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#00FF00',
            width=150, height=150,
            offset_x=100, offset_y=100
        )

        initial_pixels = 150 * 150  # 22500

        # Select region that partially overlaps layer: (125, 125) to (175, 175)
        # Overlap with layer: (125, 125) to (175, 175) = 50x50 = 2500 pixels
        await helpers.selection.select_rect_api(125, 125, 50, 50)
        await helpers.selection.delete_selection_content()

        remaining = await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)
        deleted = initial_pixels - remaining
        expected_deleted = 50 * 50  # 2500

        # Allow small tolerance
        assert abs(deleted - expected_deleted) <= 100, \
            f"Should delete ~{expected_deleted} pixels, deleted {deleted}"

    async def test_delete_outside_layer_removes_nothing(self, helpers: TestHelpers):
        """Test delete outside offset layer doesn't affect it."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#0000FF',
            width=80, height=80,
            offset_x=300, offset_y=300
        )

        initial_pixels = 80 * 80  # 6400

        # Select region far from layer
        await helpers.selection.select_rect_api(50, 50, 100, 100)
        await helpers.selection.delete_selection_content()

        remaining = await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)

        assert remaining == initial_pixels, \
            f"Layer should have exactly {initial_pixels} pixels, got {remaining}"


class TestMagicWandSelection:
    """Tests for magic wand selection."""

    async def test_magic_wand_selects_filled_region(self, helpers: TestHelpers):
        """Test magic wand selects region of consistent color."""
        await helpers.new_document(200, 200)

        # Fill left half with red
        await helpers.tools.draw_filled_rect(0, 0, 100, 200, color='#FF0000')

        # Magic wand on red area
        await helpers.selection.select_by_color(50, 100, tolerance=10)

        assert await helpers.selection.has_selection()
        bounds = await helpers.selection.get_selection_bounds()

        # Selection should approximately cover the left half (100 wide, 200 tall)
        min_width, max_width = approx_rect_pixels(100, 1, tolerance=0.15)  # Just checking width
        assert 85 <= bounds[2] <= 115, f"Width should be ~100, got {bounds[2]}"
        assert 180 <= bounds[3] <= 200, f"Height should be ~200, got {bounds[3]}"

    async def test_magic_wand_on_offset_layer(self, helpers: TestHelpers):
        """Test magic wand works correctly on offset layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#00FF00',
            width=100, height=100,
            offset_x=150, offset_y=150
        )

        # Magic wand in center of layer
        await helpers.selection.select_by_color(200, 200, tolerance=10)

        assert await helpers.selection.has_selection()
        bounds = await helpers.selection.get_selection_bounds()

        # Selection should be around layer position
        assert 145 <= bounds[0] <= 155, f"Selection x: expected ~150, got {bounds[0]}"
        assert 145 <= bounds[1] <= 155, f"Selection y: expected ~150, got {bounds[1]}"
        # Size should be close to layer size
        assert 90 <= bounds[2] <= 110, f"Selection width: expected ~100, got {bounds[2]}"
        assert 90 <= bounds[3] <= 110, f"Selection height: expected ~100, got {bounds[3]}"

    async def test_magic_wand_tolerance_affects_selection(self, helpers: TestHelpers):
        """Test tolerance parameter affects selection size."""
        await helpers.new_document(200, 200)

        # Two adjacent rects with similar colors
        await helpers.tools.draw_filled_rect(0, 0, 100, 200, color='#FF0000')
        await helpers.tools.draw_filled_rect(100, 0, 100, 200, color='#EE0000')

        # Low tolerance - select only exact color
        await helpers.selection.select_by_color(50, 100, tolerance=5, contiguous=False)
        bounds_low = await helpers.selection.get_selection_bounds()

        await helpers.selection.clear_selection()

        # High tolerance - select both similar colors
        await helpers.selection.select_by_color(50, 100, tolerance=50, contiguous=False)
        bounds_high = await helpers.selection.get_selection_bounds()

        # High tolerance should select wider area
        assert bounds_high[2] > bounds_low[2], \
            f"High tolerance width ({bounds_high[2]}) should exceed low ({bounds_low[2]})"


class TestSelectionOnOffsetLayers:
    """Tests for selection behavior with offset layers."""

    async def test_selection_partial_overlap_with_layer(self, helpers: TestHelpers):
        """Test selection partially overlapping offset layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_filled_layer(
            '#FF0000',
            width=100, height=100,
            offset_x=150, offset_y=150
        )

        initial_pixels = 100 * 100

        # Selection overlaps left half of layer
        await helpers.selection.select_rect_api(100, 150, 100, 100)
        await helpers.selection.delete_selection_content()

        remaining = await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)
        deleted = initial_pixels - remaining

        # Should delete approximately 50x100 = 5000 pixels (left half of layer overlap)
        expected = 50 * 100
        assert abs(deleted - expected) <= 200, \
            f"Should delete ~{expected} pixels, deleted {deleted}"

    async def test_select_layer_content_matches_layer_bounds(self, helpers: TestHelpers):
        """Test select_layer_content helper gives exact layer bounds."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=150,
            width=120, height=80
        )

        await helpers.selection.select_layer_content(layer_id)

        bounds = await helpers.selection.get_selection_bounds()
        assert bounds == (100, 150, 120, 80), \
            f"Expected layer bounds (100, 150, 120, 80), got {bounds}"

    async def test_select_partial_layer_applies_correct_margin(self, helpers: TestHelpers):
        """Test select_partial_layer helper applies margin correctly."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=100,
            width=100, height=100
        )

        await helpers.selection.select_partial_layer(layer_id, margin=10)

        bounds = await helpers.selection.get_selection_bounds()
        # Should be inset by margin on all sides
        assert bounds[0] == 110, f"x should be 110, got {bounds[0]}"
        assert bounds[1] == 110, f"y should be 110, got {bounds[1]}"
        assert bounds[2] == 80, f"width should be 80, got {bounds[2]}"
        assert bounds[3] == 80, f"height should be 80, got {bounds[3]}"


class TestSelectionExpansionContraction:
    """Tests for selection expand/contract operations."""

    async def test_expand_selection_increases_bounds(self, helpers: TestHelpers):
        """Test expand increases selection by expected amount."""
        await helpers.new_document(200, 200)

        await helpers.selection.select_rect_api(50, 50, 40, 40)
        original = await helpers.selection.get_selection_bounds()

        await helpers.selection.expand_selection(10)
        expanded = await helpers.selection.get_selection_bounds()

        # Should expand by 10 on each side
        assert expanded[0] == original[0] - 10, "x should decrease by 10"
        assert expanded[1] == original[1] - 10, "y should decrease by 10"
        assert expanded[2] == original[2] + 20, "width should increase by 20"
        assert expanded[3] == original[3] + 20, "height should increase by 20"

    async def test_contract_selection_decreases_bounds(self, helpers: TestHelpers):
        """Test contract decreases selection by expected amount."""
        await helpers.new_document(200, 200)

        await helpers.selection.select_rect_api(50, 50, 60, 60)
        original = await helpers.selection.get_selection_bounds()

        await helpers.selection.contract_selection(10)
        contracted = await helpers.selection.get_selection_bounds()

        # Should contract by 10 on each side
        assert contracted[0] == original[0] + 10, "x should increase by 10"
        assert contracted[1] == original[1] + 10, "y should increase by 10"
        assert contracted[2] == original[2] - 20, "width should decrease by 20"
        assert contracted[3] == original[3] - 20, "height should decrease by 20"
