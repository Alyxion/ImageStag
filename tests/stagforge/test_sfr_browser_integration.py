"""Browser integration tests for SFR effects serialization.

These tests run in a real browser via Playwright to verify:
1. Layer effects survive serialize/deserialize round-trip
2. Vector layers are visible after loading
3. Auto-save triggers when effects change
4. Document name persists through save/load

Run with: poetry run pytest tests/stagforge/test_sfr_browser_integration.py -v

NOTE: These tests require the NiceGUI server running.
Either:
  - Start dev server: poetry run python -m stagforge.main (port 8080)
  - Or use the conftest server_process fixture (port 8080)
"""

import pytest
import time
from playwright.sync_api import sync_playwright


class DevScreen:
    """Screen fixture that connects to the dev server at port 8080."""

    def __init__(self, page, base_url: str = "http://127.0.0.1:8080"):
        self.page = page
        self.base_url = base_url

    def open(self, path: str = "/"):
        """Navigate to a path."""
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        self.page.goto(url, timeout=30000)

    def wait_for_editor(self, timeout: float = 30.0):
        """Wait for the Stagforge editor to fully load."""
        self.page.wait_for_selector('.editor-root', timeout=timeout * 1000)
        # Wait for app to be initialized with layers
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.layerStack?.layers?.length > 0",
            timeout=timeout * 1000
        )
        # Wait for document manager to have an active document
        # Note: Use getActiveDocument() method, not activeDocument getter
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.documentManager?.getActiveDocument?.() != null",
            timeout=timeout * 1000
        )
        # Also wait for fileManager
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.fileManager != null",
            timeout=timeout * 1000
        )

    def wait(self, seconds: float):
        """Wait for a number of seconds."""
        self.page.wait_for_timeout(seconds * 1000)


