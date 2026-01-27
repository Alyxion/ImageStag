/**
 * Color Overlay layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - color_overlay.rs (Rust implementation)
 * - color_overlay.py (Python wrapper)
 *
 * Replaces all colors with a solid color while preserving alpha.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply color overlay effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Color overlay options
 * @param {Array<number>} [options.color=[255,0,0]] - Overlay color [r, g, b] (0-255)
 * @param {number} [options.opacity=1.0] - Opacity (0.0-1.0)
 * @returns {Object} - Result with same dimensions {data, width, height, channels}
 */
export function color_overlay(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Color overlay requires RGBA images (4 channels)');
    }

    const color = options.color ?? [255, 0, 0];
    const opacity = options.opacity ?? 1.0;

    const result = wasm.color_overlay_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
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
    color_overlay
};
