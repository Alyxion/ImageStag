/**
 * PluginManager - Manages built-in and backend filters.
 */
import { BackendConnector } from './BackendConnector.js';

export class PluginManager {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.backendConnector = null;
        this.jsFilters = new Map();      // Built-in JS filters
        this.backendFilters = new Map(); // Python backend filters
        this.imageSources = new Map();   // Image sources
    }

    /**
     * Initialize the plugin system.
     */
    async initialize() {
        // Register built-in JS filters
        this.registerBuiltInFilters();

        // Connect to backend
        this.backendConnector = new BackendConnector({
            baseUrl: window.location.origin
        });

        const connected = await this.backendConnector.checkConnection();

        if (connected) {
            // Discover backend filters
            const filters = await this.backendConnector.discoverFilters();
            for (const filter of filters) {
                this.backendFilters.set(filter.id, filter);
            }

            // Discover image sources
            const sources = await this.backendConnector.discoverImageSources();
            for (const source of sources) {
                this.imageSources.set(source.id, source);
            }

            this.app.eventBus.emit('backend:connected', {
                filters: this.backendFilters,
                sources: this.imageSources
            });
        } else {
            this.app.eventBus.emit('backend:disconnected');
        }
    }

    /**
     * Register built-in JavaScript filters.
     */
    registerBuiltInFilters() {
        // Invert colors
        this.jsFilters.set('js:invert', {
            id: 'js:invert',
            name: 'Invert Colors',
            category: 'color',
            params: [],
            apply: (imageData) => {
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    data[i] = 255 - data[i];
                    data[i + 1] = 255 - data[i + 1];
                    data[i + 2] = 255 - data[i + 2];
                }
                return imageData;
            }
        });

        // Grayscale
        this.jsFilters.set('js:grayscale', {
            id: 'js:grayscale',
            name: 'Grayscale',
            category: 'color',
            params: [],
            apply: (imageData) => {
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const avg = (data[i] + data[i + 1] + data[i + 2]) / 3;
                    data[i] = data[i + 1] = data[i + 2] = avg;
                }
                return imageData;
            }
        });

        // Brightness
        this.jsFilters.set('js:brightness', {
            id: 'js:brightness',
            name: 'Brightness',
            category: 'adjust',
            params: [
                { id: 'value', name: 'Value', type: 'range', min: -100, max: 100, default: 0 }
            ],
            apply: (imageData, params) => {
                const data = imageData.data;
                const factor = (params.value || 0) / 100 * 255;
                for (let i = 0; i < data.length; i += 4) {
                    data[i] = Math.max(0, Math.min(255, data[i] + factor));
                    data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + factor));
                    data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + factor));
                }
                return imageData;
            }
        });

        // Contrast
        this.jsFilters.set('js:contrast', {
            id: 'js:contrast',
            name: 'Contrast',
            category: 'adjust',
            params: [
                { id: 'value', name: 'Value', type: 'range', min: -100, max: 100, default: 0 }
            ],
            apply: (imageData, params) => {
                const data = imageData.data;
                const contrast = params.value || 0;
                const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));
                for (let i = 0; i < data.length; i += 4) {
                    data[i] = Math.max(0, Math.min(255, factor * (data[i] - 128) + 128));
                    data[i + 1] = Math.max(0, Math.min(255, factor * (data[i + 1] - 128) + 128));
                    data[i + 2] = Math.max(0, Math.min(255, factor * (data[i + 2] - 128) + 128));
                }
                return imageData;
            }
        });
    }

    /**
     * Get all available filters (JS + backend).
     * @returns {Array}
     */
    getAllFilters() {
        const allFilters = [];

        // Add JS filters
        for (const [id, filter] of this.jsFilters) {
            allFilters.push({
                ...filter,
                source: 'javascript'
            });
        }

        // Add backend filters
        for (const [id, filter] of this.backendFilters) {
            allFilters.push({
                ...filter,
                source: 'python'
            });
        }

        return allFilters;
    }

    /**
     * Get all available image sources.
     * @returns {Array}
     */
    getImageSources() {
        return Array.from(this.imageSources.values());
    }

    /**
     * Apply a filter to a layer.
     * @param {string} filterId - Filter ID
     * @param {Layer} layer - Target layer
     * @param {Object} params - Filter parameters
     * @returns {Promise<ImageData>}
     */
    async applyFilter(filterId, layer, params = {}) {
        const imageData = layer.getImageData();
        let result;

        if (filterId.startsWith('js:')) {
            // JavaScript filter
            const filter = this.jsFilters.get(filterId);
            if (!filter) throw new Error(`Filter not found: ${filterId}`);
            result = filter.apply(imageData, params);
        } else {
            // Backend filter
            if (!this.backendConnector?.connected) {
                throw new Error('Backend not connected');
            }
            result = await this.backendConnector.applyFilter(filterId, imageData, params);
        }

        layer.setImageData(result);
        this.app.renderer.requestRender();

        return result;
    }

    /**
     * Load a sample image to a new layer.
     * @param {string} sourceId - Source ID
     * @param {string} imageId - Image ID
     * @returns {Promise<Layer>}
     */
    async loadSampleImage(sourceId, imageId) {
        if (!this.backendConnector?.connected) {
            throw new Error('Backend not connected');
        }

        const { imageData, metadata } = await this.backendConnector.loadSampleImage(sourceId, imageId);

        // Create new layer with image
        const layer = this.app.layerStack.addLayer({
            name: metadata.name || 'Image'
        });

        // If image dimensions differ from canvas, resize canvas or scale image
        if (imageData.width !== this.app.layerStack.width || imageData.height !== this.app.layerStack.height) {
            // For now, just draw at origin (could add resize option)
            layer.ctx.putImageData(imageData, 0, 0);
        } else {
            layer.setImageData(imageData);
        }

        this.app.renderer.requestRender();
        this.app.eventBus.emit('image:loaded', { layer, metadata });

        return layer;
    }

    /**
     * Get filter info by ID.
     * @param {string} filterId
     * @returns {Object|undefined}
     */
    getFilterInfo(filterId) {
        if (filterId.startsWith('js:')) {
            return this.jsFilters.get(filterId);
        }
        return this.backendFilters.get(filterId);
    }
}
