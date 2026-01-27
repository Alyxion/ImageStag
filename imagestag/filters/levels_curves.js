/**
 * Levels and curves filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - levels_curves.rs (Rust implementation)
 * - levels_curves.py (Python wrapper)
 *
 * Provides: levels, curves, auto_levels
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Levels
// ============================================================================

/**
 * Apply levels adjustment (u8).
 * Remaps input levels to output levels with gamma correction.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {in_black, in_white, out_black, out_white, gamma}
 * @returns {Object} - Adjusted image data
 */
export const levels = createU8Filter(
    wasm.levels_wasm,
    (opts) => [
        opts.in_black ?? 0,
        opts.in_white ?? 255,
        opts.out_black ?? 0,
        opts.out_white ?? 255,
        opts.gamma ?? 1.0
    ]
);

/**
 * Apply levels adjustment (f32).
 * @param {Object} options - {in_black, in_white, out_black, out_white, gamma} (0.0-1.0 range)
 */
export const levels_f32 = createF32Filter(
    wasm.levels_f32_wasm,
    (opts) => [
        (opts.in_black ?? 0) / 255.0,
        (opts.in_white ?? 255) / 255.0,
        (opts.out_black ?? 0) / 255.0,
        (opts.out_white ?? 255) / 255.0,
        opts.gamma ?? 1.0
    ]
);

// ============================================================================
// Curves
// ============================================================================

/**
 * Apply curves adjustment (u8).
 * Uses PCHIP interpolation for smooth curve fitting.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {points: Array<[number, number]>} - Control points as [input, output] pairs (0.0-1.0)
 * @returns {Object} - Adjusted image data
 */
export const curves = createU8Filter(
    wasm.curves_wasm,
    (opts) => {
        const points = opts.points ?? [[0, 0], [1, 1]];
        // Flatten points array for WASM
        const flat = new Float32Array(points.length * 2);
        for (let i = 0; i < points.length; i++) {
            flat[i * 2] = points[i][0];
            flat[i * 2 + 1] = points[i][1];
        }
        return [flat];
    }
);

/**
 * Apply curves adjustment (f32).
 */
export const curves_f32 = createF32Filter(
    wasm.curves_f32_wasm,
    (opts) => {
        const points = opts.points ?? [[0, 0], [1, 1]];
        const flat = new Float32Array(points.length * 2);
        for (let i = 0; i < points.length; i++) {
            flat[i * 2] = points[i][0];
            flat[i * 2 + 1] = points[i][1];
        }
        return [flat];
    }
);

// ============================================================================
// Auto Levels
// ============================================================================

/**
 * Apply auto levels (histogram stretch) - u8 version.
 * Automatically adjusts levels based on image histogram.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {clip_percent: number} (0.0-0.5, e.g., 0.01 = 1%)
 * @returns {Object} - Auto-leveled image data
 */
export const auto_levels = createU8Filter(
    wasm.auto_levels_wasm,
    (opts) => [opts.clip_percent ?? 0.01]
);

/**
 * Apply auto levels (f32).
 */
export const auto_levels_f32 = createF32Filter(
    wasm.auto_levels_f32_wasm,
    (opts) => [opts.clip_percent ?? 0.01]
);

export default {
    initWasm,
    levels, levels_f32,
    curves, curves_f32,
    auto_levels, auto_levels_f32
};
