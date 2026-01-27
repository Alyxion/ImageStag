/**
 * ImageStag Filters - Central Browser Module
 *
 * Single entry point for all WASM-accelerated image filters.
 * Works in any browser environment with ES module support.
 *
 * Usage:
 *   import { initFilters, filters, applyFilter } from '/imgstag/filters/index.js';
 *
 *   await initFilters();
 *   const result = filters.grayscale(imageData);
 *   // or
 *   const result = applyFilter('grayscale', imageData, {});
 *
 * Image data format:
 *   { data: Uint8ClampedArray, width: number, height: number, channels?: number }
 *
 * All filters operate on RGBA u8 data and return the same format.
 */

import init, * as wasm from '../wasm/imagestag_rust.js';

let _initialized = false;

/**
 * Initialize the WASM module. Must be called before using any filter.
 * Safe to call multiple times.
 */
export async function initFilters() {
    if (_initialized) return;
    await init();
    _initialized = true;
}

/**
 * Check if WASM filters are initialized.
 * @returns {boolean}
 */
export function isInitialized() {
    return _initialized;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function u8filter(wasmFn, paramExtractor = () => []) {
    return (imageData, options = {}) => {
        const { data, width, height } = imageData;
        const channels = imageData.channels || 4;
        const params = paramExtractor(options);
        const u8 = data instanceof Uint8Array ? data :
            data.buffer ? new Uint8Array(data.buffer, data.byteOffset, data.byteLength) :
            new Uint8Array(data);
        const result = wasmFn(u8, width, height, channels, ...params);
        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels,
        };
    };
}

// ---------------------------------------------------------------------------
// Filter definitions — each maps a friendly name to a WASM function + params
// ---------------------------------------------------------------------------

/**
 * All available filters keyed by ID.
 * Each is a function: (imageData, options?) => imageData
 */
export const filters = {
    // --- Color ---
    grayscale:      u8filter(wasm.grayscale_rgba_wasm),
    invert:         u8filter(wasm.invert_wasm),
    brightness:     u8filter(wasm.brightness_wasm,    o => [o.amount ?? 0]),
    contrast:       u8filter(wasm.contrast_wasm,      o => [o.amount ?? 0]),
    saturation:     u8filter(wasm.saturation_wasm,    o => [o.amount ?? 0]),
    gamma:          u8filter(wasm.gamma_wasm,          o => [o.gamma_value ?? 1.0]),
    exposure:       u8filter(wasm.exposure_wasm,       o => [o.exposure_val ?? 0, o.offset ?? 0, o.gamma_val ?? 1.0]),
    hue_shift:      u8filter(wasm.hue_shift_wasm,     o => [o.degrees ?? 0]),
    vibrance:       u8filter(wasm.vibrance_wasm,       o => [o.amount ?? 0]),
    color_balance:  u8filter(wasm.color_balance_wasm,  o => {
        const s = o.shadows   || [0, 0, 0];
        const m = o.midtones  || [0, 0, 0];
        const h = o.highlights || [0, 0, 0];
        return [s[0], s[1], s[2], m[0], m[1], m[2], h[0], h[1], h[2]];
    }),

    // --- Levels / Curves ---
    levels:         u8filter(wasm.levels_wasm, o => [
        o.in_black ?? 0, o.in_white ?? 255, o.out_black ?? 0, o.out_white ?? 255, o.gamma ?? 1.0,
    ]),
    curves:         u8filter(wasm.curves_wasm, o => {
        const pts = o.points || [[0, 0], [1, 1]];
        return [new Float32Array(pts.flat())];
    }),
    auto_levels:    u8filter(wasm.auto_levels_wasm, o => [o.clip_percent ?? 0.01]),

    // --- Edge Detection ---
    sobel:          u8filter(wasm.sobel_wasm,      o => {
        const d = o.direction ?? 'both';
        // Rust expects 'h', 'v', or 'both'
        return [d === 'horizontal' ? 'h' : d === 'vertical' ? 'v' : d];
    }),
    laplacian:      u8filter(wasm.laplacian_wasm,  o => [o.kernel_size ?? 3]),
    find_edges:     u8filter(wasm.find_edges_wasm),

    // --- Blur ---
    motion_blur:    u8filter(wasm.motion_blur_wasm, o => [o.angle ?? 0, o.distance ?? 5]),

    // --- Sharpen ---
    sharpen:        u8filter(wasm.sharpen_wasm, o => [o.amount ?? 0.5]),
    unsharp_mask:   u8filter(wasm.unsharp_mask_wasm, o => [o.amount ?? 1.0, o.radius ?? 1.0, o.threshold ?? 0]),
    high_pass:      u8filter(wasm.high_pass_wasm, o => [o.radius ?? 3]),

    // --- Morphology ---
    dilate:         u8filter(wasm.dilate_wasm,  o => [o.radius ?? 1]),
    erode:          u8filter(wasm.erode_wasm,   o => [o.radius ?? 1]),

    // --- Noise ---
    add_noise:      u8filter(wasm.add_noise_wasm, o => [
        o.amount ?? 0.1, o.gaussian ?? true, o.monochrome ?? false, o.seed ?? 0,
    ]),
    median:         u8filter(wasm.median_wasm,   o => [o.radius ?? 1]),
    denoise:        u8filter(wasm.denoise_wasm,  o => [o.strength ?? 0.5]),

    // --- Stylize ---
    posterize:      u8filter(wasm.posterize_wasm,  o => [o.levels ?? 4]),
    solarize:       u8filter(wasm.solarize_wasm,   o => [o.threshold ?? 128]),
    threshold:      u8filter(wasm.threshold_wasm,  o => [o.threshold ?? 128]),
    emboss:         u8filter(wasm.emboss_wasm,     o => [o.angle ?? 45, o.depth ?? 1.0]),
};

