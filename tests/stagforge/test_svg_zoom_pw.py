"""Tests for SVG layer zoom-aware rendering - Playwright version.

This test verifies that SVG layers render at appropriate resolution
when zoomed in beyond 100%, ensuring crisp display.
"""

import asyncio
import pytest
import numpy as np
from pathlib import Path
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


# Path to the Noto emoji deer SVG
DEER_SVG_PATH = Path(__file__).parent.parent.parent / "imagestag" / "samples" / "svgs" / "noto-emoji" / "deer.svg"


class TestSVGLayerZoomRendering:
    """Tests for SVG layer zoom-aware rendering."""

    async def test_svg_layer_creation(self, helpers: TestHelpers):
        """Test that we can create an SVG layer with deer emoji."""
        # Create 500x500 document with white background
        await helpers.new_document(500, 500)

        # Fill background using direct app access
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                if (!app || !app.layerStack) return;
                const layer = app.layerStack.getActiveLayer();
                if (layer && layer.ctx) {
                    layer.ctx.fillStyle = '#FFFFFF';
                    layer.ctx.fillRect(0, 0, layer.width, layer.height);
                    app.renderer?.requestRender();
                }
            })()
        """)

        # Read the deer SVG content
        svg_content = DEER_SVG_PATH.read_text()

        # Create SVG layer
        layer_id = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;
                if (!SVGLayer) {{
                    console.error('SVGLayer not found on window');
                    return null;
                }}

                const svgContent = {repr(svg_content)};

                const layer = new SVGLayer({{
                    name: 'Deer SVG',
                    width: 300,
                    height: 300,
                    svgContent: svgContent,
                }});

                // Position in center
                layer.offsetX = 100;
                layer.offsetY = 100;

                app.layerStack.addLayer(layer);
                return layer.id;
            }})()
        """)

        assert layer_id is not None, "Failed to create SVG layer - SVGLayer class not found"

        # Wait for SVG to render
        await asyncio.sleep(0.5)

        # Verify layer was created using direct app access
        layer_info = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app?.layerStack?.getLayerById('{layer_id}');
                if (!layer) return null;
                return {{
                    id: layer.id,
                    name: layer.name,
                    width: layer.width,
                    height: layer.height,
                    offsetX: layer.offsetX,
                    offsetY: layer.offsetY,
                    type: layer.type
                }};
            }})()
        """)
        assert layer_info is not None, "Layer not found after creation"
        assert layer_info['width'] == 300
        assert layer_info['height'] == 300

    async def test_svg_layer_zoom_triggers_rerender(self, helpers: TestHelpers):
        """Test that zooming triggers SVG re-render at higher resolution."""
        # Create 500x500 document with white background
        await helpers.new_document(500, 500)

        # Read the deer SVG content
        svg_content = DEER_SVG_PATH.read_text()

        # Create SVG layer at 300x300
        layer_id = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;
                if (!SVGLayer) return null;

                const svgContent = {repr(svg_content)};

                const layer = new SVGLayer({{
                    name: 'Deer SVG',
                    width: 300,
                    height: 300,
                    svgContent: svgContent,
                }});

                layer.offsetX = 100;
                layer.offsetY = 100;

                app.layerStack.addLayer(layer);
                return layer.id;
            }})()
        """)

        assert layer_id is not None, "Failed to create SVG layer"

        # Wait for initial render
        await asyncio.sleep(0.5)

        # Get initial render state
        initial_state = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                if (!layer) return null;
                return {{
                    displayScale: layer._displayScale,
                    lastRenderedScale: layer._lastRenderedScale,
                    zoom: app.renderer.zoom
                }};
            }})()
        """)

        assert initial_state is not None
        initial_rendered_scale = initial_state['lastRenderedScale']
        print(f"Initial state: zoom={initial_state['zoom']}, displayScale={initial_state['displayScale']}, lastRenderedScale={initial_rendered_scale}")

        # Zoom to 250%
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                // Use zoomAt to zoom to 250% centered on document
                const centerX = app.renderer.displayWidth / 2;
                const centerY = app.renderer.displayHeight / 2;

                // Calculate factor to get to 250% from current zoom
                const targetZoom = 2.5;
                const factor = targetZoom / app.renderer.zoom;
                app.renderer.zoomAt(factor, centerX, centerY);
            })()
        """)

        # Wait for re-render
        await asyncio.sleep(0.5)

        # Check that display scale was updated
        zoomed_state = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                if (!layer) return null;
                return {{
                    displayScale: layer._displayScale,
                    lastRenderedScale: layer._lastRenderedScale,
                    zoom: app.renderer.zoom
                }};
            }})()
        """)

        assert zoomed_state is not None
        print(f"Zoomed state: zoom={zoomed_state['zoom']}, displayScale={zoomed_state['displayScale']}, lastRenderedScale={zoomed_state['lastRenderedScale']}")

        assert zoomed_state['zoom'] == pytest.approx(2.5, rel=0.1), \
            f"Expected zoom ~2.5, got {zoomed_state['zoom']}"
        assert zoomed_state['displayScale'] >= 2.0, \
            f"Expected displayScale >= 2.0 at 250% zoom, got {zoomed_state['displayScale']}"

        # The layer should have re-rendered at higher scale
        # (lastRenderedScale should be >= 2.0 since we zoomed to 250%)
        assert zoomed_state['lastRenderedScale'] >= 2.0, \
            f"Expected lastRenderedScale >= 2.0, got {zoomed_state['lastRenderedScale']}"

    async def test_svg_layer_has_display_scale_method(self, helpers: TestHelpers):
        """Test that SVG layer has setDisplayScale method."""
        await helpers.new_document(500, 500)

        svg_content = DEER_SVG_PATH.read_text()

        # Create SVG layer and check for setDisplayScale method
        result = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;
                if (!SVGLayer) return {{ error: 'SVGLayer not found' }};

                const svgContent = {repr(svg_content)};

                const layer = new SVGLayer({{
                    name: 'Deer SVG',
                    width: 300,
                    height: 300,
                    svgContent: svgContent,
                }});

                app.layerStack.addLayer(layer);

                return {{
                    hasSetDisplayScale: typeof layer.setDisplayScale === 'function',
                    hasDisplayScale: '_displayScale' in layer,
                    hasLastRenderedScale: '_lastRenderedScale' in layer,
                    displayScale: layer._displayScale,
                    lastRenderedScale: layer._lastRenderedScale
                }};
            }})()
        """)

        assert result is not None, "Failed to create layer"
        assert 'error' not in result, f"Error: {result.get('error')}"
        assert result['hasSetDisplayScale'], "SVGLayer should have setDisplayScale method"
        assert result['hasDisplayScale'], "SVGLayer should have _displayScale property"
        assert result['hasLastRenderedScale'], "SVGLayer should have _lastRenderedScale property"

    async def test_zoom_updates_svg_layer_display_scale(self, helpers: TestHelpers):
        """Test that zooming updates display scale on SVG layers."""
        await helpers.new_document(500, 500)

        svg_content = DEER_SVG_PATH.read_text()

        # Create SVG layer
        layer_id = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;

                const layer = new SVGLayer({{
                    name: 'Deer SVG',
                    width: 300,
                    height: 300,
                    svgContent: {repr(svg_content)},
                }});

                layer.offsetX = 100;
                layer.offsetY = 100;
                app.layerStack.addLayer(layer);
                return layer.id;
            }})()
        """)

        assert layer_id is not None

        # Wait for initial render
        await asyncio.sleep(0.3)

        # Get initial scale
        initial_scale = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                return layer?._displayScale || 1.0;
            }})()
        """)

        # Zoom to 300%
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const centerX = app.renderer.displayWidth / 2;
                const centerY = app.renderer.displayHeight / 2;
                const targetZoom = 3.0;
                const factor = targetZoom / app.renderer.zoom;
                app.renderer.zoomAt(factor, centerX, centerY);
            })()
        """)

        await asyncio.sleep(0.3)

        # Get scale after zoom
        zoomed_scale = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                return layer?._displayScale || 1.0;
            }})()
        """)

        print(f"Initial scale: {initial_scale}, Zoomed scale: {zoomed_scale}")

        # Scale should have increased after zooming in
        assert zoomed_scale >= 2.5, \
            f"Expected display scale >= 2.5 at 300% zoom, got {zoomed_scale}"

    async def test_svg_layer_zoom_400_percent(self, helpers: TestHelpers):
        """Test that SVG layer renders correctly at 400% zoom - deer should not disappear."""
        await helpers.new_document(500, 500)

        svg_content = DEER_SVG_PATH.read_text()

        # Create SVG layer
        layer_id = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;

                const layer = new SVGLayer({{
                    name: 'Deer SVG',
                    width: 300,
                    height: 300,
                    svgContent: {repr(svg_content)},
                }});

                layer.offsetX = 100;
                layer.offsetY = 100;
                app.layerStack.addLayer(layer);
                return layer.id;
            }})()
        """)

        assert layer_id is not None

        # Wait for initial render
        await asyncio.sleep(0.5)

        # Get initial content - count non-transparent pixels
        initial_content = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                if (!layer) return null;

                // SVGLayer uses _ctx for internal rendering
                const ctx = layer._ctx || layer.ctx;
                if (!ctx) return {{ error: 'No canvas context' }};

                const imageData = ctx.getImageData(0, 0, layer.width, layer.height);
                let nonTransparent = 0;
                for (let i = 3; i < imageData.data.length; i += 4) {{
                    if (imageData.data[i] > 0) nonTransparent++;
                }}
                return {{
                    width: layer.width,
                    height: layer.height,
                    nonTransparentPixels: nonTransparent,
                    displayScale: layer._displayScale,
                    lastRenderedScale: layer._lastRenderedScale
                }};
            }})()
        """)

        assert initial_content is not None
        print(f"Initial: {initial_content['nonTransparentPixels']} non-transparent pixels, scale={initial_content['displayScale']}")
        assert initial_content['nonTransparentPixels'] > 1000, \
            f"Expected deer content initially, got {initial_content['nonTransparentPixels']} pixels"

        # Zoom to 400%
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const centerX = app.renderer.displayWidth / 2;
                const centerY = app.renderer.displayHeight / 2;
                const targetZoom = 4.0;
                const factor = targetZoom / app.renderer.zoom;
                app.renderer.zoomAt(factor, centerX, centerY);
            })()
        """)

        # Wait for re-render
        await asyncio.sleep(1.0)  # Longer wait for high-res render

        # Get content at 400% zoom
        zoomed_content = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                if (!layer) return null;

                // SVGLayer uses _ctx for internal rendering
                const ctx = layer._ctx || layer.ctx;
                if (!ctx) return {{ error: 'No canvas context' }};

                const imageData = ctx.getImageData(0, 0, layer.width, layer.height);
                let nonTransparent = 0;
                for (let i = 3; i < imageData.data.length; i += 4) {{
                    if (imageData.data[i] > 0) nonTransparent++;
                }}
                return {{
                    width: layer.width,
                    height: layer.height,
                    nonTransparentPixels: nonTransparent,
                    displayScale: layer._displayScale,
                    lastRenderedScale: layer._lastRenderedScale,
                    zoom: app.renderer.zoom
                }};
            }})()
        """)

        assert zoomed_content is not None
        print(f"At 400%: {zoomed_content['nonTransparentPixels']} non-transparent pixels, scale={zoomed_content['displayScale']}, lastRendered={zoomed_content['lastRenderedScale']}")

        # CRITICAL: Deer should NOT disappear at 400% zoom
        assert zoomed_content['nonTransparentPixels'] > 1000, \
            f"DEER DISAPPEARED at 400% zoom! Only {zoomed_content['nonTransparentPixels']} pixels visible"

        # Display scale should be updated
        assert zoomed_content['displayScale'] >= 3.5, \
            f"Expected displayScale >= 3.5 at 400% zoom, got {zoomed_content['displayScale']}"

    async def test_svg_layer_zoom_1000_percent(self, helpers: TestHelpers):
        """Test that SVG layer renders correctly at 1000% zoom with 16MP limit."""
        await helpers.new_document(500, 500)

        svg_content = DEER_SVG_PATH.read_text()

        # Create SVG layer at 300x300 (300*300 = 90,000 pixels)
        # At 10x, this would be 3000x3000 = 9MP, which is under 16MP limit
        layer_id = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;

                const layer = new SVGLayer({{
                    name: 'Deer SVG',
                    width: 300,
                    height: 300,
                    svgContent: {repr(svg_content)},
                }});

                layer.offsetX = 100;
                layer.offsetY = 100;
                app.layerStack.addLayer(layer);
                return layer.id;
            }})()
        """)

        assert layer_id is not None

        # Wait for initial render
        await asyncio.sleep(0.5)

        # Zoom to 1000%
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const centerX = app.renderer.displayWidth / 2;
                const centerY = app.renderer.displayHeight / 2;
                const targetZoom = 10.0;
                const factor = targetZoom / app.renderer.zoom;
                app.renderer.zoomAt(factor, centerX, centerY);
            })()
        """)

        # Wait for re-render
        await asyncio.sleep(1.0)

        # Check that render scale matches zoom (10x is under 16MP limit for 300x300)
        zoomed_state = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                if (!layer) return null;

                const displayCanvas = layer.getDisplayCanvas();
                return {{
                    displayScale: layer._displayScale,
                    renderScale: layer.getRenderScale(),
                    zoom: app.renderer.zoom,
                    displayCanvasWidth: displayCanvas?.width || 0,
                    displayCanvasHeight: displayCanvas?.height || 0,
                    layerWidth: layer.width,
                    layerHeight: layer.height
                }};
            }})()
        """)

        assert zoomed_state is not None
        print(f"At 1000%: zoom={zoomed_state['zoom']}, renderScale={zoomed_state['renderScale']}, "
              f"displayCanvas={zoomed_state['displayCanvasWidth']}x{zoomed_state['displayCanvasHeight']}")

        # At 1000% zoom on a 300x300 layer, render scale should be 10
        # (300*10)^2 = 9MP which is under 16MP
        assert zoomed_state['renderScale'] == 10, \
            f"Expected renderScale=10 at 1000% zoom for 300x300 layer, got {zoomed_state['renderScale']}"

        # Display canvas should be 10x the layer size
        assert zoomed_state['displayCanvasWidth'] == 3000, \
            f"Expected display canvas width=3000, got {zoomed_state['displayCanvasWidth']}"
        assert zoomed_state['displayCanvasHeight'] == 3000, \
            f"Expected display canvas height=3000, got {zoomed_state['displayCanvasHeight']}"

    async def test_svg_layer_16mp_limit(self, helpers: TestHelpers):
        """Test that render scale is limited to keep display canvas under 16MP."""
        await helpers.new_document(2000, 2000)

        svg_content = DEER_SVG_PATH.read_text()

        # Create a larger SVG layer at 1000x1000 (1MP)
        # At 10x, this would be 10000x10000 = 100MP, which exceeds 16MP
        # So it should be capped at sqrt(16MP/1MP) = 4x
        layer_id = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const SVGLayer = window.SVGLayer;

                const layer = new SVGLayer({{
                    name: 'Large SVG',
                    width: 1000,
                    height: 1000,
                    svgContent: {repr(svg_content)},
                }});

                layer.offsetX = 500;
                layer.offsetY = 500;
                app.layerStack.addLayer(layer);
                return layer.id;
            }})()
        """)

        assert layer_id is not None

        # Wait for initial render
        await asyncio.sleep(0.5)

        # Zoom to 1000%
        await helpers.editor.execute_js("""
            (() => {
                const app = window.__stagforge_app__;
                const centerX = app.renderer.displayWidth / 2;
                const centerY = app.renderer.displayHeight / 2;
                const targetZoom = 10.0;
                const factor = targetZoom / app.renderer.zoom;
                app.renderer.zoomAt(factor, centerX, centerY);
            })()
        """)

        # Wait for re-render
        await asyncio.sleep(1.0)

        # Check that render scale is capped due to 16MP limit
        zoomed_state = await helpers.editor.execute_js(f"""
            (() => {{
                const app = window.__stagforge_app__;
                const layer = app.layerStack.getLayerById('{layer_id}');
                if (!layer) return null;

                const displayCanvas = layer.getDisplayCanvas();
                const pixels = displayCanvas ? displayCanvas.width * displayCanvas.height : 0;
                return {{
                    displayScale: layer._displayScale,
                    renderScale: layer.getRenderScale(),
                    zoom: app.renderer.zoom,
                    displayCanvasWidth: displayCanvas?.width || 0,
                    displayCanvasHeight: displayCanvas?.height || 0,
                    displayCanvasPixels: pixels,
                    layerWidth: layer.width,
                    layerHeight: layer.height
                }};
            }})()
        """)

        assert zoomed_state is not None
        print(f"At 1000% with 1000x1000 layer: renderScale={zoomed_state['renderScale']}, "
              f"displayCanvas={zoomed_state['displayCanvasWidth']}x{zoomed_state['displayCanvasHeight']} "
              f"({zoomed_state['displayCanvasPixels']/1e6:.1f}MP)")

        # Render scale should be capped at 4 (sqrt(16MP/1MP) = 4)
        assert zoomed_state['renderScale'] == 4, \
            f"Expected renderScale=4 (16MP limit), got {zoomed_state['renderScale']}"

        # Display canvas should be under 16MP
        assert zoomed_state['displayCanvasPixels'] <= 16_000_000, \
            f"Display canvas exceeds 16MP: {zoomed_state['displayCanvasPixels']}"
