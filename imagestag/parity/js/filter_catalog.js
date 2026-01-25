/**
 * Centralized filter catalog for JavaScript parity testing.
 *
 * This module mirrors the Python filter_catalog.py and defines ALL cross-platform
 * filters with their default test parameters. Tests are automatically generated
 * for each filter - no individual test files needed.
 *
 * ## Adding a New Filter
 *
 * 1. Add an entry to FILTER_CATALOG with:
 *    - name: Filter name (matches Rust/Python/JS function name)
 *    - params: Default parameters for testing
 *    - inputs: List of input names (optional, defaults to ["deer", "astronaut"])
 *    - skipF32: Set true if no f32 variant exists
 *
 * 2. Add the WASM wrapper function to FILTER_IMPLEMENTATIONS
 */

import { initSync } from '../../filters/js/wasm/imagestag_rust.js';
import * as wasm from '../../filters/js/wasm/imagestag_rust.js';
import { convertU8ToF32, convertF32To12bit } from '../../filters/js/grayscale.js';
import {
    TEST_WIDTH,
    TEST_HEIGHT,
    TEST_INPUTS,
    DEFAULT_INPUT_NAMES,
    DEFAULT_TOLERANCE,
} from './constants.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Initialize WASM module - must be called before using any filter functions
// Uses synchronous loading for Node.js (fetch doesn't work for local files)
export async function initWasm() {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const wasmPath = path.join(__dirname, '..', '..', 'filters', 'js', 'wasm', 'imagestag_rust_bg.wasm');
    const wasmBuffer = fs.readFileSync(wasmPath);
    initSync(wasmBuffer);
}

// =============================================================================
// FILTER CATALOG - All cross-platform filters with default test parameters
//
// Each filter is tested with BOTH deer_128 (transparency) and astronaut_128
// (solid) by default. Only specify "inputs" to override for special cases.
// =============================================================================

export const FILTER_CATALOG = [
    // Grayscale
    { name: 'grayscale', params: {} },

    // Color Adjustment
    { name: 'brightness', params: { amount: 0.3 } },
    { name: 'contrast', params: { amount: 0.5 } },
    { name: 'saturation', params: { amount: 0.5 } },
    { name: 'gamma', params: { gamma_value: 2.2 } },
    { name: 'exposure', params: { exposure_val: 1.0, offset: 0.0, gamma_val: 1.0 } },
    { name: 'invert', params: {} },

    // Color Science
    { name: 'hue_shift', params: { degrees: 90.0 } },
    { name: 'vibrance', params: { amount: 0.5 } },
    {
        name: 'color_balance',
        params: {
            shadows: [0.1, 0.0, -0.1],
            midtones: [0.0, 0.0, 0.0],
            highlights: [-0.1, 0.0, 0.1],
        },
    },

    // Stylize
    { name: 'posterize', params: { levels: 4 } },
    { name: 'solarize', params: { threshold: 128 } },
    { name: 'threshold', params: { threshold_val: 128 } },
    { name: 'emboss', params: { angle: 135.0, depth: 1.0 } },

    // Levels & Curves
    {
        name: 'levels',
        params: {
            in_black: 20,
            in_white: 235,
            out_black: 0,
            out_white: 255,
            gamma: 1.0,
        },
    },
    { name: 'curves', params: { points: [[0.0, 0.0], [0.25, 0.35], [0.75, 0.65], [1.0, 1.0]] } },
    { name: 'auto_levels', params: { clip_percent: 0.01 } },

    // Sharpen & Blur
    { name: 'sharpen', params: { amount: 1.0 } },
    { name: 'unsharp_mask', params: { amount: 1.0, radius: 2.0, threshold: 0 } },
    { name: 'high_pass', params: { radius: 3.0 } },
    { name: 'motion_blur', params: { angle: 45.0, distance: 10.0 } },

    // Edge Detection
    { name: 'sobel', params: { direction: 'both' } },
    { name: 'laplacian', params: { kernel_size: 3 } },
    { name: 'find_edges', params: {} },

    // Noise
    { name: 'add_noise', params: { amount: 0.1, gaussian: true, monochrome: false, seed: 42 } },
    { name: 'median', params: { radius: 2 } },
    { name: 'denoise', params: { strength: 0.5 } },

    // Morphology
    { name: 'dilate', params: { radius: 2.0 } },
    { name: 'erode', params: { radius: 2.0 } },
];

