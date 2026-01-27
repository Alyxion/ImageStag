/**
 * Color science filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - color_science.rs (Rust implementation)
 * - color_science.py (Python wrapper)
 *
 * Provides: hue_shift, vibrance, color_balance
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Hue Shift
// ============================================================================

/**
 * Shift image hue (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {degrees: number} (0-360, wraps around)
 * @returns {Object} - Hue-shifted image data
 */
export const hue_shift = createU8Filter(
    wasm.hue_shift_wasm,
    (opts) => [opts.degrees ?? 0]
);

/**
 * Shift image hue (f32).
 */
export const hue_shift_f32 = createF32Filter(
    wasm.hue_shift_f32_wasm,
    (opts) => [opts.degrees ?? 0]
);

// ============================================================================
// Vibrance
// ============================================================================

/**
 * Adjust image vibrance (u8).
 * Boosts less-saturated colors more than saturated ones.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {amount: number} (-1.0 to 1.0)
 * @returns {Object} - Vibrance-adjusted image data
 */
export const vibrance = createU8Filter(
    wasm.vibrance_wasm,
    (opts) => [opts.amount ?? 0]
);

/**
 * Adjust image vibrance (f32).
 */
export const vibrance_f32 = createF32Filter(
    wasm.vibrance_f32_wasm,
    (opts) => [opts.amount ?? 0]
);

// ============================================================================
// Color Balance
// ============================================================================

/**
 * Adjust image color balance (u8).
 * Adjusts shadows, midtones, and highlights independently.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {shadows: [r,g,b], midtones: [r,g,b], highlights: [r,g,b]} (each -1.0 to 1.0)
 * @returns {Object} - Color-balanced image data
 */
export const color_balance = createU8Filter(
    wasm.color_balance_wasm,
    (opts) => {
        const shadows = opts.shadows ?? [0, 0, 0];
        const midtones = opts.midtones ?? [0, 0, 0];
        const highlights = opts.highlights ?? [0, 0, 0];
        return [
            shadows[0], shadows[1], shadows[2],
            midtones[0], midtones[1], midtones[2],
            highlights[0], highlights[1], highlights[2]
        ];
    }
);

/**
 * Adjust image color balance (f32).
 */
export const color_balance_f32 = createF32Filter(
    wasm.color_balance_f32_wasm,
    (opts) => {
        const shadows = opts.shadows ?? [0, 0, 0];
        const midtones = opts.midtones ?? [0, 0, 0];
        const highlights = opts.highlights ?? [0, 0, 0];
        return [
            shadows[0], shadows[1], shadows[2],
            midtones[0], midtones[1], midtones[2],
            highlights[0], highlights[1], highlights[2]
        ];
    }
);

export default {
    initWasm,
    hue_shift, hue_shift_f32,
    vibrance, vibrance_f32,
    color_balance, color_balance_f32
};
