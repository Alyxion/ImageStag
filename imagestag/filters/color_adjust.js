/**
 * Color adjustment filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - color_adjust.rs (Rust implementation)
 * - color_adjust.py (Python wrapper)
 *
 * Provides: brightness, contrast, saturation, gamma, exposure, invert
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Brightness
// ============================================================================

/**
 * Adjust image brightness (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount: number} (-1.0 to 1.0)
 * @returns {Object} - Adjusted image data
 */
export const brightness = createU8Filter(
    wasm.brightness_wasm,
    (opts) => [opts.amount ?? 0]
);

/**
 * Adjust image brightness (f32).
 */
export const brightness_f32 = createF32Filter(
    wasm.brightness_f32_wasm,
    (opts) => [opts.amount ?? 0]
);

// ============================================================================
// Contrast
// ============================================================================

/**
 * Adjust image contrast (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount: number} (-1.0 to 1.0)
 * @returns {Object} - Adjusted image data
 */
export const contrast = createU8Filter(
    wasm.contrast_wasm,
    (opts) => [opts.amount ?? 0]
);

/**
 * Adjust image contrast (f32).
 */
export const contrast_f32 = createF32Filter(
    wasm.contrast_f32_wasm,
    (opts) => [opts.amount ?? 0]
);

// ============================================================================
// Saturation
// ============================================================================

/**
 * Adjust image saturation (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount: number} (-1.0 to 1.0)
 * @returns {Object} - Adjusted image data
 */
export const saturation = createU8Filter(
    wasm.saturation_wasm,
    (opts) => [opts.amount ?? 0]
);

/**
 * Adjust image saturation (f32).
 */
export const saturation_f32 = createF32Filter(
    wasm.saturation_f32_wasm,
    (opts) => [opts.amount ?? 0]
);

// ============================================================================
// Gamma
// ============================================================================

/**
 * Apply gamma correction (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {gamma_value: number}
 * @returns {Object} - Adjusted image data
 */
export const gamma = createU8Filter(
    wasm.gamma_wasm,
    (opts) => [opts.gamma_value ?? 1.0]
);

/**
 * Apply gamma correction (f32).
 */
export const gamma_f32 = createF32Filter(
    wasm.gamma_f32_wasm,
    (opts) => [opts.gamma_value ?? 1.0]
);

// ============================================================================
// Exposure
// ============================================================================

/**
 * Adjust exposure (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {exposure_val: number, offset: number, gamma_val: number}
 * @returns {Object} - Adjusted image data
 */
export const exposure = createU8Filter(
    wasm.exposure_wasm,
    (opts) => [opts.exposure_val ?? 0, opts.offset ?? 0, opts.gamma_val ?? 1.0]
);

/**
 * Adjust exposure (f32).
 */
export const exposure_f32 = createF32Filter(
    wasm.exposure_f32_wasm,
    (opts) => [opts.exposure_val ?? 0, opts.offset ?? 0, opts.gamma_val ?? 1.0]
);

// ============================================================================
// Invert
// ============================================================================

/**
 * Invert image colors (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Inverted image data
 */
export const invert = createU8Filter(wasm.invert_wasm);

/**
 * Invert image colors (f32).
 */
export const invert_f32 = createF32Filter(wasm.invert_f32_wasm);

export default {
    initWasm,
    brightness, brightness_f32,
    contrast, contrast_f32,
    saturation, saturation_f32,
    gamma, gamma_f32,
    exposure, exposure_f32,
    invert, invert_f32
};
