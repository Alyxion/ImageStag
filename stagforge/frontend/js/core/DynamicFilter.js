/**
 * DynamicFilter - Data container for non-destructive layer filters.
 *
 * Attached to a layer's `filters` array, these are applied after rasterization
 * but before layer effects. Unlike destructive filters, dynamic filters can be
 * reordered, toggled, deleted, and reconfigured at any time.
 */
export class DynamicFilter {
    /**
     * @param {Object} options
     * @param {string} [options.id] - Unique identifier
     * @param {string} options.filterId - Filter identifier (e.g. 'gaussian_blur')
     * @param {string} [options.name] - Display name
     * @param {boolean} [options.enabled] - Whether filter is active
     * @param {Object} [options.params] - Filter parameters
     * @param {string} [options.source] - Execution source ('wasm', 'js', 'backend')
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.filterId = options.filterId;
        this.name = options.name || 'Filter';
        this.enabled = options.enabled ?? true;
        this.params = options.params || {};
        this.source = options.source || 'wasm';
    }

    /**
     * Serialize to plain object for storage/history.
     * @returns {Object}
     */
    serialize() {
        return {
            id: this.id,
            filterId: this.filterId,
            name: this.name,
            enabled: this.enabled,
            params: { ...this.params },
            source: this.source,
        };
    }

    /**
     * Create a DynamicFilter from serialized data.
     * @param {Object} data
     * @returns {DynamicFilter}
     */
    static deserialize(data) {
        return new DynamicFilter(data);
    }

    /**
     * Create a deep clone.
     * @returns {DynamicFilter}
     */
    clone() {
        return new DynamicFilter({
            id: crypto.randomUUID(),
            filterId: this.filterId,
            name: this.name,
            enabled: this.enabled,
            params: { ...this.params },
            source: this.source,
        });
    }
}

export default DynamicFilter;
