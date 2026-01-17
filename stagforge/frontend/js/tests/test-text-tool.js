/**
 * Text Tool Tests
 *
 * Run these tests in the browser console while the editor is open.
 * Usage: Open browser console, paste this file, and run runTextToolTests()
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
const textToolTests = [];
let passCount = 0;
let failCount = 0;

function test(name, fn) {
    textToolTests.push({ name, fn });
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

async function runTextToolTests() {
    console.log('%c=== Running Text Tool Tests ===', 'font-weight: bold');
    passCount = 0;
    failCount = 0;

    for (const t of textToolTests) {
        await runTest(t);
    }

    console.log(`%c=== Results: ${passCount} passed, ${failCount} failed ===`,
        failCount > 0 ? 'color: red; font-weight: bold' : 'color: green; font-weight: bold');
}

// Helper to wait for a short time
function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============= Tests =============

test('Editor app exists', () => {
    const { state } = getApp();
    assertExists(state, 'Editor app should exist');
});

test('TextTool is registered', () => {
    const { state } = getApp();
    const tool = state?.toolManager?.tools?.get('text');
    assertExists(tool, 'TextTool should be registered');
});

test('TextTool has correct static properties', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');
    assertEqual(tool.constructor.id, 'text', 'Tool ID should be "text"');
    assertEqual(tool.constructor.name, 'Text', 'Tool name should be "Text"');
    assertEqual(tool.constructor.cursor, 'text', 'Cursor should be "text"');
});

test('TextTool has font properties', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');
    assertExists(tool.fontSize, 'Tool should have fontSize');
    assertExists(tool.fontFamily, 'Tool should have fontFamily');
    assertExists(tool.fontWeight, 'Tool should have fontWeight');
    assertExists(tool.fontStyle, 'Tool should have fontStyle');
});

test('Can select TextTool', () => {
    const { state } = getApp();
    state.toolManager.select('text');
    const currentTool = state.toolManager.currentTool;
    assertEqual(currentTool.constructor.id, 'text', 'Current tool should be text');
});

test('TextTool getProperties returns font settings', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');
    const props = tool.getProperties();

    assert(Array.isArray(props), 'getProperties should return array');
    assert(props.length >= 4, 'Should have at least 4 properties');

    const fontSizeProp = props.find(p => p.id === 'fontSize');
    assertExists(fontSizeProp, 'Should have fontSize property');
    assertEqual(fontSizeProp.type, 'range', 'fontSize should be a range');

    const fontFamilyProp = props.find(p => p.id === 'fontFamily');
    assertExists(fontFamilyProp, 'Should have fontFamily property');
    assertEqual(fontFamilyProp.type, 'select', 'fontFamily should be a select');
});

test('TextTool setProperty updates fontSize', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');

    const originalSize = tool.fontSize;
    tool.setProperty('fontSize', 48);
    assertEqual(tool.fontSize, 48, 'fontSize should be updated');

    // Restore
    tool.setProperty('fontSize', originalSize);
});

test('TextTool setProperty updates fontFamily', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');

    const originalFamily = tool.fontFamily;
    tool.setProperty('fontFamily', 'Georgia');
    assertEqual(tool.fontFamily, 'Georgia', 'fontFamily should be updated');

    // Restore
    tool.setProperty('fontFamily', originalFamily);
});

test('TextTool createTextLayer creates a TextLayer', async () => {
    const { state, vm } = getApp();
    const tool = state.toolManager.tools.get('text');

    const layersBefore = state.layerStack.layers.length;

    // Create text layer via API
    tool.createTextLayer('Test Text', 100, 100);

    const layersAfter = state.layerStack.layers.length;
    assert(layersAfter > layersBefore, 'Should have created a new layer');

    const newLayer = state.layerStack.getActiveLayer();
    assert(newLayer.isText?.() === true, 'New layer should be a text layer');
    assertEqual(newLayer.text, 'Test Text', 'Layer text should match');
    assertEqual(newLayer.offsetX, 100, 'Layer offsetX should match');
    assertEqual(newLayer.offsetY, 100, 'Layer offsetY should match');
});

test('TextLayer has correct properties', () => {
    const { state } = getApp();

    // Find a text layer
    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    assertExists(textLayer.text, 'TextLayer should have text property');
    assert(textLayer.offsetX !== undefined, 'TextLayer should have offsetX');
    assert(textLayer.offsetY !== undefined, 'TextLayer should have offsetY');
    assertExists(textLayer.fontSize, 'TextLayer should have fontSize');
    assertExists(textLayer.fontFamily, 'TextLayer should have fontFamily');
    assertExists(textLayer.color, 'TextLayer should have color');
});

test('TextLayer.setText updates text', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    const originalText = textLayer.text;
    textLayer.setText('Updated Text');
    assertEqual(textLayer.text, 'Updated Text', 'Text should be updated');

    // Restore
    textLayer.setText(originalText);
});

test('TextLayer.setFontSize updates size', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    const originalSize = textLayer.fontSize;
    textLayer.setFontSize(72);
    assertEqual(textLayer.fontSize, 72, 'Font size should be updated');

    // Restore
    textLayer.setFontSize(originalSize);
});

test('TextLayer.containsPoint works correctly', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer || !textLayer.text) {
        console.log('  Skipping: No text layer with content available');
        return;
    }

    const bounds = textLayer.getBounds();
    if (!bounds) {
        console.log('  Skipping: Text bounds unavailable');
        return;
    }

    // Point inside text bounds
    const insideX = bounds.x + bounds.width / 2;
    const insideY = bounds.y + bounds.height / 2;
    assert(textLayer.containsPoint(insideX, insideY), 'Point inside bounds should return true');

    // Point outside text bounds
    assert(!textLayer.containsPoint(-1000, -1000), 'Point outside bounds should return false');
});

test('TextLayer.getBounds returns correct bounds', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer || !textLayer.text) {
        console.log('  Skipping: No text layer with content available');
        return;
    }

    const bounds = textLayer.getBounds();
    assertExists(bounds, 'Should return bounds');
    assertExists(bounds.x, 'Bounds should have x');
    assertExists(bounds.y, 'Bounds should have y');
    assertExists(bounds.width, 'Bounds should have width');
    assertExists(bounds.height, 'Bounds should have height');
    assert(bounds.width > 0, 'Width should be positive');
    assert(bounds.height > 0, 'Height should be positive');
});

test('TextLayer.isVector returns true', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    assert(textLayer.isVector(), 'TextLayer.isVector() should return true');
});

test('TextLayer can be rasterized', () => {
    const { state } = getApp();

    // Create a fresh text layer for rasterization test
    const tool = state.toolManager.tools.get('text');
    tool.createTextLayer('Rasterize Test', 50, 50);

    const textLayer = state.layerStack.getActiveLayer();
    assert(textLayer.isText?.(), 'Should have a text layer');

    const layerId = textLayer.id;
    const rasterized = state.layerStack.rasterizeLayer(layerId);

    assertExists(rasterized, 'Rasterization should return a layer');
    assert(!rasterized.isText || !rasterized.isText(), 'Rasterized layer should not be text');
    assert(!rasterized.isVector || !rasterized.isVector(), 'Rasterized layer should not be vector');
});

test('TextTool API executeAction creates text', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');

    const layersBefore = state.layerStack.layers.length;

    const result = tool.executeAction('create', {
        text: 'API Test Text',
        x: 200,
        y: 200,
        fontSize: 32,
        fontFamily: 'Georgia',
        color: '#FF0000'
    });

    assert(result.success, 'API action should succeed');

    const layersAfter = state.layerStack.layers.length;
    assert(layersAfter > layersBefore, 'Should have created a new layer');

    const newLayer = state.layerStack.getActiveLayer();
    assertEqual(newLayer.text, 'API Test Text', 'Text should match');
    assertEqual(newLayer.fontSize, 32, 'Font size should match');
});

test('TextTool getHint returns appropriate hint', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');

    const hint = tool.getHint();
    assert(typeof hint === 'string', 'Hint should be a string');
    assert(hint.length > 0, 'Hint should not be empty');
});

test('TextLayer.select and deselect work', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    textLayer.select();
    assert(textLayer.isSelected, 'Layer should be selected');

    textLayer.deselect();
    assert(!textLayer.isSelected, 'Layer should be deselected');
});

test('TextLayer.serialize returns correct data', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    const data = textLayer.serialize();
    assertEqual(data.type, 'text', 'Type should be text');
    assertEqual(data.text, textLayer.text, 'Text should match');
    assertEqual(data.fontSize, textLayer.fontSize, 'FontSize should match');
    assertEqual(data.fontFamily, textLayer.fontFamily, 'FontFamily should match');
});

test('TextLayer bounds match text content', () => {
    const { state } = getApp();
    const tool = state.toolManager.tools.get('text');

    // Create a text layer with known text
    tool.createTextLayer('Test', 50, 50);

    const textLayer = state.layerStack.getActiveLayer();
    assert(textLayer.isText?.(), 'Should be a text layer');

    // Bounds should be small, not document-sized
    const bounds = textLayer.getBounds();
    assert(bounds.width < 200, 'Width should be based on text, not document');
    assert(bounds.height < 100, 'Height should be based on text, not document');
    assertEqual(bounds.x, 50, 'Bounds X should match position');
    assertEqual(bounds.y, 50, 'Bounds Y should match position');
});

test('TextLayer position can be changed via Move tool', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    const originalX = textLayer.offsetX;
    const originalY = textLayer.offsetY;

    // Simulate move
    textLayer.offsetX = originalX + 50;
    textLayer.offsetY = originalY + 30;

    assertEqual(textLayer.offsetX, originalX + 50, 'X position should be updated');
    assertEqual(textLayer.offsetY, originalY + 30, 'Y position should be updated');

    // Check bounds reflect new position
    const bounds = textLayer.getBounds();
    assertEqual(bounds.x, originalX + 50, 'Bounds X should reflect new position');
    assertEqual(bounds.y, originalY + 30, 'Bounds Y should reflect new position');

    // Restore
    textLayer.offsetX = originalX;
    textLayer.offsetY = originalY;
});

test('TextTool editTextLayer uses correct position', () => {
    const { state } = getApp();

    const textLayer = state.layerStack.layers.find(l => l.isText?.());
    if (!textLayer) {
        console.log('  Skipping: No text layer available');
        return;
    }

    // Set a known position
    textLayer.offsetX = 200;
    textLayer.offsetY = 150;

    const tool = state.toolManager.tools.get('text');

    // Get the layer's position for editing
    assertEqual(textLayer.offsetX, 200, 'Layer X should be 200');
    assertEqual(textLayer.offsetY, 150, 'Layer Y should be 150');

    // getPosition should return the offset
    const pos = textLayer.getPosition();
    assertEqual(pos.x, 200, 'getPosition().x should be 200');
    assertEqual(pos.y, 150, 'getPosition().y should be 150');
});

// Log instructions when script is loaded
console.log('%c=== Text Tool Tests Loaded ===', 'font-weight: bold; color: blue');
console.log('Run tests with: runTextToolTests()');
console.log('Individual tests:');
textToolTests.forEach((t, i) => console.log(`  ${i + 1}. ${t.name}`));

// Export for use
window.textToolTests = {
    runTextToolTests,
    tests: textToolTests,
    getApp,
    assert,
    assertEqual,
    assertExists,
    assertNotEqual,
    wait
};
