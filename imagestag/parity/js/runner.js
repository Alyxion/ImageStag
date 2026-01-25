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
 * Available ground truth input images.
 * These are the only inputs used for parity testing.
 */
const GROUND_TRUTH_INPUTS = ['deer_128', 'astronaut_128'];

/**
 * Load ground truth input from pre-generated .rgba file.
 * These files are created by Python's save_ground_truth_inputs().
 *
 * @param {string} inputId - Input identifier (e.g., 'deer_128')
 * @returns {Object|null} - ImageData-like object or null if not found
 */
function loadGroundTruthFromFile(inputId) {
    const inputPath = path.join(INPUTS_DIR, `${inputId}.rgba`);

    if (!fs.existsSync(inputPath)) {
        return null;
    }

    const buffer = fs.readFileSync(inputPath);
    const width = buffer.readUInt32LE(0);
    const height = buffer.readUInt32LE(4);
    const data = new Uint8ClampedArray(buffer.slice(8));

    return { data, width, height };
}

/**
 * Fetch ground truth input from API.
 * Requires the ImageStag server to be running.
 *
 * @param {string} inputId - Input identifier (e.g., 'deer_128')
 * @returns {Promise<Object|null>} - ImageData-like object or null
 */
async function fetchGroundTruthFromAPI(inputId) {
    try {
        const url = `${API_BASE_URL}/parity/inputs/${inputId}.rgba`;
        const response = await fetch(url);

        if (!response.ok) {
            console.warn(`Failed to fetch ${inputId} from API: ${response.status}`);
            return null;
        }

        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        const width = buffer.readUInt32LE(0);
        const height = buffer.readUInt32LE(4);
        const data = new Uint8ClampedArray(buffer.slice(8));

        return { data, width, height };
    } catch (error) {
        console.warn(`Failed to fetch ${inputId} from API:`, error.message);
        return null;
    }
}

/**
 * Generate test input using a ground truth image.
 *
 * First tries to load from pre-generated file, then falls back to API.
 *
 * @param {string} name - Input name (e.g., 'deer_128', 'astronaut_128')
 * @param {number} width - Expected width (for validation)
 * @param {number} height - Expected height (for validation)
 * @returns {Promise<Object>} - ImageData-like object with data, width, height
 */
export async function generateInput(name, width = 128, height = 128) {
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
 * Save test output as lossless AVIF.
 *
 * Uses sharp with lossless=true and chromaSubsampling='4:4:4' for
 * exact pixel preservation (no color space conversion artifacts).
 *
 * @param {Object} imageData - Image to save (data, width, height)
 * @param {string} category - Category
 * @param {string} name - Filter/effect name
 * @param {string} testCase - Test case ID
 * @returns {Promise<string>} - Path to saved file
 */
export async function saveTestOutput(imageData, category, name, testCase) {
    const outputPath = getOutputPath(category, name, testCase, 'avif');

    // Convert Uint8ClampedArray to Buffer for sharp
    const data = Buffer.from(imageData.data.buffer);

    // Save as lossless AVIF using sharp
    await sharp(data, {
        raw: {
            width: imageData.width,
            height: imageData.height,
            channels: 4
        }
    })
    .avif({
        quality: 100,
        lossless: true,
        chromaSubsampling: '4:4:4'
    })
    .toFile(outputPath);

    return outputPath;
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
                const outputPath = await saveTestOutput(output, 'filters', name, tc.id);
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
                const outputPath = await saveTestOutput(output, 'layer_effects', name, tc.id);
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
    groundTruthInputs: GROUND_TRUTH_INPUTS,
};
