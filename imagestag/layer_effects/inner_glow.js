/**
 * Inner Glow layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - inner_glow.rs (Rust implementation)
 * - inner_glow.py (Python wrapper)
 *
 * Creates a glow effect inside the shape edges.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply inner glow effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Inner glow options
 * @param {number} [options.radius=10] - Glow radius
 * @param {Array<number>} [options.color=[255,255,0]] - Glow color [r, g, b] (0-255)
 * @param {number} [options.opacity=0.75] - Glow opacity (0.0-1.0)
 * @param {number} [options.choke=0] - Choke amount (0.0-1.0)
 * @returns {Object} - Result with same dimensions {data, width, height, channels}
 */
export function inner_glow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Inner glow requires RGBA images (4 channels)');
    }

    const radius = options.radius ?? 10;
    const color = options.color ?? [255, 255, 0];
    const opacity = options.opacity ?? 0.75;
    const choke = options.choke ?? 0;

    const result = wasm.inner_glow_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        radius,
        color[0],
        color[1],
        color[2],
        opacity,
        choke
    );

    return {
        data: new Uint8ClampedArray(result.buffer),
        width,
        height,
        channels: 4
    };
}

export default {
    initWasm,
    inner_glow
};
