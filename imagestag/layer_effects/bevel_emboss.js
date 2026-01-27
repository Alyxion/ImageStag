/**
 * Bevel & Emboss layer effect - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - bevel_emboss.rs (Rust implementation)
 * - bevel_emboss.py (Python wrapper)
 *
 * Creates a 3D raised or sunken appearance using highlights and shadows.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

/**
 * Apply bevel and emboss effect to RGBA image.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels: 4}
 * @param {Object} options - Bevel & emboss options
 * @param {number} [options.depth=3] - Effect depth
 * @param {number} [options.angle=120] - Light source angle in degrees
 * @param {number} [options.altitude=30] - Light source altitude in degrees
 * @param {Array<number>} [options.highlight_color=[255,255,255]] - Highlight color [r, g, b]
 * @param {number} [options.highlight_opacity=0.75] - Highlight opacity (0.0-1.0)
 * @param {Array<number>} [options.shadow_color=[0,0,0]] - Shadow color [r, g, b]
 * @param {number} [options.shadow_opacity=0.75] - Shadow opacity (0.0-1.0)
 * @param {string} [options.style='inner_bevel'] - Style: 'outer_bevel', 'inner_bevel', 'emboss', 'pillow_emboss'
 * @returns {Object} - Result (may have expanded canvas for outer_bevel)
 */
export function bevel_emboss(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (channels !== 4) {
        throw new Error('Bevel & emboss requires RGBA images (4 channels)');
    }

    const depth = options.depth ?? 3;
    const angle = options.angle ?? 120;
    const altitude = options.altitude ?? 30;
    const highlight_color = options.highlight_color ?? [255, 255, 255];
    const highlight_opacity = options.highlight_opacity ?? 0.75;
    const shadow_color = options.shadow_color ?? [0, 0, 0];
    const shadow_opacity = options.shadow_opacity ?? 0.75;
    const style = options.style ?? 'inner_bevel';

    const result = wasm.bevel_emboss_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        depth,
        angle,
        altitude,
        highlight_color[0],
        highlight_color[1],
        highlight_color[2],
        highlight_opacity,
        shadow_color[0],
        shadow_color[1],
        shadow_color[2],
        shadow_opacity,
        style
    );

    // Calculate dimensions based on style
    const is_outer = style === 'outer_bevel';
    const expand = is_outer ? Math.ceil(depth) + 2 : 0;
    const new_width = width + expand * 2;
    const new_height = height + expand * 2;

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: new_width,
        height: new_height,
        channels: 4,
        offset_x: is_outer ? -expand : 0,
        offset_y: is_outer ? -expand : 0
    };
}

export default {
    initWasm,
    bevel_emboss
};
