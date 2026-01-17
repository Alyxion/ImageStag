/**
 * LayerEffect - Base class for all layer effects.
 *
 * Effects are non-destructive and applied during rendering.
 * They can expand the visual bounds beyond the layer's actual pixels.
 */

// Forward reference to registry for deserialization
let _effectRegistry = null;

export function setEffectRegistry(registry) {
    _effectRegistry = registry;
}

/**
 * Base class for all layer effects.
 */
export class LayerEffect {
    /**
     * @param {Object} options - Effect parameters
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.type = this.constructor.type;
        this.displayName = this.constructor.displayName;
        this.enabled = options.enabled ?? true;
        this.blendMode = options.blendMode || 'normal';
        this.opacity = options.opacity ?? 1.0;
    }

    /**
     * Get the expansion needed for this effect (pixels beyond layer bounds).
     * @returns {{left: number, top: number, right: number, bottom: number}}
     */
    getExpansion() {
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    /**
     * Apply effect to an ImageData and return the result.
     * @param {ImageData} imageData - Source image data
     * @param {Object} expansion - How much the canvas was expanded
     * @returns {ImageData} - Result with effect applied
     */
    apply(imageData, expansion) {
        return imageData; // Override in subclasses
    }

    /**
     * Serialize effect for storage/history.
     * @returns {Object}
     */
    serialize() {
        return {
            id: this.id,
            type: this.type,
            enabled: this.enabled,
            blendMode: this.blendMode,
            opacity: this.opacity,
            ...this.getParams()
        };
    }

    /**
     * Get effect-specific parameters.
     * @returns {Object}
     */
    getParams() {
        return {};
    }

    /**
     * Clone this effect.
     * @returns {LayerEffect}
     */
    clone() {
        const data = this.serialize();
        delete data.id;  // Generate new ID for clone
        return LayerEffect.deserialize(data);
    }

    /**
     * Create effect from serialized data.
     * @param {Object} data
     * @returns {LayerEffect}
     */
    static deserialize(data) {
        if (!_effectRegistry) {
            console.error('Effect registry not set. Call setEffectRegistry first.');
            return null;
        }
        const EffectClass = _effectRegistry[data.type];
        if (!EffectClass) {
            console.warn(`Unknown effect type: ${data.type}`);
            return null;
        }
        return new EffectClass(data);
    }
}
