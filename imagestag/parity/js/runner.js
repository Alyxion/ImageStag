/**
 * Cross-platform parity test runner for JavaScript.
 *
 * This module runs parity tests for filters and layer effects,
 * saving outputs to the shared temp directory for comparison with Python.
 *
 * Ground truth images are fetched from the API or loaded from pre-generated
 * files to ensure Python and JavaScript use identical inputs.
 *
 * Usage (Node.js):
 *   import { ParityTestRunner } from './runner.js';
 *   const runner = new ParityTestRunner();
 *   runner.registerFilter('grayscale', grayscaleFilter);
 *   await runner.runTests('filters', 'grayscale');
 *
 * Usage (Browser via API):
 *   POST /imgstag/parity/run
 *   { "category": "filters", "name": "grayscale" }
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';
import { encode as encodePng } from 'fast-png';

import {
    TEST_WIDTH,
    TEST_HEIGHT,
    TEST_INPUTS,
    DEFAULT_INPUT_NAMES,
} from './constants.js';

// Get project root (this file is at imagestag/parity/js/runner.js)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..', '..', '..');

// Configuration - uses project-local tmp/ folder
const PARITY_TEST_DIR = path.join(PROJECT_ROOT, 'tmp', 'parity');
const INPUTS_DIR = path.join(PARITY_TEST_DIR, 'inputs');
const OUTPUT_FORMAT = 'png';  // Using PNG for maximum compatibility

// API base URL for fetching ground truth images (when server is running)
const API_BASE_URL = process.env.IMAGESTAG_API_URL || 'http://localhost:8080/imgstag';

/**
 * Load ground truth input from pre-generated .raw file.
 * These files are created by Python's save_ground_truth_inputs().
 *
 * File format: [width: u32] [height: u32] [channels: u32] [data: u8[]]
 *
 * @param {string} inputName - Input name (e.g., 'deer', 'astronaut')
 * @returns {Object|null} - ImageData-like object or null if not found
 */
function loadGroundTruthFromFile(inputName) {
    const inputPath = path.join(INPUTS_DIR, `${inputName}.raw`);

    if (!fs.existsSync(inputPath)) {
        // Try legacy .rgba format
        const legacyPath = path.join(INPUTS_DIR, `${inputName}.rgba`);
        if (fs.existsSync(legacyPath)) {
            const buffer = fs.readFileSync(legacyPath);
            const width = buffer.readUInt32LE(0);
            const height = buffer.readUInt32LE(4);
            const data = new Uint8ClampedArray(buffer.slice(8));
            const channels = data.length / (width * height);
            return { data, width, height, channels };
        }
        return null;
    }

    const buffer = fs.readFileSync(inputPath);
    const width = buffer.readUInt32LE(0);
    const height = buffer.readUInt32LE(4);
    const channels = buffer.readUInt32LE(8);
    const data = new Uint8ClampedArray(buffer.slice(12));

    return { data, width, height, channels };
}

/**
 * Fetch ground truth input from API.
 * Requires the ImageStag server to be running.
 *
 * @param {string} inputName - Input name (e.g., 'deer', 'astronaut')
 * @returns {Promise<Object|null>} - ImageData-like object or null
 */
async function fetchGroundTruthFromAPI(inputName) {
    try {
        const url = `${API_BASE_URL}/parity/inputs/${inputName}.raw`;
        const response = await fetch(url);

        if (!response.ok) {
            console.warn(`Failed to fetch ${inputName} from API: ${response.status}`);
            return null;
        }

        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        const width = buffer.readUInt32LE(0);
        const height = buffer.readUInt32LE(4);
        const channels = buffer.readUInt32LE(8);
        const data = new Uint8ClampedArray(buffer.slice(12));

        return { data, width, height, channels };
    } catch (error) {
        console.warn(`Failed to fetch ${inputName} from API:`, error.message);
        return null;
    }
}

/**
 * Generate test input using a ground truth image.
 *
 * First tries to load from pre-generated file, then falls back to API.
 *
 * @param {string} name - Input name (e.g., 'deer', 'astronaut')
 * @param {number} width - Expected width (for validation)
 * @param {number} height - Expected height (for validation)
 * @returns {Promise<Object>} - ImageData-like object with data, width, height, channels
 */
export async function generateInput(name, width = TEST_WIDTH, height = TEST_HEIGHT) {
    // Get expected channel count from TEST_INPUTS
    const inputConfig = TEST_INPUTS[name];
    const expectedChannels = inputConfig ? inputConfig.channels : 4;

    // First try loading from pre-generated file
    let input = loadGroundTruthFromFile(name);

    // Fall back to API if file not found
    if (!input) {
        input = await fetchGroundTruthFromAPI(name);
    }

    if (!input) {
        throw new Error(
            `Ground truth input '${name}' not found. ` +
            `Run Python tests first to generate inputs, or start the API server.`
        );
    }

    // Validate dimensions
    if (input.width !== width || input.height !== height) {
        console.warn(
            `Input ${name} has unexpected dimensions: ${input.width}x${input.height}, ` +
            `expected ${width}x${height}`
        );
    }

    // Set channels from input or expected
    input.channels = input.channels || expectedChannels;

    return input;
}

