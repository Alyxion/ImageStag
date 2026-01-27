/**
 * Stroke layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - stroke.rs (Rust implementation)
 * - stroke.py (Python wrapper)
 *
 * Creates an outline around non-transparent areas.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply stroke/outline effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Stroke options
 * @param {number} [options.width=3] - Stroke width in pixels
 * @param {Array<number>} [options.color=[255,0,0]] - Stroke color [r, g, b] (0-255)
 * @param {number} [options.opacity=1.0] - Opacity (0.0-1.0)
 * @param {string} [options.position='outside'] - Position: 'inside', 'center', 'outside'
 * @returns {Object} - Result (may have expanded canvas for outside/center)
 */
export function stroke(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Stroke requires RGBA images (4 channels)');
    }

    const stroke_width = options.width ?? 3;
    const color = options.color ?? [255, 0, 0];
    const opacity = options.opacity ?? 1.0;
    const position = options.position ?? 'outside';

    const result = wasm.stroke_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        stroke_width,
        color[0],
        color[1],
        color[2],
        opacity,
        position
    );

    // Calculate dimensions based on position
    const is_inside = position === 'inside';
    const required_expand = is_inside ? 0 : Math.ceil(stroke_width) + 2;
    const new_width = width + required_expand * 2;
    const new_height = height + required_expand * 2;

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: new_width,
        height: new_height,
        channels: 4,
        offset_x: is_inside ? 0 : -required_expand,
        offset_y: is_inside ? 0 : -required_expand
    };
}

export default {
    initWasm,
    stroke
};
