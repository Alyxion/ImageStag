/**
 * Core utilities for JavaScript layer effect wrappers.
 *
 * This module provides shared utilities used by all layer effect JS wrappers:
 * - WASM initialization
 * - Common layer effect wrapper factories
 * - Alpha extraction and compositing helpers
 */

import { initSync } from '../wasm/imagestag_rust.js';
import * as wasm from '../wasm/imagestag_rust.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

let wasmInitialized = false;

/**
 * Initialize WASM module (required before using layer effect functions).
 * Safe to call multiple times - will only initialize once.
 */
export async function initWasm() {
    if (wasmInitialized) return;
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const wasmPath = path.join(__dirname, '..', 'wasm', 'imagestag_rust_bg.wasm');
    const wasmBuffer = fs.readFileSync(wasmPath);
    initSync(wasmBuffer);
    wasmInitialized = true;
}

/**
 * Create a standard layer effect function (u8 only, returns expanded canvas).
 * Layer effects work with alpha channel and may expand the canvas.
 * @param {Function} wasmFn - The WASM function to call
 * @param {Function} paramExtractor - Function to extract params from options object
 * @returns {Function} - Layer effect function
 */
export function createLayerEffect(wasmFn, paramExtractor = () => []) {
    return (imageData, options = {}) => {
        const { data, width, height } = imageData;
        const channels = imageData.channels || 4;

        if (channels !== 4) {
            throw new Error('Layer effects require RGBA images (4 channels)');
        }

        const params = paramExtractor(options);

        const result = wasmFn(
            new Uint8Array(data.buffer),
            width,
            height,
            ...params
        );

        // Layer effects may return expanded canvas
        // The result includes the new dimensions embedded or we compute from length
        const resultLength = result.length;
        const totalPixels = resultLength / 4;

        // Try to determine new dimensions
        // For now, assume square-ish expansion and return with estimated dimensions
        // The WASM function should ideally return the dimensions too
        const newWidth = Math.ceil(Math.sqrt(totalPixels * width / height));
        const newHeight = Math.ceil(totalPixels / newWidth);

        return {
            data: new Uint8ClampedArray(result.buffer),
            width: newWidth,
            height: newHeight,
            channels: 4
        };
    };
}

/**
 * Create a layer effect that returns same-size output.
 * For effects like color overlay that don't expand canvas.
 * @param {Function} wasmFn - The WASM function to call
 * @param {Function} paramExtractor - Function to extract params from options object
 * @returns {Function} - Layer effect function
 */
export function createInPlaceEffect(wasmFn, paramExtractor = () => []) {
    return (imageData, options = {}) => {
        const { data, width, height } = imageData;
        const channels = imageData.channels || 4;

        if (channels !== 4) {
            throw new Error('Layer effects require RGBA images (4 channels)');
        }

        const params = paramExtractor(options);

        const result = wasmFn(
            new Uint8Array(data.buffer),
            width,
            height,
            ...params
        );

        return {
            data: new Uint8ClampedArray(result.buffer),
            width,
            height,
            channels: 4
        };
    };
}

// Re-export wasm for direct access when needed
export { wasm };

export default {
    initWasm,
    createLayerEffect,
    createInPlaceEffect,
    wasm
};
