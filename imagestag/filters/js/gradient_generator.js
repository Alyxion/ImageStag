/**
 * Gradient Generator - JavaScript WASM wrapper.
 *
 * Generates gradient surfaces without requiring an input image.
 * Supports 5 styles: linear, radial, angle, reflected, diamond.
 *
 * Co-located with:
 * - gradient_generator.rs (Rust implementation)
 * - gradient_generator.py (Python wrapper)
 */

import { initWasm, wasm } from '../../layer_effects/core.js';

export { initWasm };

/**
 * Generate a gradient surface as RGBA image.
 * @param {Object} options - Generator options
 * @param {number} options.width - Output width in pixels
 * @param {number} options.height - Output height in pixels
 * @param {Array<Object>} [options.stops] - Gradient stops [{position, color: [r,g,b]}]
 * @param {string} [options.style='linear'] - Style: 'linear', 'radial', 'angle', 'reflected', 'diamond'
 * @param {number} [options.angle=90] - Gradient angle in degrees
 * @param {number} [options.scaleX=1.0] - Horizontal scale factor
 * @param {number} [options.scaleY=1.0] - Vertical scale factor
 * @param {number} [options.offsetX=0.0] - Horizontal center offset (-1.0 to 1.0)
 * @param {number} [options.offsetY=0.0] - Vertical center offset (-1.0 to 1.0)
 * @param {boolean} [options.reverse=false] - Reverse the gradient
 * @returns {Object} - {data: Uint8ClampedArray, width, height, channels: 4}
 */
export function generate_gradient(options = {}) {
    const width = options.width || 512;
    const height = options.height || 512;

    const stops = options.stops ?? [
        { position: 0, color: [0, 0, 0] },
        { position: 1, color: [255, 255, 255] }
    ];
    const style = options.style ?? 'linear';
    const angle = options.angle ?? 90;
    const scaleX = options.scaleX ?? 1.0;
    const scaleY = options.scaleY ?? 1.0;
    const offsetX = options.offsetX ?? 0.0;
    const offsetY = options.offsetY ?? 0.0;
    const reverse = options.reverse ?? false;

    // Flatten stops array: [pos, r, g, b, pos, r, g, b, ...]
    const stopsFlat = new Float32Array(stops.length * 4);
    for (let i = 0; i < stops.length; i++) {
        stopsFlat[i * 4] = stops[i].position;
        stopsFlat[i * 4 + 1] = stops[i].color[0];
        stopsFlat[i * 4 + 2] = stops[i].color[1];
        stopsFlat[i * 4 + 3] = stops[i].color[2];
    }

    const result = wasm.generate_gradient_wasm(
        width,
        height,
        stopsFlat,
        style,
        angle,
        scaleX,
        scaleY,
        offsetX,
        offsetY,
        reverse
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
    generate_gradient
};
