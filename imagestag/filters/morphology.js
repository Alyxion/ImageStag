/**
 * Morphology filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - morphology.rs (Rust implementation)
 * - morphology.py (Python wrapper)
 *
 * Provides: dilate, erode
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Dilate
// ============================================================================

/**
 * Apply dilation to image (u8).
 * Takes the maximum value in the neighborhood,
 * making bright regions grow and dark regions shrink.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {radius: number}
 * @returns {Object} - Dilated image data
 */
export const dilate = createU8Filter(
    wasm.dilate_wasm,
    (opts) => [opts.radius ?? 1.0]
);

/**
 * Apply dilation to image (f32).
 */
export const dilate_f32 = createF32Filter(
    wasm.dilate_f32_wasm,
    (opts) => [opts.radius ?? 1.0]
);

// ============================================================================
// Erode
// ============================================================================

/**
 * Apply erosion to image (u8).
 * Takes the minimum value in the neighborhood,
 * making dark regions grow and bright regions shrink.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {radius: number}
 * @returns {Object} - Eroded image data
 */
export const erode = createU8Filter(
    wasm.erode_wasm,
    (opts) => [opts.radius ?? 1.0]
);

/**
 * Apply erosion to image (f32).
 */
export const erode_f32 = createF32Filter(
    wasm.erode_f32_wasm,
    (opts) => [opts.radius ?? 1.0]
);

export default {
    initWasm,
    dilate, dilate_f32,
    erode, erode_f32
};
