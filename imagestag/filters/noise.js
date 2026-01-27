/**
 * Noise filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - noise.rs (Rust implementation)
 * - noise.py (Python wrapper)
 *
 * Provides: add_noise, median, denoise
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Add Noise
// ============================================================================

/**
 * Add noise to image (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount, gaussian, monochrome, seed}
 * @returns {Object} - Noisy image data
 */
export const add_noise = createU8Filter(
    wasm.add_noise_wasm,
    (opts) => [
        opts.amount ?? 0.1,
        opts.gaussian ?? true,
        opts.monochrome ?? false,
        opts.seed ?? 0
    ]
);

/**
 * Add noise to image (f32).
 */
export const add_noise_f32 = createF32Filter(
    wasm.add_noise_f32_wasm,
    (opts) => [
        opts.amount ?? 0.1,
        opts.gaussian ?? true,
        opts.monochrome ?? false,
        opts.seed ?? 0
    ]
);

// ============================================================================
// Median Filter
// ============================================================================

/**
 * Apply median filter for noise reduction (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {radius: number}
 * @returns {Object} - Filtered image data
 */
export const median = createU8Filter(
    wasm.median_wasm,
    (opts) => [opts.radius ?? 1]
);

/**
 * Apply median filter (f32).
 */
export const median_f32 = createF32Filter(
    wasm.median_f32_wasm,
    (opts) => [opts.radius ?? 1]
);

// ============================================================================
// Denoise
// ============================================================================

/**
 * Apply denoising (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {strength: number}
 * @returns {Object} - Denoised image data
 */
export const denoise = createU8Filter(
    wasm.denoise_wasm,
    (opts) => [opts.strength ?? 0.5]
);

/**
 * Apply denoising (f32).
 */
export const denoise_f32 = createF32Filter(
    wasm.denoise_f32_wasm,
    (opts) => [opts.strength ?? 0.5]
);

export default {
    initWasm,
    add_noise, add_noise_f32,
    median, median_f32,
    denoise, denoise_f32
};
