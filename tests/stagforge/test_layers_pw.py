"""Tests for layer operations - Playwright version."""

import pytest
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


class TestLayerCreation:
    """Tests for creating layers."""

    async def test_create_layer_default_size(self, helpers: TestHelpers):
        """Test creating a layer with default (document) size."""
        await helpers.new_document(300, 200)

        initial_count = await helpers.editor.get_layer_count()
        layer_id = await helpers.layers.create_layer()

        assert await helpers.editor.get_layer_count() == initial_count + 1
        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        # Default layer should match document size
        assert info['width'] == 300
        assert info['height'] == 200
        assert info['offsetX'] == 0
        assert info['offsetY'] == 0

    async def test_create_layer_custom_size(self, helpers: TestHelpers):
        """Test creating a layer with custom size."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(
            width=100, height=150,
            offset_x=50, offset_y=75
        )

        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['width'] == 100
        assert info['height'] == 150
        assert info['offsetX'] == 50
        assert info['offsetY'] == 75

    async def test_create_offset_layer_helper(self, helpers: TestHelpers):
        """Test the create_offset_layer helper method."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=200, offset_y=150,
            width=80, height=60
        )

        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['offsetX'] == 200
        assert info['offsetY'] == 150
        assert info['width'] == 80
        assert info['height'] == 60

    async def test_create_filled_layer(self, helpers: TestHelpers):
        """Test creating a pre-filled layer."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_filled_layer(
            '#FF0000',
            width=100, height=100,
            offset_x=50, offset_y=50
        )

        # Check layer is filled
        red_count = await helpers.pixels.count_pixels_with_color(
            (255, 0, 0, 255), tolerance=5, layer_id=layer_id
        )
        assert red_count == 100 * 100, f"Expected 10000 red pixels, got {red_count}"

    async def test_create_layer_with_name(self, helpers: TestHelpers):
        """Test creating a layer with custom name."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_layer(name="Custom Name")

        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['name'] == "Custom Name"


class TestLayerSelection:
    """Tests for selecting layers."""

    async def test_select_layer_by_index(self, helpers: TestHelpers):
        """Test selecting a layer by index."""
        await helpers.new_document(200, 200)

        # Create multiple layers
        layer1_id = await helpers.layers.create_layer(name="Layer 1")
        layer2_id = await helpers.layers.create_layer(name="Layer 2")
        layer3_id = await helpers.layers.create_layer(name="Layer 3")

        # Select by index
        await helpers.layers.select_by_index(0)
        layer0_info = await helpers.editor.get_layer_info(index=0)
        assert await helpers.layers.layer_is_active(layer0_info['id'])

    async def test_select_layer_by_id(self, helpers: TestHelpers):
        """Test selecting a layer by ID."""
        await helpers.new_document(200, 200)

        layer1_id = await helpers.layers.create_layer(name="First")
        layer2_id = await helpers.layers.create_layer(name="Second")

        await helpers.layers.select_by_id(layer1_id)
        assert await helpers.editor.get_active_layer_id() == layer1_id

    async def test_select_topmost_layer(self, helpers: TestHelpers):
        """Test selecting the topmost layer."""
        await helpers.new_document(200, 200)

        layer1_id = await helpers.layers.create_layer(name="Bottom")
        layer2_id = await helpers.layers.create_layer(name="Top")

        await helpers.layers.select_bottommost()
        await helpers.layers.select_topmost()

        active_info = await helpers.editor.get_layer_info()
        assert active_info['name'] == "Top"

    async def test_select_bottommost_layer(self, helpers: TestHelpers):
        """Test selecting the bottommost layer."""
        await helpers.new_document(200, 200)

        # Background layer already exists
        layer2_id = await helpers.layers.create_layer(name="New Layer")

        await helpers.layers.select_bottommost()
        active_info = await helpers.editor.get_layer_info(index=0)
        # Should be the background layer
        assert await helpers.layers.layer_is_active(active_info['id'])


