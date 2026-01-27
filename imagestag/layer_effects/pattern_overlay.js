/**
 * Pattern Overlay layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - pattern_overlay.rs (Rust implementation)
 * - pattern_overlay.py (Python wrapper)
 *
 * Tiles a pattern across the layer content.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply pattern overlay effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Pattern overlay options
 * @param {Object} options.pattern - Pattern image {data: Uint8ClampedArray, width, height}
 * @param {number} [options.scale=1.0] - Scale factor
 * @param {number} [options.offset_x=0] - Horizontal offset
 * @param {number} [options.offset_y=0] - Vertical offset
 * @param {number} [options.opacity=1.0] - Opacity (0.0-1.0)
 * @returns {Object} - Result with same dimensions {data, width, height, channels}
 */
export function pattern_overlay(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Pattern overlay requires RGBA images (4 channels)');
    }

    if (!options.pattern) {
        throw new Error('Pattern overlay requires a pattern image');
    }

    const pattern = options.pattern;
    const scale = options.scale ?? 1.0;
    const offset_x = options.offset_x ?? 0;
    const offset_y = options.offset_y ?? 0;
    const opacity = options.opacity ?? 1.0;

    const result = wasm.pattern_overlay_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        new Uint8Array(pattern.data.buffer),
        pattern.width,
        pattern.height,
        scale,
        offset_x,
        offset_y,
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
    pattern_overlay
};
