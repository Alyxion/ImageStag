/**
 * Document and Application Limits
 *
 * Central configuration for all size/memory limits in the application.
 * All document creation, resizing, and import operations should reference these.
 */

// === Dimension Limits ===

/** Maximum width or height of a document in pixels */
export const MAX_DIMENSION = 8000;

/** Suggested maximum width when scaling down oversized images (UHD) */
export const SUGGESTED_MAX_WIDTH = 3840;

/** Minimum dimension */
export const MIN_DIMENSION = 1;

// === Memory Limits ===

/** Bytes per pixel (RGBA) */
export const BYTES_PER_PIXEL = 4;

/**
 * Maximum memory per document in bytes (512 MB)
 * This is the total memory for all layers in a single document.
 * 512 MB = ~128 million pixels = ~11,300 x 11,300 at 1 layer
 * With 5 layers, that's ~5,000 x 5,000 per layer
 */
export const MAX_DOCUMENT_MEMORY = 512 * 1024 * 1024;

/**
 * Maximum memory for all documents combined in bytes (2 GB)
 * This is a soft limit to prevent browser crashes.
 */
export const MAX_APP_MEMORY = 2 * 1024 * 1024 * 1024;

/**
 * Warning threshold - show warning when approaching limit (80%)
 */
export const MEMORY_WARNING_THRESHOLD = 0.8;

// === Derived Limits ===

/** Maximum pixels in a single layer (based on document memory / typical layer count) */
export const MAX_LAYER_PIXELS = Math.floor(MAX_DOCUMENT_MEMORY / BYTES_PER_PIXEL / 4); // Assume ~4 layers

/** Maximum pixels in a single document (all layers combined) */
export const MAX_DOCUMENT_PIXELS = Math.floor(MAX_DOCUMENT_MEMORY / BYTES_PER_PIXEL);

// === Utility Functions ===

/**
 * Calculate memory usage for given dimensions.
 * @param {number} width
 * @param {number} height
 * @returns {number} Memory in bytes
 */
export function calculateMemory(width, height) {
    return width * height * BYTES_PER_PIXEL;
}

/**
 * Calculate memory for a document with multiple layers.
 * @param {number} width
 * @param {number} height
 * @param {number} layerCount
 * @returns {number} Memory in bytes
 */
export function calculateDocumentMemory(width, height, layerCount = 1) {
    return width * height * BYTES_PER_PIXEL * layerCount;
}

/**
 * Format bytes as human-readable string.
 * @param {number} bytes
 * @returns {string}
 */
export function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/**
 * Check if dimensions are within limits.
 * @param {number} width
 * @param {number} height
 * @returns {{valid: boolean, reason?: string, suggestedWidth?: number, suggestedHeight?: number}}
 */
export function checkDimensionLimits(width, height) {
    // Check individual dimension limits
    if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
        const scale = Math.min(MAX_DIMENSION / width, MAX_DIMENSION / height);
        return {
            valid: false,
            reason: `Dimensions exceed maximum of ${MAX_DIMENSION}px`,
            suggestedWidth: Math.floor(width * scale),
            suggestedHeight: Math.floor(height * scale)
        };
    }

    // Check memory limit for single layer
    const memory = calculateMemory(width, height);
    if (memory > MAX_DOCUMENT_MEMORY) {
        const scale = Math.sqrt(MAX_DOCUMENT_MEMORY / memory);
        return {
            valid: false,
            reason: `Image would use ${formatBytes(memory)} (max ${formatBytes(MAX_DOCUMENT_MEMORY)})`,
            suggestedWidth: Math.floor(width * scale),
            suggestedHeight: Math.floor(height * scale)
        };
    }

    return { valid: true };
}

/**
 * Check if adding a layer of given size would exceed document memory.
 * @param {number} currentMemory - Current document memory usage
 * @param {number} layerWidth
 * @param {number} layerHeight
 * @returns {{valid: boolean, reason?: string}}
 */
export function checkLayerMemory(currentMemory, layerWidth, layerHeight) {
    const layerMemory = calculateMemory(layerWidth, layerHeight);
    const totalMemory = currentMemory + layerMemory;

    if (totalMemory > MAX_DOCUMENT_MEMORY) {
        return {
            valid: false,
            reason: `Adding this layer would use ${formatBytes(totalMemory)} (max ${formatBytes(MAX_DOCUMENT_MEMORY)})`
        };
    }

    return { valid: true };
}

/**
 * Calculate suggested dimensions that fit within limits while maintaining aspect ratio.
 * Prefers scaling to UHD width when possible.
 * @param {number} width
 * @param {number} height
 * @returns {{width: number, height: number, scaled: boolean}}
 */
export function getSuggestedDimensions(width, height) {
    const check = checkDimensionLimits(width, height);

    if (check.valid) {
        return { width, height, scaled: false };
    }

    // First try scaling to UHD width
    if (width > SUGGESTED_MAX_WIDTH) {
        const scale = SUGGESTED_MAX_WIDTH / width;
        const newWidth = SUGGESTED_MAX_WIDTH;
        const newHeight = Math.floor(height * scale);

        // Verify this fits within limits
        const recheck = checkDimensionLimits(newWidth, newHeight);
        if (recheck.valid) {
            return { width: newWidth, height: newHeight, scaled: true };
        }
    }

    // Fall back to the calculated suggestions
    return {
        width: check.suggestedWidth,
        height: check.suggestedHeight,
        scaled: true
    };
}

/**
 * Clamp a dimension value to valid range.
 * @param {number} value
 * @returns {number}
 */
export function clampDimension(value) {
    return Math.min(MAX_DIMENSION, Math.max(MIN_DIMENSION, Math.round(value) || MIN_DIMENSION));
}