/**
 * Strip _f32 suffix from a string for unified naming.
 */
function stripF32Suffix(s) {
    return s.endsWith('_f32') ? s.slice(0, -4) : s;
}

/**
 * Get the output path for a test result.
 *
 * Naming convention: {filter}_{input}_js_{bitdepth}.{format}
 *
 * @param {string} category - "filters" or "layer_effects"
 * @param {string} name - Filter/effect name (may include _f32 suffix)
 * @param {string} testCase - Test case identifier (may include _f32 suffix)
 * @param {string} bitDepth - "u8" or "f32"
 * @param {string} format - Output format
 * @returns {string} - Output file path
 */
export function getOutputPath(category, name, testCase, bitDepth = 'u8', format = null) {
    // Strip _f32 suffixes - bit depth is indicated by the _u8/_f32 suffix instead
    const cleanName = stripF32Suffix(name);
    const cleanTestCase = stripF32Suffix(testCase);

    // f32 always uses PNG for 16-bit precision
    const fmt = format || (bitDepth === 'f32' ? 'png' : OUTPUT_FORMAT);

    const categoryDir = path.join(PARITY_TEST_DIR, category);
    fs.mkdirSync(categoryDir, { recursive: true });
    return path.join(categoryDir, `${cleanName}_${cleanTestCase}_js_${bitDepth}.${fmt}`);
}

/**
 * Create side-by-side comparison image [original | output].
 *
 * @param {Object} inputImage - Original input image
 * @param {Object} outputImage - Processed output image
 * @param {string} bitDepth - "u8" or "f32"
 * @returns {Object} - Combined image data
 */
function createSideBySide(inputImage, outputImage, bitDepth = 'u8') {
    const outWidth = outputImage.width;
    const outHeight = outputImage.height;
    const outChannels = outputImage.channels || 4;

    const inWidth = inputImage.width;
    const inHeight = inputImage.height;
    const inChannels = inputImage.channels || 4;

    // Target channels is max of input/output, at least 3 for visibility
    const targetChannels = Math.max(outChannels, inChannels, 3);

    // Combined width is 2x output width (original is resized/padded to match output)
    const combinedWidth = outWidth * 2;
    const combinedHeight = outHeight;

    // Handle dtype conversion for f32 (12-bit) outputs
    const is12bit = bitDepth === 'f32' && outputImage.data instanceof Uint16Array;
    const maxVal = is12bit ? 4095 : 255;

    // Create combined buffer
    const ArrayType = is12bit ? Uint16Array : Uint8ClampedArray;
    const combined = new ArrayType(combinedWidth * combinedHeight * targetChannels);

    // Helper to ensure image has target channels
    function ensureChannels(img, targetCh, isInput = false) {
        const ch = img.channels || 4;
        const w = img.width;
        const h = img.height;
        const data = img.data;

        // Create result array
        const result = new ArrayType(w * h * targetCh);

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const srcIdx = (y * w + x) * ch;
                const dstIdx = (y * w + x) * targetCh;

                if (ch === 1) {
                    // Grayscale to RGB(A)
                    let val = data[srcIdx];
                    // Convert input u8 to 12-bit if needed
                    if (isInput && is12bit && !(data instanceof Uint16Array)) {
                        val = Math.round(val * 4095 / 255);
                    }
                    result[dstIdx] = val;
                    result[dstIdx + 1] = val;
                    result[dstIdx + 2] = val;
                    if (targetCh === 4) {
                        result[dstIdx + 3] = maxVal;
                    }
                } else if (ch === 3) {
                    // RGB to RGBA
                    for (let c = 0; c < 3; c++) {
                        let val = data[srcIdx + c];
                        if (isInput && is12bit && !(data instanceof Uint16Array)) {
                            val = Math.round(val * 4095 / 255);
                        }
                        result[dstIdx + c] = val;
                    }
                    if (targetCh === 4) {
                        result[dstIdx + 3] = maxVal;
                    }
                } else if (ch === 4) {
                    // RGBA - copy all or truncate to RGB
                    for (let c = 0; c < targetCh; c++) {
                        let val = data[srcIdx + c];
                        if (isInput && is12bit && !(data instanceof Uint16Array)) {
                            val = Math.round(val * 4095 / 255);
                        }
                        result[dstIdx + c] = val;
                    }
                }
            }
        }
        return { data: result, width: w, height: h, channels: targetCh };
    }

    // Prepare input (resize/pad to match output dimensions if needed)
    let preparedInput = ensureChannels(inputImage, targetChannels, true);
    const preparedOutput = ensureChannels(outputImage, targetChannels, false);

    // If input is smaller than output, center it with transparent padding
    if (inWidth < outWidth || inHeight < outHeight) {
        const padded = new ArrayType(outWidth * outHeight * targetChannels);
        const offsetX = Math.floor((outWidth - inWidth) / 2);
        const offsetY = Math.floor((outHeight - inHeight) / 2);

        // Fill with transparent/black background
        if (targetChannels === 4) {
            for (let i = 0; i < padded.length; i += 4) {
                padded[i] = 0;
                padded[i + 1] = 0;
                padded[i + 2] = 0;
                padded[i + 3] = 0; // transparent
            }
        }

        // Copy input to center
        for (let y = 0; y < inHeight; y++) {
            for (let x = 0; x < inWidth; x++) {
                const srcIdx = (y * inWidth + x) * targetChannels;
                const dstIdx = ((y + offsetY) * outWidth + (x + offsetX)) * targetChannels;
                for (let c = 0; c < targetChannels; c++) {
                    padded[dstIdx + c] = preparedInput.data[srcIdx + c];
                }
            }
        }
        preparedInput = { data: padded, width: outWidth, height: outHeight, channels: targetChannels };
    }

    // Combine: [input | output]
    for (let y = 0; y < outHeight; y++) {
        // Left side: input
        for (let x = 0; x < outWidth; x++) {
            const srcIdx = (y * outWidth + x) * targetChannels;
            const dstIdx = (y * combinedWidth + x) * targetChannels;
            for (let c = 0; c < targetChannels; c++) {
                combined[dstIdx + c] = preparedInput.data[srcIdx + c];
            }
        }
        // Right side: output
        for (let x = 0; x < outWidth; x++) {
            const srcIdx = (y * outWidth + x) * targetChannels;
            const dstIdx = (y * combinedWidth + outWidth + x) * targetChannels;
            for (let c = 0; c < targetChannels; c++) {
                combined[dstIdx + c] = preparedOutput.data[srcIdx + c];
            }
        }
    }

    return {
        data: combined,
        width: combinedWidth,
        height: combinedHeight,
        channels: targetChannels
    };
}

