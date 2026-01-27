/**
 * Grayscale filter - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - grayscale.rs (Rust implementation)
 * - grayscale.py (Python wrapper)
 */

import { initSync } from '../wasm/imagestag_rust.js';
import * as wasm from '../wasm/imagestag_rust.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

let wasmInitialized = false;

/**
 * Initialize WASM module (required before using filter functions).
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
 * Apply grayscale filter (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Grayscale image data
 */
export function grayscale(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.grayscale_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        channels
    );

    return {
        data: new Uint8ClampedArray(result.buffer),
        width,
        height,
        channels
    };
}

/**
 * Apply grayscale filter (f32).
 * Converts u8 input to f32, processes, returns 12-bit output.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Grayscale image data (12-bit in Uint16Array)
 */
export function grayscale_f32(imageData) {
    const { width, height } = imageData;
    const channels = imageData.channels || 4;

    // Convert u8 to f32
    const inputF32 = convertU8ToF32(imageData);

    const resultF32 = wasm.grayscale_rgba_f32_wasm(
        new Float32Array(inputF32.data.buffer),
        width,
        height,
        channels
    );

    const f32Image = {
        data: new Float32Array(resultF32.buffer),
        width,
        height,
        channels
    };

    // Convert to 12-bit for storage
    return convertF32To12bit(f32Image);
}

export default { grayscale, grayscale_f32, initWasm, convertU8ToF32, convertF32To12bit };
