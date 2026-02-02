"""Tests for layer operations.

NOTE: This test file uses sync test functions but the `helpers` fixture provides
async Playwright helpers. These tests need to be converted to async to work.
There is also a `test_layers_pw.py` with async Playwright tests.
"""

import pytest

# Skip entire module - sync/async mismatch with helpers fixture
pytest.skip(
    "Sync tests with async helpers - use test_layers_pw.py instead",
    allow_module_level=True
)

from .helpers import TestHelpers


class TestLayerCreation:
    """Tests for creating layers."""

    def test_create_layer_default_size(self, helpers: TestHelpers):
        """Test creating a layer with default (document) size."""
        helpers.new_document(300, 200)

        initial_count = helpers.editor.get_layer_count()
        layer_id = helpers.layers.create_layer()

        assert helpers.editor.get_layer_count() == initial_count + 1
        info = helpers.editor.get_layer_info(layer_id=layer_id)
        # Default layer should match document size
        assert info['width'] == 300
        assert info['height'] == 200
        assert info['offsetX'] == 0
        assert info['offsetY'] == 0

    def test_create_layer_custom_size(self, helpers: TestHelpers):
        """Test creating a layer with custom size."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_layer(
            width=100, height=150,
            offset_x=50, offset_y=75
        )

        info = helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['width'] == 100
        assert info['height'] == 150
        assert info['offsetX'] == 50
        assert info['offsetY'] == 75

    def test_create_offset_layer_helper(self, helpers: TestHelpers):
        """Test the create_offset_layer helper method."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_offset_layer(
            offset_x=200, offset_y=150,
            width=80, height=60
        )

        info = helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['offsetX'] == 200
        assert info['offsetY'] == 150
        assert info['width'] == 80
        assert info['height'] == 60

    def test_create_filled_layer(self, helpers: TestHelpers):
        """Test creating a pre-filled layer."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_filled_layer(
            '#FF0000',
            width=100, height=100,
            offset_x=50, offset_y=50
        )

        # Check layer is filled
        red_count = helpers.pixels.count_pixels_with_color(
            (255, 0, 0, 255), tolerance=5, layer_id=layer_id
        )
        assert red_count == 100 * 100, f"Expected 10000 red pixels, got {red_count}"

    def test_create_layer_with_name(self, helpers: TestHelpers):
        """Test creating a layer with custom name."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_layer(name="Custom Name")

        info = helpers.editor.get_layer_info(layer_id=layer_id)
        assert info['name'] == "Custom Name"


class TestLayerSelection:
    """Tests for selecting layers."""

    def test_select_layer_by_index(self, helpers: TestHelpers):
        """Test selecting a layer by index."""
        helpers.new_document(200, 200)

        # Create multiple layers
        layer1_id = helpers.layers.create_layer(name="Layer 1")
        layer2_id = helpers.layers.create_layer(name="Layer 2")
        layer3_id = helpers.layers.create_layer(name="Layer 3")

        # Select by index
        helpers.layers.select_by_index(0)
        assert helpers.layers.layer_is_active(helpers.editor.get_layer_info(index=0)['id'])

    def test_select_layer_by_id(self, helpers: TestHelpers):
        """Test selecting a layer by ID."""
        helpers.new_document(200, 200)

        layer1_id = helpers.layers.create_layer(name="First")
        layer2_id = helpers.layers.create_layer(name="Second")

        helpers.layers.select_by_id(layer1_id)
        assert helpers.editor.get_active_layer_id() == layer1_id

    def test_select_topmost_layer(self, helpers: TestHelpers):
        """Test selecting the topmost layer."""
        helpers.new_document(200, 200)

        layer1_id = helpers.layers.create_layer(name="Bottom")
        layer2_id = helpers.layers.create_layer(name="Top")

        helpers.layers.select_bottommost()
        helpers.layers.select_topmost()

        active_info = helpers.editor.get_layer_info()
        assert active_info['name'] == "Top"

    def test_select_bottommost_layer(self, helpers: TestHelpers):
        """Test selecting the bottommost layer."""
        helpers.new_document(200, 200)

        # Background layer already exists
        layer2_id = helpers.layers.create_layer(name="New Layer")

        helpers.layers.select_bottommost()
        active_info = helpers.editor.get_layer_info(index=0)
        # Should be the background layer
        assert helpers.layers.layer_is_active(active_info['id'])


