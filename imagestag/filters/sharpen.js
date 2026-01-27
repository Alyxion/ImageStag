/**
 * Sharpen filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - sharpen.rs (Rust implementation)
 * - sharpen.py (Python wrapper)
 *
 * Provides: sharpen, unsharp_mask, high_pass, motion_blur
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Sharpen
// ============================================================================

/**
 * Sharpen image (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount: number}
 * @returns {Object} - Sharpened image data
 */
export const sharpen = createU8Filter(
    wasm.sharpen_wasm,
    (opts) => [opts.amount ?? 1.0]
);

/**
 * Sharpen image (f32).
 */
export const sharpen_f32 = createF32Filter(
    wasm.sharpen_f32_wasm,
    (opts) => [opts.amount ?? 1.0]
);

// ============================================================================
// Unsharp Mask
// ============================================================================

/**
 * Apply unsharp mask (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount, radius, threshold}
 * @returns {Object} - Sharpened image data
 */
export const unsharp_mask = createU8Filter(
    wasm.unsharp_mask_wasm,
    (opts) => [opts.amount ?? 1.0, opts.radius ?? 2.0, opts.threshold ?? 0]
);

/**
 * Apply unsharp mask (f32).
 */
export const unsharp_mask_f32 = createF32Filter(
    wasm.unsharp_mask_f32_wasm,
    (opts) => [opts.amount ?? 1.0, opts.radius ?? 2.0, (opts.threshold ?? 0) / 255.0]
);

// ============================================================================
// High Pass
// ============================================================================

/**
 * Apply high pass filter (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {radius: number}
 * @returns {Object} - High-pass filtered image data
 */
export const high_pass = createU8Filter(
    wasm.high_pass_wasm,
    (opts) => [opts.radius ?? 3.0]
);

/**
 * Apply high pass filter (f32).
 */
export const high_pass_f32 = createF32Filter(
    wasm.high_pass_f32_wasm,
    (opts) => [opts.radius ?? 3.0]
);

// ============================================================================
// Motion Blur
// ============================================================================

/**
 * Apply motion blur (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {angle, distance}
 * @returns {Object} - Blurred image data
 */
export const motion_blur = createU8Filter(
    wasm.motion_blur_wasm,
    (opts) => [opts.angle ?? 45.0, opts.distance ?? 10.0]
);

/**
 * Apply motion blur (f32).
 */
export const motion_blur_f32 = createF32Filter(
    wasm.motion_blur_f32_wasm,
    (opts) => [opts.angle ?? 45.0, opts.distance ?? 10.0]
);

export default {
    initWasm,
    sharpen, sharpen_f32,
    unsharp_mask, unsharp_mask_f32,
    high_pass, high_pass_f32,
    motion_blur, motion_blur_f32
};