// =============================================================================
// FILTER IMPLEMENTATIONS - WASM wrapper functions
// =============================================================================

/**
 * Helper to create a standard u8 filter wrapper.
 */
function createU8Filter(wasmFn, paramMapper = (p) => Object.values(p)) {
    return (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const channels = imageData.channels || 4;
        const wasmParams = paramMapper(params);

        const result = wasmFn(
            new Uint8Array(data.buffer),
            width,
            height,
            channels,
            ...wasmParams
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels
        };
    };
}

/**
 * Helper to create a standard f32 filter wrapper.
 * Converts u8 input to f32, processes, then converts to 12-bit for storage.
 */
function createF32Filter(wasmFn, paramMapper = (p) => Object.values(p)) {
    return (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const channels = imageData.channels || 4;

        // Convert u8 to f32
        const inputF32 = convertU8ToF32(imageData);
        const wasmParams = paramMapper(params);

        const resultF32 = wasmFn(
            new Float32Array(inputF32.data.buffer),
            width,
            height,
            channels,
            ...wasmParams
        );

        const f32Image = {
            data: new Float32Array(resultF32.buffer),
            width,
            height,
            channels
        };

        // Convert to 12-bit for storage
        return convertF32To12bit(f32Image);
    };
}

// Parameter mappers for filters with complex params
const paramMappers = {
    simple: (p) => [],
    amount: (p) => [p.amount ?? 0],
    gamma: (p) => [p.gamma_value ?? 1.0],
    exposure: (p) => [p.exposure_val ?? 0, p.offset ?? 0, p.gamma_val ?? 1.0],
    color_balance: (p) => [
        ...(p.shadows ?? [0, 0, 0]),
        ...(p.midtones ?? [0, 0, 0]),
        ...(p.highlights ?? [0, 0, 0]),
    ],
    posterize: (p) => [p.levels ?? 4],
    solarize_u8: (p) => [p.threshold ?? 128],
    solarize_f32: (p) => [(p.threshold ?? 128) / 255.0],
    threshold_u8: (p) => [p.threshold_val ?? 128],
    threshold_f32: (p) => [(p.threshold_val ?? 128) / 255.0],
    emboss: (p) => [p.angle ?? 135.0, p.depth ?? 1.0],
    levels_u8: (p) => [
        p.in_black ?? 0,
        p.in_white ?? 255,
        p.out_black ?? 0,
        p.out_white ?? 255,
        p.gamma ?? 1.0,
    ],
    levels_f32: (p) => [
        (p.in_black ?? 0) / 255.0,
        (p.in_white ?? 255) / 255.0,
        (p.out_black ?? 0) / 255.0,
        (p.out_white ?? 255) / 255.0,
        p.gamma ?? 1.0,
    ],
    curves: (p) => {
        const points = p.points ?? [[0, 0], [1, 1]];
        return [new Float32Array(points.flat())];
    },
    clip_percent: (p) => [p.clip_percent ?? 0.01],
    sharpen: (p) => [p.amount ?? 1.0],
    unsharp_mask_u8: (p) => [p.amount ?? 1.0, p.radius ?? 2.0, p.threshold ?? 0],
    unsharp_mask_f32: (p) => [p.amount ?? 1.0, p.radius ?? 2.0, (p.threshold ?? 0) / 255.0],
    high_pass: (p) => [p.radius ?? 3.0],
    motion_blur: (p) => [p.angle ?? 45.0, p.distance ?? 10.0],
    sobel: (p) => [p.direction ?? 'both'],
    laplacian: (p) => [p.kernel_size ?? 3],
    add_noise: (p) => [
        p.amount ?? 0.1,
        p.gaussian ?? true,
        p.monochrome ?? false,
        p.seed ?? 0,
    ],
    median: (p) => [p.radius ?? 1],
    denoise: (p) => [p.strength ?? 0.5],
    radius: (p) => [p.radius ?? 1.0],
};

