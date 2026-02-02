"""Test vector layer bounds optimization.

Verifies that vector layers are sized to fit their content's bounding box,
not the full document size.

Uses the Screen fixture (Playwright-based, NiceGUI Screen API compatible).

Run with: poetry run pytest tests/test_vector_layer_bounds.py -v

NOTE: VectorLayer class was removed in commit e703dab during layer hierarchy refactoring.
These tests need to be rewritten to use the new SVGBaseLayer/StaticSVGLayer architecture.
"""

import pytest

# Skip entire module - VectorLayer class no longer exists
pytest.skip(
    "VectorLayer class was removed - tests need rewriting for SVGBaseLayer architecture",
    allow_module_level=True
)


class TestVectorLayerBounds:
    """Test that vector layers are properly sized to their content bounds."""

    def test_small_circle_creates_bounded_layer(self, screen):
        """A small circle should create a vector layer sized to its bounds, not full document."""
        screen.open('/')
        screen.wait_for_editor()

        # Create a small circle via the VectorLayer API
        # Circle at position (100, 100) with radius 50 -> bounds ~100x100
        layer_info = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                if (!app) return {error: 'App not available'};

                // Get VectorLayer class from window
                const VectorLayer = window.VectorLayer;
                if (!VectorLayer) {
                    return {error: 'VectorLayer not available'};
                }

                // Create vector layer with a small circle
                const layer = new VectorLayer({
                    name: 'Test Circle',
                    width: app.layerStack.width,
                    height: app.layerStack.height
                });

                // Add an ellipse shape (circle)
                const shape = window.createVectorShape({
                    type: 'ellipse',
                    cx: 100, cy: 100,
                    rx: 50, ry: 50,
                    fill: true,
                    stroke: true,
                    fillColor: '#FF0000',
                    strokeColor: '#000000',
                    strokeWidth: 2,
                    opacity: 1.0
                });

                if (shape) {
                    layer.addShape(shape);
                }

                // Add to layer stack
                app.layerStack.addLayer(layer);

                // Get the computed bounds
                const bounds = layer.getShapesBounds?.();

                // Return layer dimensions
                return {
                    id: layer.id,
                    name: layer.name,
                    width: layer.width,
                    height: layer.height,
                    offsetX: layer.offsetX,
                    offsetY: layer.offsetY,
                    shapeCount: layer.shapes?.length || 0,
                    docWidth: app.layerStack.width,
                    docHeight: app.layerStack.height,
                    boundsX: bounds?.x,
                    boundsY: bounds?.y,
                    boundsWidth: bounds?.width,
                    boundsHeight: bounds?.height
                };
            }
        """)

        # Verify the layer was created
        assert layer_info is not None, "Failed to create vector layer"
        assert 'error' not in layer_info, f"Error creating layer: {layer_info.get('error')}"
        assert layer_info['shapeCount'] == 1, "Expected 1 shape in layer"

        doc_width = layer_info['docWidth']
        doc_height = layer_info['docHeight']

        print(f"Document size: {doc_width}x{doc_height}")
        print(f"Layer info: {layer_info}")

        # The shape bounds should be much smaller than full document
        # Circle at (100,100) with radius 50 + stroke 2 = bounds roughly (48,48) to (152,152)
        if layer_info.get('boundsWidth'):
            assert layer_info['boundsWidth'] < doc_width / 2, \
                f"Expected bounds width < {doc_width/2}, got {layer_info['boundsWidth']}"
            assert layer_info['boundsHeight'] < doc_height / 2, \
                f"Expected bounds height < {doc_height/2}, got {layer_info['boundsHeight']}"

            # Expected bounds: ~104x104 (100 diameter + 2*2 stroke)
            expected_size = 100 + 4  # diameter + stroke padding
            assert 80 <= layer_info['boundsWidth'] <= 150, \
                f"Expected bounds width ~{expected_size}, got {layer_info['boundsWidth']}"
            assert 80 <= layer_info['boundsHeight'] <= 150, \
                f"Expected bounds height ~{expected_size}, got {layer_info['boundsHeight']}"

    def test_vector_layer_getShapesBounds(self, screen):
        """Test that getShapesBounds() returns correct bounding box."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                if (!app) return {error: 'App not available'};

                const VectorLayer = window.VectorLayer;
                if (!VectorLayer) return {error: 'VectorLayer not available'};

                // Create vector layer with a rect at known position
                const layer = new VectorLayer({
                    name: 'Bounds Test Rect',
                    width: 800,
                    height: 600
                });

                // Add a rect at (50, 60) with size 120x80
                const rect = window.createVectorShape({
                    type: 'rect',
                    x: 50, y: 60,
                    width: 120, height: 80,
                    fill: true,
                    stroke: true,
                    fillColor: '#00FF00',
                    strokeColor: '#000000',
                    strokeWidth: 4,
                    opacity: 1.0
                });

                if (rect) layer.addShape(rect);

                // Get bounds - should be ~(48, 58) to (172, 142) with stroke
                const bounds = layer.getShapesBounds();

                return {
                    hasMethod: typeof layer.getShapesBounds === 'function',
                    bounds: bounds,
                    expectedX: 50 - 2,  // x - stroke/2
                    expectedY: 60 - 2,
                    expectedWidth: 120 + 4,  // width + stroke
                    expectedHeight: 80 + 4
                };
            }
        """)

        assert result is not None
        assert 'error' not in result, f"Error: {result.get('error')}"
        assert result['hasMethod'], "VectorLayer missing getShapesBounds() method"

        bounds = result['bounds']
        assert bounds is not None, "getShapesBounds() returned None"

        # Check bounds are approximately correct (with stroke padding)
        print(f"Bounds: {bounds}")
        print(f"Expected: x={result['expectedX']}, y={result['expectedY']}, "
              f"w={result['expectedWidth']}, h={result['expectedHeight']}")

        # Allow some tolerance for stroke calculations
        assert 40 <= bounds['x'] <= 55, f"Expected x ~48, got {bounds['x']}"
        assert 50 <= bounds['y'] <= 65, f"Expected y ~58, got {bounds['y']}"
        assert 110 <= bounds['width'] <= 140, f"Expected width ~124, got {bounds['width']}"
        assert 70 <= bounds['height'] <= 100, f"Expected height ~84, got {bounds['height']}"

    def test_layer_state_includes_dimensions(self, screen):
        """Test vector layer dimensions are available in layer stack."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                if (!app) return {error: 'App not available'};

                const VectorLayer = window.VectorLayer;
                if (!VectorLayer) return {error: 'VectorLayer not available'};

                // Create vector layer
                const layer = new VectorLayer({
                    name: 'State Test',
                    width: 800,
                    height: 600
                });

                // Add a shape
                const ellipse = window.createVectorShape({
                    type: 'ellipse',
                    cx: 200, cy: 150,
                    rx: 30, ry: 20,
                    fill: true,
                    fillColor: '#0000FF',
                    opacity: 1.0
                });
                if (ellipse) layer.addShape(ellipse);

                app.layerStack.addLayer(layer);

                // Get layer from layer stack
                const stackLayer = app.layerStack.layers.find(l => l.name === 'State Test');

                return {
                    layerId: layer.id,
                    jsWidth: layer.width,
                    jsHeight: layer.height,
                    stackLayerFound: !!stackLayer,
                    stackLayerType: stackLayer?.isVector?.() ? 'vector' : 'raster',
                    stackLayerWidth: stackLayer?.width,
                    stackLayerHeight: stackLayer?.height,
                    allLayers: app.layerStack.layers.map(l => ({
                        id: l.id,
                        name: l.name,
                        type: l.isVector?.() ? 'vector' : (l.isText?.() ? 'text' : 'raster'),
                        width: l.width,
                        height: l.height
                    }))
                };
            }
        """)

        assert result is not None
        assert 'error' not in result, f"Error: {result.get('error')}"

        print(f"JS layer: width={result['jsWidth']}, height={result['jsHeight']}")
        print(f"All layers: {result['allLayers']}")

        # Verify the layer appears in layer stack
        assert result['stackLayerFound'], f"Layer not found in stack: {result['allLayers']}"

        # Check type is vector
        assert result['stackLayerType'] == 'vector', \
            f"Expected vector layer type, got: {result['stackLayerType']}"

        # Check dimensions are present
        assert result['stackLayerWidth'] is not None, "Layer missing 'width'"
        assert result['stackLayerHeight'] is not None, "Layer missing 'height'"
        assert result['stackLayerWidth'] > 0, f"Invalid width: {result['stackLayerWidth']}"
        assert result['stackLayerHeight'] > 0, f"Invalid height: {result['stackLayerHeight']}"

    def test_svg_bounds_optimization_renders_small_area(self, screen):
        """Verify SVG rendering only renders the bounding box, not full document.

        This is the key test for SVG bounds optimization:
        - Create 800x600 document
        - Add 100x100 circle
        - Verify rendered SVG area is ~100x100, not 800x600
        """
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                if (!app) return {error: 'App not available'};

                const VectorLayer = window.VectorLayer;
                if (!VectorLayer) return {error: 'VectorLayer not available'};

                // Get document size
                const docWidth = app.layerStack.width;
                const docHeight = app.layerStack.height;

                // Create vector layer at full document size
                const layer = new VectorLayer({
                    name: 'SVG Bounds Test',
                    width: docWidth,
                    height: docHeight
                });

                // Add a small circle at (100, 100) with radius 50
                // Expected bounds: ~(50, 50) to (150, 150) = 100x100
                const circle = window.createVectorShape({
                    type: 'ellipse',
                    cx: 100, cy: 100,
                    rx: 50, ry: 50,
                    fill: true,
                    fillColor: '#FF0000',
                    stroke: true,
                    strokeColor: '#000000',
                    strokeWidth: 2,
                    opacity: 1.0
                });

                layer.addShape(circle);
                app.layerStack.addLayer(layer);

                // Get computed bounds
                const bounds = layer.getShapesBounds();

                // Force SVG render and wait for it
                await layer.renderViaSVG({ supersample: 1 });

                // Calculate sizes
                const fullArea = docWidth * docHeight;
                const boundsArea = bounds.width * bounds.height;
                const optimizationRatio = boundsArea / fullArea;

                return {
                    docWidth,
                    docHeight,
                    layerWidth: layer.width,
                    layerHeight: layer.height,
                    boundsX: bounds.x,
                    boundsY: bounds.y,
                    boundsWidth: bounds.width,
                    boundsHeight: bounds.height,
                    fullArea,
                    boundsArea,
                    optimizationRatio,
                    savingsPercent: ((1 - optimizationRatio) * 100).toFixed(1)
                };
            }
        """)

        assert result is not None
        assert 'error' not in result, f"Error: {result.get('error')}"

        print(f"Document: {result['docWidth']}x{result['docHeight']} = {result['fullArea']} px")
        print(f"Bounds: {result['boundsWidth']}x{result['boundsHeight']} = {result['boundsArea']} px")
        print(f"Optimization: {result['savingsPercent']}% smaller SVG render")

        # The bounds should be much smaller than the full document
        # Circle at (100,100) r=50 + stroke 2 = bounds roughly (48,48) to (152,152)
        # That's about 104x104 = 10,816 pixels vs 800x600 = 480,000 pixels
        assert result['boundsWidth'] < result['docWidth'] / 4, \
            f"Bounds width {result['boundsWidth']} should be much smaller than doc width {result['docWidth']}"
        assert result['boundsHeight'] < result['docHeight'] / 4, \
            f"Bounds height {result['boundsHeight']} should be much smaller than doc height {result['docHeight']}"

        # Optimization ratio should be < 10% (we're rendering <10% of the pixels)
        assert result['optimizationRatio'] < 0.10, \
            f"Expected <10% of full area, got {result['optimizationRatio']*100:.1f}%"

        # Bounds should be approximately 100x100 (diameter + stroke)
        assert 80 <= result['boundsWidth'] <= 150, \
            f"Expected bounds width ~104, got {result['boundsWidth']}"
        assert 80 <= result['boundsHeight'] <= 150, \
            f"Expected bounds height ~104, got {result['boundsHeight']}"
