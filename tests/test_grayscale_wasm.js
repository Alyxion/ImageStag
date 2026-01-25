/**
 * Test grayscale WASM filter.
 *
 * Run with: node --experimental-modules tests/test_grayscale_wasm.js
 *
 * Note: These tests use the fallback implementation since WASM
 * requires a proper WASM build. The fallback uses the same algorithm.
 */

import { grayscaleFallback } from '../imagestag/filters/js/grayscale.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
    if (!condition) {
        console.error(`✗ FAILED: ${message}`);
        failed++;
        return false;
    }
    return true;
}

function assertApprox(actual, expected, tolerance, message) {
    const diff = Math.abs(actual - expected);
    if (diff > tolerance) {
        console.error(`✗ FAILED: ${message} (expected ~${expected}, got ${actual}, diff=${diff})`);
        failed++;
        return false;
    }
    return true;
}

/**
 * Create a mock ImageData object.
 */
function createImageData(data, width, height) {
    return {
        data: new Uint8ClampedArray(data),
        width,
        height
    };
}

/**
 * Test: Pure red becomes dark gray.
 */
function testGrayscaleRed() {
    const width = 10, height = 10;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;     // R
        data[i + 1] = 0;   // G
        data[i + 2] = 0;   // B
        data[i + 3] = 255; // A
    }

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    // 0.2126 * 255 ≈ 54
    const expectedGray = Math.round(0.2126 * 255);

    if (assertApprox(result.data[0], expectedGray, 1, 'Red grayscale value') &&
        assert(result.data[0] === result.data[1], 'R should equal G') &&
        assert(result.data[1] === result.data[2], 'G should equal B') &&
        assert(result.data[3] === 255, 'Alpha should be preserved')) {
        console.log('✓ testGrayscaleRed passed');
        passed++;
    }
}

/**
 * Test: Pure green becomes bright gray.
 */
function testGrayscaleGreen() {
    const width = 10, height = 10;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 0;       // R
        data[i + 1] = 255; // G
        data[i + 2] = 0;   // B
        data[i + 3] = 255; // A
    }

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    // 0.7152 * 255 ≈ 182
    const expectedGray = Math.round(0.7152 * 255);

    if (assertApprox(result.data[0], expectedGray, 1, 'Green grayscale value')) {
        console.log('✓ testGrayscaleGreen passed');
        passed++;
    }
}

/**
 * Test: Pure blue becomes very dark gray.
 */
function testGrayscaleBlue() {
    const width = 10, height = 10;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 0;       // R
        data[i + 1] = 0;   // G
        data[i + 2] = 255; // B
        data[i + 3] = 255; // A
    }

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    // 0.0722 * 255 ≈ 18
    const expectedGray = Math.round(0.0722 * 255);

    if (assertApprox(result.data[0], expectedGray, 1, 'Blue grayscale value')) {
        console.log('✓ testGrayscaleBlue passed');
        passed++;
    }
}

/**
 * Test: White stays white.
 */
function testGrayscaleWhite() {
    const width = 10, height = 10;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 255;     // R
        data[i + 1] = 255; // G
        data[i + 2] = 255; // B
        data[i + 3] = 255; // A
    }

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    // White should remain 255
    if (assert(result.data[0] === 255, 'White should remain 255')) {
        console.log('✓ testGrayscaleWhite passed');
        passed++;
    }
}

/**
 * Test: Alpha is preserved.
 */
function testGrayscalePreservesAlpha() {
    const width = 10, height = 10;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 128;     // R
        data[i + 1] = 128; // G
        data[i + 2] = 128; // B
        data[i + 3] = 100; // A (semi-transparent)
    }

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    let allAlphaPreserved = true;
    for (let i = 3; i < result.data.length; i += 4) {
        if (result.data[i] !== 100) {
            allAlphaPreserved = false;
            break;
        }
    }

    if (assert(allAlphaPreserved, 'All alpha values should be 100')) {
        console.log('✓ testGrayscalePreservesAlpha passed');
        passed++;
    }
}

/**
 * Test: R = G = B in output.
 */
function testGrayscaleRGBEqual() {
    const width = 20, height = 20;
    const data = new Uint8ClampedArray(width * height * 4);

    // Create colorful gradient
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const i = (y * width + x) * 4;
            data[i] = x * 12;        // R gradient
            data[i + 1] = y * 10;    // G gradient
            data[i + 2] = 128;       // Constant B
            data[i + 3] = 255;       // Full opacity
        }
    }

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    let allEqual = true;
    for (let i = 0; i < result.data.length; i += 4) {
        if (result.data[i] !== result.data[i + 1] ||
            result.data[i + 1] !== result.data[i + 2]) {
            allEqual = false;
            break;
        }
    }

    if (assert(allEqual, 'All R, G, B values should be equal')) {
        console.log('✓ testGrayscaleRGBEqual passed');
        passed++;
    }
}

/**
 * Test: Dimensions are preserved.
 */
function testGrayscaleDimensions() {
    const width = 100, height = 50;
    const data = new Uint8ClampedArray(width * height * 4);

    const imageData = createImageData(data, width, height);
    const result = grayscaleFallback(imageData);

    if (assert(result.width === width, 'Width should be preserved') &&
        assert(result.height === height, 'Height should be preserved') &&
        assert(result.data.length === width * height * 4, 'Data length should match')) {
        console.log('✓ testGrayscaleDimensions passed');
        passed++;
    }
}

// Run all tests
function runTests() {
    console.log('Running grayscale filter tests...\n');

    testGrayscaleRed();
    testGrayscaleGreen();
    testGrayscaleBlue();
    testGrayscaleWhite();
    testGrayscalePreservesAlpha();
    testGrayscaleRGBEqual();
    testGrayscaleDimensions();

    console.log(`\nResults: ${passed} passed, ${failed} failed`);

    if (failed > 0) {
        process.exit(1);
    }
}

runTests();
