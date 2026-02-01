/**
 * LayerRegistry - Central registry mapping type strings to layer classes.
 *
 * Provides a single point of control for:
 * - Layer type registration
 * - Deserialization of layers from saved data
 * - Discovering available layer types
 *
 * This enables polymorphic layer handling in Document, History, and other core
 * classes without type-specific if/else chains.
 */

/**
 * @typedef {Object} LayerTypeRegistration
 * @property {Function} layerClass - The layer class constructor
 * @property {string[]} aliases - Alternative type strings that map to this class
 */

class LayerRegistry {
    /** @type {LayerRegistry|null} */
    static _instance = null;

    constructor() {
        /** @type {Map<string, {layerClass: Function, aliases: string[]}>} */
        this._types = new Map();
    }

    /**
     * Get the singleton instance.
     * @returns {LayerRegistry}
     */
    static getInstance() {
        if (!LayerRegistry._instance) {
            LayerRegistry._instance = new LayerRegistry();
        }
        return LayerRegistry._instance;
    }

    /**
     * Register a layer type.
     * @param {string} type - Primary type string (e.g., 'raster', 'text', 'svg', 'group')
     * @param {Function} layerClass - The layer class constructor
     * @param {string[]} [aliases=[]] - Alternative type strings (e.g., 'Layer', 'TextLayer')
     */
    register(type, layerClass, aliases = []) {
        this._types.set(type, { layerClass, aliases });

        // Also register aliases for quick lookup
        for (const alias of aliases) {
            if (!this._types.has(alias)) {
                this._types.set(alias, { layerClass, aliases: [], isAlias: true, primaryType: type });
            }
        }
    }

    /**
     * Get the layer class for a type string.
     * @param {string} type - Type string (primary or alias)
     * @returns {Function|null} Layer class constructor or null if not found
     */
    getClass(type) {
        const registration = this._types.get(type);
        return registration?.layerClass ?? null;
    }

    /**
     * Check if a type is registered.
     * @param {string} type - Type string to check
     * @returns {boolean}
     */
    has(type) {
        return this._types.has(type);
    }

    /**
     * Deserialize layer data to a layer instance.
     * Automatically dispatches to the correct layer class based on type.
     *
     * @param {Object} data - Serialized layer data with type or _type field
     * @returns {Promise<Object>} Deserialized layer instance
     * @throws {Error} If layer type is not registered
     */
    async deserialize(data) {
        // Check both type and _type fields for compatibility
        const type = data.type || data._type;

        if (!type) {
            throw new Error('LayerRegistry.deserialize: data has no type or _type field');
        }

        const LayerClass = this.getClass(type);

        if (!LayerClass) {
            throw new Error(`LayerRegistry.deserialize: unknown layer type "${type}"`);
        }

        // Call the class's static deserialize method
        // Some are async (Layer, SVGLayer), some are sync (LayerGroup, TextLayer)
        const result = LayerClass.deserialize(data);

        // Handle both sync and async deserialize methods
        if (result instanceof Promise) {
            return await result;
        }
        return result;
    }

    /**
     * Get all registered primary type strings.
     * @returns {string[]}
     */
    getTypes() {
        return Array.from(this._types.entries())
            .filter(([, reg]) => !reg.isAlias)
            .map(([type]) => type);
    }

    /**
     * Get registration info for a type.
     * @param {string} type - Type string
     * @returns {LayerTypeRegistration|null}
     */
    getRegistration(type) {
        return this._types.get(type) ?? null;
    }
}

/**
 * The singleton layer registry instance.
 * Import this to register layer types or deserialize layers.
 *
 * @example
 * // Register a layer type (typically done at module load)
 * import { layerRegistry } from './LayerRegistry.js';
 * import { MyLayer } from './MyLayer.js';
 * layerRegistry.register('mylayer', MyLayer, ['MyLayer']);
 *
 * @example
 * // Deserialize a layer
 * const layer = await layerRegistry.deserialize(serializedData);
 */
export const layerRegistry = LayerRegistry.getInstance();

export { LayerRegistry };
