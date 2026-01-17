/**
 * ImageData utilities for RGBA manipulation.
 */

/**
 * Convert ImageData to raw RGBA Uint8Array.
 * @param {ImageData} imageData
 * @returns {Uint8Array}
 */
export function imageDataToBytes(imageData) {
    return new Uint8Array(imageData.data.buffer.slice(0));
}

/**
 * Convert raw RGBA bytes to ImageData.
 * @param {Uint8Array} bytes
 * @param {number} width
 * @param {number} height
 * @returns {ImageData}
 */
export function bytesToImageData(bytes, width, height) {
    const imageData = new ImageData(width, height);
    imageData.data.set(bytes);
    return imageData;
}

/**
 * Create a payload for backend filter API.
 * @param {ImageData} imageData
 * @param {Object} params - Filter parameters
 * @returns {Uint8Array}
 */
export function createFilterPayload(imageData, params = {}) {
    const metadata = {
        width: imageData.width,
        height: imageData.height,
        params: params
    };
    const metadataJson = JSON.stringify(metadata);
    const metadataBytes = new TextEncoder().encode(metadataJson);
    const rawBytes = imageDataToBytes(imageData);

    // Create combined payload: [4 bytes length][metadata JSON][raw RGBA]
    const payload = new Uint8Array(4 + metadataBytes.length + rawBytes.length);
    const view = new DataView(payload.buffer);
    view.setUint32(0, metadataBytes.length, true); // little-endian
    payload.set(metadataBytes, 4);
    payload.set(rawBytes, 4 + metadataBytes.length);

    return payload;
}

/**
 * Parse backend image response.
 * @param {ArrayBuffer} buffer
 * @returns {{imageData: ImageData, metadata: Object}}
 */
export function parseImageResponse(buffer) {
    const view = new DataView(buffer);
    const metadataLength = view.getUint32(0, true);
    const metadataBytes = new Uint8Array(buffer, 4, metadataLength);
    const metadata = JSON.parse(new TextDecoder().decode(metadataBytes));
    const rgbaBytes = new Uint8Array(buffer, 4 + metadataLength);

    return {
        imageData: bytesToImageData(rgbaBytes, metadata.width, metadata.height),
        metadata: metadata
    };
}

/**
 * Get pixel color at coordinates.
 * @param {ImageData} imageData
 * @param {number} x
 * @param {number} y
 * @returns {{r: number, g: number, b: number, a: number}}
 */
export function getPixel(imageData, x, y) {
    const idx = (y * imageData.width + x) * 4;
    return {
        r: imageData.data[idx],
        g: imageData.data[idx + 1],
        b: imageData.data[idx + 2],
        a: imageData.data[idx + 3]
    };
}

/**
 * Set pixel color at coordinates.
 * @param {ImageData} imageData
 * @param {number} x
 * @param {number} y
 * @param {{r: number, g: number, b: number, a: number}} color
 */
export function setPixel(imageData, x, y, color) {
    const idx = (y * imageData.width + x) * 4;
    imageData.data[idx] = color.r;
    imageData.data[idx + 1] = color.g;
    imageData.data[idx + 2] = color.b;
    imageData.data[idx + 3] = color.a;
}
