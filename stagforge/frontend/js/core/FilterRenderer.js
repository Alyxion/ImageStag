/**
 * FilterRenderer - Applies dynamic (non-destructive) filters with caching.
 *
 * Filters are applied after layer rasterization but before effects.
 * The filtered result is cached and invalidated when the layer's content
 * changes or filter parameters change.
 *
 * Unlike effects (which expand canvas), filters operate in-place at the
 * same dimensions as the source layer canvas.
 */
export class FilterRenderer {
    /**
     * @param {Object} pluginManager - PluginManager with wasmEngine and jsFilters
     * @param {string} apiBase - API base URL for backend filter execution
     * @param {Function} getExecMode - Returns current filter execution mode
     */
    constructor(pluginManager, apiBase, getExecMode) {
        this.pluginManager = pluginManager;
        this.apiBase = apiBase;
        this.getExecMode = getExecMode;

        // Cache: layerId → { canvas, hash }
        this.cache = new Map();

        // Pending async renders
        this._pendingRenders = new Map();
    }

    /**
     * Get the filtered canvas for a layer.
     * Returns cached result if hash matches.
     *
     * @param {Object} layer - Layer with .filters array and .canvas
     * @returns {HTMLCanvasElement|null} Filtered canvas, or null if no filters
     */
    getFilteredCanvas(layer) {
        if (!layer.filters || layer.filters.length === 0) {
            return null;
        }

        const enabledFilters = layer.filters.filter(f => f.enabled);
        if (enabledFilters.length === 0) {
            return null;
        }

        const hash = this.computeHash(layer);
        const cached = this.cache.get(layer.id);

        if (cached && cached.hash === hash) {
            return cached.canvas;
        }

        // Cache miss — compute synchronously if possible, else trigger async
        const result = this._applyFiltersSync(layer, enabledFilters);
        if (result) {
            this.cache.set(layer.id, { canvas: result, hash });
            return result;
        }

        // Async filters needed — trigger background render
        if (!this._pendingRenders.has(layer.id)) {
            this._pendingRenders.set(layer.id, true);
            this._applyFiltersAsync(layer, enabledFilters, hash).then(canvas => {
                this._pendingRenders.delete(layer.id);
                if (canvas) {
                    this.cache.set(layer.id, { canvas, hash: this.computeHash(layer) });
                    // Trigger re-render by marking layer changed
                    layer.markChanged();
                }
            }).catch(() => {
                this._pendingRenders.delete(layer.id);
            });
        }

        // Return stale cache while async render runs
        return cached?.canvas || null;
    }

    /**
     * Compute cache invalidation hash.
     * @param {Object} layer
     * @returns {string}
     */
    computeHash(layer) {
        const filtersHash = layer.filters
            .filter(f => f.enabled)
            .map(f => `${f.filterId}:${JSON.stringify(f.params)}`)
            .join('|');

        // Use layer's change counter for content changes
        return `${layer.changeCounter}:${layer.width}x${layer.height}|${filtersHash}`;
    }

    /**
     * Apply all enabled filters synchronously (JS/WASM only).
     * Returns null if any filter requires async (backend) execution.
     *
     * @param {Object} layer
     * @param {Array} enabledFilters
     * @returns {HTMLCanvasElement|null}
     */
    _applyFiltersSync(layer, enabledFilters) {
        const wasmEngine = this.pluginManager?.wasmEngine;
        const jsFilters = this.pluginManager?.jsFilters;
        const execMode = this.getExecMode?.() ?? 'js';

        // Check if all filters can be executed synchronously
        for (const filter of enabledFilters) {
            const filterId = filter.filterId;
            const isJS = filterId.startsWith('js:') && jsFilters?.has(filterId);
            const isWasm = execMode === 'js' && wasmEngine?.ready && wasmEngine.hasFilter(filterId);
            if (!isJS && !isWasm) {
                return null; // Needs async backend execution
            }
        }

        // All filters are sync — apply them
        const sourceCanvas = layer.canvas;
        if (!sourceCanvas || sourceCanvas.width === 0 || sourceCanvas.height === 0) {
            return null;
        }

        // Copy source to working canvas
        const canvas = document.createElement('canvas');
        canvas.width = sourceCanvas.width;
        canvas.height = sourceCanvas.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(sourceCanvas, 0, 0);

        for (const filter of enabledFilters) {
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            let resultData;

            if (filter.filterId.startsWith('js:')) {
                const jsFilter = jsFilters.get(filter.filterId);
                resultData = jsFilter.apply(imageData, filter.params);
            } else {
                resultData = wasmEngine.applyFilter(filter.filterId, imageData, filter.params);
            }

            ctx.putImageData(resultData, 0, 0);
        }

        return canvas;
    }

