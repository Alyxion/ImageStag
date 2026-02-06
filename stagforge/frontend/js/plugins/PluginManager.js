/**
 * PluginManager - Manages built-in, WASM, and backend filters.
 */
import { BackendConnector } from './BackendConnector.js';
import { WasmFilterEngine } from './WasmFilterEngine.js';

export class PluginManager {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.backendConnector = null;
        this.wasmEngine = new WasmFilterEngine();
        this.jsFilters = new Map();      // Built-in JS filters
        this.wasmFilters = new Map();    // WASM filters (from imagestag)
        this.backendFilters = new Map(); // Python backend filters
        this.imageSources = new Map();   // Image sources
    }

    /**
     * Initialize the plugin system.
     */
    async initialize() {
        // Register built-in JS filters
        this.registerBuiltInFilters();

        // Initialize WASM filter engine (always, regardless of backend mode)
        try {
            const wasmReady = await this.wasmEngine.initialize();
            if (wasmReady) {
                const wasmList = this.wasmEngine.getFilterList();
                for (const filter of wasmList) {
                    this.wasmFilters.set(filter.id, filter);
                }
                console.log(`[PluginManager] ${this.wasmFilters.size} WASM filters available`);
                this.app.eventBus.emit('wasm:ready', { filters: this.wasmFilters });
            }
        } catch (e) {
            console.warn('[PluginManager] WASM engine init failed:', e);
        }

        const backendMode = this.app.backendMode || 'on';

        // In 'off' or 'offline' mode, skip backend connection and filter discovery
        if (backendMode === 'off' || backendMode === 'offline') {
            console.log(`[PluginManager] Backend mode "${backendMode}" - skipping backend connection`);
            this.app.eventBus.emit('backend:disconnected', { mode: backendMode });
            return;
        }

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
     * Note: Most filters are provided by the WASM engine (imagestag).
     * Only add JS filters here for functionality not available in WASM.
     */
    registerBuiltInFilters() {
        // All basic filters (invert, grayscale, brightness, contrast, etc.)
        // are provided by the WASM engine via WasmFilterEngine.
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

        // Add WASM filters
        for (const [id, filter] of this.wasmFilters) {
            allFilters.push({
                ...filter,
                source: 'wasm'
            });
        }

        // Add backend filters (skip if a WASM version exists)
        for (const [id, filter] of this.backendFilters) {
            if (!this.wasmFilters.has(id)) {
                allFilters.push({
                    ...filter,
                    source: 'python'
                });
            }
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
            // Built-in JavaScript filter
            const filter = this.jsFilters.get(filterId);
            if (!filter) throw new Error(`Filter not found: ${filterId}`);
            result = filter.apply(imageData, params);
        } else if (this.wasmEngine.ready && this.wasmEngine.hasFilter(filterId)) {
            // WASM filter
            result = this.wasmEngine.applyFilter(filterId, imageData, params);
        } else {
            // Backend filter
            if (!this.backendConnector?.connected) {
                throw new Error('Backend not connected');
            }
            result = await this.backendConnector.applyFilter(filterId, imageData, params);
        }

        layer.setImageData(result);

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
        return this.wasmFilters.get(filterId) || this.backendFilters.get(filterId);
    }
}
