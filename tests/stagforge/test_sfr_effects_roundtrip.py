"""
Comprehensive tests for SFR effects round-trip serialization.

These tests verify that layer effects are properly:
1. Serialized to JSON
2. Included in document serialization
3. Deserialized with correct parameters
4. Visible after loading (for both raster and vector layers)
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
        "() => window.__stagforge_app__ && window.__stagforge_app__.layerStack && window.VectorLayer && window.LayerEffects",
        timeout=15000
    )


class TestLayerEffectsSerialization:
    """Test that individual layer effects serialize correctly."""

    def test_drop_shadow_effect_serializes_all_params(self, page: Page):
        """Test DropShadowEffect.serialize() includes all parameters."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const { DropShadowEffect } = window.LayerEffects;

            const effect = new DropShadowEffect({
                offsetX: 15,
                offsetY: 20,
                blur: 25,
                spread: 5,
                color: '#FF5500',
                colorOpacity: 0.65,
                blendMode: 'multiply'
            });

            const serialized = effect.serialize();

            return {
                serialized,
                hasType: 'type' in serialized,
                hasOffsetX: 'offsetX' in serialized,
                hasOffsetY: 'offsetY' in serialized,
                hasBlur: 'blur' in serialized,
                hasSpread: 'spread' in serialized,
                hasColor: 'color' in serialized,
                hasColorOpacity: 'colorOpacity' in serialized,
                hasBlendMode: 'blendMode' in serialized,
                valuesCorrect: serialized.offsetX === 15 &&
                              serialized.offsetY === 20 &&
                              serialized.blur === 25 &&
                              serialized.spread === 5 &&
                              serialized.color === '#FF5500' &&
                              serialized.colorOpacity === 0.65 &&
                              serialized.blendMode === 'multiply'
            };
        }''')

        assert result['hasType'], f"Serialized effect missing 'type': {result['serialized']}"
        assert result['hasOffsetX'], f"Serialized effect missing 'offsetX': {result['serialized']}"
        assert result['hasOffsetY'], f"Serialized effect missing 'offsetY': {result['serialized']}"
        assert result['hasBlur'], f"Serialized effect missing 'blur': {result['serialized']}"
        assert result['hasColor'], f"Serialized effect missing 'color': {result['serialized']}"
        assert result['hasBlendMode'], f"Serialized effect missing 'blendMode': {result['serialized']}"
        assert result['valuesCorrect'], f"Serialized values incorrect: {result['serialized']}"

    def test_stroke_effect_serializes_all_params(self, page: Page):
        """Test StrokeEffect.serialize() includes all parameters."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const { StrokeEffect } = window.LayerEffects;

            const effect = new StrokeEffect({
                size: 8,
                position: 'center',
                color: '#00FF00',
                colorOpacity: 0.9
            });

            const serialized = effect.serialize();

            return {
                serialized,
                hasSize: 'size' in serialized,
                hasPosition: 'position' in serialized,
                hasColor: 'color' in serialized,
                valuesCorrect: serialized.size === 8 &&
                              serialized.position === 'center' &&
                              serialized.color === '#00FF00'
            };
        }''')

        assert result['hasSize'], f"Serialized effect missing 'size': {result['serialized']}"
        assert result['hasPosition'], f"Serialized effect missing 'position': {result['serialized']}"
        assert result['valuesCorrect'], f"Serialized values incorrect: {result['serialized']}"


