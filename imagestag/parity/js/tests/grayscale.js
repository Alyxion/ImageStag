/**
 * Grayscale filter parity test registration for JavaScript.
 *
 * This module registers parity tests for the grayscale filter matching
 * the Python registration in imagestag/parity/tests/grayscale.py
 *
 * IMPORTANT: Uses Rust/WASM implementation - NO JavaScript fallback.
 * Both Python and JavaScript use identical Rust code for exact parity.
 *
 * ## Bit Depth Support
 *
 * - **u8 (8-bit)**: Values 0-255, stored as lossless AVIF
 * - **f32 (float)**: Values 0.0-1.0, stored as 12-bit AVIF for precision
 *
 * Test inputs:
 * - deer_128: Noto emoji deer at 128x128 (vector with transparency)
 * - astronaut_128: Skimage astronaut at 128x128 (photographic, no transparency)
 */

import {
    grayscale,
    grayscaleF32,
    convertU8ToF32,
    convertF32To12bit,
} from '../../../filters/js/grayscale.js';

/**
 * Test cases for grayscale filter parity testing (u8).
 * Must match the Python registration exactly.
 */
export const GRAYSCALE_TEST_CASES = [
    {
        id: 'deer_128',
        description: 'Noto emoji deer - vector with transparency',
        width: 128,
        height: 128,
        inputGenerator: 'deer_128',
        bitDepth: 'u8',
    },
    {
        id: 'astronaut_128',
        description: 'Skimage astronaut - photographic image',
        width: 128,
        height: 128,
        inputGenerator: 'astronaut_128',
        bitDepth: 'u8',
    },
];

/**
 * Test cases for grayscale filter parity testing (f32).
 * These test the float version of the filter.
 */
export const GRAYSCALE_F32_TEST_CASES = [
    {
        id: 'deer_128_f32',
        description: 'Noto emoji deer - float version',
        width: 128,
        height: 128,
        inputGenerator: 'deer_128',
        bitDepth: 'f32',
    },
    {
        id: 'astronaut_128_f32',
        description: 'Skimage astronaut - float version',
        width: 128,
        height: 128,
        inputGenerator: 'astronaut_128',
        bitDepth: 'f32',
    },
];

/**
 * Grayscale filter implementation using Rust/WASM (u8).
 * This is the ONLY implementation - no fallback.
 *
 * @param {Object} imageData - Input image (data, width, height)
 * @returns {Object} - Grayscale output
 */
export function grayscaleFilter(imageData) {
    return grayscale(imageData);
}

/**
 * Grayscale filter implementation using Rust/WASM (f32).
 * Converts u8 input to f32, processes, then converts to 12-bit for storage.
 *
 * @param {Object} imageData - Input u8 image (data, width, height)
 * @returns {Object} - Grayscale output as 12-bit (Uint16Array with values 0-4095)
 */
export function grayscaleFilterF32(imageData) {
    // Convert u8 input to f32
    const inputF32 = convertU8ToF32(imageData);

    // Process in float
    const resultF32 = grayscaleF32(inputF32);

    // Convert to 12-bit for storage
    return convertF32To12bit(resultF32);
}

/**
 * Grayscale filter that returns 12-bit data for higher precision storage.
 *
 * @param {Object} imageData - Input u8 image
 * @returns {Object} - Grayscale output as 12-bit (Uint16Array with values 0-4095)
 */
export function grayscaleFilterF32As12bit(imageData) {
    // Convert u8 input to f32
    const inputF32 = convertU8ToF32(imageData);

    // Process in float
    const resultF32 = grayscaleF32(inputF32);

    // Convert to 12-bit for precision storage
    return convertF32To12bit(resultF32);
}

/**
 * Register grayscale parity tests with a runner.
 *
 * @param {ParityTestRunner} runner - Test runner instance
 */
export function registerGrayscaleParity(runner) {
    // Register u8 filter
    runner.registerFilter('grayscale', grayscaleFilter);
    runner.registerFilterTests('grayscale', GRAYSCALE_TEST_CASES);

    // Register f32 filter (stored as u8 for comparison)
    runner.registerFilter('grayscale_f32', grayscaleFilterF32);
    runner.registerFilterTests('grayscale_f32', GRAYSCALE_F32_TEST_CASES);
}
