"""Tests for change tracking feature - Playwright browser tests.

Tests the change tracking behavior in JavaScript (layer/document change tracking)
and the /changes API endpoint integration.
"""

import pytest
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


class TestLayerChangeTrackingJS:
    """Tests for layer change tracking in JavaScript."""

    async def test_layer_has_change_tracking_properties(self, helpers: TestHelpers):
        """Layer objects should have changeCounter and lastChangeTimestamp."""
        await helpers.new_document(200, 200)

        # Get layer info via API
        layer_info = await helpers.editor.get_layer_info(index=0)

        # Check change tracking fields exist
        assert 'changeCounter' in layer_info, "Layer should have changeCounter property"
        assert 'lastChangeTimestamp' in layer_info, "Layer should have lastChangeTimestamp property"

    async def test_layer_change_counter_starts_at_zero(self, helpers: TestHelpers):
        """Newly created layer should have changeCounter starting at 0."""
        await helpers.new_document(200, 200)

        # Create a fresh layer (not the background which may have been modified during init)
        new_layer_id = await helpers.layers.create_layer(name="Fresh Layer")

        layer_info = await helpers.editor.get_layer_info(layer_id=new_layer_id)
        assert layer_info['changeCounter'] == 0, "Initial changeCounter should be 0"

    async def test_layer_change_counter_increments_on_draw(self, helpers: TestHelpers):
        """Drawing on a layer should increment its changeCounter."""
        await helpers.new_document(200, 200)

        # Get initial change counter
        initial_info = await helpers.editor.get_layer_info(index=0)
        initial_counter = initial_info['changeCounter']

        # Draw something
        await helpers.tools.brush_stroke([(50, 50), (150, 150)], color='#FF0000', size=10)
        await helpers.wait_for_render()

        # Get updated change counter
        updated_info = await helpers.editor.get_layer_info(index=0)
        updated_counter = updated_info['changeCounter']

        assert updated_counter > initial_counter, \
            f"changeCounter should increase after drawing: {initial_counter} -> {updated_counter}"

    async def test_layer_timestamp_updates_on_change(self, helpers: TestHelpers):
        """Drawing on a layer should update its lastChangeTimestamp."""
        await helpers.new_document(200, 200)

        # Get initial timestamp
        initial_info = await helpers.editor.get_layer_info(index=0)
        initial_timestamp = initial_info['lastChangeTimestamp']

        # Small delay to ensure timestamp changes
        await helpers.editor.page.wait_for_timeout(100)

        # Draw something
        await helpers.tools.brush_stroke([(50, 50), (150, 150)], color='#FF0000', size=10)
        await helpers.wait_for_render()

        # Get updated timestamp
        updated_info = await helpers.editor.get_layer_info(index=0)
        updated_timestamp = updated_info['lastChangeTimestamp']

        assert updated_timestamp > initial_timestamp, \
            f"lastChangeTimestamp should increase after drawing: {initial_timestamp} -> {updated_timestamp}"

    async def test_multiple_strokes_increment_counter(self, helpers: TestHelpers):
        """Multiple brush strokes should increment the changeCounter multiple times."""
        await helpers.new_document(200, 200)

        # Get initial change counter
        initial_info = await helpers.editor.get_layer_info(index=0)
        initial_counter = initial_info['changeCounter']

        # Draw multiple strokes
        await helpers.tools.brush_stroke([(50, 50), (100, 100)], color='#FF0000', size=10)
        await helpers.wait_for_render()
        await helpers.tools.brush_stroke([(100, 100), (150, 150)], color='#00FF00', size=10)
        await helpers.wait_for_render()

        # Get updated change counter
        updated_info = await helpers.editor.get_layer_info(index=0)
        updated_counter = updated_info['changeCounter']

        # Counter should have increased by at least 2 (one per stroke)
        increase = updated_counter - initial_counter
        assert increase >= 2, \
            f"changeCounter should increase with each stroke: {initial_counter} -> {updated_counter} (increase={increase})"


