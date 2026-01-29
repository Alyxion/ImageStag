/**
 * ImageStag Selection Algorithms - WASM-accelerated selection tools.
 *
 * Provides cross-platform selection algorithms:
 * - extract_contours: Marching squares for outline generation from alpha masks
 * - magic_wand: Flood fill based color selection
 *
 * Usage:
 *   import { initSelection, extractContours, magicWandSelect } from '/static/js/selection/index.js';
 *
 *   await initSelection();
 *   const contours = extractContours(mask, width, height);
 *   const mask = magicWandSelect(imageData, x, y, { tolerance: 32 });
 */

import init, * as wasm from '/imgstag/wasm/imagestag_rust.js';

let _initialized = false;
let _initializing = null;

/**
 * Initialize the WASM module. Must be called before using any selection function.
 * Safe to call multiple times.
 */
export async function initSelection() {
    if (_initialized) return;
    if (_initializing) return _initializing;

    _initializing = (async () => {
        try {
            await init();
            _initialized = true;
            console.log('[SelectionWASM] Initialized');
        } catch (e) {
            console.error('[SelectionWASM] Failed to initialize:', e);
            throw e;
        } finally {
            _initializing = null;
        }
    })();

    return _initializing;
}

/**
 * Check if WASM selection is initialized.
 * @returns {boolean}
 */
export function isInitialized() {
    return _initialized;
}

/**
 * Extract contours from an alpha mask using Marching Squares algorithm.
 *
 * @param {Uint8Array} mask - Alpha mask (0 = unselected, >0 = selected)
 * @param {number} width - Mask width
 * @param {number} height - Mask height
 * @returns {Array<Array<[number, number]>>} Array of contour polygons
 */
export function extractContours(mask, width, height) {
    if (!_initialized) {
        throw new Error('SelectionWASM not initialized. Call initSelection() first.');
    }

    // Ensure mask is Uint8Array
    const maskArray = mask instanceof Uint8Array ? mask :
        new Uint8Array(mask);

    // Call WASM function
    const flatResult = wasm.extract_contours_wasm(maskArray, width, height);

    // Parse flat result: [num_contours, len1, x1, y1, x2, y2, ..., len2, ...]
    if (!flatResult || flatResult.length === 0) return [];

    const numContours = Math.floor(flatResult[0]);
    if (numContours <= 0) return [];

    const contours = [];
    let idx = 1;

    for (let i = 0; i < numContours; i++) {
        if (idx >= flatResult.length) break;

        const pointCount = Math.floor(flatResult[idx]);
        idx++;

        if (pointCount <= 0) continue;

        const contour = [];
        for (let j = 0; j < pointCount; j++) {
            if (idx + 1 > flatResult.length) break;
            contour.push([flatResult[idx], flatResult[idx + 1]]);
            idx += 2;
        }

        if (contour.length >= 3) {
            contours.push(contour);
        }
    }

    return contours;
}

/**
 * Magic wand selection using flood fill algorithm.
 *
 * @param {Uint8Array|Uint8ClampedArray} imageData - RGBA image data (4 bytes per pixel)
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @param {number} startX - Starting X coordinate
 * @param {number} startY - Starting Y coordinate
 * @param {Object} [options] - Selection options
 * @param {number} [options.tolerance=32] - Color tolerance (0-255)
 * @param {boolean} [options.contiguous=true] - Only select connected pixels
 * @returns {Uint8Array} Selection mask (255 = selected, 0 = not selected)
 */
export function magicWandSelect(imageData, width, height, startX, startY, options = {}) {
    if (!_initialized) {
        throw new Error('SelectionWASM not initialized. Call initSelection() first.');
    }

    const { tolerance = 32, contiguous = true } = options;

    // Convert Uint8ClampedArray to Uint8Array if needed
    const u8 = imageData instanceof Uint8Array ? imageData :
        new Uint8Array(imageData.buffer, imageData.byteOffset, imageData.byteLength);

    // Call WASM function
    const mask = wasm.magic_wand_select_wasm(u8, width, height, startX, startY, tolerance, contiguous);

    return new Uint8Array(mask);
}

export default { initSelection, isInitialized, extractContours, magicWandSelect };
