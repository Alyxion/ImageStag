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
const OUTPUT_FORMAT = 'avif';

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
 * Get the output path for a test result.
 *
 * @param {string} category - "filters" or "layer_effects"
 * @param {string} name - Filter/effect name
 * @param {string} testCase - Test case identifier
 * @param {string} format - Output format
 * @returns {string} - Output file path
 */
export function getOutputPath(category, name, testCase, format = OUTPUT_FORMAT) {
    const categoryDir = path.join(PARITY_TEST_DIR, category);
    fs.mkdirSync(categoryDir, { recursive: true });
    return path.join(categoryDir, `${name}_${testCase}_js.${format}`);
}

/**
 * Save test output image.
 *
 * For 8-bit (u8): saves as lossless AVIF with chromaSubsampling='4:4:4'
 * For 16-bit (f32): saves as 16-bit PNG for cross-platform compatibility
 *
 * @param {Object} imageData - Image to save (data, width, height)
 * @param {string} category - Category
 * @param {string} name - Filter/effect name
 * @param {string} testCase - Test case ID
 * @param {string} bitDepth - "u8" for 8-bit or "f32" for 16-bit storage
 * @returns {Promise<string>} - Path to saved file
 */
export async function saveTestOutput(imageData, category, name, testCase, bitDepth = 'u8') {
    // Get channel count from imageData (defaults to 4 if not specified)
    const channels = imageData.channels || 4;

    if (bitDepth === 'f32' && imageData.data instanceof Uint16Array) {
        // 16-bit PNG for f32 outputs (cross-platform compatible)
        const outputPath = getOutputPath(category, name, testCase, 'png');

        // Input data is 12-bit (0-4095), scale to 16-bit range (0-65535)
        const scaled = new Uint16Array(imageData.data.length);
        for (let i = 0; i < imageData.data.length; i++) {
            scaled[i] = Math.round(imageData.data[i] * 65535 / 4095);
        }

        // Use fast-png for proper 16-bit PNG encoding (Sharp doesn't support 16-bit raw input)
        const pngData = encodePng({
            width: imageData.width,
            height: imageData.height,
            data: scaled,
            depth: 16,
            channels: channels
        });

        fs.writeFileSync(outputPath, pngData);
        return outputPath;
    } else {
        // 8-bit output as AVIF (or PNG for non-4-channel)
        // Sharp AVIF requires 3 or 4 channels
        const useAvif = channels >= 3;
        const format = useAvif ? 'avif' : 'png';
        const outputPath = getOutputPath(category, name, testCase, format);
        const data = Buffer.from(imageData.data.buffer);

        let img = sharp(data, {
            raw: {
                width: imageData.width,
                height: imageData.height,
                channels: channels
            }
        });

        if (useAvif) {
            await img
                .avif({
                    quality: 100,
                    lossless: true,
                    chromaSubsampling: '4:4:4'
                })
                .toFile(outputPath);
        } else {
            await img.png().toFile(outputPath);
        }

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