class TestLayerWithEffectsSerialization:
    """Test that layers with effects serialize correctly."""

    def test_raster_layer_serialize_includes_effects(self, page: Page):
        """Test Layer.serialize() includes effects array with all effect data."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const app = window.__stagforge_app__;
            const layer = app.layerStack.getActiveLayer();
            const { DropShadowEffect, StrokeEffect } = window.LayerEffects;

            // Clear existing effects
            layer.effects = [];

            // Add effects
            layer.addEffect(new DropShadowEffect({
                offsetX: 10,
                offsetY: 10,
                blur: 15,
                color: '#000000'
            }));
            layer.addEffect(new StrokeEffect({
                size: 5,
                position: 'outside',
                color: '#FF0000'
            }));

            // Serialize layer
            const serialized = layer.serialize();

            return {
                hasEffects: 'effects' in serialized,
                effectsIsArray: Array.isArray(serialized.effects),
                effectCount: serialized.effects?.length || 0,
                effects: serialized.effects,
                firstEffectType: serialized.effects?.[0]?.type,
                secondEffectType: serialized.effects?.[1]?.type,
                firstEffectHasParams: serialized.effects?.[0]?.offsetX === 10 &&
                                     serialized.effects?.[0]?.blur === 15,
                secondEffectHasParams: serialized.effects?.[1]?.size === 5
            };
        }''')

        assert result['hasEffects'], "Layer serialization missing 'effects' field"
        assert result['effectsIsArray'], "Layer serialization 'effects' should be array"
        assert result['effectCount'] == 2, f"Expected 2 effects, got {result['effectCount']}"
        assert result['firstEffectType'] == 'dropShadow', \
            f"First effect type should be 'dropShadow', got {result['firstEffectType']}"
        assert result['secondEffectType'] == 'stroke', \
            f"Second effect type should be 'stroke', got {result['secondEffectType']}"
        assert result['firstEffectHasParams'], \
            f"First effect params incorrect: {result['effects'][0] if result['effects'] else 'N/A'}"
        assert result['secondEffectHasParams'], \
            f"Second effect params incorrect: {result['effects'][1] if result['effects'] else 'N/A'}"

    def test_vector_layer_serialize_includes_effects(self, page: Page):
        """Test VectorLayer.serialize() includes effects array."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape;
            const { DropShadowEffect, OuterGlowEffect } = window.LayerEffects;

            // Create vector layer
            const layer = new VectorLayer({
                width: 200,
                height: 200,
                name: 'Test Vector'
            });

            // Add a shape
            layer.shapes.push(createShape({
                type: 'rect',
                x: 50, y: 50, width: 100, height: 80,
                fill: '#0000FF'
            }));
            layer.fitToContent();

            // Add effects
            layer.addEffect(new DropShadowEffect({
                offsetX: 8,
                offsetY: 8,
                blur: 12,
                color: '#333333'
            }));
            layer.addEffect(new OuterGlowEffect({
                blur: 10,
                spread: 2,
                color: '#FFFF00'
            }));

            // Serialize
            const serialized = layer.serialize();

            return {
                hasEffects: 'effects' in serialized,
                effectsIsArray: Array.isArray(serialized.effects),
                effectCount: serialized.effects?.length || 0,
                effects: serialized.effects,
                effectTypes: (serialized.effects || []).map(e => e.type)
            };
        }''')

        assert result['hasEffects'], "VectorLayer serialization missing 'effects' field"
        assert result['effectsIsArray'], "VectorLayer 'effects' should be array"
        assert result['effectCount'] == 2, \
            f"Expected 2 effects, got {result['effectCount']}. Effects: {result['effects']}"
        assert 'dropShadow' in result['effectTypes'], \
            f"Should have dropShadow effect, got types: {result['effectTypes']}"
        assert 'outerGlow' in result['effectTypes'], \
            f"Should have outerGlow effect, got types: {result['effectTypes']}"


class TestEffectDeserialization:
    """Test that effects deserialize correctly from serialized data."""

    def test_effect_registry_is_set(self, page: Page):
        """Test that the effect registry is properly initialized."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const { effectRegistry, LayerEffect } = window.LayerEffects;

            return {
                hasRegistry: !!effectRegistry,
                registryKeys: effectRegistry ? Object.keys(effectRegistry) : [],
                hasDropShadow: effectRegistry?.dropShadow !== undefined,
                hasStroke: effectRegistry?.stroke !== undefined,
                hasOuterGlow: effectRegistry?.outerGlow !== undefined
            };
        }''')

        assert result['hasRegistry'], "Effect registry not set"
        assert result['hasDropShadow'], f"Registry missing dropShadow. Keys: {result['registryKeys']}"
        assert result['hasStroke'], f"Registry missing stroke. Keys: {result['registryKeys']}"

    def test_layer_effect_deserialize_creates_correct_type(self, page: Page):
        """Test LayerEffect.deserialize() creates the correct effect type."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const { LayerEffect, DropShadowEffect, StrokeEffect } = window.LayerEffects;

            // Serialized effect data
            const shadowData = {
                type: 'dropShadow',
                offsetX: 12,
                offsetY: 14,
                blur: 18,
                color: '#AA5500'
            };

            const strokeData = {
                type: 'stroke',
                size: 6,
                position: 'inside',
                color: '#00AA00'
            };

            // Deserialize
            const shadowEffect = LayerEffect.deserialize(shadowData);
            const strokeEffect = LayerEffect.deserialize(strokeData);

            return {
                shadowCreated: shadowEffect !== null,
                shadowIsDropShadow: shadowEffect instanceof DropShadowEffect,
                shadowType: shadowEffect?.type,
                shadowOffsetX: shadowEffect?.offsetX,
                shadowBlur: shadowEffect?.blur,
                shadowColor: shadowEffect?.color,

                strokeCreated: strokeEffect !== null,
                strokeIsStrokeEffect: strokeEffect instanceof StrokeEffect,
                strokeType: strokeEffect?.type,
                strokeSize: strokeEffect?.size,
                strokePosition: strokeEffect?.position
            };
        }''')

        assert result['shadowCreated'], "DropShadow effect not created from deserialize"
        assert result['shadowIsDropShadow'], "Deserialized effect is not DropShadowEffect instance"
        assert result['shadowOffsetX'] == 12, f"Shadow offsetX should be 12, got {result['shadowOffsetX']}"
        assert result['shadowBlur'] == 18, f"Shadow blur should be 18, got {result['shadowBlur']}"

        assert result['strokeCreated'], "Stroke effect not created from deserialize"
        assert result['strokeIsStrokeEffect'], "Deserialized effect is not StrokeEffect instance"
        assert result['strokeSize'] == 6, f"Stroke size should be 6, got {result['strokeSize']}"

    def test_raster_layer_deserialize_restores_effects(self, page: Page):
        """Test Layer.deserialize() properly restores effects."""
        wait_for_app(page)

        result = page.evaluate('''async () => {
            const { Layer } = await import('/static/js/core/Layer.js');
            const { DropShadowEffect, StrokeEffect } = window.LayerEffects;

            // Create a layer with effects
            const original = new Layer({ width: 100, height: 100 });
            original.addEffect(new DropShadowEffect({
                offsetX: 5, offsetY: 5, blur: 10, color: '#000000'
            }));
            original.addEffect(new StrokeEffect({
                size: 3, position: 'outside', color: '#FF0000'
            }));

            const originalEffectCount = original.effects.length;

            // Serialize
            const serialized = original.serialize();
            const serializedEffectCount = serialized.effects?.length || 0;

            // Deserialize
            const restored = await Layer.deserialize(serialized);

            return {
                originalEffectCount,
                serializedEffectCount,
                restoredEffectCount: restored.effects.length,
                effectsRestored: restored.effects.length === originalEffectCount,
                restoredTypes: restored.effects.map(e => e.type),
                firstEffectParams: {
                    offsetX: restored.effects[0]?.offsetX,
                    blur: restored.effects[0]?.blur
                },
                secondEffectParams: {
                    size: restored.effects[1]?.size,
                    position: restored.effects[1]?.position
                }
            };
        }''')

        assert result['effectsRestored'], \
            f"Effects not restored: original={result['originalEffectCount']}, " \
            f"serialized={result['serializedEffectCount']}, restored={result['restoredEffectCount']}"
        assert 'dropShadow' in result['restoredTypes'], f"dropShadow not in restored types: {result['restoredTypes']}"
        assert 'stroke' in result['restoredTypes'], f"stroke not in restored types: {result['restoredTypes']}"
        assert result['firstEffectParams']['offsetX'] == 5, "First effect offsetX not restored"
        assert result['secondEffectParams']['size'] == 3, "Second effect size not restored"

    def test_vector_layer_deserialize_restores_effects(self, page: Page):
        """Test VectorLayer.deserialize() properly restores effects."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape;
            const { DropShadowEffect, StrokeEffect, OuterGlowEffect } = window.LayerEffects;

            // Create vector layer with effects
            const original = new VectorLayer({
                width: 200, height: 200, name: 'Test'
            });
            original.shapes.push(createShape({
                type: 'rect', x: 50, y: 50, width: 80, height: 60, fill: '#00FF00'
            }));
            original.fitToContent();

            original.addEffect(new DropShadowEffect({
                offsetX: 7, offsetY: 9, blur: 14, color: '#222222'
            }));
            original.addEffect(new OuterGlowEffect({
                blur: 12, spread: 3, color: '#FFFF00'
            }));

            const originalEffectCount = original.effects.length;

            // Serialize
            const serialized = original.serialize();
            const serializedEffectCount = serialized.effects?.length || 0;
            const serializedEffectTypes = (serialized.effects || []).map(e => e.type);

            // Deserialize
            const restored = VectorLayer.deserialize(serialized);

            const restoredEffectCount = restored.effects.length;
            const restoredEffectTypes = restored.effects.map(e => e.type);

            return {
                originalEffectCount,
                serializedEffectCount,
                serializedEffectTypes,
                restoredEffectCount,
                restoredEffectTypes,
                effectsRestored: restoredEffectCount === originalEffectCount,
                typesMatch: JSON.stringify(serializedEffectTypes) === JSON.stringify(restoredEffectTypes),
                shadowBlur: restored.effects.find(e => e.type === 'dropShadow')?.blur,
                glowSpread: restored.effects.find(e => e.type === 'outerGlow')?.spread
            };
        }''')

        assert result['effectsRestored'], \
            f"VectorLayer effects not restored: original={result['originalEffectCount']}, " \
            f"serialized={result['serializedEffectCount']}, restored={result['restoredEffectCount']}"
        assert result['typesMatch'], \
            f"Effect types don't match: serialized={result['serializedEffectTypes']}, " \
            f"restored={result['restoredEffectTypes']}"
        assert result['shadowBlur'] == 14, f"Shadow blur should be 14, got {result['shadowBlur']}"
        assert result['glowSpread'] == 3, f"Glow spread should be 3, got {result['glowSpread']}"


class TestVectorLayerVisibility:
    """Test that vector layers are visible after deserialization."""

    def test_vector_layer_has_canvas_after_deserialize(self, page: Page):
        """Test VectorLayer has valid canvas data after deserialize."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape;

            // Create vector layer with shapes
            const original = new VectorLayer({
                width: 200, height: 200, name: 'Test'
            });

            // Add a visible shape
            original.shapes.push(createShape({
                type: 'rect',
                x: 50, y: 50,
                width: 100, height: 80,
                fill: '#FF0000',
                fillOpacity: 1.0
            }));
            original.fitToContent();
            original.render();

            // Check original has pixels
            const origCtx = original.ctx;
            const origData = origCtx.getImageData(0, 0, original.width, original.height);
            let origNonTransparentPixels = 0;
            for (let i = 3; i < origData.data.length; i += 4) {
                if (origData.data[i] > 0) origNonTransparentPixels++;
            }

            // Serialize
            const serialized = original.serialize();

            // Deserialize
            const restored = VectorLayer.deserialize(serialized);

            // Check restored has pixels
            const restoredCtx = restored.ctx;
            const restoredData = restoredCtx.getImageData(0, 0, restored.width, restored.height);
            let restoredNonTransparentPixels = 0;
            for (let i = 3; i < restoredData.data.length; i += 4) {
                if (restoredData.data[i] > 0) restoredNonTransparentPixels++;
            }

            return {
                originalWidth: original.width,
                originalHeight: original.height,
                origNonTransparentPixels,
                restoredWidth: restored.width,
                restoredHeight: restored.height,
                restoredNonTransparentPixels,
                hasContent: restoredNonTransparentPixels > 0,
                shapeCount: restored.shapes.length,
                visible: restored.visible
            };
        }''')

        assert result['shapeCount'] == 1, f"Should have 1 shape, got {result['shapeCount']}"
        assert result['visible'], "Layer should be visible"
        assert result['hasContent'], \
            f"Restored VectorLayer has no pixels. " \
            f"Original: {result['origNonTransparentPixels']}, Restored: {result['restoredNonTransparentPixels']}"

    def test_vector_layer_offset_preserved(self, page: Page):
        """Test VectorLayer offset is preserved after deserialize."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const VectorLayer = window.VectorLayer;
            const createShape = window.createVectorShape;

            // Create vector layer with shape NOT at origin
            const original = new VectorLayer({
                width: 400, height: 400, name: 'Offset Test'
            });

            // Shape at 200,200 (not at origin)
            original.shapes.push(createShape({
                type: 'rect',
                x: 200, y: 200,
                width: 100, height: 80,
                fill: '#00FF00'
            }));
            original.fitToContent();
            original.render();

            const originalOffsetX = original.offsetX;
            const originalOffsetY = original.offsetY;

            // Serialize and deserialize
            const serialized = original.serialize();
            const restored = VectorLayer.deserialize(serialized);

            return {
                originalOffsetX,
                originalOffsetY,
                serializedOffsetX: serialized.offsetX,
                serializedOffsetY: serialized.offsetY,
                restoredOffsetX: restored.offsetX,
                restoredOffsetY: restored.offsetY,
                offsetsPreserved: restored.offsetX === originalOffsetX &&
                                 restored.offsetY === originalOffsetY,
                offsetsNotZero: originalOffsetX > 100 && originalOffsetY > 100
            };
        }''')

        assert result['offsetsNotZero'], \
            f"Original offsets should be > 100, got ({result['originalOffsetX']}, {result['originalOffsetY']})"
        assert result['offsetsPreserved'], \
            f"Offsets not preserved: original=({result['originalOffsetX']}, {result['originalOffsetY']}), " \
            f"restored=({result['restoredOffsetX']}, {result['restoredOffsetY']})"


class TestDocumentEffectsRoundTrip:
    """Test full document round-trip with effects."""

    def test_document_serialize_includes_layer_effects(self, page: Page):
        """Test Document.serialize() includes effects from all layers."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const app = window.__stagforge_app__;
            const doc = app.documentManager?.activeDocument;
            const { DropShadowEffect, StrokeEffect } = window.LayerEffects;

            if (!doc) {
                return { error: 'No active document' };
            }

            // Get first layer and add effects
            const layer = doc.layerStack.layers[0];
            layer.effects = []; // Clear existing

            layer.addEffect(new DropShadowEffect({
                offsetX: 10, offsetY: 10, blur: 15
            }));
            layer.addEffect(new StrokeEffect({
                size: 4, position: 'outside', color: '#0000FF'
            }));

            // Serialize document
            const serialized = doc.serialize();

            const firstLayer = serialized.layers?.[0];

            return {
                hasLayers: Array.isArray(serialized.layers),
                layerCount: serialized.layers?.length || 0,
                firstLayerHasEffects: firstLayer && 'effects' in firstLayer,
                firstLayerEffectCount: firstLayer?.effects?.length || 0,
                firstLayerEffects: firstLayer?.effects
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        assert result['hasLayers'], "Document serialization missing layers"
        assert result['firstLayerHasEffects'], "First layer missing effects in serialized document"
        assert result['firstLayerEffectCount'] == 2, \
            f"Expected 2 effects in serialized layer, got {result['firstLayerEffectCount']}. " \
            f"Effects: {result['firstLayerEffects']}"


class TestAutoSaveEffectChanges:
    """Test that effect changes trigger document modification for auto-save."""

    def test_adding_effect_marks_document_modified(self, page: Page):
        """Test that adding an effect marks document as modified."""
        wait_for_app(page)

        result = page.evaluate('''() => {
            const app = window.__stagforge_app__;
            const doc = app.documentManager?.activeDocument;
            const { DropShadowEffect } = window.LayerEffects;

            if (!doc) {
                return { error: 'No active document' };
            }

            // Reset modified state
            doc.modified = false;
            const beforeModified = doc.modified;

            // Add an effect
            const layer = doc.layerStack.getActiveLayer();
            layer.addEffect(new DropShadowEffect());

            // Check if document is marked modified
            const afterModified = doc.modified;

            return {
                beforeModified,
                afterModified,
                wasMarkedModified: afterModified === true
            };
        }''')

        if 'error' in result:
            pytest.skip(result['error'])

        # This test documents the CURRENT behavior (likely fails)
        # The fix should make this pass
        assert result['wasMarkedModified'], \
            f"Adding effect should mark document modified. Before: {result['beforeModified']}, After: {result['afterModified']}"
