"""Tests for fill and gradient tools - Playwright version.

Tests the Edit → Fill with FG/BG Color commands and the gradient tool,
including their interaction with selections.
"""

import pytest
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


class TestFillWithColor:
    """Tests for Edit → Fill with FG/BG Color commands."""

    async def test_fill_entire_layer_with_fg_color(self, helpers: TestHelpers):
        """Test filling entire layer when no selection is active."""
        await helpers.new_document(200, 200)

        # Set foreground color to red
        await helpers.editor.set_foreground_color('#FF0000')

        # Fill with FG color (no selection = fill entire layer)
        await helpers.editor.fill_with_fg_color()

        # Count red pixels - should be entire layer (200 * 200 = 40000)
        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        assert red_pixels >= 39000, \
            f"Expected ~40000 red pixels after fill, got {red_pixels}"

    async def test_fill_entire_layer_with_bg_color(self, helpers: TestHelpers):
        """Test filling entire layer with background color."""
        await helpers.new_document(200, 200)

        # Set background color to blue
        await helpers.editor.set_background_color('#0000FF')

        # Fill with BG color
        await helpers.editor.fill_with_bg_color()

        # Count blue pixels
        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)

        assert blue_pixels >= 39000, \
            f"Expected ~40000 blue pixels after fill, got {blue_pixels}"

    async def test_fill_selection_only(self, helpers: TestHelpers):
        """Test filling only within selection bounds."""
        await helpers.new_document(200, 200)

        # Make rectangular selection in center (50, 50) to (150, 150) = 100x100
        await helpers.selection.select_rect(50, 50, 100, 100)

        # Set foreground to green
        await helpers.editor.set_foreground_color('#00FF00')

        # Fill with FG color
        await helpers.editor.fill_with_fg_color()

        # Count green pixels - should be ~10000 (100x100 selection)
        green_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)

        # Allow some tolerance for selection edge handling
        assert 9000 <= green_pixels <= 11000, \
            f"Expected ~10000 green pixels in selection, got {green_pixels}"

        # Verify that only the selection area was filled (green count matches expected)
        # Note: canvas may have white background, so we check green pixel count, not total non-transparent
        assert green_pixels <= 11000, \
            f"Fill should not exceed selection area"

    async def test_fill_respects_lasso_selection(self, helpers: TestHelpers):
        """Test that fill respects non-rectangular (lasso) selection."""
        await helpers.new_document(200, 200)

        # Create lasso selection (triangle)
        await helpers.selection.lasso_select([
            (100, 50),   # Top
            (50, 150),   # Bottom left
            (150, 150),  # Bottom right
        ])

        # Set foreground to red
        await helpers.editor.set_foreground_color('#FF0000')

        # Fill
        await helpers.editor.fill_with_fg_color()

        # Count red pixels - triangle area is roughly half of 100x100 = ~5000
        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Triangle with base 100 and height 100 has area ~5000
        assert 3500 <= red_pixels <= 6500, \
            f"Expected ~5000 red pixels in triangle, got {red_pixels}"

    async def test_fill_undo_restores_original(self, helpers: TestHelpers):
        """Test that undo restores the state before fill."""
        await helpers.new_document(200, 200)

        # Get initial checksum (should be empty/white)
        initial_checksum = await helpers.pixels.compute_checksum()

        # Fill entire layer with red
        await helpers.editor.set_foreground_color('#FF0000')
        await helpers.editor.fill_with_fg_color()

        after_fill_checksum = await helpers.pixels.compute_checksum()
        assert initial_checksum != after_fill_checksum, "Fill should change pixels"

        # Undo
        await helpers.undo()

        after_undo_checksum = await helpers.pixels.compute_checksum()
        assert after_undo_checksum == initial_checksum, \
            "Undo should restore original state"


