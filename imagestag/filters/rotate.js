/**
 * Rotation and mirroring filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - rotate.rs (Rust implementation)
 * - rotate.py (Python wrapper)
 *
 * Provides exact 90-degree rotation and mirroring operations for images.
 *
 * ## Rotation Direction
 *
 * All rotations are clockwise (CW):
 * - 90° CW: (x, y) -> (H - 1 - y, x)
 * - 180°: (x, y) -> (W - 1 - x, H - 1 - y)
 * - 270° CW (90° CCW): (x, y) -> (y, W - 1 - x)
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

// ============================================================================
// 8-bit (u8) Functions
// ============================================================================

/**
 * Rotate image 90 degrees clockwise (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Rotated image data with swapped dimensions {data, width: oldHeight, height: oldWidth, channels}
 */
export function rotate90CW(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.rotate_90_cw_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        channels
    );

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: height,  // Dimensions are swapped
        height: width,
        channels
    };
}

/**
 * Rotate image 180 degrees (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Rotated image data with same dimensions
 */
export function rotate180(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.rotate_180_wasm(
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
 * Rotate image 270 degrees clockwise (90 counter-clockwise) (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Rotated image data with swapped dimensions
 */
export function rotate270CW(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.rotate_270_cw_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        channels
    );

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: height,  // Dimensions are swapped
        height: width,
        channels
    };
}

/**
 * Rotate image by specified degrees (90, 180, or 270) (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {number} degrees - Rotation angle (must be 90, 180, or 270)
 * @returns {Object} - Rotated image data. For 90/270, dimensions are swapped.
 */
export function rotate(imageData, degrees) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (degrees !== 90 && degrees !== 180 && degrees !== 270) {
        throw new Error(`Degrees must be 90, 180, or 270, got ${degrees}`);
    }

    const result = wasm.rotate_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        channels,
        degrees
    );

    // Determine new dimensions
    const newWidth = (degrees === 90 || degrees === 270) ? height : width;
    const newHeight = (degrees === 90 || degrees === 270) ? width : height;

    return {
        data: new Uint8ClampedArray(result.buffer),
        width: newWidth,
        height: newHeight,
        channels
    };
}

/**
 * Flip image horizontally (mirror left-right) (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Flipped image data with same dimensions
 */
export function flipHorizontal(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.flip_horizontal_wasm(
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
 * Flip image vertically (mirror top-bottom) (u8).
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @returns {Object} - Flipped image data with same dimensions
 */
export function flipVertical(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.flip_vertical_wasm(
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

// ============================================================================
// Float (f32) Functions
// ============================================================================

/**
 * Rotate image 90 degrees clockwise (f32).
 * @param {Object} imageData - {data: Float32Array, width, height, channels}
 * @returns {Object} - Rotated image data with swapped dimensions
 */
export function rotate90CWF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.rotate_90_cw_f32_wasm(
        data,
        width,
        height,
        channels
    );

    return {
        data: new Float32Array(result.buffer),
        width: height,
        height: width,
        channels
    };
}

/**
 * Rotate image 180 degrees (f32).
 * @param {Object} imageData - {data: Float32Array, width, height, channels}
 * @returns {Object} - Rotated image data with same dimensions
 */
export function rotate180F32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.rotate_180_f32_wasm(
        data,
        width,
        height,
        channels
    );

    return {
        data: new Float32Array(result.buffer),
        width,
        height,
        channels
    };
}

/**
 * Rotate image 270 degrees clockwise (90 counter-clockwise) (f32).
 * @param {Object} imageData - {data: Float32Array, width, height, channels}
 * @returns {Object} - Rotated image data with swapped dimensions
 */
export function rotate270CWF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.rotate_270_cw_f32_wasm(
        data,
        width,
        height,
        channels
    );

    return {
        data: new Float32Array(result.buffer),
        width: height,
        height: width,
        channels
    };
}

/**
 * Rotate image by specified degrees (90, 180, or 270) (f32).
 * @param {Object} imageData - {data: Float32Array, width, height, channels}
 * @param {number} degrees - Rotation angle (must be 90, 180, or 270)
 * @returns {Object} - Rotated image data. For 90/270, dimensions are swapped.
 */
export function rotateF32(imageData, degrees) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    if (degrees !== 90 && degrees !== 180 && degrees !== 270) {
        throw new Error(`Degrees must be 90, 180, or 270, got ${degrees}`);
    }

    const result = wasm.rotate_f32_wasm(
        data,
        width,
        height,
        channels,
        degrees
    );

    const newWidth = (degrees === 90 || degrees === 270) ? height : width;
    const newHeight = (degrees === 90 || degrees === 270) ? width : height;

    return {
        data: new Float32Array(result.buffer),
        width: newWidth,
        height: newHeight,
        channels
    };
}

/**
 * Flip image horizontally (mirror left-right) (f32).
 * @param {Object} imageData - {data: Float32Array, width, height, channels}
 * @returns {Object} - Flipped image data with same dimensions
 */
export function flipHorizontalF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.flip_horizontal_f32_wasm(
        data,
        width,
        height,
        channels
    );

    return {
        data: new Float32Array(result.buffer),
        width,
        height,
        channels
    };
}

/**
 * Flip image vertically (mirror top-bottom) (f32).
 * @param {Object} imageData - {data: Float32Array, width, height, channels}
 * @returns {Object} - Flipped image data with same dimensions
 */
export function flipVerticalF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = wasm.flip_vertical_f32_wasm(
        data,
        width,
        height,
        channels
    );

    return {
        data: new Float32Array(result.buffer),
        width,
        height,
        channels
    };
}
