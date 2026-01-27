/**
 * Blur filters - JavaScript WASM wrapper.
 *
 * Co-located with:
 * - blur.rs (Rust implementation)
 * - blur.py (Python wrapper)
 *
 * Provides: gaussian_blur, box_blur
 *
 * Note: Blur filters use PyO3 bindings (numpy arrays) which don't directly
 * translate to WASM. This module provides JavaScript implementations that
 * match the Rust behavior for basic blur operations.
 */

import { initWasm, wasm } from './core.js';

export { initWasm };

// ============================================================================
// Gaussian Blur (pure JS implementation)
// ============================================================================

/**
 * Generate 1D Gaussian kernel.
 * @param {number} sigma - Standard deviation
 * @returns {Float32Array} - Normalized kernel
 */
function gaussianKernel1D(sigma) {
    const radius = Math.ceil(sigma * 3);
    const size = radius * 2 + 1;
    const kernel = new Float32Array(size);
    let sum = 0;

    for (let i = 0; i < size; i++) {
        const x = i - radius;
        kernel[i] = Math.exp(-(x * x) / (2 * sigma * sigma));
        sum += kernel[i];
    }

    // Normalize
    for (let i = 0; i < size; i++) {
        kernel[i] /= sum;
    }

    return kernel;
}

/**
 * Apply Gaussian blur to image (u8).
 * Uses separable 2-pass convolution with premultiplied alpha.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {sigma: number}
 * @returns {Object} - Blurred image data
 */
export function gaussian_blur(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;
    const sigma = options.sigma ?? 1.0;

    if (sigma <= 0) {
        return { data: new Uint8ClampedArray(data), width, height, channels };
    }

    const kernel = gaussianKernel1D(sigma);
    const half = Math.floor(kernel.length / 2);
    const hasAlpha = channels === 4;

    // Temporary buffer for horizontal pass
    const temp = new Float32Array(width * height * channels);
    const result = new Uint8ClampedArray(width * height * channels);

    // Horizontal pass
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (hasAlpha) {
                let sumR = 0, sumG = 0, sumB = 0, sumA = 0;
                for (let ki = 0; ki < kernel.length; ki++) {
                    const sx = Math.max(0, Math.min(width - 1, x + ki - half));
                    const idx = (y * width + sx) * channels;
                    const a = data[idx + 3] / 255;
                    const kv = kernel[ki];
                    sumA += a * kv;
                    sumR += data[idx] * a * kv;
                    sumG += data[idx + 1] * a * kv;
                    sumB += data[idx + 2] * a * kv;
                }
                const outIdx = (y * width + x) * channels;
                temp[outIdx] = sumR;
                temp[outIdx + 1] = sumG;
                temp[outIdx + 2] = sumB;
                temp[outIdx + 3] = sumA;
            } else {
                for (let c = 0; c < channels; c++) {
                    let sum = 0;
                    for (let ki = 0; ki < kernel.length; ki++) {
                        const sx = Math.max(0, Math.min(width - 1, x + ki - half));
                        sum += data[(y * width + sx) * channels + c] * kernel[ki];
                    }
                    temp[(y * width + x) * channels + c] = sum;
                }
            }
        }
    }

    // Vertical pass
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (hasAlpha) {
                let sumR = 0, sumG = 0, sumB = 0, sumA = 0;
                for (let ki = 0; ki < kernel.length; ki++) {
                    const sy = Math.max(0, Math.min(height - 1, y + ki - half));
                    const idx = (sy * width + x) * channels;
                    const kv = kernel[ki];
                    sumA += temp[idx + 3] * kv;
                    sumR += temp[idx] * kv;
                    sumG += temp[idx + 1] * kv;
                    sumB += temp[idx + 2] * kv;
                }
                const outIdx = (y * width + x) * channels;
                const finalAlpha = Math.max(0, Math.min(1, sumA));
                result[outIdx + 3] = Math.round(finalAlpha * 255);
                if (finalAlpha > 0.001) {
                    result[outIdx] = Math.max(0, Math.min(255, Math.round(sumR / finalAlpha)));
                    result[outIdx + 1] = Math.max(0, Math.min(255, Math.round(sumG / finalAlpha)));
                    result[outIdx + 2] = Math.max(0, Math.min(255, Math.round(sumB / finalAlpha)));
                }
            } else {
                for (let c = 0; c < channels; c++) {
                    let sum = 0;
                    for (let ki = 0; ki < kernel.length; ki++) {
                        const sy = Math.max(0, Math.min(height - 1, y + ki - half));
                        sum += temp[(sy * width + x) * channels + c] * kernel[ki];
                    }
                    result[(y * width + x) * channels + c] = Math.max(0, Math.min(255, Math.round(sum)));
                }
            }
        }
    }

    return { data: result, width, height, channels };
}

// ============================================================================
// Box Blur (pure JS implementation)
// ============================================================================

/**
 * Apply box blur to image (u8).
 * Faster than Gaussian but blockier result.
 * @param {Object} imageData - {data: Uint8ClampedArray, width, height, channels}
 * @param {Object} options - {radius: number}
 * @returns {Object} - Blurred image data
 */
export function box_blur(imageData, options = {}) {
    const { data, width, height } = imageData;
    const channels = imageData.channels || 4;
    const radius = options.radius ?? 1;

    if (radius === 0) {
        return { data: new Uint8ClampedArray(data), width, height, channels };
    }

    const result = new Uint8ClampedArray(width * height * channels);
    const hasAlpha = channels === 4;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (hasAlpha) {
                let sumR = 0, sumG = 0, sumB = 0, sumA = 0;
                let count = 0;

                for (let dy = -radius; dy <= radius; dy++) {
                    const sy = y + dy;
                    if (sy < 0 || sy >= height) continue;
                    for (let dx = -radius; dx <= radius; dx++) {
                        const sx = x + dx;
                        if (sx < 0 || sx >= width) continue;
                        const idx = (sy * width + sx) * channels;
                        const a = data[idx + 3] / 255;
                        sumA += a;
                        sumR += data[idx] * a;
                        sumG += data[idx + 1] * a;
                        sumB += data[idx + 2] * a;
                        count++;
                    }
                }

                const outIdx = (y * width + x) * channels;
                const finalAlpha = Math.max(0, Math.min(1, sumA / count));
                result[outIdx + 3] = Math.round(finalAlpha * 255);
                if (finalAlpha > 0.001) {
                    const avgR = sumR / count;
                    const avgG = sumG / count;
                    const avgB = sumB / count;
                    result[outIdx] = Math.max(0, Math.min(255, Math.round(avgR / finalAlpha)));
                    result[outIdx + 1] = Math.max(0, Math.min(255, Math.round(avgG / finalAlpha)));
                    result[outIdx + 2] = Math.max(0, Math.min(255, Math.round(avgB / finalAlpha)));
                }
            } else {
                for (let c = 0; c < channels; c++) {
                    let sum = 0;
                    let count = 0;
                    for (let dy = -radius; dy <= radius; dy++) {
                        const sy = y + dy;
                        if (sy < 0 || sy >= height) continue;
                        for (let dx = -radius; dx <= radius; dx++) {
                            const sx = x + dx;
                            if (sx < 0 || sx >= width) continue;
                            sum += data[(sy * width + sx) * channels + c];
                            count++;
                        }
                    }
                    result[(y * width + x) * channels + c] = Math.round(sum / count);
                }
            }
        }
    }

    return { data: result, width, height, channels };
}

export default {
    initWasm,
    gaussian_blur,
    box_blur
};
