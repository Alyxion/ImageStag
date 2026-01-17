/**
 * BackendConnector - Handles communication with the Python backend.
 */
import { createFilterPayload, bytesToImageData, parseImageResponse } from '../utils/ImageData.js';

export class BackendConnector {
    /**
     * @param {Object} options
     * @param {string} [options.baseUrl=''] - Base URL for API calls
     * @param {number} [options.timeout=30000] - Request timeout in ms
     */
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '';
        this.timeout = options.timeout || 30000;
        this.connected = false;
        this.availableFilters = [];
        this.availableImageSources = [];
    }

    /**
     * Check if backend is available.
     * @returns {Promise<boolean>}
     */
    async checkConnection() {
        try {
            const response = await fetch(`${this.baseUrl}/api/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            this.connected = response.ok;
            return this.connected;
        } catch (error) {
            this.connected = false;
            return false;
        }
    }

    /**
     * Discover available filters from backend.
     * @returns {Promise<Array>}
     */
    async discoverFilters() {
        if (!this.connected) return [];

        try {
            const response = await fetch(`${this.baseUrl}/api/filters`);
            const data = await response.json();
            this.availableFilters = data.filters || [];
            return this.availableFilters;
        } catch (error) {
            console.warn('Failed to discover filters:', error);
            return [];
        }
    }

    /**
     * Discover available image sources.
     * @returns {Promise<Array>}
     */
    async discoverImageSources() {
        if (!this.connected) return [];

        try {
            const response = await fetch(`${this.baseUrl}/api/images/sources`);
            const data = await response.json();
            this.availableImageSources = data.sources || [];
            return this.availableImageSources;
        } catch (error) {
            console.warn('Failed to discover image sources:', error);
            return [];
        }
    }

    /**
     * Apply a filter to ImageData.
     * @param {string} filterId - Filter ID
     * @param {ImageData} imageData - Input image data
     * @param {Object} params - Filter parameters
     * @returns {Promise<ImageData>}
     */
    async applyFilter(filterId, imageData, params = {}) {
        if (!this.connected) {
            throw new Error('Backend not connected');
        }

        const payload = createFilterPayload(imageData, params);

        const response = await fetch(`${this.baseUrl}/api/filters/${filterId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/octet-stream'
            },
            body: payload,
            signal: AbortSignal.timeout(this.timeout)
        });

        if (!response.ok) {
            let errorDetail = 'Filter failed';
            try {
                const error = await response.json();
                errorDetail = error.detail || errorDetail;
            } catch (e) {
                // Ignore JSON parse error
            }
            throw new Error(errorDetail);
        }

        // Parse response (raw RGBA bytes)
        const resultBytes = new Uint8Array(await response.arrayBuffer());
        return bytesToImageData(resultBytes, imageData.width, imageData.height);
    }

    /**
     * Load a sample image.
     * @param {string} sourceId - Source ID
     * @param {string} imageId - Image ID
     * @returns {Promise<{imageData: ImageData, metadata: Object}>}
     */
    async loadSampleImage(sourceId, imageId) {
        const response = await fetch(`${this.baseUrl}/api/images/${sourceId}/${imageId}`);

        if (!response.ok) {
            throw new Error('Failed to load image');
        }

        const buffer = await response.arrayBuffer();
        return parseImageResponse(buffer);
    }

    /**
     * Get filter info by ID.
     * @param {string} filterId
     * @returns {Object|undefined}
     */
    getFilterInfo(filterId) {
        return this.availableFilters.find(f => f.id === filterId);
    }

    /**
     * Get image source info by ID.
     * @param {string} sourceId
     * @returns {Object|undefined}
     */
    getSourceInfo(sourceId) {
        return this.availableImageSources.find(s => s.id === sourceId);
    }
}
