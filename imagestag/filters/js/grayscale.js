/**
 * ImageStag Grayscale Filter (Rust/WASM)
 *
 * Converts RGBA images to grayscale using ITU-R BT.709 luminosity coefficients.
 * Uses the same Rust implementation as the Python version for exact parity.
 *
 * ## Bit Depth Support
 *
 * - **u8 (8-bit)**: Values 0-255, standard for web/display
 * - **f32 (float)**: Values 0.0-1.0, for HDR/linear workflows
 *
 * Both versions use identical Rust code compiled to WASM.
 *
 * Usage (Node.js):
 *   import { grayscale, grayscaleF32 } from './grayscale.js';
 *   const result = grayscale(imageData);        // u8
 *   const resultF32 = grayscaleF32(imageDataF32); // f32
 *
 * Usage (Browser):
 *   import { grayscale } from '/imgstag/static/filters/js/grayscale.js';
 *   const result = grayscale(imageData);
 */

// Import the WASM module (Node.js)
import {
    grayscale_rgba_wasm,
    grayscale_rgba_f32_wasm,
    convert_u8_to_f32_wasm,
    convert_f32_to_u8_wasm,
    convert_f32_to_12bit_wasm,
    convert_12bit_to_f32_wasm,
} from './wasm/imagestag_rust.js';

// ============================================================================
// 8-bit (u8) Functions
// ============================================================================

/**
 * Convert ImageData to grayscale using Rust/WASM (8-bit).
 *
 * Uses ITU-R BT.709 luminosity coefficients:
 * Y = 0.2126*R + 0.7152*G + 0.0722*B
 *
 * This is the ONLY implementation - no fallback.
 * Both Python and JavaScript use identical Rust code.
 *
 * @param {Object} imageData - Input image with {data: Uint8ClampedArray, width, height, channels?}
 * @returns {Object} - Grayscale image with same structure
 */
export function grayscale(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    // Call Rust/WASM implementation
    const result = grayscale_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height,
        channels
    );

    // Return in ImageData-compatible format
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
 * Convert float ImageData to grayscale using Rust/WASM (float).
 *
 * Uses ITU-R BT.709 luminosity coefficients (same as u8 version).
 * Input/output values are 0.0-1.0.
 *
 * @param {Object} imageData - Input image with {data: Float32Array, width, height, channels?}
 * @returns {Object} - Grayscale image with Float32Array data
 */
export function grayscaleF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    // Call Rust/WASM implementation
    const result = grayscale_rgba_f32_wasm(
        new Float32Array(data.buffer),
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

// ============================================================================
// Conversion Utilities
// ============================================================================

/**
 * Convert u8 image (0-255) to f32 (0.0-1.0).
 *
 * @param {Object} imageData - Input image with Uint8ClampedArray data
 * @returns {Object} - Image with Float32Array data
 */
export function convertU8ToF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = convert_u8_to_f32_wasm(
        new Uint8Array(data.buffer),
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
 * Convert f32 image (0.0-1.0) to u8 (0-255).
 *
 * @param {Object} imageData - Input image with Float32Array data
 * @returns {Object} - Image with Uint8ClampedArray data
 */
export function convertF32ToU8(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = convert_f32_to_u8_wasm(
        new Float32Array(data.buffer),
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
 * Convert f32 image (0.0-1.0) to 12-bit (0-4095).
 *
 * @param {Object} imageData - Input image with Float32Array data
 * @returns {Object} - Image with Uint16Array data (values 0-4095)
 */
export function convertF32To12bit(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = convert_f32_to_12bit_wasm(
        new Float32Array(data.buffer),
        width,
        height,
        channels
    );

    return {
        data: new Uint16Array(result.buffer),
        width,
        height,
        channels
    };
}

/**
 * Convert 12-bit image (0-4095) to f32 (0.0-1.0).
 *
 * @param {Object} imageData - Input image with Uint16Array data
 * @returns {Object} - Image with Float32Array data
 */
export function convert12bitToF32(imageData) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;

    const result = convert_12bit_to_f32_wasm(
        new Uint16Array(data.buffer),
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