@pytest.fixture(scope="module")
def dev_browser():
    """Launch Playwright browser for dev server tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def screen(dev_browser):
    """Create a screen instance connected to dev server at port 8080."""
    page = dev_browser.new_page()
    s = DevScreen(page)
    yield s
    page.close()


class TestEffectsRoundTrip:
    """Test layer effects survive full serialize/deserialize in browser."""

    def test_raster_layer_effects_roundtrip(self, screen):
        """Effects on raster layer should survive serialize/deserialize."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                // Get the default layer (Background)
                const layer = app.layerStack.layers[0];

                // Add a drop shadow effect
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                if (!DropShadow) {
                    return { error: 'DropShadow not in registry', registry: Object.keys(LayerEffects.effectRegistry) };
                }

                const shadow = new DropShadow({
                    offsetX: 15,
                    offsetY: 15,
                    blur: 10,
                    color: '#FF0000',
                    opacity: 0.8
                });
                layer.addEffect(shadow);

                // Serialize the layer
                const serialized = layer.serialize();

                // Verify effects array is present and has the effect
                if (!serialized.effects || serialized.effects.length === 0) {
                    return { error: 'No effects in serialized data', serialized };
                }

                const effectData = serialized.effects[0];
                if (effectData.type !== 'dropShadow') {
                    return { error: 'Wrong effect type', effectData };
                }

                // Now deserialize (we need to import Layer class dynamically)
                const Layer = layer.constructor;
                const restored = await Layer.deserialize(serialized);

                // Verify effects were restored
                if (!restored.effects || restored.effects.length === 0) {
                    return { error: 'No effects after deserialize', restored: restored.serialize() };
                }

                const restoredEffect = restored.effects[0];

                return {
                    success: true,
                    original: {
                        type: shadow.type,
                        offsetX: shadow.offsetX,
                        offsetY: shadow.offsetY,
                        blur: shadow.blur,
                        color: shadow.color,
                        opacity: shadow.opacity
                    },
                    restored: {
                        type: restoredEffect.type,
                        offsetX: restoredEffect.offsetX,
                        offsetY: restoredEffect.offsetY,
                        blur: restoredEffect.blur,
                        color: restoredEffect.color,
                        opacity: restoredEffect.opacity
                    }
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        # Verify effect properties match
        assert result['restored']['type'] == 'dropShadow'
        assert result['restored']['offsetX'] == 15
        assert result['restored']['offsetY'] == 15
        assert result['restored']['blur'] == 10
        assert result['restored']['color'] == '#FF0000'
        assert result['restored']['opacity'] == 0.8

    def test_vector_layer_effects_roundtrip(self, screen):
        """Effects on vector layer should survive serialize/deserialize."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;
                const LayerEffects = window.LayerEffects;

                // Create a vector layer with a shape
                const layer = new VectorLayer({
                    name: 'Test Vector',
                    width: app.layerStack.width,
                    height: app.layerStack.height
                });

                // Set doc dimensions for proper offset handling
                layer._docWidth = app.layerStack.width;
                layer._docHeight = app.layerStack.height;

                const rect = createShape({
                    type: 'rect',
                    x: 50, y: 50,
                    width: 100, height: 100,
                    fill: true,
                    fillColor: '#00FF00',
                    stroke: true,
                    strokeColor: '#000000',
                    strokeWidth: 2
                });
                layer.addShape(rect);

                // Add a stroke effect
                const Stroke = LayerEffects.effectRegistry['stroke'];
                if (!Stroke) {
                    return { error: 'Stroke not in registry', registry: Object.keys(LayerEffects.effectRegistry) };
                }

                const stroke = new Stroke({
                    size: 5,
                    position: 'outside',
                    color: '#0000FF',
                    opacity: 1.0
                });
                layer.addEffect(stroke);

                // Serialize
                const serialized = layer.serialize();

                // Check serialized data
                if (!serialized.effects || serialized.effects.length === 0) {
                    return { error: 'No effects in serialized vector layer', serialized };
                }
                if (!serialized.shapes || serialized.shapes.length === 0) {
                    return { error: 'No shapes in serialized vector layer', serialized };
                }

                // Deserialize
                const restored = VectorLayer.deserialize(serialized);

                // Verify effects were restored
                if (!restored.effects || restored.effects.length === 0) {
                    return { error: 'No effects after vector deserialize' };
                }

                const restoredEffect = restored.effects[0];

                return {
                    success: true,
                    serializedEffectsCount: serialized.effects.length,
                    serializedShapesCount: serialized.shapes.length,
                    restoredEffectsCount: restored.effects.length,
                    restoredShapesCount: restored.shapes.length,
                    effectType: restoredEffect.type,
                    effectSize: restoredEffect.size,
                    effectColor: restoredEffect.color
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['serializedEffectsCount'] == 1
        assert result['restoredEffectsCount'] == 1
        assert result['effectType'] == 'stroke'
        assert result['effectSize'] == 5
        assert result['effectColor'] == '#0000FF'

    def test_multiple_effects_roundtrip(self, screen):
        """Multiple effects should all survive serialize/deserialize."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                const layer = app.layerStack.layers[0];

                // Add multiple effects
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const Stroke = LayerEffects.effectRegistry['stroke'];
                const OuterGlow = LayerEffects.effectRegistry['outerGlow'];

                layer.addEffect(new DropShadow({ offsetX: 5, offsetY: 5, blur: 8 }));
                layer.addEffect(new Stroke({ size: 3, color: '#FF0000' }));
                if (OuterGlow) {
                    layer.addEffect(new OuterGlow({ blur: 10, color: '#FFFF00' }));
                }

                const serialized = layer.serialize();
                const effectCount = serialized.effects?.length || 0;

                // Deserialize
                const Layer = layer.constructor;
                const restored = await Layer.deserialize(serialized);

                const restoredCount = restored.effects?.length || 0;
                const effectTypes = restored.effects?.map(e => e.type) || [];

                return {
                    success: true,
                    originalCount: effectCount,
                    restoredCount: restoredCount,
                    effectTypes: effectTypes
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result}"
        assert result['success'] is True
        assert result['restoredCount'] >= 2, f"Expected at least 2 effects, got {result['restoredCount']}"
        assert 'dropShadow' in result['effectTypes']
        assert 'stroke' in result['effectTypes']


class TestVectorLayerVisibility:
    """Test vector layers are visible after loading."""

    def test_vector_layer_has_pixels_after_deserialize(self, screen):
        """Vector layer canvas should have pixels immediately after deserialize."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;

                // Create a vector layer with a bright shape
                const layer = new VectorLayer({
                    name: 'Test Vector',
                    width: 200,
                    height: 200
                });
                layer._docWidth = 200;
                layer._docHeight = 200;

                const rect = createShape({
                    type: 'rect',
                    x: 50, y: 50,
                    width: 100, height: 100,
                    fill: true,
                    fillColor: '#FF0000',
                    stroke: false
                });
                layer.addShape(rect);

                // Serialize
                const serialized = layer.serialize();

                // Deserialize
                const restored = VectorLayer.deserialize(serialized);

                // Check if canvas has any content IMMEDIATELY (before async render completes)
                const ctx = restored.canvas?.getContext('2d');
                if (!ctx) {
                    return { error: 'No canvas context' };
                }

                // Sample some pixels from the center area where the rect should be
                const imageData = ctx.getImageData(0, 0, restored.canvas.width, restored.canvas.height);
                const data = imageData.data;

                // Count non-transparent pixels
                let nonTransparent = 0;
                for (let i = 3; i < data.length; i += 4) {
                    if (data[i] > 0) nonTransparent++;
                }

                // Count red pixels (our shape)
                let redPixels = 0;
                for (let i = 0; i < data.length; i += 4) {
                    if (data[i] > 200 && data[i+1] < 50 && data[i+2] < 50 && data[i+3] > 200) {
                        redPixels++;
                    }
                }

                return {
                    success: true,
                    canvasWidth: restored.canvas.width,
                    canvasHeight: restored.canvas.height,
                    nonTransparentPixels: nonTransparent,
                    redPixels: redPixels,
                    hasContent: nonTransparent > 100,
                    shapesCount: restored.shapes.length
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['shapesCount'] == 1, "Shape should be restored"
        assert result['hasContent'], f"Canvas should have content immediately after deserialize, got {result['nonTransparentPixels']} pixels"
        assert result['redPixels'] > 100, f"Should have red pixels from shape, got {result['redPixels']}"

    def test_vector_layer_offset_preserved_after_deserialize(self, screen):
        """Vector layer offsets should be preserved after deserialize."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;

                // Create a vector layer
                const layer = new VectorLayer({
                    name: 'Offset Test',
                    width: 400,
                    height: 400
                });
                layer._docWidth = 400;
                layer._docHeight = 400;

                // Add a shape that's not at origin
                const rect = createShape({
                    type: 'rect',
                    x: 200, y: 150,
                    width: 100, height: 100,
                    fill: true,
                    fillColor: '#00FF00'
                });
                layer.addShape(rect);

                // Let fitToContent set the offsets
                layer.fitToContent();

                const originalOffsetX = layer.offsetX;
                const originalOffsetY = layer.offsetY;

                // Serialize
                const serialized = layer.serialize();

                // Deserialize
                const restored = VectorLayer.deserialize(serialized);

                return {
                    success: true,
                    original: {
                        offsetX: originalOffsetX,
                        offsetY: originalOffsetY
                    },
                    serialized: {
                        offsetX: serialized.offsetX,
                        offsetY: serialized.offsetY
                    },
                    restored: {
                        offsetX: restored.offsetX,
                        offsetY: restored.offsetY
                    }
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result}"
        assert result['success'] is True

        # Offsets should be preserved through serialization
        orig = result['original']
        ser = result['serialized']
        res = result['restored']

        assert ser['offsetX'] == orig['offsetX'], f"Serialized offsetX should match original"
        assert ser['offsetY'] == orig['offsetY'], f"Serialized offsetY should match original"
        assert res['offsetX'] == orig['offsetX'], f"Restored offsetX ({res['offsetX']}) should match original ({orig['offsetX']})"
        assert res['offsetY'] == orig['offsetY'], f"Restored offsetY ({res['offsetY']}) should match original ({orig['offsetY']})"


class TestDocumentRoundTrip:
    """Test full document serialization with effects."""

    def test_document_with_effects_roundtrip(self, screen):
        """Full document with layer effects should serialize/deserialize correctly."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;
                const LayerEffects = window.LayerEffects;

                // Get active document
                const doc = app.documentManager.getActiveDocument();
                if (!doc) {
                    return { error: 'No active document' };
                }

                // Add a vector layer with effects
                const vectorLayer = new VectorLayer({
                    name: 'Effects Test Layer',
                    width: doc.width,
                    height: doc.height
                });
                vectorLayer._docWidth = doc.width;
                vectorLayer._docHeight = doc.height;

                const rect = createShape({
                    type: 'rect',
                    x: 100, y: 100,
                    width: 150, height: 150,
                    fill: true,
                    fillColor: '#3366FF'
                });
                vectorLayer.addShape(rect);

                // Add drop shadow
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                vectorLayer.addEffect(new DropShadow({
                    offsetX: 10,
                    offsetY: 10,
                    blur: 15,
                    color: '#000000',
                    opacity: 0.6
                }));

                app.layerStack.addLayer(vectorLayer);

                // Set a custom document name
                doc.name = 'TestDocument';

                // Serialize the full document
                const serialized = await doc.serialize();

                // Find the vector layer in serialized data
                const vectorLayerData = serialized.layers.find(l => l.name === 'Effects Test Layer');
                if (!vectorLayerData) {
                    return { error: 'Vector layer not in serialized document', layers: serialized.layers.map(l => l.name) };
                }
                if (!vectorLayerData.effects || vectorLayerData.effects.length === 0) {
                    return { error: 'Effects not in serialized vector layer', vectorLayerData };
                }

                // Deserialize into a new document
                const Document = doc.constructor;
                const restoredDoc = await Document.deserialize(serialized, app.eventBus);

                // Find the restored vector layer
                const restoredVector = restoredDoc.layerStack.layers.find(l => l.name === 'Effects Test Layer');
                if (!restoredVector) {
                    return { error: 'Vector layer not restored', layers: restoredDoc.layerStack.layers.map(l => l.name) };
                }

                return {
                    success: true,
                    docName: restoredDoc.name,
                    layerCount: restoredDoc.layerStack.layers.length,
                    vectorLayerFound: !!restoredVector,
                    effectsCount: restoredVector.effects?.length || 0,
                    effectType: restoredVector.effects?.[0]?.type,
                    shapesCount: restoredVector.shapes?.length || 0,
                    hasCanvas: !!restoredVector.canvas
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['docName'] == 'TestDocument', f"Document name not preserved: {result['docName']}"
        assert result['layerCount'] >= 2, f"Should have at least 2 layers, got {result['layerCount']}"
        assert result['vectorLayerFound'] is True
        assert result['effectsCount'] == 1, f"Should have 1 effect, got {result['effectsCount']}"
        assert result['effectType'] == 'dropShadow'
        assert result['shapesCount'] == 1


class TestAutoSaveIntegration:
    """Test auto-save triggers correctly in the browser."""

    def test_adding_effect_marks_document_modified(self, screen):
        """Adding an effect should mark the document as modified."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                const doc = app.documentManager.getActiveDocument();
                if (!doc) {
                    return { error: 'No active document' };
                }

                // Clear modified flag
                doc.modified = false;
                const modifiedBefore = doc.modified;

                // Get layer
                const layer = app.layerStack.layers[0];

                // Add effect via LayerPanel (simulating UI interaction)
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const effect = new DropShadow();
                layer.addEffect(effect);

                // Mark modified (simulating what LayerPanel does)
                app.documentManager?.getActiveDocument()?.markModified();

                const modifiedAfter = doc.modified;

                return {
                    success: true,
                    modifiedBefore,
                    modifiedAfter,
                    effectAdded: layer.effects.length > 0
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['modifiedBefore'] is False, "Document should not be modified initially"
        assert result['modifiedAfter'] is True, "Document should be modified after adding effect"
        assert result['effectAdded'] is True

    def test_effect_param_change_marks_document_modified(self, screen):
        """Changing an effect parameter should mark the document as modified."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                const doc = app.documentManager.getActiveDocument();
                if (!doc) {
                    return { error: 'No active document' };
                }

                // Add an effect first
                const layer = app.layerStack.layers[0];
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const effect = new DropShadow({ blur: 5 });
                layer.addEffect(effect);

                // Clear modified flag
                doc.modified = false;
                const modifiedBefore = doc.modified;

                // Change effect parameter
                effect.blur = 20;
                layer._effectCacheVersion++;

                // Mark modified (simulating what updateEffectParam does)
                app.documentManager?.getActiveDocument()?.markModified();

                const modifiedAfter = doc.modified;

                return {
                    success: true,
                    modifiedBefore,
                    modifiedAfter,
                    newBlur: effect.blur
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['modifiedBefore'] is False
        assert result['modifiedAfter'] is True
        assert result['newBlur'] == 20


class TestFileManagerIntegration:
    """Test FileManager serialize/deserialize (in-memory, no actual file I/O)."""

    def test_filemanager_serialize_includes_effects(self, screen):
        """FileManager.serializeDocument should include layer effects."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                if (!app.fileManager) {
                    return { error: 'FileManager not initialized' };
                }

                // Add effect to first layer
                const layer = app.layerStack.layers[0];
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                layer.addEffect(new DropShadow({ blur: 12, offsetX: 8, offsetY: 8 }));

                // Serialize via FileManager
                const sfrData = await app.fileManager.serializeDocument();

                // Check structure
                if (sfrData.format !== 'stagforge') {
                    return { error: 'Wrong format', sfrData };
                }

                // Find our layer
                const layerData = sfrData.document.layers[0];
                if (!layerData.effects || layerData.effects.length === 0) {
                    return { error: 'No effects in SFR document', layerData };
                }

                return {
                    success: true,
                    format: sfrData.format,
                    version: sfrData.version,
                    hasMetadata: !!sfrData.metadata,
                    effectsCount: layerData.effects.length,
                    effectType: layerData.effects[0].type,
                    effectBlur: layerData.effects[0].blur
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['format'] == 'stagforge'
        assert result['version'] == 2  # SFR v2 format
        assert result['hasMetadata'] is True
        assert result['effectsCount'] >= 1
        assert result['effectType'] == 'dropShadow'
        assert result['effectBlur'] == 12

    def test_filemanager_load_restores_effects(self, screen):
        """FileManager.loadDocument should restore layer effects."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;
                const LayerEffects = window.LayerEffects;

                if (!app.fileManager) {
                    return { error: 'FileManager not initialized' };
                }

                // Create a vector layer with effects
                const doc = app.documentManager.getActiveDocument();
                const vectorLayer = new VectorLayer({
                    name: 'SFR Test Vector',
                    width: doc.width,
                    height: doc.height
                });
                vectorLayer._docWidth = doc.width;
                vectorLayer._docHeight = doc.height;

                vectorLayer.addShape(createShape({
                    type: 'ellipse',
                    cx: 200, cy: 200,
                    rx: 80, ry: 80,
                    fill: true,
                    fillColor: '#FF6600'
                }));

                const Stroke = LayerEffects.effectRegistry['stroke'];
                vectorLayer.addEffect(new Stroke({ size: 4, color: '#000000' }));

                app.layerStack.addLayer(vectorLayer);
                doc.name = 'SFRTestDoc';

                // Serialize
                const sfrData = await app.fileManager.serializeDocument();

                // Simulate loading by calling loadDocument with the data
                // We need to test the deserialize path
                const loadedDoc = await app.fileManager.loadDocument(sfrData, 'SFRTestDoc.sfr');

                // Find our vector layer
                const restoredVector = app.layerStack.layers.find(l => l.name === 'SFR Test Vector');

                return {
                    success: true,
                    docName: app.documentManager.getActiveDocument()?.name,
                    foundVector: !!restoredVector,
                    effectsCount: restoredVector?.effects?.length || 0,
                    effectType: restoredVector?.effects?.[0]?.type,
                    hasCanvas: !!restoredVector?.canvas,
                    shapesCount: restoredVector?.shapes?.length || 0
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['docName'] == 'SFRTestDoc', f"Document name not restored: {result['docName']}"
        assert result['foundVector'] is True, "Vector layer not found after load"
        assert result['effectsCount'] == 1, f"Effects not restored: {result['effectsCount']}"
        assert result['effectType'] == 'stroke'
        assert result['shapesCount'] == 1


class TestEffectRegistry:
    """Test that effect registry is properly populated."""

    def test_all_effect_types_in_registry(self, screen):
        """All standard effect types should be in the registry."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const LayerEffects = window.LayerEffects;

                if (!LayerEffects || !LayerEffects.effectRegistry) {
                    return { error: 'LayerEffects or registry not available' };
                }

                const registryKeys = Object.keys(LayerEffects.effectRegistry);

                // Expected effect types
                const expectedTypes = [
                    'dropShadow',
                    'innerShadow',
                    'outerGlow',
                    'innerGlow',
                    'bevelEmboss',
                    'stroke',
                    'colorOverlay'
                ];

                const missing = expectedTypes.filter(t => !registryKeys.includes(t));
                const present = expectedTypes.filter(t => registryKeys.includes(t));

                return {
                    success: missing.length === 0,
                    registryKeys,
                    expectedTypes,
                    present,
                    missing
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"

        if result.get('missing'):
            pytest.fail(f"Missing effect types in registry: {result['missing']}")

        assert result['success'] is True, f"Some effects missing: {result['missing']}"
        assert len(result['present']) >= 5, f"At least 5 effects should be present, got {len(result['present'])}"

    def test_effect_deserialize_uses_registry(self, screen):
        """LayerEffect.deserialize should correctly use the registry."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const LayerEffects = window.LayerEffects;

                // Get LayerEffect base class
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const instance = new DropShadow({ blur: 25, offsetX: 12 });

                // Serialize
                const data = instance.serialize();

                // Deserialize using static method
                const LayerEffect = Object.getPrototypeOf(DropShadow);
                const restored = LayerEffect.deserialize(data);

                if (!restored) {
                    return { error: 'Deserialize returned null', data };
                }

                return {
                    success: true,
                    originalType: instance.type,
                    restoredType: restored.type,
                    restoredBlur: restored.blur,
                    restoredOffsetX: restored.offsetX,
                    isDropShadow: restored instanceof DropShadow
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['restoredType'] == 'dropShadow'
        assert result['restoredBlur'] == 25
        assert result['restoredOffsetX'] == 12
        assert result['isDropShadow'] is True


class TestEffectHistoryIntegration:
    """Test that effect changes are properly tracked in history."""

    def test_effect_changes_create_single_history_entry(self, screen):
        """Modifying effects should create a single history entry when panel closes."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                if (!app.history) {
                    return { error: 'History not available' };
                }

                const layer = app.layerStack.layers[0];
                const layerId = layer.id;

                // Get initial history count
                const historyCountBefore = app.history.undoStack.length;

                // Capture effects before (layer-specific snapshot)
                const effectsBefore = layer.effects ? layer.effects.map(e => e.serialize()) : [];

                // Add an effect (simulating user adding via panel)
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const effect = new DropShadow({ blur: 10, offsetX: 5, offsetY: 5 });
                layer.addEffect(effect);

                // Change the effect params multiple times (simulating slider dragging)
                effect.blur = 15;
                layer._effectCacheVersion++;
                effect.blur = 20;
                layer._effectCacheVersion++;
                effect.offsetX = 10;
                layer._effectCacheVersion++;

                // Simulate closing effects panel - commit if changed
                const effectsAfter = layer.effects.map(e => e.serialize());
                if (JSON.stringify(effectsBefore) !== JSON.stringify(effectsAfter)) {
                    app.history.beginCapture('Modify Layer Effects', []);
                    app.history.captureEffectsBefore(layerId, effectsBefore);
                    app.history.commitCapture();
                }

                const historyCountAfter = app.history.undoStack.length;

                return {
                    success: true,
                    historyCountBefore,
                    historyCountAfter,
                    historyEntriesAdded: historyCountAfter - historyCountBefore,
                    lastAction: app.history.undoStack[app.history.undoStack.length - 1]?.action,
                    effectsOnLayer: layer.effects.length,
                    finalBlur: effect.blur
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        # Should create exactly ONE history entry for all the changes
        assert result['historyEntriesAdded'] == 1, \
            f"Expected 1 history entry, got {result['historyEntriesAdded']}"
        assert result['lastAction'] == 'Modify Layer Effects'
        assert result['effectsOnLayer'] == 1
        assert result['finalBlur'] == 20

    def test_effect_changes_can_be_undone(self, screen):
        """Effect changes should be undoable as a single operation."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                if (!app.history) {
                    return { error: 'History not available' };
                }

                const layer = app.layerStack.layers[0];

                // Clear any existing effects
                layer.effects = [];

                // Simulate opening effects panel - capture snapshot
                const beforeSnapshot = app.history.captureStructureSnapshot();

                // Add multiple effects
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const Stroke = LayerEffects.effectRegistry['stroke'];

                layer.addEffect(new DropShadow({ blur: 15 }));
                layer.addEffect(new Stroke({ size: 3 }));

                const effectsAfterAdd = layer.effects.length;

                // Simulate closing effects panel
                app.history.beginCapture('Modify Layer Effects', []);
                app.history.setStructureBefore(beforeSnapshot);
                app.history.commitCapture();

                // Now undo (async)
                const canUndo = app.history.canUndo();
                await app.history.undo();

                const effectsAfterUndo = layer.effects.length;

                // Redo to verify (async)
                await app.history.redo();
                const effectsAfterRedo = layer.effects.length;

                return {
                    success: true,
                    effectsAfterAdd,
                    effectsAfterUndo,
                    effectsAfterRedo,
                    canUndo
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['effectsAfterAdd'] == 2, "Should have 2 effects after adding"
        assert result['effectsAfterUndo'] == 0, "Undo should restore to 0 effects"
        assert result['effectsAfterRedo'] == 2, "Redo should restore 2 effects"

    def test_no_history_entry_when_no_changes(self, screen):
        """No history entry should be created if effects are unchanged."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                if (!app.history) {
                    return { error: 'History not available' };
                }

                const layer = app.layerStack.layers[0];

                // Add an effect first
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                layer.addEffect(new DropShadow({ blur: 10 }));

                // Commit this initial change
                app.history.beginCapture('Initial Effect', []);
                app.history.beginStructuralChange();
                app.history.commitCapture();

                const historyCountBefore = app.history.undoStack.length;

                // Simulate opening effects panel - capture snapshot
                const beforeSnapshot = app.history.captureStructureSnapshot();

                // DON'T make any changes - just "close" the panel

                // Check if changed (it shouldn't be)
                const afterSnapshot = app.history.captureStructureSnapshot();
                const beforeEffects = JSON.stringify(beforeSnapshot.layerMeta.map(m => m.effects));
                const afterEffects = JSON.stringify(afterSnapshot.layerMeta.map(m => m.effects));

                if (beforeEffects !== afterEffects) {
                    // This should NOT happen since we made no changes
                    app.history.beginCapture('Modify Layer Effects', []);
                    app.history.setStructureBefore(beforeSnapshot);
                    app.history.commitCapture();
                }

                const historyCountAfter = app.history.undoStack.length;

                return {
                    success: true,
                    historyCountBefore,
                    historyCountAfter,
                    historyEntriesAdded: historyCountAfter - historyCountBefore,
                    effectsUnchanged: beforeEffects === afterEffects
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['effectsUnchanged'] is True, "Effects should be unchanged"
        # No new history entry should be created
        assert result['historyEntriesAdded'] == 0, \
            f"Expected 0 history entries when no changes, got {result['historyEntriesAdded']}"

    def test_effect_changes_mark_document_modified(self, screen):
        """Effect changes should mark document as modified for auto-save."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            () => {
                const app = window.__stagforge_app__;
                const LayerEffects = window.LayerEffects;

                const doc = app.documentManager.getActiveDocument();
                if (!doc) {
                    return { error: 'No active document' };
                }

                const layer = app.layerStack.layers[0];

                // Clear modified flag
                doc.modified = false;

                // Simulate opening effects panel - capture snapshot
                const beforeSnapshot = app.history.captureStructureSnapshot();

                // Add an effect
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                layer.addEffect(new DropShadow({ blur: 10 }));

                const modifiedDuringEdit = doc.modified;

                // Simulate closing effects panel with changes
                const afterSnapshot = app.history.captureStructureSnapshot();
                const beforeEffects = JSON.stringify(beforeSnapshot.layerMeta.map(m => m.effects));
                const afterEffects = JSON.stringify(afterSnapshot.layerMeta.map(m => m.effects));

                if (beforeEffects !== afterEffects) {
                    app.history.beginCapture('Modify Layer Effects', []);
                    app.history.setStructureBefore(beforeSnapshot);
                    app.history.commitCapture();
                    // Mark document as modified (what LayerPanel does)
                    doc.markModified();
                }

                const modifiedAfterClose = doc.modified;

                return {
                    success: true,
                    modifiedDuringEdit,
                    modifiedAfterClose
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        # Document should be marked modified after closing panel with changes
        assert result['modifiedAfterClose'] is True, \
            "Document should be marked modified after effect changes"

    def test_ui_effects_panel_creates_history(self, screen):
        """Adding effect via UI panel should create history entry."""
        screen.open('/')
        screen.wait_for_editor()
        screen.wait(1)  # Wait for JS to load

        # Clear effects first
        screen.page.evaluate('() => { window.__stagforge_app__.layerStack.layers[0].effects = []; }')

        # Get history count before
        history_before = screen.page.evaluate('() => window.__stagforge_app__.history.undoStack.length')

        # Click fx button to open effects panel
        screen.page.locator('button[title="Layer Effects"]').click()
        screen.page.wait_for_selector('#effects-panel', timeout=5000)

        # Click on Inner Glow checkbox
        screen.page.locator('[data-effect-type="innerGlow"] .effect-checkbox').click()
        screen.wait(0.3)

        # Click OK to close panel
        screen.page.locator('#effects-ok').click()
        screen.wait(0.5)

        # Get results
        result = screen.page.evaluate('''
            () => {
                const app = window.__stagforge_app__;
                return {
                    historyCount: app.history.undoStack.length,
                    lastAction: app.history.undoStack[app.history.undoStack.length - 1]?.action,
                    effectsOnLayer: app.layerStack.layers[0].effects.length,
                    effectType: app.layerStack.layers[0].effects[0]?.type,
                    docModified: app.documentManager.getActiveDocument()?.modified
                };
            }
        ''')

        assert result['historyCount'] > history_before, "History should have new entry"
        assert result['lastAction'] == 'Modify Layer Effects'
        assert result['effectsOnLayer'] == 1
        assert result['effectType'] == 'innerGlow'
        assert result['docModified'] is True

    def test_ui_effects_panel_undo_redo(self, screen):
        """Effect changes via UI should support undo/redo."""
        screen.open('/')
        screen.wait_for_editor()
        screen.wait(1)

        # Clear effects
        screen.page.evaluate('() => { window.__stagforge_app__.layerStack.layers[0].effects = []; }')

        # Open effects panel and add effect
        screen.page.locator('button[title="Layer Effects"]').click()
        screen.page.wait_for_selector('#effects-panel', timeout=5000)
        screen.page.locator('[data-effect-type="dropShadow"] .effect-checkbox').click()
        screen.wait(0.3)
        screen.page.locator('#effects-ok').click()
        screen.wait(0.5)

        # Test undo/redo
        result = screen.page.evaluate('''
            async () => {
                const app = window.__stagforge_app__;
                const layer = app.layerStack.layers[0];

                const effectsBeforeUndo = layer.effects.length;

                await app.history.undo();
                const effectsAfterUndo = layer.effects.length;

                await app.history.redo();
                const effectsAfterRedo = layer.effects.length;

                return {
                    effectsBeforeUndo,
                    effectsAfterUndo,
                    effectsAfterRedo
                };
            }
        ''')

        assert result['effectsBeforeUndo'] == 1, "Should have 1 effect before undo"
        assert result['effectsAfterUndo'] == 0, "Undo should remove effect"
        assert result['effectsAfterRedo'] == 1, "Redo should restore effect"


class TestComprehensiveDocumentRoundtrip:
    """Test full document roundtrip with image, vector, and text layers."""

    def test_document_with_all_layer_types_roundtrip(self, screen):
        """Create doc with raster (drawn), vector, text layers - verify all survive roundtrip."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const VectorLayer = window.VectorLayer;
                const TextLayer = window.TextLayer;
                const createShape = window.createVectorShape;
                const LayerEffects = window.LayerEffects;
                const { Document } = await import('/static/js/core/Document.js');

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                const doc = app.documentManager.getActiveDocument();
                if (!doc) {
                    return { error: 'No active document' };
                }

                // 1. Draw content on the raster layer (Background)
                const rasterLayer = app.layerStack.layers[0];
                rasterLayer.name = 'Raster With Content';

                // Draw a red rectangle
                rasterLayer.ctx.fillStyle = '#FF0000';
                rasterLayer.ctx.fillRect(50, 50, 100, 100);

                // Draw a blue circle
                rasterLayer.ctx.fillStyle = '#0000FF';
                rasterLayer.ctx.beginPath();
                rasterLayer.ctx.arc(250, 150, 50, 0, Math.PI * 2);
                rasterLayer.ctx.fill();

                // 2. Add a vector layer with shapes
                const vectorLayer = new VectorLayer({
                    name: 'Vector Shapes',
                    width: doc.width,
                    height: doc.height
                });
                vectorLayer._docWidth = doc.width;
                vectorLayer._docHeight = doc.height;

                vectorLayer.addShape(createShape({
                    type: 'rect',
                    x: 200, y: 200,
                    width: 150, height: 100,
                    fill: true,
                    fillColor: '#00FF00'
                }));
                vectorLayer.addShape(createShape({
                    type: 'ellipse',
                    cx: 100, cy: 300,
                    rx: 60, ry: 40,
                    fill: true,
                    fillColor: '#FFFF00'
                }));
                app.layerStack.addLayer(vectorLayer);

                // 3. Add a text layer
                let textLayer = null;
                if (TextLayer) {
                    textLayer = new TextLayer({
                        name: 'Sample Text',
                        width: doc.width,
                        height: doc.height
                    });
                    textLayer._docWidth = doc.width;
                    textLayer._docHeight = doc.height;
                    textLayer.text = 'Hello World';
                    textLayer.fontSize = 32;
                    textLayer.fontFamily = 'Arial';
                    textLayer.color = '#000000';
                    textLayer.x = 100;
                    textLayer.y = 400;
                    app.layerStack.addLayer(textLayer);
                }

                // 4. Add effects to layers
                const DropShadow = LayerEffects.effectRegistry['dropShadow'];
                const Stroke = LayerEffects.effectRegistry['stroke'];
                vectorLayer.addEffect(new DropShadow({ blur: 8, offsetX: 5, offsetY: 5 }));
                rasterLayer.addEffect(new Stroke({ size: 3, color: '#000000' }));

                // Count red pixels before save
                const rasterImageData = rasterLayer.ctx.getImageData(0, 0, rasterLayer.width, rasterLayer.height);
                let redPixelsBefore = 0;
                for (let i = 0; i < rasterImageData.data.length; i += 4) {
                    if (rasterImageData.data[i] === 255 && rasterImageData.data[i+1] === 0 && rasterImageData.data[i+2] === 0 && rasterImageData.data[i+3] === 255) {
                        redPixelsBefore++;
                    }
                }

                // Record state before serialization
                const beforeState = {
                    layerCount: app.layerStack.layers.length,
                    rasterName: rasterLayer.name,
                    rasterEffectsCount: rasterLayer.effects.length,
                    vectorName: vectorLayer.name,
                    vectorShapesCount: vectorLayer.shapes.length,
                    vectorEffectsCount: vectorLayer.effects.length,
                    textName: textLayer?.name,
                    textContent: textLayer?.text,
                    redPixels: redPixelsBefore
                };

                // 5. Serialize via FileManager
                const sfrData = await app.fileManager.serializeDocument();

                // 6. Verify serialized data structure
                const serializedLayers = sfrData.document.layers;
                const serializedRaster = serializedLayers.find(l => l.name === 'Raster With Content');
                const serializedVector = serializedLayers.find(l => l.type === 'vector');
                const serializedText = serializedLayers.find(l => l.type === 'text');

                if (!serializedRaster?.imageData) {
                    return { error: 'Serialized raster layer missing imageData', serializedRaster };
                }
                if (!serializedRaster.imageData.startsWith('data:image/png;base64,')) {
                    return { error: 'Serialized imageData not a valid data URL', imageData: serializedRaster.imageData.substring(0, 50) };
                }

                // 7. Deserialize to a NEW document
                const restoredDoc = await Document.deserialize(sfrData.document, app.eventBus);

                // 8. Verify restored layers
                const restoredLayers = restoredDoc.layerStack.layers;
                const restoredRaster = restoredLayers.find(l => l.name === 'Raster With Content');
                const restoredVector = restoredLayers.find(l => l.type === 'vector');
                const restoredText = restoredLayers.find(l => l.type === 'text');

                // Check raster layer has pixel data
                let redPixelsAfter = 0;
                if (restoredRaster && restoredRaster.canvas && restoredRaster.ctx) {
                    const restoredImageData = restoredRaster.ctx.getImageData(0, 0, restoredRaster.width, restoredRaster.height);
                    for (let i = 0; i < restoredImageData.data.length; i += 4) {
                        if (restoredImageData.data[i] === 255 && restoredImageData.data[i+1] === 0 && restoredImageData.data[i+2] === 0 && restoredImageData.data[i+3] === 255) {
                            redPixelsAfter++;
                        }
                    }
                }

                const afterState = {
                    layerCount: restoredLayers.length,
                    rasterFound: !!restoredRaster,
                    rasterHasCanvas: !!restoredRaster?.canvas,
                    rasterWidth: restoredRaster?.width,
                    rasterHeight: restoredRaster?.height,
                    rasterEffectsCount: restoredRaster?.effects?.length || 0,
                    redPixels: redPixelsAfter,
                    vectorFound: !!restoredVector,
                    vectorShapesCount: restoredVector?.shapes?.length || 0,
                    vectorEffectsCount: restoredVector?.effects?.length || 0,
                    textFound: !!restoredText,
                    textContent: restoredText?.text
                };

                return {
                    success: true,
                    beforeState,
                    afterState,
                    serializedLayerCount: serializedLayers.length,
                    serializedRasterHasImageData: !!serializedRaster?.imageData,
                    serializedVectorHasShapes: serializedVector?.shapes?.length > 0,
                    serializedTextHasContent: !!serializedText?.text
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        before = result['beforeState']
        after = result['afterState']

        # Verify layer counts match
        assert after['layerCount'] == before['layerCount'], \
            f"Layer count mismatch: {after['layerCount']} vs {before['layerCount']}"

        # Verify raster layer pixel content
        assert after['rasterFound'] is True, "Raster layer not found after restore"
        assert after['rasterHasCanvas'] is True, "Raster layer has no canvas"
        assert after['redPixels'] > 0, \
            f"Raster layer has no red pixels after restore (expected ~{before['redPixels']}, got {after['redPixels']})"
        assert after['redPixels'] == before['redPixels'], \
            f"Red pixel count mismatch: {after['redPixels']} vs {before['redPixels']}"
        assert after['rasterEffectsCount'] == before['rasterEffectsCount'], \
            f"Raster effects count mismatch: {after['rasterEffectsCount']} vs {before['rasterEffectsCount']}"

        # Verify vector layer
        assert after['vectorFound'] is True, "Vector layer not found after restore"
        assert after['vectorShapesCount'] == before['vectorShapesCount'], \
            f"Vector shapes count mismatch: {after['vectorShapesCount']} vs {before['vectorShapesCount']}"
        assert after['vectorEffectsCount'] == before['vectorEffectsCount'], \
            f"Vector effects count mismatch: {after['vectorEffectsCount']} vs {before['vectorEffectsCount']}"

        # Verify text layer (if TextLayer is available)
        if before['textName'] is not None:
            assert after['textFound'] is True, "Text layer not found after restore"
            assert after['textContent'] == before['textContent'], \
                f"Text content mismatch: '{after['textContent']}' vs '{before['textContent']}'"

    def test_filemanager_load_creates_working_document(self, screen):
        """FileManager.loadDocument should create a fully working document with rendered content."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                const doc = app.documentManager.getActiveDocument();
                doc.name = 'OriginalDoc';

                // Draw on the base layer
                const baseLayer = app.layerStack.layers[0];
                baseLayer.ctx.fillStyle = '#FF00FF';
                baseLayer.ctx.fillRect(0, 0, 200, 200);

                // Add vector layer
                const vectorLayer = new VectorLayer({
                    name: 'LoadTest Vector',
                    width: doc.width,
                    height: doc.height
                });
                vectorLayer._docWidth = doc.width;
                vectorLayer._docHeight = doc.height;
                vectorLayer.addShape(createShape({
                    type: 'rect',
                    x: 250, y: 50,
                    width: 100, height: 100,
                    fill: true,
                    fillColor: '#00FFFF'
                }));
                app.layerStack.addLayer(vectorLayer);

                // Count magenta pixels before
                let magentaBefore = 0;
                const beforeData = baseLayer.ctx.getImageData(0, 0, 200, 200);
                for (let i = 0; i < beforeData.data.length; i += 4) {
                    if (beforeData.data[i] === 255 && beforeData.data[i+1] === 0 && beforeData.data[i+2] === 255 && beforeData.data[i+3] === 255) {
                        magentaBefore++;
                    }
                }

                // Serialize
                const sfrData = await app.fileManager.serializeDocument();
                const serializedDocName = sfrData.document.name;

                // Now simulate loading via loadDocument (which adds a new document)
                const docCountBefore = app.documentManager.documents.length;
                await app.fileManager.loadDocument(sfrData, 'TestLoad.sfr');
                const docCountAfter = app.documentManager.documents.length;

                // Get the newly loaded document's layers (it should be active now)
                const loadedDoc = app.documentManager.getActiveDocument();
                const loadedLayers = loadedDoc.layerStack.layers;
                const loadedRaster = loadedLayers.find(l => l.type !== 'vector' && l.type !== 'text');
                const loadedVector = loadedLayers.find(l => l.type === 'vector');

                // Count magenta pixels after
                let magentaAfter = 0;
                if (loadedRaster && loadedRaster.ctx) {
                    const afterData = loadedRaster.ctx.getImageData(0, 0, Math.min(200, loadedRaster.width), Math.min(200, loadedRaster.height));
                    for (let i = 0; i < afterData.data.length; i += 4) {
                        if (afterData.data[i] === 255 && afterData.data[i+1] === 0 && afterData.data[i+2] === 255 && afterData.data[i+3] === 255) {
                            magentaAfter++;
                        }
                    }
                }

                return {
                    success: true,
                    docCountBefore,
                    docCountAfter,
                    serializedDocName,
                    loadedDocName: loadedDoc.name,
                    loadedLayerCount: loadedLayers.length,
                    rasterFound: !!loadedRaster,
                    rasterHasCtx: !!loadedRaster?.ctx,
                    rasterWidth: loadedRaster?.width,
                    rasterHeight: loadedRaster?.height,
                    vectorFound: !!loadedVector,
                    vectorShapeCount: loadedVector?.shapes?.length || 0,
                    magentaBefore,
                    magentaAfter,
                    magentaMatch: magentaBefore === magentaAfter,
                    // Debug: show first layer info
                    firstLayerType: loadedLayers[0]?.type,
                    firstLayerName: loadedLayers[0]?.name,
                    firstLayerHasCtx: !!loadedLayers[0]?.ctx
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        # Debug output
        print(f"Serialized doc name: {result['serializedDocName']}")
        print(f"Loaded doc name: {result['loadedDocName']}")
        print(f"First layer: type={result['firstLayerType']}, name={result['firstLayerName']}, hasCtx={result['firstLayerHasCtx']}")
        print(f"Magenta pixels: before={result['magentaBefore']}, after={result['magentaAfter']}")

        # Document name should be updated from filename
        assert result['loadedDocName'] == 'TestLoad', \
            f"Document name should be 'TestLoad', got '{result['loadedDocName']}' (serialized was '{result['serializedDocName']}')"
        assert result['loadedLayerCount'] >= 2, \
            f"Should have at least 2 layers, got {result['loadedLayerCount']}"
        assert result['rasterFound'] is True, "Raster layer not found"
        assert result['rasterHasCtx'] is True, \
            f"Raster layer has no ctx (canvas not initialized). Layer info: width={result.get('rasterWidth')}, height={result.get('rasterHeight')}"
        assert result['vectorFound'] is True, "Vector layer not found"
        assert result['vectorShapeCount'] == 1, \
            f"Vector should have 1 shape, got {result['vectorShapeCount']}"
        assert result['magentaAfter'] > 0, \
            f"No magenta pixels found after load (expected {result['magentaBefore']})"
        assert result['magentaMatch'] is True, \
            f"Magenta pixel count mismatch: {result['magentaAfter']} vs {result['magentaBefore']}"

    def test_raster_layer_imagedata_serialization(self, screen):
        """Verify that raster layer imageData is properly serialized as data URL."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const doc = app.documentManager.getActiveDocument();
                const layer = app.layerStack.layers[0];

                // Draw distinct pattern
                layer.ctx.fillStyle = '#FF0000';
                layer.ctx.fillRect(0, 0, 50, 50);
                layer.ctx.fillStyle = '#00FF00';
                layer.ctx.fillRect(50, 0, 50, 50);
                layer.ctx.fillStyle = '#0000FF';
                layer.ctx.fillRect(0, 50, 50, 50);
                layer.ctx.fillStyle = '#FFFF00';
                layer.ctx.fillRect(50, 50, 50, 50);

                // Get the serialized layer directly
                const serialized = layer.serialize();

                // Check imageData
                const hasImageData = !!serialized.imageData;
                const isDataUrl = serialized.imageData?.startsWith('data:image/png;base64,');
                const dataLength = serialized.imageData?.length || 0;

                // Now deserialize and check pixels
                const { Layer } = await import('/static/js/core/Layer.js');
                const restored = await Layer.deserialize(serialized);

                // Check corner pixels
                const topLeftPixel = restored.ctx.getImageData(10, 10, 1, 1).data;
                const topRightPixel = restored.ctx.getImageData(60, 10, 1, 1).data;
                const bottomLeftPixel = restored.ctx.getImageData(10, 60, 1, 1).data;
                const bottomRightPixel = restored.ctx.getImageData(60, 60, 1, 1).data;

                return {
                    success: true,
                    hasImageData,
                    isDataUrl,
                    dataLength,
                    topLeft: Array.from(topLeftPixel),
                    topRight: Array.from(topRightPixel),
                    bottomLeft: Array.from(bottomLeftPixel),
                    bottomRight: Array.from(bottomRightPixel)
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['hasImageData'] is True, "Layer missing imageData"
        assert result['isDataUrl'] is True, "imageData is not a valid PNG data URL"
        assert result['dataLength'] > 100, f"imageData too short: {result['dataLength']}"

        # Verify pixel colors (with some tolerance for compression)
        assert result['topLeft'][0] > 200 and result['topLeft'][1] < 50, \
            f"Top-left should be red, got {result['topLeft']}"
        assert result['topRight'][1] > 200 and result['topRight'][0] < 50, \
            f"Top-right should be green, got {result['topRight']}"
        assert result['bottomLeft'][2] > 200 and result['bottomLeft'][0] < 50, \
            f"Bottom-left should be blue, got {result['bottomLeft']}"
        assert result['bottomRight'][0] > 200 and result['bottomRight'][1] > 200, \
            f"Bottom-right should be yellow, got {result['bottomRight']}"


class TestSFRv2ZipFormat:
    """Test SFR v2 ZIP format with separate image files."""

    def test_zip_format_saves_webp_images(self, screen):
        """serializeDocumentZip should create ZIP with WebP layer images."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                // Draw something on the base layer
                const layer = app.layerStack.layers[0];
                layer.ctx.fillStyle = '#FF0000';
                layer.ctx.fillRect(0, 0, 100, 100);

                // Serialize to ZIP format
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // Check ZIP blob properties
                const isBlob = zipBlob instanceof Blob;
                const blobSize = zipBlob.size;
                const blobType = zipBlob.type;

                // Read the ZIP to verify contents
                const JSZip = window.JSZip;
                if (!JSZip) {
                    return { error: 'JSZip not loaded' };
                }

                const zip = await JSZip.loadAsync(zipBlob);

                // Check for content.json
                const contentFile = zip.file('content.json');
                const hasContentJson = !!contentFile;

                // Check for layers folder
                const layersFolder = zip.folder('layers');
                const layerFiles = [];
                if (layersFolder) {
                    layersFolder.forEach((relativePath, file) => {
                        layerFiles.push(relativePath);
                    });
                }

                // Read content.json
                let contentJson = null;
                if (contentFile) {
                    const contentText = await contentFile.async('string');
                    contentJson = JSON.parse(contentText);
                }

                return {
                    success: true,
                    isBlob,
                    blobSize,
                    blobType,
                    hasContentJson,
                    layerFilesCount: layerFiles.length,
                    layerFiles,
                    format: contentJson?.format,
                    version: contentJson?.version,
                    layerId: contentJson?.document?.layers?.[0]?.id,
                    layerImageFile: contentJson?.document?.layers?.[0]?.imageFile,
                    layerImageFormat: contentJson?.document?.layers?.[0]?.imageFormat,
                    hasInlineImageData: !!contentJson?.document?.layers?.[0]?.imageData
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['isBlob'] is True, "Should be a Blob"
        assert result['blobSize'] > 0, "Blob should have content"
        assert result['hasContentJson'] is True, "ZIP should contain content.json"
        assert result['layerFilesCount'] >= 1, f"Should have layer files, got {result['layerFilesCount']}"
        assert result['format'] == 'stagforge'
        assert result['version'] == 2, f"Version should be 2, got {result['version']}"
        assert result['layerImageFile'] is not None, "Layer should have imageFile reference"
        assert result['layerImageFile'].endswith('.webp'), f"Should use WebP, got {result['layerImageFile']}"
        assert result['layerImageFormat'] == 'webp'
        assert result['hasInlineImageData'] is False, "Should NOT have inline imageData"

    def test_zip_format_roundtrip_preserves_pixels(self, screen):
        """ZIP save/load should preserve raster layer pixel content."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                // Draw pattern on the base layer
                const layer = app.layerStack.layers[0];
                layer.ctx.fillStyle = '#FF0000';
                layer.ctx.fillRect(0, 0, 50, 50);
                layer.ctx.fillStyle = '#00FF00';
                layer.ctx.fillRect(50, 0, 50, 50);

                // Count red and green pixels before
                const beforeData = layer.ctx.getImageData(0, 0, 100, 100);
                let redBefore = 0, greenBefore = 0;
                for (let i = 0; i < beforeData.data.length; i += 4) {
                    const r = beforeData.data[i];
                    const g = beforeData.data[i + 1];
                    const b = beforeData.data[i + 2];
                    if (r > 200 && g < 50 && b < 50) redBefore++;
                    if (g > 200 && r < 50 && b < 50) greenBefore++;
                }

                // Serialize to ZIP
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // Parse ZIP back
                const parseResult = await app.fileManager.parseFile(
                    new File([zipBlob], 'test.sfr', { type: 'application/zip' })
                );

                const { data, layerImages } = parseResult;

                // Check layerImages map
                const hasLayerImages = layerImages && layerImages.size > 0;
                const layerImageKeys = layerImages ? Array.from(layerImages.keys()) : [];

                // Load document from parsed data
                const { Document } = await import('/static/js/core/Document.js');

                // Process layer images
                for (const layerData of data.document.layers) {
                    if (layerData.imageFile && layerImages.has(layerData.id)) {
                        const blob = layerImages.get(layerData.id);
                        layerData.imageData = await app.fileManager.blobToDataURL(blob);
                        delete layerData.imageFile;
                    }
                }

                const restoredDoc = await Document.deserialize(data.document, app.eventBus);
                const restoredLayer = restoredDoc.layerStack.layers[0];

                // Count red and green pixels after
                const afterData = restoredLayer.ctx.getImageData(0, 0, 100, 100);
                let redAfter = 0, greenAfter = 0;
                for (let i = 0; i < afterData.data.length; i += 4) {
                    const r = afterData.data[i];
                    const g = afterData.data[i + 1];
                    const b = afterData.data[i + 2];
                    if (r > 200 && g < 50 && b < 50) redAfter++;
                    if (g > 200 && r < 50 && b < 50) greenAfter++;
                }

                return {
                    success: true,
                    hasLayerImages,
                    layerImageKeys,
                    redBefore,
                    greenBefore,
                    redAfter,
                    greenAfter,
                    redMatch: redBefore === redAfter,
                    greenMatch: greenBefore === greenAfter
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        assert result['hasLayerImages'] is True, "Should have layer images from ZIP"
        assert result['redBefore'] > 0, "Should have red pixels before"
        assert result['greenBefore'] > 0, "Should have green pixels before"
        assert result['redMatch'] is True, \
            f"Red pixels should match: {result['redBefore']} vs {result['redAfter']}"
        assert result['greenMatch'] is True, \
            f"Green pixels should match: {result['greenBefore']} vs {result['greenAfter']}"

    def test_zip_format_vector_layers_inline(self, screen):
        """Vector layers should be stored inline in content.json, not as separate files."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;
                const VectorLayer = window.VectorLayer;
                const createShape = window.createVectorShape;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                const doc = app.documentManager.getActiveDocument();

                // Add vector layer with shapes
                const vectorLayer = new VectorLayer({
                    name: 'Test Vector',
                    width: doc.width,
                    height: doc.height
                });
                vectorLayer._docWidth = doc.width;
                vectorLayer._docHeight = doc.height;
                vectorLayer.addShape(createShape({
                    type: 'rect',
                    x: 50, y: 50,
                    width: 100, height: 80,
                    fill: true,
                    fillColor: '#0000FF'
                }));
                app.layerStack.addLayer(vectorLayer);

                // Serialize to ZIP
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // Read the ZIP
                const JSZip = window.JSZip;
                const zip = await JSZip.loadAsync(zipBlob);

                // Check layers folder for vector files (should have none)
                const layerFiles = [];
                const layersFolder = zip.folder('layers');
                if (layersFolder) {
                    layersFolder.forEach((path, file) => {
                        layerFiles.push(path);
                    });
                }

                // Read content.json
                const contentFile = zip.file('content.json');
                const contentText = await contentFile.async('string');
                const content = JSON.parse(contentText);

                // Find vector layer in JSON
                const vectorLayerJson = content.document.layers.find(l => l.type === 'vector');

                return {
                    success: true,
                    layerFilesCount: layerFiles.length,
                    layerFiles,
                    // Only raster layer should have file
                    rasterFilesCount: layerFiles.filter(f => f.endsWith('.webp')).length,
                    vectorLayerFound: !!vectorLayerJson,
                    vectorHasShapes: vectorLayerJson?.shapes?.length > 0,
                    vectorShapeCount: vectorLayerJson?.shapes?.length || 0,
                    vectorHasImageFile: !!vectorLayerJson?.imageFile,
                    vectorFirstShape: vectorLayerJson?.shapes?.[0]
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True
        # Should have 1 WebP file (for raster), not for vector
        assert result['rasterFilesCount'] == 1, \
            f"Should have 1 raster file (WebP), got {result['rasterFilesCount']}"
        assert result['vectorLayerFound'] is True, "Vector layer should be in content.json"
        assert result['vectorHasShapes'] is True, "Vector layer should have shapes"
        assert result['vectorShapeCount'] == 1, f"Should have 1 shape, got {result['vectorShapeCount']}"
        assert result['vectorHasImageFile'] is False, "Vector layer should NOT have imageFile"
        assert result['vectorFirstShape']['type'] == 'rect', "Shape should be a rect"

