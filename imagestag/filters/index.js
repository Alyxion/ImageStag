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
    brightness:     u8filter(wasm.brightness_wasm,    o => [(o.amount ?? 0) / 100]),
    contrast:       u8filter(wasm.contrast_wasm,      o => [(o.amount ?? 0) / 100]),
    saturation:     u8filter(wasm.saturation_wasm,    o => [(o.amount ?? 0) / 100]),
    gamma:          u8filter(wasm.gamma_wasm,          o => [o.gamma_value ?? 1.0]),
    exposure:       u8filter(wasm.exposure_wasm,       o => [o.exposure_val ?? 0, o.offset ?? 0, o.gamma_val ?? 1.0]),
    hue_shift:      u8filter(wasm.hue_shift_wasm,     o => [o.degrees ?? 0]),
    vibrance:       u8filter(wasm.vibrance_wasm,       o => [(o.amount ?? 0) / 100]),
    color_balance:  u8filter(wasm.color_balance_wasm,  o => {
        // Support both legacy triplet params and new range-based params
        if (o.shadows || o.midtones || o.highlights) {
            const s = o.shadows   || [0, 0, 0];
            const m = o.midtones  || [0, 0, 0];
            const h = o.highlights || [0, 0, 0];
            return [s[0], s[1], s[2], m[0], m[1], m[2], h[0], h[1], h[2]];
        }
        // Range-based: red/green/blue apply to selected tonal range
        const r = (o.red ?? 0) / 100, g = (o.green ?? 0) / 100, b = (o.blue ?? 0) / 100;
        const range = o.range ?? 'midtones';
        const s = range === 'shadows'    ? [r, g, b] : [0, 0, 0];
        const m = range === 'midtones'   ? [r, g, b] : [0, 0, 0];
        const h = range === 'highlights' ? [r, g, b] : [0, 0, 0];
        return [s[0], s[1], s[2], m[0], m[1], m[2], h[0], h[1], h[2]];
    }),
    sepia:          u8filter(wasm.sepia_wasm,          o => [(o.intensity ?? 100) / 100]),
    temperature:    u8filter(wasm.temperature_wasm,    o => [(o.amount ?? 0) / 100]),
    channel_mixer:  u8filter(wasm.channel_mixer_wasm,  o => [o.r_source ?? 0, o.g_source ?? 1, o.b_source ?? 2]),
    equalize_histogram: u8filter(wasm.equalize_histogram_wasm),

    // --- Levels / Curves ---
    levels:         u8filter(wasm.levels_wasm, o => [
        o.in_black ?? 0, o.in_white ?? 255, o.out_black ?? 0, o.out_white ?? 255, o.gamma ?? 1.0,
    ]),
    curves:         u8filter(wasm.curves_wasm, o => {
        const pts = o.points || [[0, 0], [1, 1]];
        return [new Float32Array(pts.flat())];
    }),
    auto_levels:    u8filter(wasm.auto_levels_wasm, o => [(o.clip_percent ?? 1.0) / 100]),

    // --- Edge Detection ---
    sobel:          u8filter(wasm.sobel_wasm,      o => {
        const d = o.direction ?? 'both';
        // Rust expects 'h', 'v', or 'both'
        return [d === 'horizontal' ? 'h' : d === 'vertical' ? 'v' : d, o.kernel_size ?? 3];
    }),
    laplacian:      u8filter(wasm.laplacian_wasm,  o => [o.kernel_size ?? 3]),
    find_edges:     u8filter(wasm.find_edges_wasm, o => [o.sigma ?? 1.0, o.low_threshold ?? 0.1, o.high_threshold ?? 0.2]),
    draw_contours:  u8filter(wasm.draw_contours_wasm, o => [o.threshold ?? 128, o.line_width ?? 2, o.color_r ?? 0, o.color_g ?? 255, o.color_b ?? 0]),

    // --- Blur ---
    gaussian_blur:  u8filter(wasm.gaussian_blur_wasm,  o => [o.sigma ?? 3.0]),
    box_blur:       u8filter(wasm.box_blur_wasm,       o => [o.radius ?? 5]),
    motion_blur:    u8filter(wasm.motion_blur_wasm,    o => [o.angle ?? 0, o.distance ?? 5]),

    // --- Sharpen ---
    sharpen:        u8filter(wasm.sharpen_wasm, o => [o.amount ?? 0.5]),
    unsharp_mask:   u8filter(wasm.unsharp_mask_wasm, o => [o.amount ?? 1.0, o.radius ?? 1.0, o.threshold ?? 0]),
    high_pass:      u8filter(wasm.high_pass_wasm, o => [o.radius ?? 3]),

    // --- Morphology ---
    dilate:         u8filter(wasm.dilate_wasm,           o => [o.radius ?? 1]),
    erode:          u8filter(wasm.erode_wasm,            o => [o.radius ?? 1]),
    morphology_open:    u8filter(wasm.morphology_open_wasm,    o => [o.radius ?? 1]),
    morphology_close:   u8filter(wasm.morphology_close_wasm,   o => [o.radius ?? 1]),
    morphology_gradient: u8filter(wasm.morphology_gradient_wasm, o => [o.radius ?? 1]),
    tophat:         u8filter(wasm.tophat_wasm,           o => [o.radius ?? 1]),
    blackhat:       u8filter(wasm.blackhat_wasm,         o => [o.radius ?? 1]),

    // --- Noise ---
    add_noise:      u8filter(wasm.add_noise_wasm, o => [
        (o.amount ?? 20) / 100, o.gaussian ?? true, o.monochrome ?? false, o.seed ?? 0,
    ]),
    median:         u8filter(wasm.median_wasm,   o => [o.radius ?? 1]),
    denoise:        u8filter(wasm.denoise_wasm,  o => [(o.strength ?? 33) / 100]),

    // --- Stylize ---
    posterize:      u8filter(wasm.posterize_wasm,  o => [o.levels ?? 4]),
    solarize:       u8filter(wasm.solarize_wasm,   o => [o.threshold ?? 128]),
    threshold:      u8filter(wasm.threshold_wasm,  o => [o.threshold ?? 128]),
    emboss:         u8filter(wasm.emboss_wasm,     o => [o.angle ?? 135, o.depth ?? 1.0]),
    pixelate:       u8filter(wasm.pixelate_wasm,   o => [o.block_size ?? 10]),
    vignette:       u8filter(wasm.vignette_wasm,   o => [(o.amount ?? 40) * 0.02]),

    // --- Composite filters (chain/dispatch to individual WASM filters) ---
    brightness_contrast: (imageData, options = {}) => {
        let result = imageData;
        const b = options.brightness ?? 0;
        const c = options.contrast ?? 0;
        const g = options.gamma ?? 1.0;
        if (b !== 0) result = filters.brightness(result, { amount: b });
        if (c !== 0) result = filters.contrast(result, { amount: c });
        if (g !== 1.0) result = filters.gamma(result, { gamma_value: g });
        return result;
    },
    hue_saturation: (imageData, options = {}) => {
        let result = imageData;
        const h = options.hue ?? 0;
        const s = options.saturation ?? 0;
        const l = options.lightness ?? 0;
        const v = options.vibrance ?? 0;
        const t = options.temperature ?? 0;
        if (h !== 0) result = filters.hue_shift(result, { degrees: h });
        if (s !== 0) result = filters.saturation(result, { amount: s });
        if (l !== 0) result = filters.brightness(result, { amount: l });
        if (v !== 0) result = filters.vibrance(result, { amount: v });
        if (t !== 0) result = filters.temperature(result, { amount: t });
        return result;
    },
    binary_threshold: (imageData, options = {}) => {
        return filters.threshold(imageData, { threshold: options.threshold ?? 128 });
    },
    auto_contrast: (imageData, options = {}) => {
        return filters.auto_levels(imageData, { clip_percent: options.clip_percent ?? 1.0 });
    },
    median_blur: (imageData, options = {}) => {
        return filters.median(imageData, { radius: options.radius ?? 3 });
    },
    find_contours: (imageData, options = {}) => {
        const sigma = options.sigma ?? 1.0;
        const lowT = options.low_threshold ?? 0.1;
        const highT = options.high_threshold ?? 0.2;
        const lineWidth = options.line_width ?? 2;
        const color = options.color ?? '#000000';

        // Canny edge detection
        let edges = filters.find_edges(imageData, { sigma, low_threshold: lowT, high_threshold: highT });

        // Thicken edges if line_width > 1
        if (lineWidth > 1) {
            edges = filters.dilate(edges, { radius: lineWidth - 1 });
        }

        // Parse color
        const c = color.replace('#', '');
        const cr = parseInt(c.substring(0, 2), 16);
        const cg = parseInt(c.substring(2, 4), 16);
        const cb = parseInt(c.substring(4, 6), 16);

        // Colorize: edge pixels get chosen color, rest is transparent black
        const src = edges.data;
        const out = new Uint8ClampedArray(src.length);
        for (let i = 0; i < src.length; i += 4) {
            const lum = src[i]; // luminance from Canny output
            if (lum > 0) {
                const f = lum / 255;
                out[i]     = Math.round(f * cr);
                out[i + 1] = Math.round(f * cg);
                out[i + 2] = Math.round(f * cb);
                out[i + 3] = lum;
            }
        }
        return { data: out, width: edges.width, height: edges.height, channels: edges.channels || 4 };
    },
    pencil_sketch: u8filter(wasm.pencil_sketch_wasm, o => [o.sigma_s ?? 60, o.shade_factor ?? 50]),
    edge_detect: (imageData, options = {}) => {
        const method = options.method ?? 'sobel';
        switch (method) {
            case 'laplacian': return filters.laplacian(imageData, options);
            default: return filters.sobel(imageData, options);
        }
    },
    morphology_op: (imageData, options = {}) => {
        const op = options.operation ?? 'dilate';
        const params = { radius: options.radius ?? 1 };
        switch (op) {
            case 'erode': return filters.erode(imageData, params);
            case 'open': return filters.morphology_open(imageData, params);
            case 'close': return filters.morphology_close(imageData, params);
            case 'gradient': return filters.morphology_gradient(imageData, params);
            case 'tophat': return filters.tophat(imageData, params);
            case 'blackhat': return filters.blackhat(imageData, params);
            default: return filters.dilate(imageData, params);
        }
    },
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
    brightness_contrast: { name: 'Brightness/Contrast', category: 'color', params: [
        { id: 'brightness', name: 'Brightness', type: 'range', min: -100, max: 100, step: 1, default: 0, suffix: '%' },
        { id: 'contrast', name: 'Contrast', type: 'range', min: -100, max: 100, step: 1, default: 0, suffix: '%' },
        { id: 'gamma', name: 'Gamma', type: 'range', min: 0.1, max: 3.0, step: 0.01, default: 1.0 },
    ]},
    hue_saturation: { name: 'Hue / Saturation', category: 'color', params: [
        { id: 'hue', name: 'Hue', type: 'range', min: -180, max: 180, step: 1, default: 0, suffix: '°' },
        { id: 'saturation', name: 'Saturation', type: 'range', min: -100, max: 100, step: 1, default: 0, suffix: '%' },
        { id: 'lightness', name: 'Lightness', type: 'range', min: -100, max: 100, step: 1, default: 0, suffix: '%' },
        { id: 'vibrance', name: 'Vibrance', type: 'range', min: -100, max: 100, step: 1, default: 0, suffix: '%' },
        { id: 'temperature', name: 'Temperature', type: 'range', min: -100, max: 100, step: 1, default: 0 },
    ]},
    exposure:      { name: 'Exposure',         category: 'color',      params: [
        { id: 'exposure_val', name: 'Exposure', type: 'range', min: -3, max: 3, step: 0.01, default: 0, suffix: 'EV' },
        { id: 'offset', name: 'Offset', type: 'range', min: -0.5, max: 0.5, step: 0.01, default: 0 },
        { id: 'gamma_val', name: 'Gamma', type: 'range', min: 0.1, max: 5, step: 0.01, default: 1.0 },
    ]},
    color_balance: { name: 'Color Balance',   category: 'color',      params: [
        { id: 'range', name: 'Tonal Range', type: 'select', options: ['shadows', 'midtones', 'highlights'], default: 'midtones' },
        { id: 'red', name: 'Cyan/Red', type: 'range', min: -100, max: 100, step: 1, default: 0 },
        { id: 'green', name: 'Magenta/Green', type: 'range', min: -100, max: 100, step: 1, default: 0 },
        { id: 'blue', name: 'Yellow/Blue', type: 'range', min: -100, max: 100, step: 1, default: 0 },
    ]},
    sepia:         { name: 'Sepia',            category: 'color',      params: [
        { id: 'intensity', name: 'Intensity', type: 'range', min: 0, max: 100, step: 1, default: 100, suffix: '%' },
    ]},
    channel_mixer: { name: 'Channel Mixer',    category: 'color',      params: [
        { id: 'r_source', name: 'Red Source', type: 'select', options: [0, 1, 2], default: 0 },
        { id: 'g_source', name: 'Green Source', type: 'select', options: [0, 1, 2], default: 1 },
        { id: 'b_source', name: 'Blue Source', type: 'select', options: [0, 1, 2], default: 2 },
    ]},
    equalize_histogram: { name: 'Equalize Histogram', category: 'color', params: [] },

    levels:        { name: 'Levels',           category: 'color',      params: [
        { id: 'in_black',  name: 'Input Black',  type: 'range', min: 0, max: 255, step: 1, default: 0 },
        { id: 'in_white',  name: 'Input White',  type: 'range', min: 0, max: 255, step: 1, default: 255 },
        { id: 'out_black', name: 'Output Black', type: 'range', min: 0, max: 255, step: 1, default: 0 },
        { id: 'out_white', name: 'Output White', type: 'range', min: 0, max: 255, step: 1, default: 255 },
        { id: 'gamma',     name: 'Gamma',        type: 'range', min: 0.1, max: 5, step: 0.01, default: 1.0 },
    ]},
    auto_levels:   { name: 'Auto Levels',     category: 'color',      params: [
        { id: 'clip_percent', name: 'Clip %', type: 'range', min: 0, max: 5, step: 0.1, default: 1.0, suffix: '%' },
    ]},
    auto_contrast: { name: 'Auto Contrast', category: 'color', params: [
        { id: 'clip_percent', name: 'Clip Percent', type: 'range', min: 0.0, max: 5.0, step: 0.1, default: 1.0, suffix: '%' },
    ]},
    median_blur:   { name: 'Median Blur', category: 'blur', params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 21, step: 1, default: 3 },
    ]},

    edge_detect:   { name: 'Edge Detection',   category: 'edge',       params: [
        { id: 'method', name: 'Method', type: 'select', options: ['sobel', 'laplacian'], default: 'sobel' },
        { id: 'direction', name: 'Direction', type: 'select', options: ['both', 'horizontal', 'vertical'], default: 'both', visible_when: { method: ['sobel'] } },
        { id: 'kernel_size', name: 'Kernel Size', type: 'select', options: [3, 5, 7], default: 3 },
    ]},
    find_contours: { name: 'Find Contours', category: 'edge', params: [
        { id: 'sigma', name: 'Sigma', type: 'range', min: 0.1, max: 5.0, step: 0.1, default: 1.0 },
        { id: 'low_threshold', name: 'Low Threshold', type: 'range', min: 0.01, max: 0.5, step: 0.01, default: 0.1 },
        { id: 'high_threshold', name: 'High Threshold', type: 'range', min: 0.01, max: 0.5, step: 0.01, default: 0.2 },
        { id: 'line_width', name: 'Line Width', type: 'range', min: 1, max: 10, step: 1, default: 2, suffix: 'px' },
        { id: 'color', name: 'Color', type: 'color', default: '#000000' },
    ]},

    gaussian_blur: { name: 'Gaussian Blur',    category: 'blur',       params: [
        { id: 'sigma', name: 'Sigma', type: 'range', min: 0.1, max: 20, step: 0.1, default: 3.0, suffix: 'px' },
    ]},
    box_blur:      { name: 'Box Blur',         category: 'blur',       params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 50, step: 1, default: 5, suffix: 'px' },
    ]},
    motion_blur:   { name: 'Motion Blur',      category: 'blur',       params: [
        { id: 'angle', name: 'Angle', type: 'range', min: 0, max: 360, step: 1, default: 0, suffix: '°' },
        { id: 'distance', name: 'Distance', type: 'range', min: 1, max: 50, step: 1, default: 5, suffix: 'px' },
    ]},

    sharpen:       { name: 'Sharpen',          category: 'sharpen',    params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 5, step: 0.1, default: 0.5 },
    ]},
    unsharp_mask:  { name: 'Unsharp Mask',     category: 'sharpen',    params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 5, step: 0.1, default: 1.0 },
        { id: 'radius', name: 'Radius', type: 'range', min: 0.1, max: 20, step: 0.1, default: 1.0, suffix: 'px' },
        { id: 'threshold', name: 'Threshold', type: 'range', min: 0, max: 255, step: 1, default: 0 },
    ]},
    high_pass:     { name: 'High Pass',        category: 'sharpen',    params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 50, step: 1, default: 3, suffix: 'px' },
    ]},

    morphology_op: { name: 'Morphological',      category: 'morphology', params: [
        { id: 'operation', name: 'Operation', type: 'select', options: ['dilate', 'erode', 'open', 'close', 'gradient', 'tophat', 'blackhat'], default: 'dilate' },
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 20, step: 1, default: 1, suffix: 'px' },
    ]},

    add_noise:     { name: 'Add Noise',        category: 'noise',      params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 100, step: 1, default: 20, suffix: '%' },
        { id: 'gaussian', name: 'Gaussian', type: 'checkbox', default: true },
        { id: 'monochrome', name: 'Monochrome', type: 'checkbox', default: false },
    ]},
    median:        { name: 'Median',           category: 'noise',      params: [
        { id: 'radius', name: 'Radius', type: 'range', min: 1, max: 10, step: 1, default: 1 },
    ]},
    denoise:       { name: 'Denoise',          category: 'noise',      params: [
        { id: 'strength', name: 'Strength', type: 'range', min: 0, max: 100, step: 1, default: 33, suffix: '%' },
    ]},

    posterize:     { name: 'Posterize',        category: 'artistic',   params: [
        { id: 'levels', name: 'Levels', type: 'range', min: 2, max: 32, step: 1, default: 4 },
    ]},
    solarize:      { name: 'Solarize',         category: 'artistic',   params: [
        { id: 'threshold', name: 'Threshold', type: 'range', min: 0, max: 255, step: 1, default: 128 },
    ]},
    threshold:     { name: 'Threshold',        category: 'color',      params: [
        { id: 'threshold', name: 'Threshold', type: 'range', min: 0, max: 255, step: 1, default: 128 },
    ]},
    pixelate:      { name: 'Pixelate',         category: 'artistic',   params: [
        { id: 'block_size', name: 'Block Size', type: 'range', min: 2, max: 50, step: 1, default: 10, suffix: 'px' },
    ]},
    vignette:      { name: 'Vignette',         category: 'artistic',   params: [
        { id: 'amount', name: 'Amount', type: 'range', min: 0, max: 100, step: 1, default: 40, suffix: '%' },
    ]},
    emboss:        { name: 'Emboss',           category: 'artistic',   params: [
        { id: 'angle', name: 'Angle', type: 'range', min: 0, max: 360, step: 1, default: 135, suffix: '°' },
        { id: 'depth', name: 'Depth', type: 'range', min: 0.1, max: 5, step: 0.1, default: 1.0 },
    ]},
    pencil_sketch: { name: 'Pencil Sketch', category: 'artistic', params: [
        { id: 'sigma_s', name: 'Smoothness', type: 'range', min: 10, max: 200, step: 10, default: 60 },
        { id: 'sigma_r', name: 'Edge Strength', type: 'range', min: 1, max: 100, step: 1, default: 35, suffix: '%' },
        { id: 'shade_factor', name: 'Shade Factor', type: 'range', min: 0, max: 100, step: 1, default: 50, suffix: '%' },
    ]},
};

export default { initFilters, isInitialized, filters, applyFilter, getFilterIds, filterMetadata };
