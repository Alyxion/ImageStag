/**
 * LayerStack - Manages multiple layers.
 */
import { Layer } from './Layer.js';
import { VectorLayer } from './VectorLayer.js';
import { BlendModes } from './BlendModes.js';

export class LayerStack {
    /**
     * @param {number} width - Document width
     * @param {number} height - Document height
     * @param {EventBus} eventBus - Event bus for notifications
     */
    constructor(width, height, eventBus) {
        this.width = width;
        this.height = height;
        this.eventBus = eventBus;
        this.layers = [];
        this.activeLayerIndex = -1;
    }

    /**
     * Add a new layer or add an existing layer instance.
     * @param {Object|Layer|VectorLayer} layerOrOptions - Layer instance or options
     * @returns {Layer|VectorLayer}
     */
    addLayer(layerOrOptions = {}) {
        let layer;

        // Check if it's already a Layer instance
        if (layerOrOptions instanceof Layer) {
            layer = layerOrOptions;
        } else {
            // Create a new Layer from options
            layer = new Layer({
                width: this.width,
                height: this.height,
                ...layerOrOptions
            });
        }

        this.layers.push(layer);
        this.activeLayerIndex = this.layers.length - 1;
        this.eventBus.emit('layer:added', { layer, index: this.activeLayerIndex });
        return layer;
    }

    /**
     * Set the active layer by ID.
     * @param {string} id - Layer ID
     */
    setActiveLayerById(id) {
        const index = this.getLayerIndex(id);
        if (index >= 0) {
            this.setActiveLayer(index);
        }
    }

    /**
     * Rasterize a vector layer in place.
     * @param {string} layerId - ID of the vector layer to rasterize
     * @returns {Layer|null} The new raster layer, or null if layer not found
     */
    rasterizeLayer(layerId) {
        const index = this.getLayerIndex(layerId);
        if (index < 0) return null;

        const layer = this.layers[index];

        // Only rasterize if it's a vector layer
        if (!layer.isVector || !layer.isVector()) return layer;

        // Rasterize the vector layer
        const rasterLayer = layer.rasterize();

        // Replace in the array
        this.layers[index] = rasterLayer;

        this.eventBus.emit('layer:rasterized', { layerId, index, layer: rasterLayer });
        return rasterLayer;
    }

    /**
     * Remove a layer by index.
     * @param {number} index
     * @returns {boolean}
     */
    removeLayer(index) {
        if (this.layers.length <= 1) return false; // Keep at least one layer
        if (index < 0 || index >= this.layers.length) return false;

        const [removed] = this.layers.splice(index, 1);
        this.activeLayerIndex = Math.min(this.activeLayerIndex, this.layers.length - 1);
        this.eventBus.emit('layer:removed', { layer: removed, index });
        return true;
    }

    /**
     * Move a layer from one position to another.
     * @param {number} fromIndex
     * @param {number} toIndex
     */
    moveLayer(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= this.layers.length) return;
        if (toIndex < 0 || toIndex >= this.layers.length) return;

        const [layer] = this.layers.splice(fromIndex, 1);
        this.layers.splice(toIndex, 0, layer);

        if (this.activeLayerIndex === fromIndex) {
            this.activeLayerIndex = toIndex;
        } else if (fromIndex < this.activeLayerIndex && toIndex >= this.activeLayerIndex) {
            this.activeLayerIndex--;
        } else if (fromIndex > this.activeLayerIndex && toIndex <= this.activeLayerIndex) {
            this.activeLayerIndex++;
        }

        this.eventBus.emit('layer:moved', { fromIndex, toIndex });
    }

    /**
     * Duplicate a layer.
     * @param {number} index
     * @returns {Layer|null}
     */
    duplicateLayer(index) {
        if (index < 0 || index >= this.layers.length) return null;

        const original = this.layers[index];
        const cloned = original.clone();
        this.layers.splice(index + 1, 0, cloned);
        this.activeLayerIndex = index + 1;
        this.eventBus.emit('layer:duplicated', { original, cloned, index: index + 1 });
        return cloned;
    }

    /**
     * Merge a layer with the one below it.
     * @param {number} index
     * @returns {boolean}
     */
    mergeDown(index) {
        if (index <= 0 || index >= this.layers.length) return false;

        const upper = this.layers[index];
        const lower = this.layers[index - 1];

        // Composite upper onto lower
        lower.ctx.globalAlpha = upper.opacity;
        lower.ctx.globalCompositeOperation = BlendModes.toCompositeOperation(upper.blendMode);
        lower.ctx.drawImage(upper.canvas, 0, 0);
        lower.ctx.globalAlpha = 1.0;
        lower.ctx.globalCompositeOperation = 'source-over';

        this.layers.splice(index, 1);
        this.activeLayerIndex = index - 1;
        this.eventBus.emit('layer:merged', { index });
        return true;
    }

    /**
     * Flatten all layers into one.
     * @returns {Layer}
     */
    flattenAll() {
        const resultLayer = new Layer({
            width: this.width,
            height: this.height,
            name: 'Flattened'
        });

        // Fill with white background
        resultLayer.ctx.fillStyle = '#FFFFFF';
        resultLayer.ctx.fillRect(0, 0, this.width, this.height);

        // Composite all visible layers (bottom to top)
        for (const layer of this.layers) {
            if (!layer.visible) continue;
            resultLayer.ctx.globalAlpha = layer.opacity;
            resultLayer.ctx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
            resultLayer.ctx.drawImage(layer.canvas, 0, 0);
        }

        resultLayer.ctx.globalAlpha = 1.0;
        resultLayer.ctx.globalCompositeOperation = 'source-over';

        this.layers = [resultLayer];
        this.activeLayerIndex = 0;
        this.eventBus.emit('layer:flattened');
        return resultLayer;
    }

    /**
     * Get the currently active layer.
     * @returns {Layer|null}
     */
    getActiveLayer() {
        return this.layers[this.activeLayerIndex] || null;
    }

    /**
     * Set the active layer by index.
     * @param {number} index
     */
    setActiveLayer(index) {
        if (index >= 0 && index < this.layers.length) {
            this.activeLayerIndex = index;
            this.eventBus.emit('layer:activated', { index, layer: this.layers[index] });
        }
    }

    /**
     * Get layer by ID.
     * @param {string} id
     * @returns {Layer|null}
     */
    getLayerById(id) {
        return this.layers.find(l => l.id === id) || null;
    }

    /**
     * Get index of a layer by ID.
     * @param {string} id
     * @returns {number}
     */
    getLayerIndex(id) {
        return this.layers.findIndex(l => l.id === id);
    }
}
