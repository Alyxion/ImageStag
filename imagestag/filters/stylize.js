/**
 * Stylize filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - stylize.rs (Rust implementation)
 * - stylize.py (Python wrapper)
 *
 * Provides: posterize, solarize, threshold, emboss
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Posterize
// ============================================================================

/**
 * Reduce color levels (posterize) - u8 version.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {levels: number} (2-256)
 * @returns {Object} - Posterized image data
 */
export const posterize = createU8Filter(
    wasm.posterize_wasm,
    (opts) => [opts.levels ?? 4]
);

/**
 * Reduce color levels (posterize) - f32 version.
 */
export const posterize_f32 = createF32Filter(
    wasm.posterize_f32_wasm,
    (opts) => [opts.levels ?? 4]
);

// ============================================================================
// Solarize
// ============================================================================

/**
 * Apply solarize effect (u8).
 * Inverts tones above the threshold.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {threshold: number} (0-255 for u8)
 * @returns {Object} - Solarized image data
 */
export const solarize = createU8Filter(
    wasm.solarize_wasm,
    (opts) => [opts.threshold ?? 128]
);

/**
 * Apply solarize effect (f32).
 * @param {Object} options - {threshold: number} (0.0-1.0 for f32)
 */
export const solarize_f32 = createF32Filter(
    wasm.solarize_f32_wasm,
    (opts) => [(opts.threshold ?? 128) / 255.0]
);

// ============================================================================
// Threshold
// ============================================================================

/**
 * Apply binary threshold (u8).
 * Converts image to black and white based on threshold.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {threshold: number} (0-255 for u8)
 * @returns {Object} - Thresholded image data
 */
export const threshold = createU8Filter(
    wasm.threshold_wasm,
    (opts) => [opts.threshold ?? 128]
);

/**
 * Apply binary threshold (f32).
 * @param {Object} options - {threshold: number} (0.0-1.0 for f32)
 */
export const threshold_f32 = createF32Filter(
    wasm.threshold_f32_wasm,
    (opts) => [(opts.threshold ?? 128) / 255.0]
);

// ============================================================================
// Emboss
// ============================================================================

/**
 * Apply emboss effect (u8).
 * Creates a 3D raised effect using directional convolution.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {angle: number, depth: number}
 * @returns {Object} - Embossed image data
 */
export const emboss = createU8Filter(
    wasm.emboss_wasm,
    (opts) => [opts.angle ?? 45.0, opts.depth ?? 1.0]
);

/**
 * Apply emboss effect (f32).
 */
export const emboss_f32 = createF32Filter(
    wasm.emboss_f32_wasm,
    (opts) => [opts.angle ?? 45.0, opts.depth ?? 1.0]
);

export default {
    initWasm,
    posterize, posterize_f32,
    solarize, solarize_f32,
    threshold, threshold_f32,
    emboss, emboss_f32
};
