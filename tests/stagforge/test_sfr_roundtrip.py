"""
Combinatory SFR roundtrip tests for JS ↔ Python layer serialization.

Tests that documents with all layer types and effects can be:
1. Created in JavaScript, saved to SFR, loaded in Python
2. Created in Python, saved to SFR, loaded in JavaScript

This verifies full parity between JS and Python layer/effect serialization.

Uses conftest.py's server fixture (auto-starts on port 8089) and screen fixture.

Run with: poetry run pytest tests/stagforge/test_sfr_roundtrip.py -v
"""

import base64
import io
import json
import tempfile
import uuid
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

# Python layer models
from stagforge.layers import (
    PixelLayer,
    StaticSVGLayer,
    TextLayer,
    TextRun,
    LayerGroup,
)
from stagforge.formats import SFRDocument

# Alias for compatibility with existing test code
Document = SFRDocument

# Python layer effects
from imagestag.layer_effects import (
    DropShadow,
    InnerShadow,
    OuterGlow,
    InnerGlow,
    BevelEmboss,
    Stroke,
    ColorOverlay,
    Satin,
    GradientOverlay,
    PatternOverlay,
    LayerEffect,
)

# screen fixture is provided by conftest.py (auto-starts server on port 8089)


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_test_image_data_url(width: int = 100, height: int = 100, color: tuple = (255, 0, 0, 255)) -> str:
    """Create a solid color test image as a data URL."""
    img = Image.new('RGBA', (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f"data:image/png;base64,{b64}"


def create_test_svg_content(color: str = "#0000FF") -> str:
    """Create test SVG content."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="{color}"/>
</svg>'''


# ==============================================================================
# JavaScript → Python Roundtrip Tests
# ==============================================================================

class TestJSToPythonRoundtrip:
    """Test creating documents in JS and loading them in Python."""

    def test_all_layer_types_js_to_python(self, screen):
        """Create document with all layer types in JS, verify loads correctly in Python."""
        screen.open('/')
        screen.wait_for_editor()

        # Create document with all layer types in JavaScript
        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const doc = app.documentManager.getActiveDocument();
                const fileManager = app.fileManager;

                // Clear existing layers
                while (doc.layerStack.layers.length > 0) {
                    doc.layerStack.removeLayer(doc.layerStack.layers[0]);
                }

                // 1. Create a raster (pixel) layer with some content
                const rasterLayer = doc.layerStack.createLayer();
                rasterLayer.name = 'TestRasterLayer';
                // Draw a red rectangle
                rasterLayer.ctx.fillStyle = '#FF0000';
                rasterLayer.ctx.fillRect(10, 10, 80, 80);

                // 2. Create an SVG layer
                const SVGLayerClass = (await import('/static/js/core/StaticSVGLayer.js')).StaticSVGLayer;
                const svgContent = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#00FF00"/></svg>';
                const svgLayer = await SVGLayerClass.fromSVGString(svgContent, 100, 100);
                svgLayer.name = 'TestSVGLayer';
                doc.layerStack.addLayer(svgLayer);

                // 3. Create a text layer
                const TextLayerClass = (await import('/static/js/core/TextLayer.js')).TextLayer;
                const textLayer = new TextLayerClass({
                    width: 200,
                    height: 50,
                    runs: [{ text: 'Hello World', fontSize: 24, fontFamily: 'Arial', color: '#0000FF' }],
                    fontSize: 24,
                    fontFamily: 'Arial',
                    color: '#0000FF',
                });
                textLayer.name = 'TestTextLayer';
                doc.layerStack.addLayer(textLayer);

                // 4. Create a layer group
                const LayerGroupClass = (await import('/static/js/core/LayerGroup.js')).LayerGroup;
                const group = new LayerGroupClass({ name: 'TestGroup' });
                doc.layerStack.addLayer(group);

                // 5. Add a nested raster layer inside the group
                const nestedLayer = doc.layerStack.createLayer();
                nestedLayer.name = 'NestedRasterLayer';
                nestedLayer.ctx.fillStyle = '#FFFF00';
                nestedLayer.ctx.fillRect(0, 0, 50, 50);
                doc.layerStack.moveLayerToGroup(nestedLayer, group);

                // Set document name
                doc.name = 'CombinedLayerTest';

                // Serialize to SFR format
                const sfrData = await fileManager.exportToSFRBlob();

                // Convert blob to base64 for transfer
                const arrayBuffer = await sfrData.arrayBuffer();
                const bytes = new Uint8Array(arrayBuffer);
                let binary = '';
                for (let i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                const base64 = btoa(binary);

                // Return layer info for verification
                const layerInfo = doc.layerStack.layers.map(l => ({
                    id: l.id,
                    name: l.name,
                    type: l.type,
                    parentId: l.parentId,
                }));

                return {
                    success: true,
                    sfrBase64: base64,
                    documentName: doc.name,
                    layerCount: doc.layerStack.layers.length,
                    layers: layerInfo,
                };
            }
        """)

        assert result.get('success'), f"JS creation failed: {result.get('error', result)}"
        assert result['documentName'] == 'CombinedLayerTest'
        assert result['layerCount'] >= 4, f"Expected at least 4 layers, got {result['layerCount']}"

        # Decode the SFR file
        sfr_bytes = base64.b64decode(result['sfrBase64'])

        # Load in Python
        with tempfile.NamedTemporaryFile(suffix='.sfr', delete=False) as f:
            f.write(sfr_bytes)
            f.flush()
            sfr_path = Path(f.name)

        try:
            doc = SFRDocument.load(sfr_path)

            # Verify document loaded correctly
            assert doc.name == 'CombinedLayerTest'
            assert len(doc.layers) >= 4

            # Find layers by name and verify their types
            layer_by_name = {l.get('name'): l for l in doc.layers}

            # Verify raster layer
            assert 'TestRasterLayer' in layer_by_name
            raster = layer_by_name['TestRasterLayer']
            assert raster.get('type') == 'raster'

            # Verify SVG layer
            assert 'TestSVGLayer' in layer_by_name
            svg = layer_by_name['TestSVGLayer']
            assert svg.get('type') == 'svg'
            assert 'svgContent' in svg or 'imageData' in svg

            # Verify text layer
            assert 'TestTextLayer' in layer_by_name
            text = layer_by_name['TestTextLayer']
            assert text.get('type') == 'text'
            assert 'runs' in text

            # Verify group
            assert 'TestGroup' in layer_by_name
            group = layer_by_name['TestGroup']
            assert group.get('type') == 'group'

        finally:
            sfr_path.unlink()

    def test_layer_effects_js_to_python(self, screen):
        """Create layers with effects in JS, verify effects load in Python."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const doc = app.documentManager.getActiveDocument();
                const fileManager = app.fileManager;
                const LayerEffects = window.LayerEffects;

                // Clear existing layers
                while (doc.layerStack.layers.length > 0) {
                    doc.layerStack.removeLayer(doc.layerStack.layers[0]);
                }

                // Create a raster layer
                const layer = doc.layerStack.createLayer();
                layer.name = 'EffectsTestLayer';
                layer.ctx.fillStyle = '#FF0000';
                layer.ctx.fillRect(20, 20, 160, 160);

                // Add multiple effects
                const effects = [
                    { type: 'dropShadow', params: { offsetX: 10, offsetY: 10, blur: 5, color: '#000000', opacity: 0.75 } },
                    { type: 'innerShadow', params: { offsetX: 3, offsetY: 3, blur: 4, color: '#333333', opacity: 0.5 } },
                    { type: 'outerGlow', params: { blur: 8, color: '#FFFF00', opacity: 0.6 } },
                    { type: 'stroke', params: { size: 3, color: '#0000FF', position: 'outside' } },
                ];

                for (const { type, params } of effects) {
                    const EffectClass = LayerEffects.effectRegistry[type];
                    if (EffectClass) {
                        const effect = new EffectClass(params);
                        layer.addEffect(effect);
                    }
                }

                doc.name = 'EffectsRoundtripTest';

                // Export to SFR
                const sfrData = await fileManager.exportToSFRBlob();
                const arrayBuffer = await sfrData.arrayBuffer();
                const bytes = new Uint8Array(arrayBuffer);
                let binary = '';
                for (let i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }

                return {
                    success: true,
                    sfrBase64: btoa(binary),
                    effectCount: layer.effects.length,
                    effectTypes: layer.effects.map(e => e.type),
                };
            }
        """)

        assert result.get('success'), f"JS creation failed: {result}"
        assert result['effectCount'] >= 4

        # Load in Python
        sfr_bytes = base64.b64decode(result['sfrBase64'])

        with tempfile.NamedTemporaryFile(suffix='.sfr', delete=False) as f:
            f.write(sfr_bytes)
            sfr_path = Path(f.name)

        try:
            doc = SFRDocument.load(sfr_path)

            # Find the effects layer
            effects_layer = None
            for layer in doc.layers:
                if layer.get('name') == 'EffectsTestLayer':
                    effects_layer = layer
                    break

            assert effects_layer is not None, "EffectsTestLayer not found"

            # Verify effects
            effects = effects_layer.get('effects', [])
            assert len(effects) >= 4, f"Expected at least 4 effects, got {len(effects)}"

            effect_types = [e.get('type') for e in effects]
            assert 'dropShadow' in effect_types
            assert 'innerShadow' in effect_types
            assert 'outerGlow' in effect_types
            assert 'stroke' in effect_types

            # Verify effect parameters are preserved
            drop_shadow = next((e for e in effects if e.get('type') == 'dropShadow'), None)
            assert drop_shadow is not None
            assert drop_shadow.get('offsetX') == 10
            assert drop_shadow.get('offsetY') == 10
            assert drop_shadow.get('blur') == 5

        finally:
            sfr_path.unlink()