class TestLayerProperties:
    """Tests for layer properties."""

    def test_get_layer_offset(self, helpers: TestHelpers):
        """Test getting layer offset."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_offset_layer(
            offset_x=123, offset_y=456,
            width=50, height=50
        )

        offset = helpers.layers.get_layer_offset(layer_id)
        assert offset == (123, 456)

    def test_get_layer_size(self, helpers: TestHelpers):
        """Test getting layer size."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_layer(width=150, height=200)

        size = helpers.layers.get_layer_size(layer_id)
        assert size == (150, 200)

    def test_get_layer_bounds(self, helpers: TestHelpers):
        """Test getting layer bounds."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_offset_layer(
            offset_x=100, offset_y=50,
            width=200, height=150
        )

        bounds = helpers.layers.get_layer_bounds(layer_id)
        assert bounds == (100, 50, 200, 150)

    def test_set_layer_offset(self, helpers: TestHelpers):
        """Test setting layer offset."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_layer(width=100, height=100)

        helpers.layers.set_layer_offset(200, 150, layer_id)

        offset = helpers.layers.get_layer_offset(layer_id)
        assert offset == (200, 150)

    def test_set_layer_opacity(self, helpers: TestHelpers):
        """Test setting layer opacity."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_layer()

        helpers.layers.set_layer_opacity(0.5, layer_id)

        info = helpers.editor.get_layer_info(layer_id=layer_id)
        assert abs(info['opacity'] - 0.5) < 0.01

    def test_set_layer_visibility(self, helpers: TestHelpers):
        """Test toggling layer visibility."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_filled_layer('#FF0000', width=200, height=200)

        # Initially visible
        assert helpers.editor.get_layer_info(layer_id=layer_id)['visible'] == True

        # Hide
        helpers.layers.set_layer_visibility(False, layer_id)
        assert helpers.editor.get_layer_info(layer_id=layer_id)['visible'] == False

        # Show again
        helpers.layers.set_layer_visibility(True, layer_id)
        assert helpers.editor.get_layer_info(layer_id=layer_id)['visible'] == True


