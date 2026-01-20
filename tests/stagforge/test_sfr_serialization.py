"""
Tests for SFR serialization without requiring dynamic imports.

These tests verify that VectorLayer serialization includes all necessary
properties for correct save/load round-trips.
"""

import pytest
from playwright.sync_api import sync_playwright, Page


@pytest.fixture(scope="module")
def browser():
    """Launch browser for tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


def wait_for_app(page: Page):
    """Wait for the app to be ready."""
    page.goto("http://127.0.0.1:8080")
    page.wait_for_selector('.editor-root', timeout=15000)
    page.wait_for_function(
        "() => window.__stagforge_app__ && window.__stagforge_app__.layerStack && window.VectorLayer",
        timeout=15000
    )
    page.evaluate("() => { window.app = window.__stagforge_app__; }")


class TestVectorLayerSerialization:
    """Test VectorLayer serialize/deserialize directly in browser JS."""

    def test_vector_layer_serializes_offsets(self, page: Page):
        """Test that VectorLayer.serialize() includes offsetX and offsetY."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape || window.createShape;

            if (!VectorLayer || !createShape) {
                return { error: 'VectorLayer or createVectorShape not available' };
            }

            // Create a vector layer with shape at non-origin position
            const layer = new VectorLayer({
                width: 400,
                height: 400,
                name: 'Test Vector'
            });

            // Add shape at (150, 150)
            const shape = createShape({
                type: 'rect',
                x: 150,
                y: 150,
                width: 100,
                height: 80,
                fill: '#FF0000'
            });
            layer.shapes.push(shape);

            // Fit to content - should set offsetX/Y to ~148 (with padding)
            layer.fitToContent();

            // Serialize
            const serialized = layer.serialize();

            return {
                hasOffsetX: 'offsetX' in serialized,
                hasOffsetY: 'offsetY' in serialized,
                hasEffects: 'effects' in serialized,
                hasDocWidth: '_docWidth' in serialized,
                hasDocHeight: '_docHeight' in serialized,
                offsetX: serialized.offsetX,
                offsetY: serialized.offsetY,
                version: serialized._version
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['hasOffsetX'], "Serialized data should have offsetX"
        assert result['hasOffsetY'], "Serialized data should have offsetY"
        assert result['hasEffects'], "Serialized data should have effects"
        assert result['hasDocWidth'], "Serialized data should have _docWidth"
        assert result['hasDocHeight'], "Serialized data should have _docHeight"
        assert result['offsetX'] > 100, f"offsetX should be > 100, got {result['offsetX']}"
        assert result['offsetY'] > 100, f"offsetY should be > 100, got {result['offsetY']}"
        assert result['version'] == 2, f"VERSION should be 2, got {result['version']}"

    def test_vector_layer_serializes_effects(self, page: Page):
        """Test that VectorLayer.serialize() includes effects array."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape || window.createShape;
            const { DropShadowEffect, StrokeEffect } = window.LayerEffects;

            if (!VectorLayer || !createShape) {
                return { error: 'VectorLayer or createVectorShape not available' };
            }

            // Create vector layer with effects
            const layer = new VectorLayer({
                width: 200,
                height: 200,
                name: 'Test Vector'
            });

            // Add a shape
            const shape = createShape({
                type: 'rect',
                x: 50,
                y: 50,
                width: 100,
                height: 80,
                fill: '#00FF00'
            });
            layer.shapes.push(shape);
            layer.fitToContent();

            // Add effects
            layer.addEffect(new DropShadowEffect({
                offsetX: 5,
                offsetY: 5,
                blur: 10,
                color: '#000000'
            }));
            layer.addEffect(new StrokeEffect({
                size: 3,
                position: 'outside',
                color: '#FF0000'
            }));

            // Serialize
            const serialized = layer.serialize();

            return {
                effectCount: serialized.effects?.length || 0,
                effectTypes: (serialized.effects || []).map(e => e.type),
                firstEffect: serialized.effects?.[0] || null,
                secondEffect: serialized.effects?.[1] || null
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['effectCount'] == 2, \
            f"Should have 2 effects, got {result['effectCount']}"
        assert 'dropShadow' in result['effectTypes'], \
            f"Should have dropShadow effect, got {result['effectTypes']}"
        assert 'stroke' in result['effectTypes'], \
            f"Should have stroke effect, got {result['effectTypes']}"
        assert result['firstEffect']['blur'] == 10, \
            "Drop shadow blur should be 10"
        assert result['secondEffect']['size'] == 3, \
            "Stroke size should be 3"

    def test_vector_layer_deserializes_offsets(self, page: Page):
        """Test that VectorLayer.deserialize() restores offsetX and offsetY."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape || window.createShape;

            if (!VectorLayer || !createShape) {
                return { error: 'VectorLayer or createVectorShape not available' };
            }

            // Create original layer
            const original = new VectorLayer({
                width: 400,
                height: 400,
                name: 'Original'
            });

            const shape = createShape({
                type: 'rect',
                x: 200,
                y: 200,
                width: 100,
                height: 80,
                fill: '#0000FF'
            });
            original.shapes.push(shape);
            original.fitToContent();

            const originalOffsetX = original.offsetX;
            const originalOffsetY = original.offsetY;

            // Serialize
            const serialized = original.serialize();

            // Deserialize to new layer
            const restored = VectorLayer.deserialize(serialized);

            return {
                originalOffsetX,
                originalOffsetY,
                restoredOffsetX: restored.offsetX,
                restoredOffsetY: restored.offsetY,
                offsetXMatch: originalOffsetX === restored.offsetX,
                offsetYMatch: originalOffsetY === restored.offsetY,
                serializedOffsetX: serialized.offsetX,
                serializedOffsetY: serialized.offsetY
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['offsetXMatch'], \
            f"offsetX should match: original={result['originalOffsetX']}, " \
            f"serialized={result['serializedOffsetX']}, restored={result['restoredOffsetX']}"
        assert result['offsetYMatch'], \
            f"offsetY should match: original={result['originalOffsetY']}, " \
            f"serialized={result['serializedOffsetY']}, restored={result['restoredOffsetY']}"

    def test_vector_layer_deserializes_effects(self, page: Page):
        """Test that VectorLayer.deserialize() restores effects."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape || window.createShape;
            const { DropShadowEffect, StrokeEffect, OuterGlowEffect } = window.LayerEffects;

            if (!VectorLayer || !createShape) {
                return { error: 'VectorLayer or createVectorShape not available' };
            }

            // Create original layer with effects
            const original = new VectorLayer({
                width: 200,
                height: 200,
                name: 'Original'
            });

            original.shapes.push(createShape({
                type: 'ellipse',
                cx: 100,
                cy: 100,
                rx: 50,
                ry: 30,
                fill: '#FFFF00'
            }));
            original.fitToContent();

            // Add multiple effects with specific params
            original.addEffect(new DropShadowEffect({
                offsetX: 7,
                offsetY: 9,
                blur: 15,
                color: '#123456',
                colorOpacity: 0.65
            }));
            original.addEffect(new StrokeEffect({
                size: 5,
                position: 'center',
                color: '#ABCDEF'
            }));
            original.addEffect(new OuterGlowEffect({
                blur: 12,
                spread: 3,
                color: '#FF00FF',
                colorOpacity: 0.8
            }));

            const originalEffectCount = original.effects.length;

            // Serialize
            const serialized = original.serialize();

            // Deserialize
            const restored = VectorLayer.deserialize(serialized);

            // Compare effect counts and params
            const effectComparisons = [];
            for (let i = 0; i < original.effects.length; i++) {
                const origEffect = original.effects[i];
                const restoredEffect = restored.effects[i];

                if (!restoredEffect) {
                    effectComparisons.push({
                        index: i,
                        type: origEffect.type,
                        match: false,
                        error: 'Effect missing after deserialize'
                    });
                    continue;
                }

                let paramsMatch = true;
                const mismatches = [];

                if (origEffect.type === 'dropShadow') {
                    if (restoredEffect.offsetX !== 7) mismatches.push('offsetX: ' + restoredEffect.offsetX + ' != 7');
                    if (restoredEffect.blur !== 15) mismatches.push('blur: ' + restoredEffect.blur + ' != 15');
                    if (restoredEffect.color !== '#123456') mismatches.push('color: ' + restoredEffect.color + ' != #123456');
                } else if (origEffect.type === 'stroke') {
                    if (restoredEffect.size !== 5) mismatches.push('size: ' + restoredEffect.size + ' != 5');
                    if (restoredEffect.position !== 'center') mismatches.push('position: ' + restoredEffect.position + ' != center');
                } else if (origEffect.type === 'outerGlow') {
                    if (restoredEffect.blur !== 12) mismatches.push('blur: ' + restoredEffect.blur + ' != 12');
                    if (restoredEffect.spread !== 3) mismatches.push('spread: ' + restoredEffect.spread + ' != 3');
                }

                paramsMatch = mismatches.length === 0;

                effectComparisons.push({
                    index: i,
                    type: origEffect.type,
                    restoredType: restoredEffect.type,
                    match: paramsMatch,
                    mismatches
                });
            }

            return {
                originalEffectCount,
                serializedEffectCount: serialized.effects?.length || 0,
                restoredEffectCount: restored.effects.length,
                effectCountMatch: originalEffectCount === restored.effects.length,
                effectComparisons,
                allEffectsMatch: effectComparisons.every(c => c.match)
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['effectCountMatch'], \
            f"Effect count should match: original={result['originalEffectCount']}, " \
            f"serialized={result['serializedEffectCount']}, restored={result['restoredEffectCount']}"

        for comp in result['effectComparisons']:
            assert comp['match'], \
                f"Effect {comp['index']} ({comp['type']}) doesn't match: {comp.get('mismatches', comp.get('error'))}"

    def test_v1_data_migrates_to_v2(self, page: Page):
        """Test that old v1 serialized data gets migrated properly."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;

            if (!VectorLayer) {
                return { error: 'VectorLayer not available' };
            }

            // Create v1-style serialized data (missing offsetX, offsetY, effects)
            const v1Data = {
                _version: 1,
                _type: 'VectorLayer',
                type: 'vector',
                id: 'test-layer-id',
                name: 'Old Layer',
                width: 200,
                height: 150,
                opacity: 0.8,
                blendMode: 'multiply',
                visible: true,
                locked: false,
                shapes: [
                    {
                        type: 'rect',
                        x: 50,
                        y: 50,
                        width: 100,
                        height: 80,
                        fill: '#FF0000'
                    }
                ]
                // Note: no offsetX, offsetY, effects, _docWidth, _docHeight
            };

            // Deserialize - should trigger migration
            const restored = VectorLayer.deserialize(v1Data);

            return {
                hasOffsetX: 'offsetX' in restored,
                hasOffsetY: 'offsetY' in restored,
                hasEffects: Array.isArray(restored.effects),
                offsetX: restored.offsetX,
                offsetY: restored.offsetY,
                effectCount: restored.effects.length,
                width: restored.width,
                height: restored.height
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['hasOffsetX'], "Migrated layer should have offsetX"
        assert result['hasOffsetY'], "Migrated layer should have offsetY"
        assert result['hasEffects'], "Migrated layer should have effects array"
        assert result['effectCount'] == 0, "Migrated layer should have 0 effects"


class TestDocumentSerialization:
    """Test full document serialization with VectorLayer."""

    def test_document_with_vector_layer_serializes_correctly(self, page: Page):
        """Test that Document.serialize() includes VectorLayer with all props."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape || window.createShape;
            const { DropShadowEffect } = window.LayerEffects;
            const app = window.__stagforge_app__;

            if (!VectorLayer || !createShape) {
                return { error: 'VectorLayer or createVectorShape not available' };
            }

            if (!app || !app.documentManager) {
                return { error: 'App or documentManager not available' };
            }

            const doc = app.documentManager?.activeDocument;

            if (!doc) {
                return { error: 'No active document available' };
            }

            // Create vector layer
            const vectorLayer = new VectorLayer({
                width: 400,
                height: 400,
                name: 'Vector Layer'
            });

            vectorLayer.shapes.push(createShape({
                type: 'rect',
                x: 150,
                y: 150,
                width: 100,
                height: 80,
                fill: '#00FF00'
            }));
            vectorLayer.fitToContent();

            // Add effect
            vectorLayer.addEffect(new DropShadowEffect({
                offsetX: 8,
                offsetY: 8,
                blur: 10
            }));

            // Add to document
            doc.layerStack.addLayer(vectorLayer);

            // Serialize document
            const serialized = doc.serialize();

            // Find the vector layer in serialized data
            const vectorLayerData = serialized.layers.find(l => l.type === 'vector');

            return {
                totalLayers: serialized.layers.length,
                hasVectorLayer: !!vectorLayerData,
                vectorLayerHasOffsetX: vectorLayerData && 'offsetX' in vectorLayerData,
                vectorLayerHasOffsetY: vectorLayerData && 'offsetY' in vectorLayerData,
                vectorLayerHasEffects: vectorLayerData && Array.isArray(vectorLayerData.effects),
                vectorLayerEffectCount: vectorLayerData?.effects?.length || 0,
                vectorLayerOffsetX: vectorLayerData?.offsetX,
                vectorLayerOffsetY: vectorLayerData?.offsetY
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['hasVectorLayer'], "Serialized doc should have vector layer"
        assert result['vectorLayerHasOffsetX'], "Vector layer should have offsetX"
        assert result['vectorLayerHasOffsetY'], "Vector layer should have offsetY"
        assert result['vectorLayerHasEffects'], "Vector layer should have effects array"
        assert result['vectorLayerEffectCount'] == 1, \
            f"Vector layer should have 1 effect, got {result['vectorLayerEffectCount']}"
        assert result['vectorLayerOffsetX'] > 100, \
            f"Vector layer offsetX should be > 100, got {result['vectorLayerOffsetX']}"

    def test_document_deserializes_vector_layer_correctly(self, page: Page):
        """Test that Document.deserialize() restores VectorLayer with all props."""
        wait_for_app(page)

        result = page.evaluate('''async () => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape || window.createShape;
            const { DropShadowEffect, StrokeEffect } = window.LayerEffects;
            const app = window.__stagforge_app__;

            if (!VectorLayer || !createShape) {
                return { error: 'VectorLayer or createVectorShape not available' };
            }

            if (!app || !app.documentManager) {
                return { error: 'App or documentManager not available' };
            }

            // Need to dynamically import Document for deserialize
            const { Document } = await import('/static/js/core/Document.js');

            const doc = app.documentManager?.activeDocument;

            if (!doc) {
                return { error: 'No active document available' };
            }

            // Create vector layer with effects
            const vectorLayer = new VectorLayer({
                width: 400,
                height: 400,
                name: 'Test Vector'
            });

            vectorLayer.shapes.push(createShape({
                type: 'ellipse',
                cx: 250,
                cy: 250,
                rx: 60,
                ry: 40,
                fill: '#0000FF'
            }));
            vectorLayer.fitToContent();

            vectorLayer.addEffect(new DropShadowEffect({
                offsetX: 12,
                offsetY: 12,
                blur: 15,
                color: '#333333'
            }));
            vectorLayer.addEffect(new StrokeEffect({
                size: 4,
                position: 'outside',
                color: '#FFFF00'
            }));

            doc.layerStack.addLayer(vectorLayer);

            // Record original state
            const originalOffsetX = vectorLayer.offsetX;
            const originalOffsetY = vectorLayer.offsetY;
            const originalEffectCount = vectorLayer.effects.length;

            // Serialize
            const serialized = doc.serialize();

            // Deserialize to new document
            const restoredDoc = await Document.deserialize(serialized, app.eventBus);

            // Find vector layer
            const restoredVector = restoredDoc.layerStack.layers.find(l => l.type === 'vector');

            return {
                originalOffsetX,
                originalOffsetY,
                originalEffectCount,
                hasRestoredVector: !!restoredVector,
                restoredOffsetX: restoredVector?.offsetX,
                restoredOffsetY: restoredVector?.offsetY,
                restoredEffectCount: restoredVector?.effects?.length || 0,
                restoredShapeCount: restoredVector?.shapes?.length || 0,
                offsetsMatch: restoredVector?.offsetX === originalOffsetX &&
                             restoredVector?.offsetY === originalOffsetY,
                effectsMatch: restoredVector?.effects?.length === originalEffectCount
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['hasRestoredVector'], "Restored doc should have vector layer"
        assert result['offsetsMatch'], \
            f"Offsets should match: original=({result['originalOffsetX']}, {result['originalOffsetY']}), " \
            f"restored=({result['restoredOffsetX']}, {result['restoredOffsetY']})"
        assert result['effectsMatch'], \
            f"Effect count should match: original={result['originalEffectCount']}, " \
            f"restored={result['restoredEffectCount']}"
        assert result['restoredShapeCount'] == 1, \
            f"Should have 1 shape, got {result['restoredShapeCount']}"
