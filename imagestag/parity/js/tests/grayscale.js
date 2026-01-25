/**
 * Grayscale filter parity test registration for JavaScript.
 *
 * This module registers parity tests for the grayscale filter matching
 * the Python registration in imagestag/parity/tests/grayscale.py
 *
 * IMPORTANT: Uses Rust/WASM implementation - NO JavaScript fallback.
 * Both Python and JavaScript use identical Rust code for exact parity.
 *
 * Test inputs:
 * - deer_128: Noto emoji deer at 128x128 (vector with transparency)
 * - astronaut_128: Skimage astronaut at 128x128 (photographic, no transparency)
 */

import { grayscale } from '../../../filters/js/grayscale.js';

/**
 * Test cases for grayscale filter parity testing.
 * Must match the Python registration exactly.
 */
export const GRAYSCALE_TEST_CASES = [
    {
        id: 'deer_128',
        description: 'Noto emoji deer - vector with transparency',
        width: 128,
        height: 128,
        inputGenerator: 'deer_128',
    },
    {
        id: 'astronaut_128',
        description: 'Skimage astronaut - photographic image',
        width: 128,
        height: 128,
        inputGenerator: 'astronaut_128',
    },
];

/**
 * Grayscale filter implementation using Rust/WASM.
 * This is the ONLY implementation - no fallback.
 *
 * @param {Object} imageData - Input image (data, width, height)
 * @returns {Object} - Grayscale output
 */
export function grayscaleFilter(imageData) {
    return grayscale(imageData);
}

/**
 * Register grayscale parity tests with a runner.
 *
 * @param {ParityTestRunner} runner - Test runner instance
 */
export function registerGrayscaleParity(runner) {
    runner.registerFilter('grayscale', grayscaleFilter);
    runner.registerFilterTests('grayscale', GRAYSCALE_TEST_CASES);
}
