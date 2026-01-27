/**
 * Inner Shadow layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - inner_shadow.rs (Rust implementation)
 * - inner_shadow.py (Python wrapper)
 *
 * Creates a shadow inside the shape by inverting and blurring alpha.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply inner shadow effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Inner shadow options
 * @param {number} [options.offset_x=5] - Horizontal shadow offset in pixels
 * @param {number} [options.offset_y=5] - Vertical shadow offset in pixels
 * @param {number} [options.blur_radius=10] - Shadow blur radius
 * @param {number} [options.choke=0] - Choke amount (0.0-1.0)
 * @param {Array<number>} [options.color=[0,0,0]] - Shadow color [r, g, b] (0-255)
 * @param {number} [options.opacity=0.75] - Shadow opacity (0.0-1.0)
 * @returns {Object} - Result with same dimensions {data, width, height, channels}
 */
export function inner_shadow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Inner shadow requires RGBA images (4 channels)');
    }

    const offset_x = options.offset_x ?? 5;
    const offset_y = options.offset_y ?? 5;
    const blur_radius = options.blur_radius ?? 10;
    const choke = options.choke ?? 0;
    const color = options.color ?? [0, 0, 0];
    const opacity = options.opacity ?? 0.75;

    const result = wasm.inner_shadow_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        offset_x,
        offset_y,
        blur_radius,
        choke,
        color[0],
        color[1],
        color[2],
        opacity
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
    inner_shadow
};