# ==============================================================================
# Python → JavaScript Roundtrip Tests
# ==============================================================================

class TestPythonToJSRoundtrip:
    """Test creating documents in Python and loading them in JavaScript."""

    def test_all_layer_types_python_to_js(self, screen):
        """Create document with all layer types in Python, verify loads correctly in JS."""
        screen.open('/')
        screen.wait_for_editor()

        # Create document in Python
        doc_id = str(uuid.uuid4())

        layers = [
            # Raster layer
            {
                'id': str(uuid.uuid4()),
                'name': 'PythonRasterLayer',
                'type': 'raster',
                'width': 100,
                'height': 100,
                'offsetX': 0,
                'offsetY': 0,
                'opacity': 1.0,
                'blendMode': 'normal',
                'visible': True,
                'imageData': create_test_image_data_url(100, 100, (255, 0, 0, 255)),
            },
            # SVG layer
            {
                'id': str(uuid.uuid4()),
                'name': 'PythonSVGLayer',
                'type': 'svg',
                'width': 100,
                'height': 100,
                'offsetX': 100,
                'offsetY': 0,
                'opacity': 1.0,
                'blendMode': 'normal',
                'visible': True,
                'svgContent': create_test_svg_content('#00FF00'),
                'naturalWidth': 100,
                'naturalHeight': 100,
            },
            # Text layer
            {
                'id': str(uuid.uuid4()),
                'name': 'PythonTextLayer',
                'type': 'text',
                'width': 200,
                'height': 50,
                'offsetX': 0,
                'offsetY': 100,
                'opacity': 1.0,
                'blendMode': 'normal',
                'visible': True,
                'runs': [{'text': 'Python Text', 'fontSize': 24, 'fontFamily': 'Arial', 'color': '#0000FF'}],
                'fontSize': 24,
                'fontFamily': 'Arial',
                'color': '#0000FF',
            },
            # Layer group
            {
                'id': str(uuid.uuid4()),
                'name': 'PythonGroup',
                'type': 'group',
                'width': 0,
                'height': 0,
                'offsetX': 0,
                'offsetY': 0,
                'opacity': 1.0,
                'blendMode': 'passthrough',
                'visible': True,
                'expanded': True,
            },
        ]

        doc = Document(
            id=doc_id,
            name='PythonCreatedDocument',
            width=400,
            height=300,
            pages=[{
                'id': str(uuid.uuid4()),
                'name': 'Page 1',
                'layers': layers,
                'activeLayerIndex': 0,
            }],
        )

        # Save to SFR
        with tempfile.NamedTemporaryFile(suffix='.sfr', delete=False) as f:
            sfr_path = Path(f.name)

        try:
            doc.save(sfr_path)

            # Read and encode for transfer to JS
            with open(sfr_path, 'rb') as f:
                sfr_bytes = f.read()
            sfr_base64 = base64.b64encode(sfr_bytes).decode('ascii')

            # Load in JavaScript
            result = screen.page.evaluate(f"""
                async () => {{
                    const app = window.__stagforge_app__;
                    const fileManager = app.fileManager;

                    // Decode base64 to blob
                    const base64 = '{sfr_base64}';
                    const binary = atob(base64);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {{
                        bytes[i] = binary.charCodeAt(i);
                    }}
                    const blob = new Blob([bytes], {{ type: 'application/zip' }});

                    // Create a File object
                    const file = new File([blob], 'test.sfr', {{ type: 'application/zip' }});

                    // Load the SFR file
                    try {{
                        await fileManager.loadSFRFile(file);
                    }} catch (e) {{
                        return {{ error: 'Failed to load SFR: ' + e.message }};
                    }}

                    // Get loaded document info
                    const doc = app.documentManager.getActiveDocument();
                    const layerInfo = doc.layerStack.layers.map(l => ({{
                        id: l.id,
                        name: l.name,
                        type: l.type,
                        width: l.width,
                        height: l.height,
                    }}));

                    return {{
                        success: true,
                        documentName: doc.name,
                        documentWidth: doc.width,
                        documentHeight: doc.height,
                        layerCount: doc.layerStack.layers.length,
                        layers: layerInfo,
                    }};
                }}
            """)

            assert result.get('success'), f"JS load failed: {result.get('error', result)}"
            assert result['documentName'] == 'PythonCreatedDocument'
            assert result['documentWidth'] == 400
            assert result['documentHeight'] == 300

            # Verify layers
            layer_names = [l['name'] for l in result['layers']]
            assert 'PythonRasterLayer' in layer_names
            assert 'PythonSVGLayer' in layer_names
            assert 'PythonTextLayer' in layer_names
            assert 'PythonGroup' in layer_names

            # Verify layer types
            layer_by_name = {l['name']: l for l in result['layers']}
            assert layer_by_name['PythonRasterLayer']['type'] == 'raster'
            assert layer_by_name['PythonSVGLayer']['type'] == 'svg'
            assert layer_by_name['PythonTextLayer']['type'] == 'text'
            assert layer_by_name['PythonGroup']['type'] == 'group'

        finally:
            sfr_path.unlink()

    def test_layer_effects_python_to_js(self, screen):
        """Create layers with effects in Python, verify effects load in JS."""
        screen.open('/')
        screen.wait_for_editor()

        # Create document with effects in Python
        effects_data = [
            {'type': 'dropShadow', 'offsetX': 8, 'offsetY': 8, 'blur': 6, 'color': '#000000', 'opacity': 0.7},
            {'type': 'innerShadow', 'offsetX': 2, 'offsetY': 2, 'blur': 3, 'color': '#444444', 'opacity': 0.5},
            {'type': 'outerGlow', 'blur': 10, 'color': '#FF0000', 'opacity': 0.8},
            {'type': 'stroke', 'size': 2, 'color': '#00FF00', 'position': 'outside'},
        ]

        layer_data = {
            'id': str(uuid.uuid4()),
            'name': 'PythonEffectsLayer',
            'type': 'raster',
            'width': 100,
            'height': 100,
            'offsetX': 50,
            'offsetY': 50,
            'opacity': 1.0,
            'blendMode': 'normal',
            'visible': True,
            'imageData': create_test_image_data_url(100, 100, (0, 0, 255, 255)),
            'effects': effects_data,
        }

        doc = Document(
            id=str(uuid.uuid4()),
            name='PythonEffectsDocument',
            width=300,
            height=300,
            pages=[{
                'id': str(uuid.uuid4()),
                'name': 'Page 1',
                'layers': [layer_data],
                'activeLayerIndex': 0,
            }],
        )

        # Save to SFR
        with tempfile.NamedTemporaryFile(suffix='.sfr', delete=False) as f:
            sfr_path = Path(f.name)

        try:
            doc.save(sfr_path)

            with open(sfr_path, 'rb') as f:
                sfr_base64 = base64.b64encode(f.read()).decode('ascii')

            # Load in JavaScript
            result = screen.page.evaluate(f"""
                async () => {{
                    const app = window.__stagforge_app__;
                    const fileManager = app.fileManager;

                    // Decode and load
                    const base64 = '{sfr_base64}';
                    const binary = atob(base64);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {{
                        bytes[i] = binary.charCodeAt(i);
                    }}
                    const blob = new Blob([bytes], {{ type: 'application/zip' }});
                    const file = new File([blob], 'test.sfr', {{ type: 'application/zip' }});

                    try {{
                        await fileManager.loadSFRFile(file);
                    }} catch (e) {{
                        return {{ error: 'Failed to load SFR: ' + e.message }};
                    }}

                    const doc = app.documentManager.getActiveDocument();

                    // Find the effects layer
                    const effectsLayer = doc.layerStack.layers.find(l => l.name === 'PythonEffectsLayer');
                    if (!effectsLayer) {{
                        return {{ error: 'Effects layer not found', layers: doc.layerStack.layers.map(l => l.name) }};
                    }}

                    // Get effects info
                    const effectsInfo = (effectsLayer.effects || []).map(e => ({{
                        type: e.type,
                        ...e.serialize()
                    }}));

                    return {{
                        success: true,
                        layerName: effectsLayer.name,
                        effectCount: effectsLayer.effects?.length || 0,
                        effects: effectsInfo,
                    }};
                }}
            """)

            assert result.get('success'), f"JS load failed: {result.get('error', result)}"
            assert result['effectCount'] >= 4, f"Expected 4+ effects, got {result['effectCount']}"

            # Verify effect types
            effect_types = [e['type'] for e in result['effects']]
            assert 'dropShadow' in effect_types
            assert 'innerShadow' in effect_types
            assert 'outerGlow' in effect_types
            assert 'stroke' in effect_types

            # Verify drop shadow parameters
            drop_shadow = next((e for e in result['effects'] if e['type'] == 'dropShadow'), None)
            assert drop_shadow is not None
            assert drop_shadow.get('offsetX') == 8
            assert drop_shadow.get('offsetY') == 8
            assert drop_shadow.get('blur') == 6

        finally:
            sfr_path.unlink()


