/**
 * Vector Layer Tests
 *
 * Run these tests in the browser console while the editor is open.
 * Usage: Open browser console, paste this file, and run runAllTests()
 */

// Get the editor app instance from the Vue component
function getApp() {
    const root = document.querySelector('.editor-root');
    if (!root || !root.__vue_app__) {
        console.error('Editor not found. Make sure the editor is loaded.');
        return null;
    }
    // Access the Vue component instance
    const vm = root.__vueParentComponent?.ctx || root._vnode?.component?.ctx;
    if (!vm) {
        console.error('Vue component not found.');
        return null;
    }
    // Get the internal app state
    const state = vm.getState?.();
    return state;
}

// Test framework
const tests = [];
let passCount = 0;
let failCount = 0;

function test(name, fn) {
    tests.push({ name, fn });
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message || 'Assertion failed');
    }
}

function assertEqual(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(message || `Expected ${expected}, got ${actual}`);
    }
}

function assertExists(value, message) {
    if (value === null || value === undefined) {
        throw new Error(message || 'Value should exist');
    }
}

async function runTest(test) {
    try {
        await test.fn();
        console.log(`%c PASS: ${test.name}`, 'color: green');
        passCount++;
    } catch (error) {
        console.log(`%c FAIL: ${test.name}`, 'color: red');
        console.error(error);
        failCount++;
    }
}

async function runAllTests() {
    console.log('%c=== Running Vector Layer Tests ===', 'font-weight: bold');
    passCount = 0;
    failCount = 0;

    for (const t of tests) {
        await runTest(t);
    }

    console.log(`%c=== Results: ${passCount} passed, ${failCount} failed ===`,
        failCount > 0 ? 'color: red; font-weight: bold' : 'color: green; font-weight: bold');
}

// ============= Tests =============

test('Editor app exists', () => {
    const app = getApp();
    assertExists(app, 'Editor app should exist');
});

test('LayerStack exists', () => {
    const app = getApp();
    assertExists(app?.layerStack, 'LayerStack should exist');
});

test('ToolManager exists', () => {
    const app = getApp();
    assertExists(app?.toolManager, 'ToolManager should exist');
});

test('RectTool is registered', () => {
    const app = getApp();
    const tool = app?.toolManager?.tools?.get('rect');
    assertExists(tool, 'RectTool should be registered');
});

test('VectorShapeEditTool is registered', () => {
    const app = getApp();
    const tool = app?.toolManager?.tools?.get('vector-edit');
    assertExists(tool, 'VectorShapeEditTool should be registered');
});

test('PenTool is registered', () => {
    const app = getApp();
    const tool = app?.toolManager?.tools?.get('pen');
    assertExists(tool, 'PenTool should be registered');
});

test('RectTool creates vector layer', async () => {
    const app = getApp();
    const rectTool = app.toolManager.tools.get('rect');

    // Count layers before
    const layersBefore = app.layerStack.layers.length;

    // Simulate drawing a rectangle
    rectTool.startX = 100;
    rectTool.startY = 100;
    rectTool.createVectorShape(200, 200, false);

    // Check that a layer was added
    const layersAfter = app.layerStack.layers.length;
    assert(layersAfter > layersBefore, 'Should have created a new layer');

    // Check that the new layer is a vector layer
    const newLayer = app.layerStack.getActiveLayer();
    assert(newLayer.isVector?.() === true, 'New layer should be a vector layer');
    assert(newLayer.shapes.length > 0, 'Vector layer should have at least one shape');
});

test('Vector layer renders shapes', async () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.()) {
        // Create a vector layer first
        const rectTool = app.toolManager.tools.get('rect');
        rectTool.startX = 50;
        rectTool.startY = 50;
        rectTool.createVectorShape(100, 100, false);
    }

    const vectorLayer = app.layerStack.getActiveLayer();
    assert(vectorLayer.isVector?.(), 'Should have a vector layer');

    // Force render
    vectorLayer.render();

    // Check that canvas has content (not all transparent)
    const imageData = vectorLayer.ctx.getImageData(0, 0, vectorLayer.width, vectorLayer.height);
    let hasContent = false;
    for (let i = 3; i < imageData.data.length; i += 4) {
        if (imageData.data[i] > 0) {
            hasContent = true;
            break;
        }
    }
    assert(hasContent, 'Vector layer canvas should have rendered content');
});

