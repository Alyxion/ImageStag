/**
 * Core utilities for JavaScript filter wrappers.
 *
 * Co-located with:
 * - core.rs (Rust implementation)
 * - No Python equivalent (utilities are internal)
 *
 * This module provides shared utilities used by all filter JS wrappers:
 * - WASM initialization
 * - u8/f32 conversion helpers
 * - Common filter wrapper factories
 */

import { initSync } from '../wasm/imagestag_rust.js';
import * as wasm from '../wasm/imagestag_rust.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

let wasmInitialized = false;

/**
 * Initialize WASM module (required before using filter functions).
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
 * Convert u8 image data to f32.
 * @param {Object} imageData - {data, width, height, channels}
 * @returns {Object} - f32 image data
 */
export function convertU8ToF32(imageData) {
    const { data, width, height, channels } = imageData;
    const length = width * height * channels;
    const f32Data = new Float32Array(length);
    for (let i = 0; i < length; i++) {
        f32Data[i] = data[i] / 255.0;
    }
    return { data: f32Data, width, height, channels };
}

/**
 * Convert f32 image data to 12-bit (stored in Uint16Array).
 * @param {Object} imageData - {data, width, height, channels}
 * @returns {Object} - 12-bit image data
 */
export function convertF32To12bit(imageData) {
    const { data, width, height, channels } = imageData;
    const length = width * height * channels;
    const u16Data = new Uint16Array(length);
    for (let i = 0; i < length; i++) {
        u16Data[i] = Math.round(Math.max(0, Math.min(1, data[i])) * 4095);
    }
    return { data: u16Data, width, height, channels };
}

/**
 * Convert f32 image data to u8.
 * @param {Object} imageData - {data, width, height, channels}
 * @returns {Object} - u8 image data
 */
export function convertF32ToU8(imageData) {
    const { data, width, height, channels } = imageData;
    const length = width * height * channels;
    const u8Data = new Uint8ClampedArray(length);
    for (let i = 0; i < length; i++) {
        u8Data[i] = Math.round(Math.max(0, Math.min(1, data[i])) * 255);
    }
    return { data: u8Data, width, height, channels };
}

/**
 * Create a standard u8 filter function.
 * @param {Function} wasmFn - The WASM function to call
 * @param {Function} paramExtractor - Function to extract params from options object
 * @returns {Function} - Filter function
 */
export function createU8Filter(wasmFn, paramExtractor = () => []) {
    return (imageData, options = {}) => {
        const { data, width, height } = imageData;
        const channels = imageData.channels || 4;
        const params = paramExtractor(options);

        const result = wasmFn(
            new Uint8Array(data.buffer),
            width,
            height,
            channels,
            ...params
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
 * Create a standard f32 filter function.
 * Converts u8 input to f32, processes, returns 12-bit output.
 * @param {Function} wasmFn - The WASM function to call
 * @param {Function} paramExtractor - Function to extract params from options object
 * @returns {Function} - Filter function
 */
export function createF32Filter(wasmFn, paramExtractor = () => []) {
    return (imageData, options = {}) => {
        const { width, height } = imageData;
        const channels = imageData.channels || 4;
        const params = paramExtractor(options);

        // Convert u8 to f32
        const inputF32 = convertU8ToF32(imageData);

        const resultF32 = wasmFn(
            new Float32Array(inputF32.data.buffer),
            width,
            height,
            channels,
            ...params
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

// Re-export wasm for direct access when needed
export { wasm };

export default {
    initWasm,
    convertU8ToF32,
    convertF32To12bit,
    convertF32ToU8,
    createU8Filter,
    createF32Filter,
    wasm
};
