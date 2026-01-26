/**
 * Centralized layer effect catalog for JavaScript parity testing.
 *
 * This module mirrors the Python layer_effect_catalog.py and defines ALL layer effects
 * with their default test parameters.
 *
 * ## Available Layer Effects (with WASM bindings)
 *
 * - drop_shadow: Shadow cast behind layer
 * - inner_shadow: Shadow inside layer edges
 * - outer_glow: Glow outside layer edges
 * - inner_glow: Glow inside layer edges
 * - bevel_emboss: 3D raised/sunken appearance
 * - satin: Silky interior shading
 * - color_overlay: Solid color fill
 * - gradient_overlay: Gradient fill
 * - pattern_overlay: Tiled pattern fill
 * - stroke: Outline around layer
 */

import { initSync } from '../../filters/js/wasm/imagestag_rust.js';
import * as wasm from '../../filters/js/wasm/imagestag_rust.js';
import { convertU8ToF32, convertF32To12bit } from '../../filters/js/grayscale.js';
import {
    TEST_WIDTH,
    TEST_HEIGHT,
    DEFAULT_TOLERANCE,
} from './constants.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Initialize WASM module
export async function initWasm() {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const wasmPath = path.join(__dirname, '..', '..', 'filters', 'js', 'wasm', 'imagestag_rust_bg.wasm');
    const wasmBuffer = fs.readFileSync(wasmPath);
    initSync(wasmBuffer);
}

// =============================================================================
// LAYER EFFECT CATALOG - All effects with WASM bindings
// =============================================================================

export const LAYER_EFFECT_CATALOG = [
    {
        name: 'drop_shadow',
        params: {
            offset_x: 4.0,
            offset_y: 4.0,
            blur_radius: 5.0,
            color: [0, 0, 0],
            opacity: 0.75,
        },
        inputs: ['deer'],
    },
    {
        name: 'inner_shadow',
        params: {
            offset_x: 2.0,
            offset_y: 2.0,
            blur_radius: 5.0,
            choke: 0.0,
            color: [0, 0, 0],
            opacity: 0.75,
        },
        inputs: ['deer'],
    },
    {
        name: 'outer_glow',
        params: {
            radius: 10.0,
            color: [255, 255, 0],
            opacity: 0.75,
            spread: 0.0,
        },
        inputs: ['deer'],
    },
    {
        name: 'inner_glow',
        params: {
            radius: 10.0,
            color: [255, 255, 0],
            opacity: 0.75,
            choke: 0.0,
        },
        inputs: ['deer'],
    },
    {
        name: 'bevel_emboss',
        params: {
            depth: 3.0,
            angle: 120.0,
            altitude: 30.0,
            highlight_color: [255, 255, 255],
            highlight_opacity: 0.75,
            shadow_color: [0, 0, 0],
            shadow_opacity: 0.75,
            style: 'inner_bevel',
        },
        inputs: ['deer'],
    },
    {
        name: 'satin',
        params: {
            color: [0, 0, 0],
            opacity: 0.5,
            angle: 19.0,
            distance: 11.0,
            size: 14.0,
            invert: false,
        },
        inputs: ['deer'],
    },
    {
        name: 'color_overlay',
        params: {
            color: [255, 0, 0],
            opacity: 1.0,
        },
        inputs: ['deer'],
    },
    {
        name: 'gradient_overlay',
        params: {
            // Gradient stops: [pos, r, g, b, ...]
            stops: [0.0, 255, 0, 0, 0.5, 255, 255, 0, 1.0, 0, 0, 255],
            style: 'linear',
            angle: 90.0,
            scale: 1.0,
            reverse: false,
            opacity: 1.0,
        },
        inputs: ['deer'],
    },
    {
        name: 'pattern_overlay',
        params: {
            scale: 4.0,
            offset_x: 0,
            offset_y: 0,
            opacity: 0.8,
        },
        inputs: ['deer'],
    },
    {
        name: 'stroke',
        params: {
            width: 3.0,
            color: [255, 0, 0],  // Red for visibility
            opacity: 1.0,
            position: 'outside',
        },
        inputs: ['deer'],
    },
];