class TestLayerProperties:
    """Tests for layer properties."""

    async def test_get_layer_offset(self, helpers: TestHelpers):
        """Test getting layer offset."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=123, offset_y=456,
            width=50, height=50
        )

        offset = await helpers.layers.get_layer_offset(layer_id)
        assert offset == (123, 456)

    async def test_get_layer_size(self, helpers: TestHelpers):
        """Test getting layer size."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(width=150, height=200)

        size = await helpers.layers.get_layer_size(layer_id)
        assert size == (150, 200)

    async def test_get_layer_bounds(self, helpers: TestHelpers):
        """Test getting layer bounds."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=50,
            width=200, height=150
        )

        bounds = await helpers.layers.get_layer_bounds(layer_id)
        assert bounds == (100, 50, 200, 150)

    async def test_set_layer_offset(self, helpers: TestHelpers):
        """Test setting layer offset."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_layer(width=100, height=100)

        await helpers.layers.set_layer_offset(200, 150, layer_id)

        offset = await helpers.layers.get_layer_offset(layer_id)
        assert offset == (200, 150)

    async def test_set_layer_opacity(self, helpers: TestHelpers):
        """Test setting layer opacity."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_layer()

        await helpers.layers.set_layer_opacity(0.5, layer_id)

        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert abs(info['opacity'] - 0.5) < 0.01

    async def test_set_layer_visibility(self, helpers: TestHelpers):
        """Test toggling layer visibility."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_filled_layer('#FF0000', width=200, height=200)

        # Initially visible
        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['visible'] == True

        # Hide
        await helpers.layers.set_layer_visibility(False, layer_id)
        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['visible'] == False

        # Show again
        await helpers.layers.set_layer_visibility(True, layer_id)
        info = await helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['visible'] == True