/**
 * Save test output image.
 *
 * For 8-bit (u8): saves as lossless AVIF with chromaSubsampling='4:4:4'
 * For 16-bit (f32): saves as 16-bit PNG for cross-platform compatibility
 *
 * Creates side-by-side comparison: [original | output] when inputImage is provided.
 *
 * Output naming: {filter}_{input}_js_{bitdepth}.{format}
 *
 * @param {Object} imageData - Image to save (data, width, height)
 * @param {string} category - Category
 * @param {string} name - Filter/effect name
 * @param {string} testCase - Test case ID
 * @param {string} bitDepth - "u8" for 8-bit or "f32" for 16-bit storage
 * @param {Object|null} inputImage - Original input image for side-by-side comparison
 * @returns {Promise<string>} - Path to saved file
 */
export async function saveTestOutput(imageData, category, name, testCase, bitDepth = 'u8', inputImage = null) {
    // Create side-by-side comparison if input image is provided
    const finalImage = inputImage ? createSideBySide(inputImage, imageData, bitDepth) : imageData;

    // Get channel count from imageData (defaults to 4 if not specified)
    const channels = finalImage.channels || 4;

    if (bitDepth === 'f32' && finalImage.data instanceof Uint16Array) {
        // 16-bit PNG for f32 outputs (cross-platform compatible)
        const outputPath = getOutputPath(category, name, testCase, 'f32');

        // Input data is 12-bit (0-4095), scale to 16-bit range (0-65535)
        const scaled = new Uint16Array(finalImage.data.length);
        for (let i = 0; i < finalImage.data.length; i++) {
            scaled[i] = Math.round(finalImage.data[i] * 65535 / 4095);
        }

        // Use fast-png for proper 16-bit PNG encoding (Sharp doesn't support 16-bit raw input)
        const pngData = encodePng({
            width: finalImage.width,
            height: finalImage.height,
            data: scaled,
            depth: 16,
            channels: channels
        });

        fs.writeFileSync(outputPath, pngData);
        return outputPath;
    } else {
        // 8-bit output as PNG (lossless, cross-platform compatible)
        const outputPath = getOutputPath(category, name, testCase, 'u8', 'png');
        const data = Buffer.from(finalImage.data.buffer);

        await sharp(data, {
            raw: {
                width: finalImage.width,
                height: finalImage.height,
                channels: channels
            }
        }).png().toFile(outputPath);

        return outputPath;
    }
}

