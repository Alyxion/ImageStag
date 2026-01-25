/**
 * ImageStag Grayscale Filter (Rust/WASM)
 *
 * Converts RGBA images to grayscale using ITU-R BT.709 luminosity coefficients.
 * Uses the same Rust implementation as the Python version for exact parity.
 *
 * Usage (Node.js):
 *   import { grayscale } from './grayscale.js';
 *   const result = grayscale(imageData);
 *
 * Usage (Browser):
 *   import { grayscale } from '/imgstag/static/filters/js/grayscale.js';
 *   const result = grayscale(imageData);
 */

// Import the WASM module (Node.js)
import { grayscale_rgba_wasm } from './wasm/imagestag_rust.js';

/**
 * Convert ImageData to grayscale using Rust/WASM.
 *
 * Uses ITU-R BT.709 luminosity coefficients:
 * Y = 0.2126*R + 0.7152*G + 0.0722*B
 *
 * This is the ONLY implementation - no fallback.
 * Both Python and JavaScript use identical Rust code.
 *
 * @param {Object} imageData - Input image with {data: Uint8ClampedArray, width, height}
 * @returns {Object} - Grayscale RGBA image with same structure
 */
export function grayscale(imageData) {
    const { data, width, height } = imageData;

    // Call Rust/WASM implementation
    const result = grayscale_rgba_wasm(
        new Uint8Array(data.buffer),
        width,
        height
    );

    // Return in ImageData-compatible format
    return {
        data: new Uint8ClampedArray(result.buffer),
        width,
        height
    };
}