// =============================================================================
// LAYER EFFECT IMPLEMENTATIONS - WASM wrappers
// =============================================================================

/**
 * Create default 2x2 checkerboard pattern.
 */
function createDefaultPattern() {
    // 2x2 checkerboard RGBA
    return new Uint8Array([
        255, 255, 255, 255,   0,   0,   0, 255,
          0,   0,   0, 255, 255, 255, 255, 255,
    ]);
}

// u8 layer effect implementations
export const LAYER_EFFECT_IMPLEMENTATIONS = {
    drop_shadow: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [0, 0, 0];

        const result = wasm.drop_shadow_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            params.offset_x ?? 4.0,
            params.offset_y ?? 4.0,
            params.blur_radius ?? 5.0,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 0.75
        );

        // Note: drop_shadow expands canvas, need to compute new dimensions
        const blur_expand = Math.ceil((params.blur_radius ?? 5.0) * 3.0);
        const offset_expand = Math.ceil(Math.max(Math.abs(params.offset_x ?? 4.0), Math.abs(params.offset_y ?? 4.0)));
        const expand = blur_expand + offset_expand + 2;
        const newWidth = width + expand * 2;
        const newHeight = height + expand * 2;

        return {
            data: new Uint8ClampedArray(result.buffer),
            width: newWidth,
            height: newHeight,
            channels: 4
        };
    },

    inner_shadow: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [0, 0, 0];

        const result = wasm.inner_shadow_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            params.offset_x ?? 2.0,
            params.offset_y ?? 2.0,
            params.blur_radius ?? 5.0,
            params.choke ?? 0.0,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 0.75
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    },

    outer_glow: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [255, 255, 0];

        const result = wasm.outer_glow_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            params.radius ?? 10.0,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 0.75,
            params.spread ?? 0.0
        );

        // outer_glow expands canvas
        const expand = Math.ceil((params.radius ?? 10.0) * 3.0) + 2;
        const newWidth = width + expand * 2;
        const newHeight = height + expand * 2;

        return {
            data: new Uint8ClampedArray(result.buffer),
            width: newWidth,
            height: newHeight,
            channels: 4
        };
    },

    inner_glow: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [255, 255, 0];

        const result = wasm.inner_glow_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            params.radius ?? 10.0,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 0.75,
            params.choke ?? 0.0
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    },

    bevel_emboss: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const highlightColor = params.highlight_color || [255, 255, 255];
        const shadowColor = params.shadow_color || [0, 0, 0];

        const result = wasm.bevel_emboss_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            params.depth ?? 3.0,
            params.angle ?? 120.0,
            params.altitude ?? 30.0,
            highlightColor[0],
            highlightColor[1],
            highlightColor[2],
            params.highlight_opacity ?? 0.75,
            shadowColor[0],
            shadowColor[1],
            shadowColor[2],
            params.shadow_opacity ?? 0.75,
            params.style ?? 'inner_bevel'
        );

        // outer_bevel expands canvas
        const isOuter = params.style === 'outer_bevel';
        const expand = isOuter ? Math.ceil(params.depth ?? 3.0) + 2 : 0;
        const newWidth = width + expand * 2;
        const newHeight = height + expand * 2;

        return {
            data: new Uint8ClampedArray(result.buffer),
            width: newWidth,
            height: newHeight,
            channels: 4
        };
    },

    satin: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [0, 0, 0];

        const result = wasm.satin_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 0.5,
            params.angle ?? 19.0,
            params.distance ?? 11.0,
            params.size ?? 14.0,
            params.invert ?? false
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    },

    color_overlay: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [255, 0, 0];

        const result = wasm.color_overlay_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 1.0
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    },

    gradient_overlay: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const stops = params.stops || [0.0, 0, 0, 0, 1.0, 255, 255, 255];

        const result = wasm.gradient_overlay_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            new Float32Array(stops),
            params.style || 'linear',
            params.angle ?? 90.0,
            params.scale ?? 1.0,
            params.reverse ?? false,
            params.opacity ?? 1.0
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    },

    pattern_overlay: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const pattern = params.pattern || createDefaultPattern();
        const patternWidth = params.patternWidth || 2;
        const patternHeight = params.patternHeight || 2;

        const result = wasm.pattern_overlay_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            new Uint8Array(pattern),
            patternWidth,
            patternHeight,
            params.scale ?? 1.0,
            params.offset_x ?? 0,
            params.offset_y ?? 0,
            params.opacity ?? 1.0
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    },

    stroke: (imageData, params = {}) => {
        const { data, width, height } = imageData;
        const color = params.color || [0, 0, 0];

        const result = wasm.stroke_rgba_wasm(
            new Uint8Array(data.buffer),
            width,
            height,
            params.width ?? 2.0,
            color[0],
            color[1],
            color[2],
            params.opacity ?? 1.0,
            params.position ?? 'outside'
        );

        // outside/center stroke expands canvas
        const isInside = params.position === 'inside';
        const expand = isInside ? 0 : Math.ceil(params.width ?? 2.0) + 2;
        const newWidth = width + expand * 2;
        const newHeight = height + expand * 2;

        return {
            data: new Uint8ClampedArray(result.buffer),
            width: newWidth,
            height: newHeight,
            channels: 4
        };
    },
};

