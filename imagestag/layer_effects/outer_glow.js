/**
 * Outer Glow layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - outer_glow.rs (Rust implementation)
 * - outer_glow.py (Python wrapper)
 *
 * Creates a glow effect outside the shape edges.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply outer glow effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Outer glow options
 * @param {number} [options.radius=10] - Glow radius
 * @param {Array<number>} [options.color=[255,255,0]] - Glow color [r, g, b] (0-255)
 * @param {number} [options.opacity=0.75] - Glow opacity (0.0-1.0)
 * @param {number} [options.spread=0] - Spread amount (0.0-1.0)
 * @returns {Object} - Result with expanded canvas {data, width, height, channels, offset_x, offset_y}
 */
export function outer_glow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Outer glow requires RGBA images (4 channels)');
    }

    const radius = options.radius ?? 10;
    const color = options.color ?? [255, 255, 0];
    const opacity = options.opacity ?? 0.75;
    const spread = options.spread ?? 0;

    const result = wasm.outer_glow_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        radius,
        color[0],
        color[1],
        color[2],
        opacity,
        spread
    );

    // Calculate expanded dimensions
    const required_expand = Math.ceil(radius * 3) + 2;
    const new_width = width + required_expand * 2;
    const new_height = height + required_expand * 2;

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: new_width,
        height: new_height,
        channels: 4,
        offset_x: -required_expand,
        offset_y: -required_expand
    };
}

export default {
    initWasm,
    outer_glow
};