    /**
     * Apply filters asynchronously (handles backend filters).
     *
     * @param {Object} layer
     * @param {Array} enabledFilters
     * @param {string} expectedHash
     * @returns {Promise<HTMLCanvasElement|null>}
     */
    async _applyFiltersAsync(layer, enabledFilters, expectedHash) {
        const sourceCanvas = layer.canvas;
        if (!sourceCanvas || sourceCanvas.width === 0 || sourceCanvas.height === 0) {
            return null;
        }

        const wasmEngine = this.pluginManager?.wasmEngine;
        const jsFilters = this.pluginManager?.jsFilters;
        const execMode = this.getExecMode?.() ?? 'js';

        // Copy source
        const canvas = document.createElement('canvas');
        canvas.width = sourceCanvas.width;
        canvas.height = sourceCanvas.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(sourceCanvas, 0, 0);

        for (const filter of enabledFilters) {
            // Check if hash changed (layer was modified during async)
            if (this.computeHash(layer) !== expectedHash) return null;

            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            let resultData;

            if (filter.filterId.startsWith('js:') && jsFilters?.has(filter.filterId)) {
                resultData = jsFilters.get(filter.filterId).apply(imageData, filter.params);
            } else if (execMode === 'js' && wasmEngine?.ready && wasmEngine.hasFilter(filter.filterId)) {
                resultData = wasmEngine.applyFilter(filter.filterId, imageData, filter.params);
            } else {
                // Backend execution
                resultData = await this._applyFilterBackend(filter.filterId, imageData, filter.params);
            }

            if (resultData) {
                ctx.putImageData(resultData, 0, 0);
            }
        }

        return canvas;
    }

    /**
     * Apply a single filter via backend API.
     *
     * @param {string} filterId
     * @param {ImageData} imageData
     * @param {Object} params
     * @returns {Promise<ImageData>}
     */
    async _applyFilterBackend(filterId, imageData, params) {
        const metadata = JSON.stringify({
            width: imageData.width,
            height: imageData.height,
            params: params,
        });
        const metadataBytes = new TextEncoder().encode(metadata);
        const metadataLength = new Uint32Array([metadataBytes.length]);

        const payload = new Uint8Array(4 + metadataBytes.length + imageData.data.length);
        payload.set(new Uint8Array(metadataLength.buffer), 0);
        payload.set(metadataBytes, 4);
        payload.set(imageData.data, 4 + metadataBytes.length);

        const response = await fetch(`${this.apiBase}/filters/${filterId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/octet-stream' },
            body: payload,
        });

        if (!response.ok) return null;

        const resultBytes = new Uint8Array(await response.arrayBuffer());
        return new ImageData(
            new Uint8ClampedArray(resultBytes),
            imageData.width,
            imageData.height
        );
    }

    /**
     * Invalidate cache for a specific layer.
     * @param {string} layerId
     */
    invalidate(layerId) {
        this.cache.delete(layerId);
        this._pendingRenders.delete(layerId);
    }

    /**
     * Clear all caches.
     */
    clearAll() {
        this.cache.clear();
        this._pendingRenders.clear();
    }
}