// u8 filter implementations
export const FILTER_IMPLEMENTATIONS = {
    grayscale: createU8Filter(wasm.grayscale_rgba_wasm, paramMappers.simple),
    brightness: createU8Filter(wasm.brightness_wasm, paramMappers.amount),
    contrast: createU8Filter(wasm.contrast_wasm, paramMappers.amount),
    saturation: createU8Filter(wasm.saturation_wasm, paramMappers.amount),
    gamma: createU8Filter(wasm.gamma_wasm, paramMappers.gamma),
    exposure: createU8Filter(wasm.exposure_wasm, paramMappers.exposure),
    invert: createU8Filter(wasm.invert_wasm, paramMappers.simple),
    hue_shift: createU8Filter(wasm.hue_shift_wasm, (p) => [p.degrees ?? 0]),
    vibrance: createU8Filter(wasm.vibrance_wasm, paramMappers.amount),
    color_balance: createU8Filter(wasm.color_balance_wasm, paramMappers.color_balance),
    posterize: createU8Filter(wasm.posterize_wasm, paramMappers.posterize),
    solarize: createU8Filter(wasm.solarize_wasm, paramMappers.solarize_u8),
    threshold: createU8Filter(wasm.threshold_wasm, paramMappers.threshold_u8),
    emboss: createU8Filter(wasm.emboss_wasm, paramMappers.emboss),
    levels: createU8Filter(wasm.levels_wasm, paramMappers.levels_u8),
    curves: createU8Filter(wasm.curves_wasm, paramMappers.curves),
    auto_levels: createU8Filter(wasm.auto_levels_wasm, paramMappers.clip_percent),
    sharpen: createU8Filter(wasm.sharpen_wasm, paramMappers.sharpen),
    unsharp_mask: createU8Filter(wasm.unsharp_mask_wasm, paramMappers.unsharp_mask_u8),
    high_pass: createU8Filter(wasm.high_pass_wasm, paramMappers.high_pass),
    motion_blur: createU8Filter(wasm.motion_blur_wasm, paramMappers.motion_blur),
    sobel: createU8Filter(wasm.sobel_wasm, paramMappers.sobel),
    laplacian: createU8Filter(wasm.laplacian_wasm, paramMappers.laplacian),
    find_edges: createU8Filter(wasm.find_edges_wasm, paramMappers.simple),
    add_noise: createU8Filter(wasm.add_noise_wasm, paramMappers.add_noise),
    median: createU8Filter(wasm.median_wasm, paramMappers.median),
    denoise: createU8Filter(wasm.denoise_wasm, paramMappers.denoise),
    dilate: createU8Filter(wasm.dilate_wasm, paramMappers.radius),
    erode: createU8Filter(wasm.erode_wasm, paramMappers.radius),
};