# ==============================================================================
# Full Roundtrip Tests (JS → Python → JS)
# ==============================================================================

class TestFullRoundtrip:
    """Test full roundtrip: JS → Python (modify) → JS."""

    def test_modify_document_in_python(self, screen):
        """Create in JS, load in Python, modify, save, reload in JS."""
        screen.open('/')
        screen.wait_for_editor()

        # Step 1: Create document in JS
        result1 = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const doc = app.documentManager.getActiveDocument();
                const fileManager = app.fileManager;

                // Clear and create new layer
                while (doc.layerStack.layers.length > 0) {
                    doc.layerStack.removeLayer(doc.layerStack.layers[0]);
                }

                const layer = doc.layerStack.createLayer();
                layer.name = 'OriginalLayer';
                layer.ctx.fillStyle = '#FF0000';
                layer.ctx.fillRect(0, 0, 100, 100);

                doc.name = 'RoundtripTest';

                const sfrData = await fileManager.exportToSFRBlob();
                const arrayBuffer = await sfrData.arrayBuffer();
                const bytes = new Uint8Array(arrayBuffer);
                let binary = '';
                for (let i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }

                return { success: true, sfrBase64: btoa(binary) };
            }
        """)

        assert result1.get('success')

        # Step 2: Load in Python, modify, save
        sfr_bytes = base64.b64decode(result1['sfrBase64'])

        with tempfile.NamedTemporaryFile(suffix='.sfr', delete=False) as f:
            f.write(sfr_bytes)
            sfr_path = Path(f.name)

        modified_path = None
        try:
            doc = SFRDocument.load(sfr_path)

            # Modify: change document name
            doc.name = 'ModifiedInPython'

            # Modify: add a new layer
            new_layer = {
                'id': str(uuid.uuid4()),
                'name': 'AddedByPython',
                'type': 'raster',
                'width': 50,
                'height': 50,
                'offsetX': 150,
                'offsetY': 150,
                'opacity': 1.0,
                'blendMode': 'normal',
                'visible': True,
                'imageData': create_test_image_data_url(50, 50, (0, 255, 0, 255)),
            }
            doc.layers.append(new_layer)

            # Save modified document
            with tempfile.NamedTemporaryFile(suffix='.sfr', delete=False) as f:
                modified_path = Path(f.name)
            doc.save(modified_path)

            with open(modified_path, 'rb') as f:
                modified_base64 = base64.b64encode(f.read()).decode('ascii')

            # Step 3: Load modified document in JS
            result2 = screen.page.evaluate(f"""
                async () => {{
                    const app = window.__stagforge_app__;
                    const fileManager = app.fileManager;

                    const base64 = '{modified_base64}';
                    const binary = atob(base64);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {{
                        bytes[i] = binary.charCodeAt(i);
                    }}
                    const blob = new Blob([bytes], {{ type: 'application/zip' }});
                    const file = new File([blob], 'modified.sfr', {{ type: 'application/zip' }});

                    await fileManager.loadSFRFile(file);

                    const doc = app.documentManager.getActiveDocument();
                    const layerNames = doc.layerStack.layers.map(l => l.name);

                    return {{
                        success: true,
                        documentName: doc.name,
                        layerNames: layerNames,
                        hasOriginal: layerNames.includes('OriginalLayer'),
                        hasPythonLayer: layerNames.includes('AddedByPython'),
                    }};
                }}
            """)

            assert result2.get('success'), f"JS reload failed: {result2}"
            assert result2['documentName'] == 'ModifiedInPython'
            assert result2['hasOriginal'], "Original layer not found"
            assert result2['hasPythonLayer'], "Python-added layer not found"

        finally:
            sfr_path.unlink()
            if modified_path:
                modified_path.unlink()