// f32 layer effect implementations (convert u8->process->f32->12bit)
export const LAYER_EFFECT_IMPLEMENTATIONS_F32 = {};

// Generate f32 versions for all effects
for (const [name, fn] of Object.entries(LAYER_EFFECT_IMPLEMENTATIONS)) {
    LAYER_EFFECT_IMPLEMENTATIONS_F32[`${name}_f32`] = (imageData, params = {}) => {
        const result = fn(imageData, params);
        const f32Result = convertU8ToF32(result);
        return convertF32To12bit(f32Result);
    };
}

/**
 * Register all layer effects with the parity test runner.
 */
export function registerAllEffects(runner) {
    const results = {};

    for (const entry of LAYER_EFFECT_CATALOG) {
        const { name, params, inputs } = entry;

        // Register u8 effect
        if (LAYER_EFFECT_IMPLEMENTATIONS[name]) {
            const effectFn = (imageData) => LAYER_EFFECT_IMPLEMENTATIONS[name](imageData, params);
            runner.registerEffect(name, effectFn);

            const testCases = inputs.map(inputName => ({
                id: inputName,
                description: `${name} effect - ${inputName}`,
                width: TEST_WIDTH,
                height: TEST_HEIGHT,
                inputGenerator: inputName,
                bitDepth: 'u8',
                params,
            }));
            runner.registerEffectTests(name, testCases);
            results[name] = true;
        } else {
            results[name] = false;
        }

        // Register f32 effect
        const f32Name = `${name}_f32`;
        if (LAYER_EFFECT_IMPLEMENTATIONS_F32[f32Name]) {
            const effectFn = (imageData) => LAYER_EFFECT_IMPLEMENTATIONS_F32[f32Name](imageData, params);
            runner.registerEffect(f32Name, effectFn);

            const testCases = inputs.map(inputName => ({
                id: `${inputName}_f32`,
                description: `${name} effect - ${inputName} (f32)`,
                width: TEST_WIDTH,
                height: TEST_HEIGHT,
                inputGenerator: inputName,
                bitDepth: 'f32',
                params,
            }));
            runner.registerEffectTests(f32Name, testCases);
            results[f32Name] = true;
        }
    }

    return results;
}

/**
 * Get catalog summary.
 */
export function getCatalogSummary() {
    const lines = [
        '# Cross-Platform Layer Effect Catalog (JavaScript)',
        '',
        `Total effects with WASM: ${LAYER_EFFECT_CATALOG.length}`,
        '',
        '| Effect | Parameters |',
        '|--------|-----------|',
    ];

    for (const entry of LAYER_EFFECT_CATALOG) {
        const paramStr = Object.entries(entry.params)
            .filter(([k]) => k !== 'stops' && k !== 'pattern')
            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
            .join(', ') || '(none)';
        lines.push(`| ${entry.name} | ${paramStr} |`);
    }

    return lines.join('\n');
}
