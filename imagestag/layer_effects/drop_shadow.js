/**
 * Drop Shadow layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - drop_shadow.rs (Rust implementation)
 * - drop_shadow.py (Python wrapper)
 *
 * Creates a shadow cast behind the layer by blurring and offsetting the alpha.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply drop shadow effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Drop shadow options
 * @param {number} [options.offset_x=5] - Horizontal shadow offset in pixels
 * @param {number} [options.offset_y=5] - Vertical shadow offset in pixels
 * @param {number} [options.blur_radius=10] - Shadow blur radius
 * @param {Array<number>} [options.color=[0,0,0]] - Shadow color [r, g, b] (0-255)
 * @param {number} [options.opacity=0.75] - Shadow opacity (0.0-1.0)
 * @returns {Object} - Result with expanded canvas {data, width, height, channels, offset_x, offset_y}
 */
export function drop_shadow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Drop shadow requires RGBA images (4 channels)');
    }

    const offset_x = options.offset_x ?? 5;
    const offset_y = options.offset_y ?? 5;
    const blur_radius = options.blur_radius ?? 10;
    const color = options.color ?? [0, 0, 0];
    const opacity = options.opacity ?? 0.75;

    const result = wasm.drop_shadow_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        offset_x,
        offset_y,
        blur_radius,
        color[0],
        color[1],
        color[2],
        opacity
    );

    // Calculate expanded dimensions
    const blur_expand = Math.ceil(blur_radius * 3);
    const offset_expand = Math.ceil(Math.max(Math.abs(offset_x), Math.abs(offset_y)));
    const required_expand = blur_expand + offset_expand + 2;

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
    drop_shadow
};
