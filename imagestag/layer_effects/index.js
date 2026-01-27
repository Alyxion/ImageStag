/**
 * ImageStag Layer Effects - Central Browser Module
 *
 * Single entry point for all WASM-accelerated layer effects.
 * Works in any browser environment with ES module support.
 *
 * Usage:
 *   import { initEffects, effects, applyEffect } from '/imgstag/layer_effects/index.js';
 *
 *   await initEffects();
 *   const result = effects.drop_shadow(imageData, { blur_radius: 10, offset_x: 5, offset_y: 5 });
 *
 * Image data format (input):
 *   { data: Uint8ClampedArray, width: number, height: number, channels: 4 }
 *
 * Result format (output — may have different dimensions):
 *   { data: Uint8ClampedArray, width, height, channels: 4, offset_x, offset_y }
 */

import init, * as wasm from '../wasm/imagestag_rust.js';

let _initialized = false;

/** Convert any typed array to Uint8Array (safe for WASM). */
function toU8(data) {
    if (data instanceof Uint8Array) return data;
    if (data.buffer) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    return new Uint8Array(data);
}

/**
 * Initialize the WASM module. Must be called before using any effect.
 * Safe to call multiple times. Shares init state with filters/index.js.
 */
export async function initEffects() {
    if (_initialized) return;
    await init();
    _initialized = true;
}

export function isInitialized() {
    return _initialized;
}

// ---------------------------------------------------------------------------
// Effect implementations
// ---------------------------------------------------------------------------

/**
 * Drop Shadow — shadow behind the layer.
 * @param {Object} imageData
 * @param {Object} options
 * @param {number} [options.offset_x=5]
 * @param {number} [options.offset_y=5]
 * @param {number} [options.blur_radius=10]
 * @param {number[]} [options.color=[0,0,0]]
 * @param {number} [options.opacity=0.75]
 * @returns {Object} Expanded result with offset_x, offset_y
 */
function drop_shadow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const ox = options.offset_x ?? 5;
    const oy = options.offset_y ?? 5;
    const blur = options.blur_radius ?? 10;
    const c = options.color ?? [0, 0, 0];
    const opacity = options.opacity ?? 0.75;

    const result = wasm.drop_shadow_rgba_wasm(
        toU8(data), width, height,
        ox, oy, blur, c[0], c[1], c[2], opacity
    );

    const expand = Math.ceil(blur * 3) + Math.ceil(Math.max(Math.abs(ox), Math.abs(oy))) + 2;
    return {
        data: new Uint8ClampedArray(result.buffer),
        width: width + expand * 2,
        height: height + expand * 2,
        channels: 4,
        offset_x: -expand,
        offset_y: -expand,
    };
}

/**
 * Inner Shadow — shadow inside layer edges.
 */
function inner_shadow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const ox = options.offset_x ?? 5;
    const oy = options.offset_y ?? 5;
    const blur = options.blur_radius ?? 10;
    const choke = options.choke ?? 0;
    const c = options.color ?? [0, 0, 0];
    const opacity = options.opacity ?? 0.75;

    const result = wasm.inner_shadow_rgba_wasm(
        toU8(data), width, height,
        ox, oy, blur, choke, c[0], c[1], c[2], opacity
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Outer Glow — glow radiating outward.
 */
function outer_glow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const radius = options.radius ?? 10;
    const c = options.color ?? [255, 255, 0];
    const opacity = options.opacity ?? 0.75;
    const spread = options.spread ?? 0;

    const result = wasm.outer_glow_rgba_wasm(
        toU8(data), width, height,
        radius, c[0], c[1], c[2], opacity, spread
    );

    const expand = Math.ceil(radius * 3) + spread + 2;
    return {
        data: new Uint8ClampedArray(result.buffer),
        width: width + expand * 2,
        height: height + expand * 2,
        channels: 4,
        offset_x: -expand,
        offset_y: -expand,
    };
}

/**
 * Inner Glow — glow radiating inward.
 */