test('Shape containsPoint works', () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.() || layer.shapes.length === 0) {
        console.log('  Skipping: No vector shapes available');
        return;
    }

    const shape = layer.shapes[0];
    const bounds = shape.getBounds();

    // Test point inside
    const centerX = bounds.x + bounds.width / 2;
    const centerY = bounds.y + bounds.height / 2;
    assert(shape.containsPoint(centerX, centerY), 'Center point should be inside shape');

    // Test point outside
    assert(!shape.containsPoint(-1000, -1000), 'Far point should be outside shape');
});

test('Shape getControlPoints returns valid controls', () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.() || layer.shapes.length === 0) {
        console.log('  Skipping: No vector shapes available');
        return;
    }

    const shape = layer.shapes[0];
    const controls = shape.getControlPoints();

    assert(Array.isArray(controls), 'getControlPoints should return array');
    assert(controls.length > 0, 'Shape should have control points');

    for (const ctrl of controls) {
        assertExists(ctrl.id, 'Control point should have id');
        assertExists(ctrl.x, 'Control point should have x');
        assertExists(ctrl.y, 'Control point should have y');
        assertExists(ctrl.type, 'Control point should have type');
    }
});

test('VectorLayer.getShapeAt finds shapes', () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.() || layer.shapes.length === 0) {
        console.log('  Skipping: No vector shapes available');
        return;
    }

    const shape = layer.shapes[0];
    const bounds = shape.getBounds();
    const centerX = bounds.x + bounds.width / 2;
    const centerY = bounds.y + bounds.height / 2;

    const foundShape = layer.getShapeAt(centerX, centerY);
    assertExists(foundShape, 'Should find shape at center point');
    assertEqual(foundShape.id, shape.id, 'Found shape should be the correct shape');
});

test('VectorLayer.selectShape selects shape', () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.() || layer.shapes.length === 0) {
        console.log('  Skipping: No vector shapes available');
        return;
    }

    const shape = layer.shapes[0];

    // Clear selection first
    layer.clearSelection();
    assertEqual(layer.selectedShapeIds.size, 0, 'Selection should be cleared');

    // Select the shape
    layer.selectShape(shape.id);
    assert(layer.selectedShapeIds.has(shape.id), 'Shape should be selected');
    assert(shape.selected, 'Shape.selected flag should be true');
});

test('Shape.moveBy moves shape', () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.() || layer.shapes.length === 0) {
        console.log('  Skipping: No vector shapes available');
        return;
    }

    const shape = layer.shapes[0];
    const boundsBefore = shape.getBounds();

    // Move the shape
    shape.moveBy(10, 20);

    const boundsAfter = shape.getBounds();
    assertEqual(boundsAfter.x, boundsBefore.x + 10, 'Shape x should move by 10');
    assertEqual(boundsAfter.y, boundsBefore.y + 20, 'Shape y should move by 20');

    // Move back
    shape.moveBy(-10, -20);
});

test('VectorShapeEditTool can get vector layer', () => {
    const app = getApp();
    const editTool = app.toolManager.tools.get('vector-edit');

    // Select a vector layer first
    const vectorLayers = app.layerStack.layers.filter(l => l.isVector?.());
    if (vectorLayers.length === 0) {
        console.log('  Skipping: No vector layers available');
        return;
    }

    app.layerStack.setActiveLayerById(vectorLayers[0].id);

    const layer = editTool.getVectorLayer();
    assertExists(layer, 'Should get vector layer');
    assert(layer.isVector(), 'Retrieved layer should be vector');
});

test('Selection renders handles', () => {
    const app = getApp();
    const layer = app.layerStack.getActiveLayer();

    if (!layer?.isVector?.() || layer.shapes.length === 0) {
        console.log('  Skipping: No vector shapes available');
        return;
    }

    const shape = layer.shapes[0];
    layer.selectShape(shape.id);
    layer.render();

    // Visual check - log that selection handles should be visible
    console.log('  Visual check: Selection handles should be visible on canvas');

    // We can't easily verify the visual rendering, but we can check
    // that renderSelection is called (by existence of control points)
    const controls = shape.getControlPoints();
    assert(controls.length > 0, 'Selected shape should have control points for handles');
});

// Log instructions when script is loaded
console.log('%c=== Vector Layer Tests Loaded ===', 'font-weight: bold; color: blue');
console.log('Run tests with: runAllTests()');
console.log('Individual tests:');
tests.forEach((t, i) => console.log(`  ${i + 1}. ${t.name}`));

// Export for use
window.vectorLayerTests = {
    runAllTests,
    tests,
    getApp,
    assert,
    assertEqual,
    assertExists
};