/**
 * Apply a filter by ID.
 * @param {string} id - Filter ID (e.g. 'grayscale', 'brightness')
 * @param {Object} imageData - {data, width, height, channels?}
 * @param {Object} [options] - Filter-specific parameters
 * @returns {Object} - Filtered image data
 * @throws {Error} If filter ID is unknown
 */
export function applyFilter(id, imageData, options = {}) {
    const fn = filters[id];
    if (!fn) throw new Error(`Unknown filter: ${id}`);
    return fn(imageData, options);
}

/**
 * Get list of all available filter IDs.
 * @returns {string[]}
 */
export function getFilterIds() {
    return Object.keys(filters);
}

/**
 * Filter metadata for UI display and parameter schemas.
 * Maps filter IDs to { name, category, params[] } objects matching
 * the same schema as the backend /api/filters endpoint.
 */
export const filterMetadata = {
    grayscale:     { name: 'Grayscale',        category: 'color',      params: [] },
    invert:        { name: 'Invert',           category: 'color',      params: [] },
    brightness:    { name: 'Brightness',       category: 'color',      params: [
        { id: 'amount', name: 'Amount', type: 'range', min: -1, max: 1, step: 0.01, default: 0 },
    ]},
    contrast:      { name: 'Contrast',         category: 'color',      params: [
        { id: 'amount', name: 'Amount', type: 'range', min: -1, max: 1, step: 0.01, default: 0 },
    ]},
    saturation:    { name: 'Saturation',       category: 'color',      params: [
        { id: 'amount', name: 'Amount', type: 'range', min: -1, max: 1, step: 0.01, default: 0 },
    ]},
    gamma:         { name: 'Gamma',            category: 'color',      params: [
        { id: 'gamma_value', name: 'Gamma', type: 'range', min: 0.1, max: 5, step: 0.01, default: 1.0 },
    ]},
    exposure:      { name: 'Exposure',         category: 'color',      params: [
        { id: 'exposure_val', name: 'Exposure', type: 'range', min: -3, max: 3, step: 0.01, default: 0 },
        { id: 'offset', name: 'Offset', type: 'range', min: -0.5, max: 0.5, step: 0.01, default: 0 },
        { id: 'gamma_val', name: 'Gamma', type: 'range', min: 0.1, max: 5, step: 0.01, default: 1.0 },
    ]},
    hue_shift:     { name: 'Hue Shift',       category: 'color',      params: [
        { id: 'degrees', name: 'Degrees', type: 'range', min: 0, max: 360, step: 1, default: 0 },
    ]},
    vibrance:      { name: 'Vibrance',        category: 'color',      params: [
        { id: 'amount', name: 'Amount', type: 'range', min: -1, max: 1, step: 0.01, default: 0 },
    ]},
    color_balance: { name: 'Color Balance',   category: 'color',      params: [
        { id: 'shadows',    name: 'Shadows (R,G,B)',    type: 'color_triplet', min: -1, max: 1, default: [0,0,0] },
        { id: 'midtones',   name: 'Midtones (R,G,B)',   type: 'color_triplet', min: -1, max: 1, default: [0,0,0] },
        { id: 'highlights', name: 'Highlights (R,G,B)', type: 'color_triplet', min: -1, max: 1, default: [0,0,0] },
    ]},

    levels:        { name: 'Levels',           category: 'color',      params: [
        { id: 'in_black',  name: 'Input Black',  type: 'range', min: 0, max: 255, step: 1, default: 0 },
        { id: 'in_white',  name: 'Input White',  type: 'range', min: 0, max: 255, step: 1, default: 255 },
        { id: 'out_black', name: 'Output Black', type: 'range', min: 0, max: 255, step: 1, default: 0 },
        { id: 'out_white', name: 'Output White', type: 'range', min: 0, max: 255, step: 1, default: 255 },
        { id: 'gamma',     name: 'Gamma',        type: 'range', min: 0.1, max: 5, step: 0.01, default: 1.0 },
    ]},
    auto_levels:   { name: 'Auto Levels',     category: 'color',      params: [
        { id: 'clip_percent', name: 'Clip %', type: 'range', min: 0, max: 0.5, step: 0.001, default: 0.01 },
    ]},

    sobel:         { name: 'Sobel Edge',       category: 'edge',       params: [
        { id: 'direction', name: 'Direction', type: 'select', options: ['both', 'horizontal', 'vertical'], default: 'both' },
    ]},
    laplacian:     { name: 'Laplacian Edge',   category: 'edge',       params: [
        { id: 'kernel_size', name: 'Kernel Size', type: 'select', options: [3, 5], default: 3 },
    ]},
    find_edges:    { name: 'Find Edges (Canny)', category: 'edge',    params: [] },

    motion_blur:   { name: 'Motion Blur',      category: 'blur',       params: [
        { id: 'angle', name: 'Angle', type: 'range', min: 0, max: 360, step: 1, default: 0 },
        { id: 'distance', name: 'Distance', type: 'range', min: 1, max: 50, step: 1, default: 5 },
    ]},

    sharpen:       { name: 'Sharpen',          category: 'sharpen',    params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 5, step: 0.1, default: 0.5 },
    ]},
    unsharp_mask:  { name: 'Unsharp Mask',     category: 'sharpen',    params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 5, step: 0.1, default: 1.0 },
        { id: 'radius', name: 'Radius', type: 'range', min: 0.1, max: 20, step: 0.1, default: 1.0 },
        { id: 'threshold', name: 'Threshold', type: 'range', min: 0, max: 255, step: 1, default: 0 },
    ]},
    high_pass:     { name: 'High Pass',        category: 'sharpen',    params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 50, step: 1, default: 3 },
    ]},

    dilate:        { name: 'Dilate',           category: 'morphology', params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 20, step: 1, default: 1 },
    ]},
    erode:         { name: 'Erode',            category: 'morphology', params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 20, step: 1, default: 1 },
    ]},

    add_noise:     { name: 'Add Noise',        category: 'noise',      params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 1, step: 0.01, default: 0.1 },
        { id: 'gaussian', name: 'Gaussian', type: 'checkbox', default: true },
        { id: 'monochrome', name: 'Monochrome', type: 'checkbox', default: false },
    ]},
    median:        { name: 'Median',           category: 'noise',      params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 10, step: 1, default: 1 },
    ]},
    denoise:       { name: 'Denoise',          category: 'noise',      params: [
        { id: 'strength', name: 'Strength', type: 'range', min: 0, max: 1, step: 0.01, default: 0.5 },
    ]},

    posterize:     { name: 'Posterize',        category: 'artistic',   params: [
        { id: 'levels', name: 'Levels', type: 'range', min: 2, max: 32, step: 1, default: 4 },
    ]},
    solarize:      { name: 'Solarize',         category: 'artistic',   params: [
        { id: 'threshold', name: 'Threshold', type: 'range', min: 0, max: 255, step: 1, default: 128 },
    ]},
    threshold:     { name: 'Threshold',        category: 'threshold',  params: [
        { id: 'threshold', name: 'Threshold', type: 'range', min: 0, max: 255, step: 1, default: 128 },
    ]},
    emboss:        { name: 'Emboss',           category: 'artistic',   params: [
        { id: 'angle', name: 'Angle', type: 'range', min: 0, max: 360, step: 1, default: 45 },
        { id: 'depth', name: 'Depth', type: 'range', min: 0.1, max: 5, step: 0.1, default: 1.0 },
    ]},
};

export default { initFilters, isInitialized, filters, applyFilter, getFilterIds, filterMetadata };