function inner_glow(imageData, options = {}) {
    const { data, width, height } = imageData;
    const radius = options.radius ?? 10;
    const c = options.color ?? [255, 255, 0];
    const opacity = options.opacity ?? 0.75;
    const choke = options.choke ?? 0;

    const result = wasm.inner_glow_rgba_wasm(
        toU8(data), width, height,
        radius, c[0], c[1], c[2], opacity, choke
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Bevel & Emboss — 3D raised/sunken appearance.
 */
function bevel_emboss(imageData, options = {}) {
    const { data, width, height } = imageData;
    const depth = options.depth ?? 3;
    const angle = options.angle ?? 120;
    const altitude = options.altitude ?? 30;
    const hc = options.highlight_color ?? [255, 255, 255];
    const ho = options.highlight_opacity ?? 0.75;
    const sc = options.shadow_color ?? [0, 0, 0];
    const so = options.shadow_opacity ?? 0.75;
    const style = options.style ?? 'inner_bevel';

    const result = wasm.bevel_emboss_rgba_wasm(
        toU8(data), width, height,
        depth, angle, altitude,
        hc[0], hc[1], hc[2], ho,
        sc[0], sc[1], sc[2], so,
        style
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Satin — internal shading effect.
 */
function satin(imageData, options = {}) {
    const { data, width, height } = imageData;
    const c = options.color ?? [0, 0, 0];
    const opacity = options.opacity ?? 0.5;
    const angle = options.angle ?? 19;
    const distance = options.distance ?? 11;
    const size = options.size ?? 14;
    const invert = options.invert ?? false;

    const result = wasm.satin_rgba_wasm(
        toU8(data), width, height,
        c[0], c[1], c[2], opacity, angle, distance, size, invert
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Color Overlay — solid color fill on layer content.
 */
function color_overlay(imageData, options = {}) {
    const { data, width, height } = imageData;
    const c = options.color ?? [255, 0, 0];
    const opacity = options.opacity ?? 1.0;

    const result = wasm.color_overlay_rgba_wasm(
        toU8(data), width, height,
        c[0], c[1], c[2], opacity
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Gradient Overlay — gradient fill on layer content.
 */
function gradient_overlay(imageData, options = {}) {
    const { data, width, height } = imageData;
    const stops = options.stops ?? [
        { position: 0, color: [0, 0, 0] },
        { position: 1, color: [255, 255, 255] },
    ];
    const style = options.style ?? 'linear';
    const angle = options.angle ?? 90;
    const scale = options.scale ?? 1.0;
    const reverse = options.reverse ?? false;
    const opacity = options.opacity ?? 1.0;

    // Flatten stops: [position, r, g, b, ...]
    const flat = new Float32Array(stops.length * 4);
    for (let i = 0; i < stops.length; i++) {
        flat[i * 4]     = stops[i].position;
        flat[i * 4 + 1] = stops[i].color[0];
        flat[i * 4 + 2] = stops[i].color[1];
        flat[i * 4 + 3] = stops[i].color[2];
    }

    const result = wasm.gradient_overlay_rgba_wasm(
        toU8(data), width, height,
        flat, style, angle, scale, reverse, opacity
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Pattern Overlay — tiled pattern on layer content.
 */
function pattern_overlay(imageData, options = {}) {
    const { data, width, height } = imageData;
    const pattern = options.pattern;
    if (!pattern) throw new Error('pattern_overlay requires a pattern image');
    const scale = options.scale ?? 1.0;
    const ox = options.offset_x ?? 0;
    const oy = options.offset_y ?? 0;
    const opacity = options.opacity ?? 1.0;

    const result = wasm.pattern_overlay_rgba_wasm(
        toU8(data), width, height,
        toU8(pattern.data),
        pattern.width, pattern.height,
        scale, ox, oy, opacity
    );
    return { data: new Uint8ClampedArray(result.buffer), width, height, channels: 4, offset_x: 0, offset_y: 0 };
}

/**
 * Stroke — outline around layer content.
 */
function stroke(imageData, options = {}) {
    const { data, width, height } = imageData;
    const strokeWidth = options.width ?? 3;
    const c = options.color ?? [255, 0, 0];
    const opacity = options.opacity ?? 1.0;
    const position = options.position ?? 'outside';

    const result = wasm.stroke_rgba_wasm(
        toU8(data), width, height,
        strokeWidth, c[0], c[1], c[2], opacity, position
    );

    // Expansion depends on position
    let expand = 0;
    if (position === 'outside') expand = Math.ceil(strokeWidth);
    else if (position === 'center') expand = Math.ceil(strokeWidth / 2);

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: width + expand * 2,
        height: height + expand * 2,
        channels: 4,
        offset_x: -expand,
        offset_y: -expand,
    };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const effects = {
    drop_shadow,
    inner_shadow,
    outer_glow,
    inner_glow,
    bevel_emboss,
    satin,
    color_overlay,
    gradient_overlay,
    pattern_overlay,
    stroke,
};

/**
 * Apply an effect by ID.
 * @param {string} id - Effect ID
 * @param {Object} imageData - RGBA image data
 * @param {Object} [options] - Effect parameters
 * @returns {Object} Result image data with offset_x/offset_y
 */
export function applyEffect(id, imageData, options = {}) {
    const fn = effects[id];
    if (!fn) throw new Error(`Unknown effect: ${id}`);
    return fn(imageData, options);
}

/**
 * Get list of all available effect IDs.
 * @returns {string[]}
 */
export function getEffectIds() {
    return Object.keys(effects);
}

export default { initEffects, isInitialized, effects, applyEffect, getEffectIds };