class TestFloodFillTool:
    """Tests for the flood fill (paint bucket) tool."""

    async def test_flood_fill_fills_contiguous_area(self, helpers: TestHelpers):
        """Test flood fill fills the entire same-color region when clicked."""
        await helpers.new_document(200, 200)

        # Canvas starts with white/transparent background
        # Flood fill the entire canvas with red from center
        await helpers.tools.fill_at(100, 100, color='#FF0000', tolerance=10)

        # Should fill the entire layer (200x200 = 40000 pixels)
        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Allow tolerance for edge handling
        assert red_pixels >= 35000, \
            f"Expected ~40000 red pixels from flood fill, got {red_pixels}"

    async def test_flood_fill_with_high_tolerance(self, helpers: TestHelpers):
        """Test flood fill with high tolerance fills more colors."""
        await helpers.new_document(200, 200)

        # Create gradient-like area with slightly different shades
        await helpers.tools.draw_filled_rect(0, 0, 100, 200, color='#808080')  # Gray
        await helpers.tools.draw_filled_rect(100, 0, 100, 200, color='#909090')  # Slightly lighter gray

        # Fill with low tolerance - should only fill clicked shade
        await helpers.tools.fill_at(50, 100, color='#FF0000', tolerance=5)
        red_after_low = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Undo and try again with high tolerance
        await helpers.undo()

        await helpers.tools.fill_at(50, 100, color='#FF0000', tolerance=50)
        red_after_high = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # High tolerance should fill more
        assert red_after_high >= red_after_low, \
            f"High tolerance should fill more. Low: {red_after_low}, High: {red_after_high}"

    async def test_flood_fill_respects_selection(self, helpers: TestHelpers):
        """Test flood fill is constrained by selection bounds."""
        await helpers.new_document(200, 200)

        # Make selection (50x50 starting at 50,50)
        await helpers.selection.select_rect(50, 50, 50, 50)

        # Flood fill within selection area - should only fill selection
        await helpers.tools.fill_at(75, 75, color='#FF0000', tolerance=100)

        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Should be ~2500 (50x50 selection)
        assert 2000 <= red_pixels <= 3000, \
            f"Flood fill should be constrained to selection, got {red_pixels} red pixels"


class TestGradientTool:
    """Tests for the gradient tool."""

    async def test_gradient_fills_entire_layer(self, helpers: TestHelpers):
        """Test gradient covers entire layer when no selection."""
        await helpers.new_document(200, 200)

        # Draw gradient from red to blue
        await helpers.tools.gradient_stroke(
            (0, 100), (200, 100),
            fg_color='#FF0000',
            bg_color='#0000FF'
        )

        # Should have non-transparent pixels across entire canvas
        non_transparent = await helpers.pixels.count_non_transparent_pixels()

        assert non_transparent >= 39000, \
            f"Expected ~40000 non-transparent pixels, got {non_transparent}"

    async def test_gradient_respects_selection(self, helpers: TestHelpers):
        """Test gradient is constrained to selection."""
        await helpers.new_document(200, 200)

        # Make selection
        await helpers.selection.select_rect(50, 50, 100, 100)

        # Draw gradient (red to blue)
        await helpers.tools.gradient_stroke(
            (50, 100), (150, 100),
            fg_color='#FF0000',
            bg_color='#0000FF'
        )

        # Count red-ish pixels (start of gradient) - should only be in selection
        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=80)
        # Count blue-ish pixels (end of gradient) - should only be in selection
        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=80)

        # Gradient should have some red and blue pixels within the selection
        # Combined should be significant portion of 10000 (100x100 selection)
        total_gradient = red_pixels + blue_pixels
        assert total_gradient >= 4000, \
            f"Gradient should fill selection with colors, got {red_pixels} red + {blue_pixels} blue = {total_gradient}"
        assert total_gradient <= 15000, \
            f"Gradient should be constrained to selection, got {total_gradient} gradient pixels"

    async def test_radial_gradient(self, helpers: TestHelpers):
        """Test radial gradient creates circular pattern."""
        await helpers.new_document(200, 200)

        # Draw radial gradient from center
        await helpers.tools.gradient_stroke(
            (100, 100), (100, 50),  # Center to edge (50px radius)
            fg_color='#FF0000',
            bg_color='#0000FF',
            gradient_type='radial'
        )

        # Center should be closer to red
        # We can't easily verify the exact pattern, but verify it drew something
        non_transparent = await helpers.pixels.count_non_transparent_pixels()
        assert non_transparent >= 39000, \
            f"Radial gradient should fill canvas, got {non_transparent} pixels"

    async def test_gradient_undo(self, helpers: TestHelpers):
        """Test gradient can be undone."""
        await helpers.new_document(200, 200)

        initial_checksum = await helpers.pixels.compute_checksum()

        await helpers.tools.gradient_stroke(
            (0, 100), (200, 100),
            fg_color='#FF0000',
            bg_color='#0000FF'
        )

        after_gradient = await helpers.pixels.compute_checksum()
        assert initial_checksum != after_gradient

        await helpers.undo()

        after_undo = await helpers.pixels.compute_checksum()
        assert after_undo == initial_checksum, \
            "Undo should restore state before gradient"