/**
 * Load test output from AVIF file.
 *
 * @param {string} category - Category
 * @param {string} name - Filter/effect name
 * @param {string} testCase - Test case ID
 * @returns {Promise<Object|null>} - Loaded image or null
 */
export async function loadTestOutput(category, name, testCase) {
    const outputPath = getOutputPath(category, name, testCase, 'avif');

    if (!fs.existsSync(outputPath)) {
        return null;
    }

    const { data, info } = await sharp(outputPath)
        .ensureAlpha()
        .raw()
        .toBuffer({ resolveWithObject: true });

    return {
        data: new Uint8ClampedArray(data.buffer),
        width: info.width,
        height: info.height
    };
}

/**
 * Parity test runner for JavaScript filters and effects.
 */
export class ParityTestRunner {
    constructor() {
        /** @type {Map<string, Function>} */
        this.filters = new Map();
        /** @type {Map<string, Function>} */
        this.effects = new Map();
        /** @type {Map<string, Object[]>} */
        this.filterTests = new Map();
        /** @type {Map<string, Object[]>} */
        this.effectTests = new Map();
    }

    /**
     * Register a filter implementation.
     *
     * @param {string} name - Filter name
     * @param {Function} func - Filter function (imageData) => imageData
     */
    registerFilter(name, func) {
        this.filters.set(name, func);
    }

    /**
     * Register a layer effect implementation.
     *
     * @param {string} name - Effect name
     * @param {Function} func - Effect function (imageData) => imageData
     */
    registerEffect(name, func) {
        this.effects.set(name, func);
    }

    /**
     * Register test cases for a filter.
     *
     * @param {string} name - Filter name
     * @param {Object[]} testCases - Array of test case objects
     */
    registerFilterTests(name, testCases) {
        this.filterTests.set(name, testCases);
    }

    /**
     * Register test cases for an effect.
     *
     * @param {string} name - Effect name
     * @param {Object[]} testCases - Array of test case objects
     */
    registerEffectTests(name, testCases) {
        this.effectTests.set(name, testCases);
    }

    /**
     * Run tests for a specific filter.
     *
     * @param {string} name - Filter name
     * @returns {Promise<Object[]>} - Results for each test case
     */
    async runFilterTests(name) {
        const func = this.filters.get(name);
        if (!func) {
            throw new Error(`No JS implementation registered for filter: ${name}`);
        }

        const testCases = this.filterTests.get(name) || [];
        const results = [];

        for (const tc of testCases) {
            try {
                const input = await generateInput(tc.inputGenerator, tc.width, tc.height);
                const output = func(input);
                const bitDepth = tc.bitDepth || 'u8';
                // Save pure output for parity testing (no side-by-side)
                const outputPath = await saveTestOutput(output, 'filters', name, tc.id, bitDepth);
                results.push({
                    id: tc.id,
                    success: true,
                    path: outputPath,
                });
            } catch (error) {
                results.push({
                    id: tc.id,
                    success: false,
                    error: error.message,
                });
            }
        }

        return results;
    }

    /**
     * Run tests for a specific effect.
     *
     * @param {string} name - Effect name
     * @returns {Promise<Object[]>} - Results for each test case
     */
    async runEffectTests(name) {
        const func = this.effects.get(name);
        if (!func) {
            throw new Error(`No JS implementation registered for effect: ${name}`);
        }

        const testCases = this.effectTests.get(name) || [];
        const results = [];

        for (const tc of testCases) {
            try {
                const input = await generateInput(tc.inputGenerator, tc.width, tc.height);
                const output = func(input);
                const bitDepth = tc.bitDepth || 'u8';
                // Save pure output for parity testing (no side-by-side)
                const outputPath = await saveTestOutput(output, 'layer_effects', name, tc.id, bitDepth);
                results.push({
                    id: tc.id,
                    success: true,
                    path: outputPath,
                });
            } catch (error) {
                results.push({
                    id: tc.id,
                    success: false,
                    error: error.message,
                });
            }
        }

        return results;
    }

    /**
     * Run all registered tests.
     *
     * @returns {Promise<Object>} - Results organized by category and name
     */
    async runAllTests() {
        const results = {
            filters: {},
            layer_effects: {},
        };

        for (const name of this.filterTests.keys()) {
            if (this.filters.has(name)) {
                results.filters[name] = await this.runFilterTests(name);
            }
        }

        for (const name of this.effectTests.keys()) {
            if (this.effects.has(name)) {
                results.layer_effects[name] = await this.runEffectTests(name);
            }
        }

        return results;
    }
}

// Export configuration for external use
export const config = {
    testDir: PARITY_TEST_DIR,
    inputsDir: INPUTS_DIR,
    outputFormat: OUTPUT_FORMAT,
    apiBaseUrl: API_BASE_URL,
    testInputs: TEST_INPUTS,
};