// f32 filter implementations
export const FILTER_IMPLEMENTATIONS_F32 = {
    grayscale_f32: createF32Filter(wasm.grayscale_rgba_f32_wasm, paramMappers.simple),
    brightness_f32: createF32Filter(wasm.brightness_f32_wasm, paramMappers.amount),
    contrast_f32: createF32Filter(wasm.contrast_f32_wasm, paramMappers.amount),
    saturation_f32: createF32Filter(wasm.saturation_f32_wasm, paramMappers.amount),
    gamma_f32: createF32Filter(wasm.gamma_f32_wasm, paramMappers.gamma),
    exposure_f32: createF32Filter(wasm.exposure_f32_wasm, paramMappers.exposure),
    invert_f32: createF32Filter(wasm.invert_f32_wasm, paramMappers.simple),
    hue_shift_f32: createF32Filter(wasm.hue_shift_f32_wasm, (p) => [p.degrees ?? 0]),
    vibrance_f32: createF32Filter(wasm.vibrance_f32_wasm, paramMappers.amount),
    color_balance_f32: createF32Filter(wasm.color_balance_f32_wasm, paramMappers.color_balance),
    posterize_f32: createF32Filter(wasm.posterize_f32_wasm, paramMappers.posterize),
    solarize_f32: createF32Filter(wasm.solarize_f32_wasm, paramMappers.solarize_f32),
    threshold_f32: createF32Filter(wasm.threshold_f32_wasm, paramMappers.threshold_f32),
    emboss_f32: createF32Filter(wasm.emboss_f32_wasm, paramMappers.emboss),
    levels_f32: createF32Filter(wasm.levels_f32_wasm, paramMappers.levels_f32),
    curves_f32: createF32Filter(wasm.curves_f32_wasm, paramMappers.curves),
    auto_levels_f32: createF32Filter(wasm.auto_levels_f32_wasm, paramMappers.clip_percent),
    sharpen_f32: createF32Filter(wasm.sharpen_f32_wasm, paramMappers.sharpen),
    unsharp_mask_f32: createF32Filter(wasm.unsharp_mask_f32_wasm, paramMappers.unsharp_mask_f32),
    high_pass_f32: createF32Filter(wasm.high_pass_f32_wasm, paramMappers.high_pass),
    motion_blur_f32: createF32Filter(wasm.motion_blur_f32_wasm, paramMappers.motion_blur),
    sobel_f32: createF32Filter(wasm.sobel_f32_wasm, paramMappers.sobel),
    laplacian_f32: createF32Filter(wasm.laplacian_f32_wasm, paramMappers.laplacian),
    find_edges_f32: createF32Filter(wasm.find_edges_f32_wasm, paramMappers.simple),
    add_noise_f32: createF32Filter(wasm.add_noise_f32_wasm, paramMappers.add_noise),
    median_f32: createF32Filter(wasm.median_f32_wasm, paramMappers.median),
    denoise_f32: createF32Filter(wasm.denoise_f32_wasm, paramMappers.denoise),
    dilate_f32: createF32Filter(wasm.dilate_f32_wasm, paramMappers.radius),
    erode_f32: createF32Filter(wasm.erode_f32_wasm, paramMappers.radius),
};

/**
 * Register all filters from the catalog with the parity test runner.
 *
 * @param {ParityTestRunner} runner - The test runner instance
 * @returns {Object} - Map of filter names to registration success
 */
export function registerAllFilters(runner) {
    const results = {};

    for (const entry of FILTER_CATALOG) {
        const { name, params } = entry;
        const inputs = entry.inputs || DEFAULT_INPUT_NAMES;
        const skipF32 = entry.skipF32 || false;

        // Register u8 filter
        if (FILTER_IMPLEMENTATIONS[name]) {
            const filterFn = (imageData) => FILTER_IMPLEMENTATIONS[name](imageData, params);
            runner.registerFilter(name, filterFn);

            const testCases = inputs.map(inputName => ({
                id: inputName,
                description: `${name} filter - ${inputName}`,
                width: TEST_WIDTH,
                height: TEST_HEIGHT,
                inputGenerator: inputName,
                bitDepth: 'u8',
                params,
            }));
            runner.registerFilterTests(name, testCases);
            results[name] = true;
        } else {
            results[name] = false;
        }

        // Register f32 filter
        const f32Name = `${name}_f32`;
        if (!skipF32 && FILTER_IMPLEMENTATIONS_F32[f32Name]) {
            const filterFn = (imageData) => FILTER_IMPLEMENTATIONS_F32[f32Name](imageData, params);
            runner.registerFilter(f32Name, filterFn);

            const testCases = inputs.map(inputName => ({
                id: `${inputName}_f32`,
                description: `${name} filter - ${inputName} (f32)`,
                width: TEST_WIDTH,
                height: TEST_HEIGHT,
                inputGenerator: inputName,
                bitDepth: 'f32',
                params,
            }));
            runner.registerFilterTests(f32Name, testCases);
            results[f32Name] = true;
        }
    }

    return results;
}

/**
 * Get a summary of the filter catalog.
 */
export function getCatalogSummary() {
    const lines = [
        '# Cross-Platform Filter Catalog (JavaScript)',
        '',
        `Total filters: ${FILTER_CATALOG.length}`,
        '',
        '| Filter | Parameters |',
        '|--------|-----------|',
    ];

    for (const entry of FILTER_CATALOG) {
        const paramStr = Object.entries(entry.params)
            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
            .join(', ') || '(none)';
        lines.push(`| ${entry.name} | ${paramStr} |`);
    }

    return lines.join('\n');
}
