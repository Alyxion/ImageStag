/**
 * Gradient Overlay layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - gradient_overlay.rs (Rust implementation)
 * - gradient_overlay.py (Python wrapper)
 *
 * Applies a gradient fill over the layer content.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply gradient overlay effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Gradient overlay options
 * @param {Array<Object>} [options.stops] - Gradient stops [{position, color: [r,g,b]}]
 * @param {string} [options.style='linear'] - Style: 'linear', 'radial', 'angle', 'reflected', 'diamond'
 * @param {number} [options.angle=90] - Gradient angle in degrees (for linear/reflected)
 * @param {number} [options.scale=1.0] - Scale factor (0.1-1.5)
 * @param {boolean} [options.reverse=false] - Reverse the gradient
 * @param {number} [options.opacity=1.0] - Opacity (0.0-1.0)
 * @returns {Object} - Result with same dimensions {data, width, height, channels}
 */
export function gradient_overlay(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Gradient overlay requires RGBA images (4 channels)');
    }

    // Default gradient: black to white
    const stops = options.stops ?? [
        { position: 0, color: [0, 0, 0] },
        { position: 1, color: [255, 255, 255] }
    ];
    const style = options.style ?? 'linear';
    const angle = options.angle ?? 90;
    const scale = options.scale ?? 1.0;
    const reverse = options.reverse ?? false;
    const opacity = options.opacity ?? 1.0;

    // Flatten stops array: [pos, r, g, b, pos, r, g, b, ...]
    const stopsFlat = new Float32Array(stops.length * 4);
    for (let i = 0; i < stops.length; i++) {
        stopsFlat[i * 4] = stops[i].position;
        stopsFlat[i * 4 + 1] = stops[i].color[0];
        stopsFlat[i * 4 + 2] = stops[i].color[1];
        stopsFlat[i * 4 + 3] = stops[i].color[2];
    }

    const result = wasm.gradient_overlay_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        stopsFlat,
        style,
        angle,
        scale,
        reverse,
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
    gradient_overlay
};
