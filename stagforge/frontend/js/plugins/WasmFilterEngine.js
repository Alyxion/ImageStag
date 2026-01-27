/**
 * WasmFilterEngine - Client-side WASM filter execution for Stagforge.
 *
 * Loads the ImageStag WASM filter module and provides the same interface
 * as the backend filter API, allowing filters to run entirely in the browser.
 *
 * Usage:
 *   const engine = new WasmFilterEngine();
 *   await engine.initialize();
 *   const result = engine.applyFilter('grayscale', imageData, {});
 */

export class WasmFilterEngine {
    constructor() {
        this._module = null;
        this._initialized = false;
        this._initializing = null;
    }

    /**
     * Whether the WASM engine is ready.
     * @returns {boolean}
     */
    get ready() {
        return this._initialized;
    }

    /**
     * Initialize the WASM filter module.
     * Safe to call multiple times — deduplicates concurrent calls.
     * @returns {Promise<boolean>} true if initialization succeeded
     */
    async initialize() {
        if (this._initialized) return true;
        if (this._initializing) return this._initializing;

        this._initializing = (async () => {
            try {
                this._module = await import('/imgstag/filters/index.js');
                await this._module.initFilters();
                this._initialized = true;
                console.log('[WasmFilterEngine] Initialized —', this._module.getFilterIds().length, 'filters available');
                return true;
            } catch (e) {
                console.error('[WasmFilterEngine] Failed to initialize:', e);
                this._initialized = false;
                return false;
            } finally {
                this._initializing = null;
            }
        })();

        return this._initializing;
    }

    /**
     * Get all available WASM filter IDs.
     * @returns {string[]}
     */
    getFilterIds() {
        if (!this._module) return [];
        return this._module.getFilterIds();
    }

    /**
     * Get filter metadata (name, category, params) for all WASM filters.
     * Returns the same schema as /api/filters.
     * @returns {Array<{id, name, category, params}>}
     */
    getFilterList() {
        if (!this._module) return [];
        const meta = this._module.filterMetadata;
        return Object.entries(meta).map(([id, info]) => ({
            id,
            name: info.name,
            description: info.name,
            category: info.category,
            params: info.params,
            source: 'wasm',
        }));
    }

    /**
     * Check if a specific filter is available in WASM.
     * @param {string} filterId
     * @returns {boolean}
     */
    hasFilter(filterId) {
        if (!this._module) return false;
        return this._module.getFilterIds().includes(filterId);
    }

    /**
     * Apply a filter to an ImageData object.
     * @param {string} filterId - Filter ID
     * @param {ImageData} imageData - Browser ImageData (from canvas)
     * @param {Object} params - Filter parameters
     * @returns {ImageData} - Filtered ImageData
     * @throws {Error} if filter not found or not initialized
     */
    applyFilter(filterId, imageData, params = {}) {
        if (!this._initialized || !this._module) {
            throw new Error('WasmFilterEngine not initialized');
        }

        // Wrap browser ImageData in the format expected by imagestag filters
        const input = {
            data: imageData.data,
            width: imageData.width,
            height: imageData.height,
            channels: 4,
        };

        const result = this._module.applyFilter(filterId, input, params);

        // Convert back to browser ImageData
        return new ImageData(
            new Uint8ClampedArray(result.data),
            result.width,
            result.height
        );
    }
}
