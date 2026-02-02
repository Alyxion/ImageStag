"""
Unit tests for SVG document export/import functionality.

Tests the round-trip: Export to SVG -> Import from SVG -> Verify properties match.
Also tests the "debaking" mechanism that extracts original SVG content from the transform envelope.
"""

import pytest
import re

# Simple test SVG content
SIMPLE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="red"/>
</svg>'''


class TestSVGExportImport:
    """Test SVG export/import round-trip."""

    @pytest.mark.asyncio
    async def test_svg_layer_roundtrip_basic(self, helpers):
        """Test basic SVG layer export and reimport."""
        await helpers.new_document(400, 300)

        # Create SVG layer
        layer_props = await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'Test Circle',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 200,
                    height: 200
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();

                return {{
                    id: layer.id,
                    name: layer.name,
                    naturalWidth: layer.naturalWidth,
                    naturalHeight: layer.naturalHeight
                }};
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # Import
        doc_info = await helpers.editor.execute_js(f"""
            (async () => {{
                const {{ Document }} = await import('/static/js/core/Document.js');
                const doc = await Document.fromSVG({repr(svg_export)}, window.__stagforge_app__.eventBus);

                return {{
                    width: doc.width,
                    height: doc.height,
                    layerCount: doc.layerStack.layers.length,
                    layers: doc.layerStack.layers.map(l => ({{
                        name: l.name,
                        type: l.type,
                        naturalWidth: l.naturalWidth,
                        naturalHeight: l.naturalHeight
                    }}))
                }};
            }})()
        """)

        # Find the SVG layer in imported doc
        svg_layers = [l for l in doc_info['layers'] if l['type'] == 'svg']
        assert len(svg_layers) >= 1, "Should have at least one SVG layer"

        imported_layer = svg_layers[0]
        assert imported_layer['name'] == "Test Circle"
        assert imported_layer['naturalWidth'] == 100  # From viewBox
        assert imported_layer['naturalHeight'] == 100

    @pytest.mark.asyncio
    async def test_svg_layer_roundtrip_with_rotation(self, helpers):
        """Test SVG layer with rotation preserves rotation on reimport."""
        await helpers.new_document(400, 300)

        # Create SVG layer with rotation
        await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'Rotated',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 200,
                    height: 200,
                    rotation: 45,
                    offsetX: 100,
                    offsetY: 50
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # Import
        doc_info = await helpers.editor.execute_js(f"""
            (async () => {{
                const {{ Document }} = await import('/static/js/core/Document.js');
                const doc = await Document.fromSVG({repr(svg_export)}, window.__stagforge_app__.eventBus);

                return {{
                    layers: doc.layerStack.layers.map(l => ({{
                        name: l.name,
                        type: l.type,
                        rotation: l.rotation,
                        offsetX: l.offsetX,
                        offsetY: l.offsetY
                    }}))
                }};
            }})()
        """)

        svg_layers = [l for l in doc_info['layers'] if l['type'] == 'svg']
        assert len(svg_layers) >= 1

        imported = svg_layers[0]
        assert imported['rotation'] == 45, f"Rotation should be 45, got {imported['rotation']}"
        assert imported['offsetX'] == 100, f"offsetX should be 100, got {imported['offsetX']}"
        assert imported['offsetY'] == 50, f"offsetY should be 50, got {imported['offsetY']}"

    @pytest.mark.asyncio
    async def test_svg_layer_roundtrip_with_scale(self, helpers):
        """Test SVG layer with scale (mirror) preserves scaleX/scaleY on reimport."""
        await helpers.new_document(400, 300)

        # Create SVG layer with mirror
        await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'Mirrored',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 200,
                    height: 200,
                    scaleX: -1,
                    scaleY: 1
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # Import
        doc_info = await helpers.editor.execute_js(f"""
            (async () => {{
                const {{ Document }} = await import('/static/js/core/Document.js');
                const doc = await Document.fromSVG({repr(svg_export)}, window.__stagforge_app__.eventBus);

                return {{
                    layers: doc.layerStack.layers.map(l => ({{
                        name: l.name,
                        type: l.type,
                        scaleX: l.scaleX,
                        scaleY: l.scaleY
                    }}))
                }};
            }})()
        """)

        svg_layers = [l for l in doc_info['layers'] if l['type'] == 'svg']
        assert len(svg_layers) >= 1

        imported = svg_layers[0]
        assert imported['scaleX'] == -1, f"scaleX should be -1, got {imported['scaleX']}"
        assert imported['scaleY'] == 1, f"scaleY should be 1, got {imported['scaleY']}"

    @pytest.mark.asyncio
    async def test_svg_layer_roundtrip_with_resize(self, helpers):
        """Test SVG layer resized to different dimensions."""
        await helpers.new_document(400, 300)

        # Create SVG layer with different target size
        await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'Resized',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 300,
                    height: 200
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # Import
        doc_info = await helpers.editor.execute_js(f"""
            (async () => {{
                const {{ Document }} = await import('/static/js/core/Document.js');
                const doc = await Document.fromSVG({repr(svg_export)}, window.__stagforge_app__.eventBus);

                return {{
                    layers: doc.layerStack.layers.map(l => ({{
                        name: l.name,
                        type: l.type,
                        width: l.width,
                        height: l.height,
                        naturalWidth: l.naturalWidth,
                        naturalHeight: l.naturalHeight
                    }}))
                }};
            }})()
        """)

        svg_layers = [l for l in doc_info['layers'] if l['type'] == 'svg']
        assert len(svg_layers) >= 1

        imported = svg_layers[0]
        assert imported['width'] == 300, f"width should be 300, got {imported['width']}"
        assert imported['height'] == 200, f"height should be 200, got {imported['height']}"
        assert imported['naturalWidth'] == 100, f"naturalWidth should be 100, got {imported['naturalWidth']}"
        assert imported['naturalHeight'] == 100, f"naturalHeight should be 100, got {imported['naturalHeight']}"


class TestSVGDebaking:
    """Test the debaking mechanism - SVG should not be duplicated."""

    @pytest.mark.asyncio
    async def test_svg_not_stored_twice(self, helpers):
        """Verify SVG content is NOT stored in both properties and visual representation."""
        await helpers.new_document(400, 300)

        # Create SVG layer
        await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'No Duplicate',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 200,
                    height: 200
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # Check for duplication - svgData should NOT be in sf:properties
        has_svgdata_in_props = '<sf:svgData>' in svg_export

        # Count viewBox occurrences (should be exactly 1)
        viewbox_count = svg_export.count('viewBox="0 0 100 100"')

        assert not has_svgdata_in_props, \
            "svgData should NOT be stored in sf:properties"
        assert viewbox_count == 1, \
            f"SVG viewBox should appear exactly once, found {viewbox_count} times"

    @pytest.mark.asyncio
    async def test_debake_extracts_original_svg(self, helpers):
        """Test that debaking extracts the original SVG content."""
        await helpers.new_document(400, 300)

        # Create SVG layer with rotation and scaling
        await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'To Debake',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 250,
                    height: 250,
                    rotation: 30,
                    scaleX: -1,
                    offsetX: 150,
                    offsetY: 100
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # Debake using utility
        debaked_svg = await helpers.editor.execute_js(f"""
            (async () => {{
                const {{ debakeSVGContent, parseSVG, getLayerGroups }} = await import('/static/js/core/svgExportUtils.js');
                const xmlDoc = parseSVG({repr(svg_export)});
                const groups = getLayerGroups(xmlDoc);

                for (const group of groups) {{
                    const type = group.getAttributeNS('http://stagforge.io/xmlns/2026', 'type');
                    if (type === 'svg') {{
                        return debakeSVGContent(group);
                    }}
                }}
                return '';
            }})()
        """)

        # Verify debaked content contains original elements
        assert 'viewBox="0 0 100 100"' in debaked_svg, \
            "Debaked SVG should have original viewBox"
        assert '<circle' in debaked_svg, \
            "Debaked SVG should contain original circle element"

    @pytest.mark.asyncio
    async def test_debake_removes_transform_wrapper(self, helpers):
        """Test that debaking removes the transform wrapper."""
        await helpers.new_document(400, 300)

        # Create SVG layer with transforms
        await helpers.editor.execute_js(f"""
            (async () => {{
                const app = window.__stagforge_app__;
                const {{ StaticSVGLayer }} = await import('/static/js/core/StaticSVGLayer.js');

                const layer = new StaticSVGLayer({{
                    name: 'Transform Test',
                    svgContent: {repr(SIMPLE_SVG)},
                    width: 200,
                    height: 200,
                    rotation: 45,
                    offsetX: 100,
                    offsetY: 100
                }});

                const doc = app.documentManager.getActiveDocument();
                doc.layerStack.addLayer(layer);
                await layer.render();
            }})()
        """)

        # Export
        svg_export = await helpers.editor.execute_js("""
            (async () => {
                const doc = window.__stagforge_app__.documentManager.getActiveDocument();
                return await doc.toSVG();
            })()
        """)

        # The exported SVG should have transform in the wrapper
        assert 'rotate(45)' in svg_export, "Export should contain rotation transform"

        # Debake
        debaked_svg = await helpers.editor.execute_js(f"""
            (async () => {{
                const {{ debakeSVGContent, parseSVG, getLayerGroups }} = await import('/static/js/core/svgExportUtils.js');
                const xmlDoc = parseSVG({repr(svg_export)});
                const groups = getLayerGroups(xmlDoc);

                for (const group of groups) {{
                    const type = group.getAttributeNS('http://stagforge.io/xmlns/2026', 'type');
                    if (type === 'svg') {{
                        return debakeSVGContent(group);
                    }}
                }}
                return '';
            }})()
        """)

        # Debaked SVG should NOT have the transform wrapper
        assert 'rotate(45)' not in debaked_svg, \
            "Debaked SVG should not contain rotation transform"


class TestSVGDetection:
    """Test Stagforge SVG detection."""

    @pytest.mark.asyncio
    async def test_detect_stagforge_svg(self, helpers):
        """Test isStagforgeSVG correctly identifies Stagforge documents."""
        await helpers.new_document(100, 100)

        result = await helpers.editor.execute_js("""
            (async () => {
                const { isStagforgeSVG } = await import('/static/js/core/svgExportUtils.js');

                const stagforgeSvg = `<?xml version="1.0"?>
                    <svg xmlns="http://www.w3.org/2000/svg"
                         xmlns:sf="http://stagforge.io/xmlns/2026"
                         sf:version="1">
                    </svg>`;

                const regularSvg = `<?xml version="1.0"?>
                    <svg xmlns="http://www.w3.org/2000/svg">
                        <circle cx="50" cy="50" r="40"/>
                    </svg>`;

                return {
                    stagforge: isStagforgeSVG(stagforgeSvg),
                    regular: isStagforgeSVG(regularSvg),
                    empty: isStagforgeSVG(''),
                    nullVal: isStagforgeSVG(null)
                };
            })()
        """)

        assert result['stagforge'] is True, "Should detect Stagforge SVG"
        assert result['regular'] is False, "Should not detect regular SVG as Stagforge"
        assert result['empty'] is False, "Should handle empty string"
        assert result['nullVal'] is False, "Should handle null"