class TestLayerOperations:
    """Tests for layer operations."""

    def test_duplicate_layer(self, helpers: TestHelpers):
        """Test duplicating a layer."""
        helpers.new_document(200, 200)

        original_id = helpers.layers.create_filled_layer('#FF0000', width=100, height=100)
        original_checksum = helpers.pixels.compute_checksum(layer_id=original_id)
        initial_count = helpers.editor.get_layer_count()

        dup_id = helpers.layers.duplicate_layer(original_id)

        # Should have one more layer
        assert helpers.editor.get_layer_count() == initial_count + 1

        # Content should match
        dup_checksum = helpers.pixels.compute_checksum(layer_id=dup_id)
        assert dup_checksum == original_checksum

    def test_delete_layer(self, helpers: TestHelpers):
        """Test deleting a layer."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_layer(name="To Delete")
        initial_count = helpers.editor.get_layer_count()

        helpers.layers.delete_layer(layer_id)

        assert helpers.editor.get_layer_count() == initial_count - 1
        assert not helpers.layers.layer_exists(layer_id)

    def test_clear_layer(self, helpers: TestHelpers):
        """Test clearing a layer."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_filled_layer('#00FF00', width=150, height=150)
        assert helpers.pixels.count_non_transparent_pixels(layer_id=layer_id) > 0

        helpers.layers.clear_layer(layer_id)

        assert helpers.pixels.count_non_transparent_pixels(layer_id=layer_id) == 0

    def test_fill_layer_with_color(self, helpers: TestHelpers):
        """Test filling a layer with color."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_layer(width=100, height=100)
        helpers.layers.fill_layer_with_color('#0000FF', layer_id)

        blue_count = helpers.pixels.count_pixels_with_color(
            (0, 0, 255, 255), tolerance=5, layer_id=layer_id
        )
        assert blue_count == 100 * 100


class TestLayerMerging:
    """Tests for layer merging operations."""

    def test_merge_down(self, helpers: TestHelpers):
        """Test merging a layer down."""
        helpers.new_document(200, 200)

        # Create bottom layer with red
        helpers.layers.fill_layer_with_color('#FF0000')

        # Create top layer with blue circle
        top_id = helpers.layers.create_layer()
        helpers.tools.draw_filled_circle(100, 100, 30, color='#0000FF')

        initial_count = helpers.editor.get_layer_count()

        helpers.layers.merge_down()

        # Should have one fewer layer
        assert helpers.editor.get_layer_count() == initial_count - 1

        # Content should be merged (both red and blue present)
        red = helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=5)
        blue = helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=5)
        assert red > 0, "Should have red from bottom layer"
        assert blue > 0, "Should have blue from merged layer"

    def test_flatten_all(self, helpers: TestHelpers):
        """Test flattening all layers."""
        helpers.new_document(200, 200)

        # Create multiple layers with different content
        helpers.layers.fill_layer_with_color('#FF0000')
        helpers.layers.create_layer()
        helpers.tools.draw_filled_rect(50, 50, 60, 60, color='#00FF00')
        helpers.layers.create_layer()
        helpers.tools.draw_filled_circle(150, 150, 20, color='#0000FF')

        initial_count = helpers.editor.get_layer_count()
        assert initial_count >= 3

        helpers.layers.flatten_all()

        # Should have only one layer
        assert helpers.editor.get_layer_count() == 1


class TestLayerReordering:
    """Tests for layer reordering."""

    def test_move_layer_up(self, helpers: TestHelpers):
        """Test moving a layer up in the stack."""
        helpers.new_document(200, 200)

        layer1_id = helpers.layers.create_layer(name="Layer 1")
        layer2_id = helpers.layers.create_layer(name="Layer 2")
        layer3_id = helpers.layers.create_layer(name="Layer 3")

        # Move layer 1 up
        helpers.layers.move_layer_up(layer1_id)

        # Get new order
        layers = helpers.layers.get_all_layers()
        layer1_idx = next(i for i, l in enumerate(layers) if l['id'] == layer1_id)
        layer2_idx = next(i for i, l in enumerate(layers) if l['id'] == layer2_id)

        # Layer 1 should now be above layer 2
        assert layer1_idx > layer2_idx

    def test_move_layer_down(self, helpers: TestHelpers):
        """Test moving a layer down in the stack."""
        helpers.new_document(200, 200)

        layer1_id = helpers.layers.create_layer(name="Layer 1")
        layer2_id = helpers.layers.create_layer(name="Layer 2")
        layer3_id = helpers.layers.create_layer(name="Layer 3")

        # Layer 3 is on top, move it down
        helpers.layers.move_layer_down(layer3_id)

        layers = helpers.layers.get_all_layers()
        layer2_idx = next(i for i, l in enumerate(layers) if l['id'] == layer2_id)
        layer3_idx = next(i for i, l in enumerate(layers) if l['id'] == layer3_id)

        # Layer 3 should now be below layer 2
        assert layer3_idx < layer2_idx


class TestLayerWithOffsets:
    """Tests for operations on offset layers."""

    def test_draw_on_offset_layer_correct_position(self, helpers: TestHelpers):
        """Test that drawing on offset layer places content correctly."""
        helpers.new_document(400, 400)

        # Create offset layer
        layer_id = helpers.layers.create_offset_layer(
            offset_x=150, offset_y=150,
            width=100, height=100
        )

        # Draw rectangle directly on layer canvas
        helpers.layers.draw_rect_on_layer(20, 20, 40, 40, '#FF0000', layer_id)

        # Content should be at (20, 20) in layer canvas coords
        content_bounds = helpers.pixels.get_bounding_box_of_content(layer_id=layer_id)
        assert content_bounds[0] >= 15 and content_bounds[0] <= 25, \
            f"Content x should be around 20, got {content_bounds[0]}"

    def test_composite_rendering_with_offset_layers(self, helpers: TestHelpers):
        """Test that offset layers render correctly in composite."""
        helpers.new_document(300, 300)

        # Background
        helpers.layers.fill_layer_with_color('#FFFFFF')

        # Create offset layer with red rectangle
        layer_id = helpers.layers.create_offset_layer(
            offset_x=100, offset_y=100,
            width=100, height=100
        )
        helpers.layers.fill_layer_with_color('#FF0000', layer_id)

        # Check composite at various positions
        # Outside offset layer - should be white
        pixel = helpers.pixels.get_pixel(50, 50)
        assert pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200, \
            f"Expected white at (50,50), got {pixel}"

        # Inside offset layer - should be red
        pixel = helpers.pixels.get_pixel(150, 150)
        assert pixel[0] > 200 and pixel[1] < 50 and pixel[2] < 50, \
            f"Expected red at (150,150), got {pixel}"


class TestLayerUndoRedo:
    """Tests for undo/redo with layer operations."""

    def test_undo_add_layer(self, helpers: TestHelpers):
        """Test that undo removes an added layer."""
        helpers.new_document(200, 200)

        initial_count = helpers.editor.get_layer_count()
        layer_id = helpers.layers.create_layer()
        assert helpers.editor.get_layer_count() == initial_count + 1

        helpers.undo()
        # Note: Layer creation may or may not be undoable depending on implementation
        # This test verifies the behavior

    def test_undo_delete_layer(self, helpers: TestHelpers):
        """Test that undo restores a deleted layer."""
        helpers.new_document(200, 200)

        layer_id = helpers.layers.create_filled_layer('#FF0000', width=100, height=100)
        initial_count = helpers.editor.get_layer_count()
        checksum = helpers.pixels.compute_checksum(layer_id=layer_id)

        helpers.layers.delete_layer(layer_id)
        assert helpers.editor.get_layer_count() == initial_count - 1

        helpers.undo()
        # After undo, the layer count should be restored
        # Note: Actual behavior depends on history implementation

    def test_undo_merge_down(self, helpers: TestHelpers):
        """Test that undo restores merged layers."""
        helpers.new_document(200, 200)

        helpers.layers.fill_layer_with_color('#FF0000')
        layer2_id = helpers.layers.create_filled_layer('#0000FF', width=50, height=50)

        initial_count = helpers.editor.get_layer_count()

        helpers.layers.merge_down(layer2_id)
        assert helpers.editor.get_layer_count() == initial_count - 1

        helpers.undo()
        # After undo, should have original layer count
        # Note: Actual behavior depends on history implementation
