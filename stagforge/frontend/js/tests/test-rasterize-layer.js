/**
 * Rasterize Layer Tests
 *
 * Run these tests in the browser console while the editor is open.
 * Usage: Open browser console, paste this file, and run runRasterizeTests()
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
    return { state, vm };
}

// Test framework
const rasterizeTests = [];
let passCount = 0;
let failCount = 0;

function test(name, fn) {
    rasterizeTests.push({ name, fn });
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

function assertNotEqual(actual, notExpected, message) {
    if (actual === notExpected) {
        throw new Error(message || `Expected value to not equal ${notExpected}`);
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

async function runRasterizeTests() {
    console.log('%c=== Running Rasterize Layer Tests ===', 'font-weight: bold');
    passCount = 0;
    failCount = 0;

    for (const t of rasterizeTests) {
        await runTest(t);
    }

    console.log(`%c=== Results: ${passCount} passed, ${failCount} failed ===`,
        failCount > 0 ? 'color: red; font-weight: bold' : 'color: green; font-weight: bold');
}

// ============= Tests =============

test('Editor app exists', () => {
    const { state } = getApp();
    assertExists(state, 'Editor app should exist');
});

test('LayerStack exists', () => {
    const { state } = getApp();
    assertExists(state?.layerStack, 'LayerStack should exist');
});

test('LayerStack has rasterizeLayer method', () => {
    const { state } = getApp();
    assertExists(state?.layerStack?.rasterizeLayer, 'LayerStack should have rasterizeLayer method');
    assertEqual(typeof state.layerStack.rasterizeLayer, 'function', 'rasterizeLayer should be a function');
});

test('Can create a vector layer with RectTool', async () => {
    const { state } = getApp();
    const rectTool = state.toolManager.tools.get('rect');
    assertExists(rectTool, 'RectTool should exist');

    const layersBefore = state.layerStack.layers.length;

    // Simulate drawing a rectangle
    rectTool.startX = 100;
    rectTool.startY = 100;
    rectTool.createVectorShape(200, 200, false);

    const layersAfter = state.layerStack.layers.length;
    assert(layersAfter > layersBefore, 'Should have created a new layer');

    const newLayer = state.layerStack.getActiveLayer();
    assert(newLayer.isVector?.() === true, 'New layer should be a vector layer');
});

test('Can rasterize a vector layer programmatically', async () => {
    const { state } = getApp();

    // First ensure we have a vector layer
    let vectorLayer = state.layerStack.getActiveLayer();
    if (!vectorLayer?.isVector?.()) {
        // Create one
        const rectTool = state.toolManager.tools.get('rect');
        rectTool.startX = 50;
        rectTool.startY = 50;
        rectTool.createVectorShape(150, 150, false);
        vectorLayer = state.layerStack.getActiveLayer();
    }

    assert(vectorLayer.isVector(), 'Should have a vector layer to rasterize');

    const vectorLayerId = vectorLayer.id;
    const originalName = vectorLayer.name;
    const originalIndex = state.layerStack.getLayerIndex(vectorLayerId);

    // Rasterize the layer
    const rasterLayer = state.layerStack.rasterizeLayer(vectorLayerId);

    assertExists(rasterLayer, 'Rasterize should return a layer');
    assert(!rasterLayer.isVector || !rasterLayer.isVector(), 'Rasterized layer should not be a vector layer');
    assertEqual(rasterLayer.name, originalName, 'Rasterized layer should keep the name');

    // Check it replaced the original in the stack
    const layerAtIndex = state.layerStack.layers[originalIndex];
    assertEqual(layerAtIndex, rasterLayer, 'Rasterized layer should replace original at same index');
});

test('Rasterized layer has canvas content', async () => {
    const { state } = getApp();

    // Create a fresh vector layer
    const rectTool = state.toolManager.tools.get('rect');
    state.toolManager.select('rect');
    rectTool.fillShape = true;
    rectTool.strokeShape = true;
    rectTool.startX = 20;
    rectTool.startY = 20;
    rectTool.createVectorShape(80, 80, false);

    const vectorLayer = state.layerStack.getActiveLayer();
    assert(vectorLayer.isVector(), 'Should have a vector layer');

    const vectorLayerId = vectorLayer.id;

    // Rasterize
    const rasterLayer = state.layerStack.rasterizeLayer(vectorLayerId);

    // Check canvas has content
    const imageData = rasterLayer.ctx.getImageData(0, 0, rasterLayer.width, rasterLayer.height);
    let hasContent = false;
    for (let i = 3; i < imageData.data.length; i += 4) {
        if (imageData.data[i] > 0) {
            hasContent = true;
            break;
        }
    }
    assert(hasContent, 'Rasterized layer should have canvas content');
});

test('Rasterizing non-existent layer returns null', () => {
    const { state } = getApp();
    const result = state.layerStack.rasterizeLayer('non-existent-layer-id');
    assertEqual(result, null, 'Rasterizing non-existent layer should return null');
});

test('Rasterizing a raster layer returns the same layer', () => {
    const { state } = getApp();

    // Find a raster layer or create one by rasterizing
    let rasterLayer = state.layerStack.layers.find(l => !l.isVector || !l.isVector());

    if (!rasterLayer) {
        // Create a vector layer and rasterize it
        const rectTool = state.toolManager.tools.get('rect');
        rectTool.startX = 10;
        rectTool.startY = 10;
        rectTool.createVectorShape(50, 50, false);
        const vectorLayer = state.layerStack.getActiveLayer();
        rasterLayer = state.layerStack.rasterizeLayer(vectorLayer.id);
    }

    const layerId = rasterLayer.id;
    const result = state.layerStack.rasterizeLayer(layerId);

    assertEqual(result, rasterLayer, 'Rasterizing a raster layer should return the same layer');
});

test('Vue component updateLayerList method exists', () => {
    const { vm } = getApp();
    assertExists(vm.updateLayerList, 'Vue component should have updateLayerList method');
    assertEqual(typeof vm.updateLayerList, 'function', 'updateLayerList should be a function');
});

test('confirmRasterize calls updateLayerList (method reference check)', () => {
    const { vm } = getApp();
    assertExists(vm.confirmRasterize, 'Vue component should have confirmRasterize method');
    assertEqual(typeof vm.confirmRasterize, 'function', 'confirmRasterize should be a function');

    // Check that the method string contains updateLayerList (not updateLayers)
    const methodSource = vm.confirmRasterize.toString();
    assert(
        methodSource.includes('updateLayerList'),
        'confirmRasterize should call updateLayerList, not updateLayers'
    );
    assert(
        !methodSource.includes('updateLayers()'),
        'confirmRasterize should NOT call updateLayers()'
    );
});

test('Full rasterize flow via showRasterizeDialog', async () => {
    const { state, vm } = getApp();

    // Create a vector layer
    const rectTool = state.toolManager.tools.get('rect');
    rectTool.startX = 30;
    rectTool.startY = 30;
    rectTool.createVectorShape(100, 100, false);

    const vectorLayer = state.layerStack.getActiveLayer();
    assert(vectorLayer.isVector(), 'Should have a vector layer');

    const vectorLayerId = vectorLayer.id;

    // Track if callback was called
    let callbackCalled = false;
    let callbackResult = null;

    // Show the rasterize dialog
    vm.showRasterizeDialog(vectorLayer, (confirmed) => {
        callbackCalled = true;
        callbackResult = confirmed;
    });

    // Verify dialog state was set
    assertEqual(vm.showRasterizePrompt, true, 'Rasterize prompt should be shown');
    assertEqual(vm.rasterizeLayerId, vectorLayerId, 'Rasterize layer ID should be set');

    // Confirm the rasterize
    vm.confirmRasterize();

    // Verify cleanup
    assertEqual(vm.showRasterizePrompt, false, 'Rasterize prompt should be hidden after confirm');
    assertEqual(vm.rasterizeLayerId, null, 'Rasterize layer ID should be cleared');

    // Verify callback was called
    assert(callbackCalled, 'Callback should have been called');
    assertEqual(callbackResult, true, 'Callback should receive true for confirmed');

    // Verify the layer was rasterized
    const layerIndex = state.layerStack.layers.findIndex(l => l.id === vectorLayerId || l.name === vectorLayer.name);
    const currentLayer = state.layerStack.layers[layerIndex];
    assert(!currentLayer.isVector || !currentLayer.isVector(), 'Layer should now be rasterized');
});

test('Cancel rasterize does not modify layer', async () => {
    const { state, vm } = getApp();

    // Create a vector layer
    const rectTool = state.toolManager.tools.get('rect');
    rectTool.startX = 40;
    rectTool.startY = 40;
    rectTool.createVectorShape(90, 90, false);

    const vectorLayer = state.layerStack.getActiveLayer();
    assert(vectorLayer.isVector(), 'Should have a vector layer');

    const vectorLayerId = vectorLayer.id;

    // Track if callback was called
    let callbackCalled = false;
    let callbackResult = null;

    // Show the rasterize dialog
    vm.showRasterizeDialog(vectorLayer, (confirmed) => {
        callbackCalled = true;
        callbackResult = confirmed;
    });

    // Cancel the rasterize
    vm.cancelRasterize();

    // Verify cleanup
    assertEqual(vm.showRasterizePrompt, false, 'Rasterize prompt should be hidden after cancel');
    assertEqual(vm.rasterizeLayerId, null, 'Rasterize layer ID should be cleared');

    // Verify callback was called with false
    assert(callbackCalled, 'Callback should have been called');
    assertEqual(callbackResult, false, 'Callback should receive false for cancelled');

    // Verify the layer is still a vector layer
    const currentLayer = state.layerStack.getLayerById(vectorLayerId);
    assertExists(currentLayer, 'Layer should still exist');
    assert(currentLayer.isVector?.(), 'Layer should still be a vector layer');
});

// Log instructions when script is loaded
console.log('%c=== Rasterize Layer Tests Loaded ===', 'font-weight: bold; color: blue');
console.log('Run tests with: runRasterizeTests()');
console.log('Individual tests:');
rasterizeTests.forEach((t, i) => console.log(`  ${i + 1}. ${t.name}`));

// Export for use
window.rasterizeLayerTests = {
    runRasterizeTests,
    tests: rasterizeTests,
    getApp,
    assert,
    assertEqual,
    assertExists,
    assertNotEqual
};
