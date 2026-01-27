/**
 * Edge detection filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - edge.rs (Rust implementation)
 * - edge.py (Python wrapper)
 *
 * Provides: sobel, laplacian, find_edges
 */

import { initWasm, createU8Filter, createF32Filter, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Sobel
// ============================================================================

/**
 * Apply Sobel edge detection (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {direction: 'horizontal'|'vertical'|'both'}
 * @returns {Object} - Edge-detected image data
 */
export const sobel = createU8Filter(
    wasm.sobel_wasm,
    (opts) => [opts.direction ?? 'both']
);

/**
 * Apply Sobel edge detection (f32).
 */
export const sobel_f32 = createF32Filter(
    wasm.sobel_f32_wasm,
    (opts) => [opts.direction ?? 'both']
);

// ============================================================================
// Laplacian
// ============================================================================

/**
 * Apply Laplacian edge detection (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {kernel_size: number}
 * @returns {Object} - Edge-detected image data
 */
export const laplacian = createU8Filter(
    wasm.laplacian_wasm,
    (opts) => [opts.kernel_size ?? 3]
);

/**
 * Apply Laplacian edge detection (f32).
 */
export const laplacian_f32 = createF32Filter(
    wasm.laplacian_f32_wasm,
    (opts) => [opts.kernel_size ?? 3]
);

// ============================================================================
// Find Edges
// ============================================================================

/**
 * Find edges using combined gradient (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Edge-detected image data
 */
export const find_edges = createU8Filter(wasm.find_edges_wasm);

/**
 * Find edges using combined gradient (f32).
 */
export const find_edges_f32 = createF32Filter(wasm.find_edges_f32_wasm);

export default {
    initWasm,
    sobel, sobel_f32,
    laplacian, laplacian_f32,
    find_edges, find_edges_f32
};