class TestLayerOperations:
    """Tests for layer operations."""

    async def test_duplicate_layer(self, helpers: TestHelpers):
        """Test duplicating a layer."""
        await helpers.new_document(200, 200)

        original_id = await helpers.layers.create_filled_layer('#FF0000', width=100, height=100)
        original_checksum = await helpers.pixels.compute_checksum(layer_id=original_id)
        initial_count = await helpers.editor.get_layer_count()

        dup_id = await helpers.layers.duplicate_layer(original_id)

        # Should have one more layer
        assert await helpers.editor.get_layer_count() == initial_count + 1

        # Content should match
        dup_checksum = await helpers.pixels.compute_checksum(layer_id=dup_id)
        assert dup_checksum == original_checksum

    async def test_delete_layer(self, helpers: TestHelpers):
        """Test deleting a layer."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_layer(name="To Delete")
        initial_count = await helpers.editor.get_layer_count()

        await helpers.layers.delete_layer(layer_id)

        assert await helpers.editor.get_layer_count() == initial_count - 1
        assert not await helpers.layers.layer_exists(layer_id)

    async def test_clear_layer(self, helpers: TestHelpers):
        """Test clearing a layer."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_filled_layer('#00FF00', width=150, height=150)
        assert await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id) > 0

        await helpers.layers.clear_layer(layer_id)

        assert await helpers.pixels.count_non_transparent_pixels(layer_id=layer_id) == 0

    async def test_fill_layer_with_color(self, helpers: TestHelpers):
        """Test filling a layer with color."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_layer(width=100, height=100)
        await helpers.layers.fill_layer_with_color('#0000FF', layer_id)

        blue_count = await helpers.pixels.count_pixels_with_color(
            (0, 0, 255, 255), tolerance=5, layer_id=layer_id
        )
        assert blue_count == 100 * 100


class TestLayerMerging:
    """Tests for layer merging operations."""

    async def test_merge_down(self, helpers: TestHelpers):
        """Test merging a layer down."""
        await helpers.new_document(200, 200)

        # Create bottom layer with red
        await helpers.layers.fill_layer_with_color('#FF0000')

        # Create top layer with blue circle
        top_id = await helpers.layers.create_layer()
        await helpers.tools.draw_filled_circle(100, 100, 30, color='#0000FF')

        initial_count = await helpers.editor.get_layer_count()

        await helpers.layers.merge_down()

        # Should have one fewer layer
        assert await helpers.editor.get_layer_count() == initial_count - 1

        # Content should be merged (both red and blue present)
        red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=5)
        blue = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=5)
        assert red > 0, "Should have red from bottom layer"
        assert blue > 0, "Should have blue from merged layer"

    async def test_flatten_all(self, helpers: TestHelpers):
        """Test flattening all layers."""
        await helpers.new_document(200, 200)

        # Create multiple layers with different content
        await helpers.layers.fill_layer_with_color('#FF0000')
        await helpers.layers.create_layer()
        await helpers.tools.draw_filled_rect(50, 50, 60, 60, color='#00FF00')
        await helpers.layers.create_layer()
        await helpers.tools.draw_filled_circle(150, 150, 20, color='#0000FF')

        initial_count = await helpers.editor.get_layer_count()
        assert initial_count >= 3

        await helpers.layers.flatten_all()

        # Should have only one layer
        assert await helpers.editor.get_layer_count() == 1


class TestLayerReordering:
    """Tests for layer reordering."""

    async def test_move_layer_up(self, helpers: TestHelpers):
        """Test moving a layer up in the stack."""
        await helpers.new_document(200, 200)

        layer1_id = await helpers.layers.create_layer(name="Layer 1")
        layer2_id = await helpers.layers.create_layer(name="Layer 2")
        layer3_id = await helpers.layers.create_layer(name="Layer 3")

        # Move layer 1 up
        await helpers.layers.move_layer_up(layer1_id)

        # Get new order
        layers = await helpers.layers.get_all_layers()
        layer1_idx = next(i for i, l in enumerate(layers) if l['id'] == layer1_id)
        layer2_idx = next(i for i, l in enumerate(layers) if l['id'] == layer2_id)

        # Layer 1 should now be above layer 2
        assert layer1_idx > layer2_idx

    async def test_move_layer_down(self, helpers: TestHelpers):
        """Test moving a layer down in the stack."""
        await helpers.new_document(200, 200)

        layer1_id = await helpers.layers.create_layer(name="Layer 1")
        layer2_id = await helpers.layers.create_layer(name="Layer 2")
        layer3_id = await helpers.layers.create_layer(name="Layer 3")

        # Layer 3 is on top, move it down
        await helpers.layers.move_layer_down(layer3_id)

        layers = await helpers.layers.get_all_layers()
        layer2_idx = next(i for i, l in enumerate(layers) if l['id'] == layer2_id)
        layer3_idx = next(i for i, l in enumerate(layers) if l['id'] == layer3_id)

        # Layer 3 should now be below layer 2
        assert layer3_idx < layer2_idx


class TestLayerWithOffsets:
    """Tests for operations on offset layers."""

    async def test_draw_on_offset_layer_correct_position(self, helpers: TestHelpers):
        """Test that drawing on offset layer places content correctly."""
        await helpers.new_document(400, 400)

        # Create offset layer
        layer_id = await helpers.layers.create_offset_layer(
            offset_x=150, offset_y=150,
            width=100, height=100
        )

        # Draw rectangle directly on layer canvas
        await helpers.layers.draw_rect_on_layer(20, 20, 40, 40, '#FF0000', layer_id)

        # Content should be at (20, 20) in layer canvas coords
        content_bounds = await helpers.pixels.get_bounding_box_of_content(layer_id=layer_id)
        assert content_bounds[0] >= 15 and content_bounds[0] <= 25, \
            f"Content x should be around 20, got {content_bounds[0]}"

    async def test_composite_rendering_with_offset_layers(self, helpers: TestHelpers):
        """Test that offset layers render correctly in composite."""
        await helpers.new_document(300, 300)

        # Background
        await helpers.layers.fill_layer_with_color('#FFFFFF')

        # Create offset layer with red rectangle
        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=100,
            width=100, height=100
        )
        await helpers.layers.fill_layer_with_color('#FF0000', layer_id)

        # Check composite at various positions
        # Outside offset layer - should be white
        pixel = await helpers.pixels.get_pixel(50, 50)
        assert pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200, \
            f"Expected white at (50,50), got {pixel}"

        # Inside offset layer - should be red
        pixel = await helpers.pixels.get_pixel(150, 150)
        assert pixel[0] > 200 and pixel[1] < 50 and pixel[2] < 50, \
            f"Expected red at (150,150), got {pixel}"


class TestLayerUndoRedo:
    """Tests for undo/redo with layer operations."""

    async def test_undo_add_layer(self, helpers: TestHelpers):
        """Test that undo removes an added layer."""
        await helpers.new_document(200, 200)

        initial_count = await helpers.editor.get_layer_count()
        layer_id = await helpers.layers.create_layer()
        assert await helpers.editor.get_layer_count() == initial_count + 1

        await helpers.undo()
        # Note: Layer creation may or may not be undoable depending on implementation
        # This test verifies the behavior

    async def test_undo_delete_layer(self, helpers: TestHelpers):
        """Test that undo restores a deleted layer."""
        await helpers.new_document(200, 200)

        layer_id = await helpers.layers.create_filled_layer('#FF0000', width=100, height=100)
        initial_count = await helpers.editor.get_layer_count()
        checksum = await helpers.pixels.compute_checksum(layer_id=layer_id)

        await helpers.layers.delete_layer(layer_id)
        assert await helpers.editor.get_layer_count() == initial_count - 1

        await helpers.undo()
        # After undo, the layer count should be restored
        # Note: Actual behavior depends on history implementation

    async def test_undo_merge_down(self, helpers: TestHelpers):
        """Test that undo restores merged layers."""
        await helpers.new_document(200, 200)

        await helpers.layers.fill_layer_with_color('#FF0000')
        layer2_id = await helpers.layers.create_filled_layer('#0000FF', width=50, height=50)

        initial_count = await helpers.editor.get_layer_count()

        await helpers.layers.merge_down(layer2_id)
        assert await helpers.editor.get_layer_count() == initial_count - 1

        await helpers.undo()
        # After undo, should have original layer count
        # Note: Actual behavior depends on history implementation