class TestLayerExpansionBehavior:
    """Tests for layer expansion behavior during fill operations.

    New layers start at 0x0 and grow dynamically:
    - Fill FG/BG expands layer to document bounds (or selection bounds)
    - Gradient expands layer to document bounds
    - Flood fill in transparent area expands, then shrinks to content
    - Flood fill in non-transparent area does NOT expand
    """

    async def test_new_layer_starts_empty(self, helpers: TestHelpers):
        """Verify that new layers start with 0x0 dimensions."""
        await helpers.new_document(200, 200)

        # Add a new empty layer
        layer_id = await helpers.editor.add_layer(name='Test Layer')
        await helpers.editor.select_layer(layer_id=layer_id)

        # Get layer dimensions
        dims = await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                return { width: layer?.width || 0, height: layer?.height || 0 };
            })()
        """)

        assert dims['width'] == 0 and dims['height'] == 0, \
            f"New layer should be 0x0, got {dims['width']}x{dims['height']}"

    async def test_fill_fg_expands_empty_layer_to_document(self, helpers: TestHelpers):
        """Fill FG on empty layer should expand it to document bounds."""
        await helpers.new_document(200, 200)

        # Add a new empty layer and select it
        layer_id = await helpers.editor.add_layer(name='Test Layer')
        await helpers.editor.select_layer(layer_id=layer_id)

        # Fill with FG color
        await helpers.editor.set_foreground_color('#FF0000')
        await helpers.editor.fill_with_fg_color()

        # Wait a bit for rendering
        import asyncio
        await asyncio.sleep(0.2)

        # Get layer dimensions and debug info
        debug = await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                // Check pixel colors in the layer
                let nonTransparent = 0;
                let redPixels = 0;
                let samplePixel = null;
                if (layer?.ctx && layer.width > 0 && layer.height > 0) {
                    const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        if (imageData.data[i + 3] > 0) {
                            nonTransparent++;
                            // Check for red (255, 0, 0)
                            if (imageData.data[i] > 200 && imageData.data[i + 1] < 50 && imageData.data[i + 2] < 50) {
                                redPixels++;
                            }
                        }
                    }
                    // Sample first pixel
                    samplePixel = [imageData.data[0], imageData.data[1], imageData.data[2], imageData.data[3]];
                }
                return {
                    width: layer?.width || 0,
                    height: layer?.height || 0,
                    name: layer?.name || 'unknown',
                    visible: layer?.visible ?? true,
                    opacity: layer?.opacity ?? 1,
                    layerNonTransparent: nonTransparent,
                    layerRedPixels: redPixels,
                    samplePixel: samplePixel,
                    fgColor: app?.foregroundColor || 'unknown',
                    totalLayers: app?.layerStack?.layers?.length || 0,
                    activeIndex: app?.layerStack?.activeLayerIndex ?? -1
                };
            })()
        """)

        assert debug['width'] == 200 and debug['height'] == 200, \
            f"Layer should expand to document size (200x200), got {debug['width']}x{debug['height']} - debug: {debug}"

        # Verify pixels were filled on the layer itself
        assert debug['layerNonTransparent'] >= 39000, \
            f"Expected ~40000 non-transparent pixels on layer, got {debug['layerNonTransparent']} - debug: {debug}"

        # Verify pixels in composite
        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        assert red_pixels >= 39000, f"Expected ~40000 red pixels in composite, got {red_pixels} - debug: {debug}"

    async def test_gradient_expands_empty_layer_to_document(self, helpers: TestHelpers):
        """Gradient on empty layer should expand it to document bounds."""
        await helpers.new_document(200, 200)

        # Add a new empty layer and select it
        layer_id = await helpers.editor.add_layer(name='Test Layer')
        await helpers.editor.select_layer(layer_id=layer_id)

        # Draw gradient
        await helpers.tools.gradient_stroke(
            (0, 100), (200, 100),
            fg_color='#FF0000',
            bg_color='#0000FF'
        )

        # Get layer dimensions - should now be document size
        dims = await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                return { width: layer?.width || 0, height: layer?.height || 0 };
            })()
        """)

        assert dims['width'] == 200 and dims['height'] == 200, \
            f"Layer should expand to document size after gradient, got {dims['width']}x{dims['height']}"

    async def test_flood_fill_empty_layer_expands_and_shrinks(self, helpers: TestHelpers):
        """Flood fill on empty layer expands to doc bounds then shrinks to content."""
        await helpers.new_document(200, 200)

        # Add a new empty layer and select it
        layer_id = await helpers.editor.add_layer(name='Test Layer')
        await helpers.editor.select_layer(layer_id=layer_id)

        # Flood fill at center - empty layer is all transparent
        await helpers.tools.fill_at(100, 100, color='#FF0000', tolerance=10)

        # Should fill entire document then trim to content (which is the whole fill)
        dims = await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                return { width: layer?.width || 0, height: layer?.height || 0 };
            })()
        """)

        # Layer should be document-sized (filled entire transparent area)
        assert dims['width'] == 200 and dims['height'] == 200, \
            f"Flood fill on empty layer should fill to document bounds, got {dims['width']}x{dims['height']}"

    async def test_flood_fill_enclosed_transparent_area_shrinks_to_content(self, helpers: TestHelpers):
        """Flood fill in enclosed transparent area should shrink layer to actual content."""
        await helpers.new_document(200, 200)

        # Draw a red frame (donut shape) leaving transparent center
        # Draw red everywhere first
        await helpers.editor.set_foreground_color('#FF0000')
        await helpers.editor.fill_with_fg_color()

        # Clear center to transparent using a brush or selection
        # Make selection in center and delete
        await helpers.selection.select_rect(50, 50, 100, 100)
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                if (layer?.ctx) {
                    layer.ctx.clearRect(50, 50, 100, 100);
                    layer.invalidateImageCache?.();
                }
                app?.renderer?.requestRender();
            })()
        """)
        await helpers.selection.deselect()

        # Now flood fill the transparent center with blue
        await helpers.tools.fill_at(100, 100, color='#0000FF', tolerance=10)

        # Count blue pixels - should be approximately 100x100 = 10000
        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)

        assert 9000 <= blue_pixels <= 11000, \
            f"Flood fill in enclosed area should fill ~10000 pixels, got {blue_pixels}"

    async def test_flood_fill_opaque_area_does_not_expand_layer(self, helpers: TestHelpers):
        """Flood fill starting in opaque area should not expand layer bounds."""
        await helpers.new_document(200, 200)

        # Draw a small rect in the corner (layer will be sized to content)
        await helpers.tools.draw_filled_rect(10, 10, 50, 50, color='#808080')

        # Get layer dimensions before flood fill
        dims_before = await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                return {
                    width: layer?.width || 0,
                    height: layer?.height || 0,
                    offsetX: layer?.offsetX || 0,
                    offsetY: layer?.offsetY || 0
                };
            })()
        """)

        # Flood fill inside the gray rect (opaque area)
        await helpers.tools.fill_at(35, 35, color='#FF0000', tolerance=10)

        # Get layer dimensions after flood fill
        dims_after = await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getActiveLayer();
                return {
                    width: layer?.width || 0,
                    height: layer?.height || 0,
                    offsetX: layer?.offsetX || 0,
                    offsetY: layer?.offsetY || 0
                };
            })()
        """)

        # Layer should NOT have expanded - same dimensions
        assert dims_before['width'] == dims_after['width'], \
            f"Layer width should not change: was {dims_before['width']}, now {dims_after['width']}"
        assert dims_before['height'] == dims_after['height'], \
            f"Layer height should not change: was {dims_before['height']}, now {dims_after['height']}"

    async def test_flood_fill_outer_transparent_border_expands_then_shrinks(self, helpers: TestHelpers):
        """Flood fill in outer transparent border expands layer then shrinks to content."""
        await helpers.new_document(200, 200)

        # Draw a small shape in the center - transparent around edges
        await helpers.tools.draw_filled_rect(80, 80, 40, 40, color='#808080')

        # Flood fill the outer transparent area (click in corner)
        await helpers.tools.fill_at(10, 10, color='#0000FF', tolerance=10)

        # The blue fill should cover everything except the gray rect
        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)
        gray_pixels = await helpers.pixels.count_pixels_with_color((128, 128, 128, 255), tolerance=10)

        # Expected: 200*200 - 40*40 = 40000 - 1600 = 38400 blue pixels
        assert blue_pixels >= 35000, \
            f"Flood fill should cover outer area (~38400 pixels), got {blue_pixels}"

        # Gray rect should still exist
        assert gray_pixels >= 1400, \
            f"Gray rect should still exist (~1600 pixels), got {gray_pixels}"
