/**
 * Satin layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - satin.rs (Rust implementation)
 * - satin.py (Python wrapper)
 *
 * Creates silky interior shading by compositing shifted, blurred copies
 * of the alpha channel.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply satin effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Satin options
 * @param {Array<number>} [options.color=[0,0,0]] - Satin color [r, g, b] (0-255)
 * @param {number} [options.opacity=0.5] - Opacity (0.0-1.0)
 * @param {number} [options.angle=19] - Light angle in degrees
 * @param {number} [options.distance=11] - Distance in pixels
 * @param {number} [options.size=14] - Size (blur amount)
 * @param {boolean} [options.invert=false] - Invert the effect
 * @returns {Object} - Result with same dimensions {data, width, height, channels}
 */
export function satin(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Satin requires RGBA images (4 channels)');
    }

    const color = options.color ?? [0, 0, 0];
    const opacity = options.opacity ?? 0.5;
    const angle = options.angle ?? 19;
    const distance = options.distance ?? 11;
    const size = options.size ?? 14;
    const invert = options.invert ?? false;

    const result = wasm.satin_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        color[0],
        color[1],
        color[2],
        opacity,
        angle,
        distance,
        size,
        invert
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
    satin
};
