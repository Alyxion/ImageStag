/**
 * Document - Represents a single document/image with all its state.
 *
 * Each document has its own:
 * - LayerStack (layers and their content)
 * - History (undo/redo state)
 * - Selection state
 * - Document dimensions
 * - Metadata (filename, modified state, etc.)
 */
import { LayerStack } from './LayerStack.js';
import { History } from './History.js';

export class Document {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {number} options.width - Document width
     * @param {number} options.height - Document height
     * @param {number} [options.dpi=72] - Document DPI (dots per inch)
     * @param {string} [options.name] - Document name
     * @param {Object} [options.eventBus] - Event bus for this document
     */
    constructor(options = {}) {
        this.id = crypto.randomUUID();
        this.name = options.name || 'Untitled';
        this.width = options.width || 800;
        this.height = options.height || 600;
        this.dpi = options.dpi || 72;

        // Create a document-scoped event bus proxy
        this.eventBus = options.eventBus || this.createEventBusProxy();

        // Document state
        this.modified = false;
        this.filePath = null;  // For saved documents
        this.lastSaved = null;

        // Core systems (lazy initialization)
        this._layerStack = null;
        this._history = null;

        // Selection state (document-specific)
        this.selection = null;  // Will be set by app when needed

        // Clipboard is shared across documents (managed by app)

        // View state (can be document-specific)
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;

        // Foreground/background colors (document-specific)
        this.foregroundColor = '#000000';
        this.backgroundColor = '#FFFFFF';
    }

    /**
     * Create a simple event bus proxy that prefixes events with document ID.
     */
    createEventBusProxy() {
        const listeners = new Map();
        return {
            on: (event, callback) => {
                if (!listeners.has(event)) {
                    listeners.set(event, []);
                }
                listeners.get(event).push(callback);
            },
            off: (event, callback) => {
                if (listeners.has(event)) {
                    const arr = listeners.get(event);
                    const idx = arr.indexOf(callback);
                    if (idx !== -1) arr.splice(idx, 1);
                }
            },
            emit: (event, data) => {
                if (listeners.has(event)) {
                    for (const cb of listeners.get(event)) {
                        cb(data);
                    }
                }
            }
        };
    }

    /**
     * Get or create the layer stack.
     */
    get layerStack() {
        if (!this._layerStack) {
            this._layerStack = new LayerStack(this.width, this.height, this.eventBus);
        }
        return this._layerStack;
    }

    /**
     * Get or create the history system.
     */
    get history() {
        if (!this._history) {
            // Create a minimal app context for history
            const appContext = {
                layerStack: this.layerStack,
                eventBus: this.eventBus
            };
            this._history = new History(appContext);
        }
        return this._history;
    }

    /**
     * Mark document as modified.
     */
    markModified() {
        this.modified = true;
        this.eventBus.emit('document:modified', { document: this });
    }

    /**
     * Mark document as saved.
     */
    markSaved() {
        this.modified = false;
        this.lastSaved = new Date();
        this.eventBus.emit('document:saved', { document: this });
    }

    /**
     * Get display name (includes * if modified).
     */
    get displayName() {
        return this.modified ? `${this.name}*` : this.name;
    }

    /**
     * Resize document canvas.
     * @param {number} width
     * @param {number} height
     * @param {string} [anchor='center'] - Anchor point for resize
     */
    resize(width, height, anchor = 'center') {
        const oldWidth = this.width;
        const oldHeight = this.height;

        this.width = width;
        this.height = height;

        // Calculate offset based on anchor
        let offsetX = 0, offsetY = 0;
        switch (anchor) {
            case 'top-left':
                offsetX = 0; offsetY = 0;
                break;
            case 'top':
                offsetX = (width - oldWidth) / 2; offsetY = 0;
                break;
            case 'top-right':
                offsetX = width - oldWidth; offsetY = 0;
                break;
            case 'left':
                offsetX = 0; offsetY = (height - oldHeight) / 2;
                break;
            case 'center':
                offsetX = (width - oldWidth) / 2;
                offsetY = (height - oldHeight) / 2;
                break;
            case 'right':
                offsetX = width - oldWidth; offsetY = (height - oldHeight) / 2;
                break;
            case 'bottom-left':
                offsetX = 0; offsetY = height - oldHeight;
                break;
            case 'bottom':
                offsetX = (width - oldWidth) / 2; offsetY = height - oldHeight;
                break;
            case 'bottom-right':
                offsetX = width - oldWidth; offsetY = height - oldHeight;
                break;
        }

        // Resize layer stack
        this.layerStack.resize(width, height, offsetX, offsetY);

        this.markModified();
        this.eventBus.emit('document:resized', {
            document: this,
            width, height,
            oldWidth, oldHeight
        });
    }

    /**
     * Rotate the entire canvas by 90, 180, or 270 degrees clockwise.
     * This rotates all layers and swaps dimensions for 90/270.
     * @param {number} degrees - Rotation angle (90, 180, or 270)
     */
    rotateCanvas(degrees) {
        if (![90, 180, 270].includes(degrees)) {
            console.error('[Document] Invalid rotation angle:', degrees);
            return;
        }

        const oldWidth = this.width;
        const oldHeight = this.height;

        // Swap dimensions for 90 or 270 degree rotation
        if (degrees === 90 || degrees === 270) {
            this.width = oldHeight;
            this.height = oldWidth;
        }

        // Rotate each layer
        for (const layer of this.layerStack.layers) {
            this._rotateLayer(layer, degrees, oldWidth, oldHeight);
        }

        // Update layer stack dimensions
        this.layerStack.width = this.width;
        this.layerStack.height = this.height;

        // Clear selection (rotating selection mask is complex)
        if (this.selection?.clear) {
            this.selection.clear();
        }

        this.markModified();
        this.eventBus.emit('document:rotated', {
            document: this,
            degrees,
            width: this.width,
            height: this.height,
            oldWidth, oldHeight
        });
    }

    /**
     * Rotate a single layer by the given degrees.
     * @private
     */
    _rotateLayer(layer, degrees, oldDocWidth, oldDocHeight) {
        // Handle different layer types
        if (layer.isVector && layer.isVector()) {
            this._rotateVectorLayer(layer, degrees, oldDocWidth, oldDocHeight);
        } else if (layer.isSVG && layer.isSVG()) {
            this._rotateSVGLayer(layer, degrees, oldDocWidth, oldDocHeight);
        } else if (layer.isText && layer.isText()) {
            this._rotateTextLayer(layer, degrees, oldDocWidth, oldDocHeight);
        } else {
            // Raster layer
            this._rotateRasterLayer(layer, degrees, oldDocWidth, oldDocHeight);
        }
    }

    /**
     * Rotate a raster layer.
     * @private
     */
    _rotateRasterLayer(layer, degrees, oldDocWidth, oldDocHeight) {
        const oldCanvas = layer.canvas;
        const oldWidth = layer.width;
        const oldHeight = layer.height;
        const oldOffsetX = layer.offsetX || 0;
        const oldOffsetY = layer.offsetY || 0;

        // Calculate new dimensions
        let newWidth, newHeight;
        if (degrees === 180) {
            newWidth = oldWidth;
            newHeight = oldHeight;
        } else {
            // 90 or 270: swap dimensions
            newWidth = oldHeight;
            newHeight = oldWidth;
        }

        // Create new canvas
        const newCanvas = document.createElement('canvas');
        newCanvas.width = newWidth;
        newCanvas.height = newHeight;
        const newCtx = newCanvas.getContext('2d');

        // Rotate and draw
        newCtx.save();
        if (degrees === 90) {
            newCtx.translate(newWidth, 0);
            newCtx.rotate(Math.PI / 2);
        } else if (degrees === 180) {
            newCtx.translate(newWidth, newHeight);
            newCtx.rotate(Math.PI);
        } else if (degrees === 270) {
            newCtx.translate(0, newHeight);
            newCtx.rotate(-Math.PI / 2);
        }
        newCtx.drawImage(oldCanvas, 0, 0);
        newCtx.restore();

        // Calculate new offset based on rotation around document center
        let newOffsetX, newOffsetY;
        const centerX = oldDocWidth / 2;
        const centerY = oldDocHeight / 2;
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

        // Rotate layer center point around document center
        const dx = layerCenterX - centerX;
        const dy = layerCenterY - centerY;
        const rad = (degrees * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        const newCenterX = centerX + dx * cos - dy * sin;
        const newCenterY = centerY + dx * sin + dy * cos;

        // Adjust for new document center (if dimensions swapped)
        const newDocCenterX = this.width / 2;
        const newDocCenterY = this.height / 2;
        const adjustedCenterX = newCenterX - centerX + newDocCenterX;
        const adjustedCenterY = newCenterY - centerY + newDocCenterY;

        newOffsetX = Math.round(adjustedCenterX - newWidth / 2);
        newOffsetY = Math.round(adjustedCenterY - newHeight / 2);

        // Update layer
        layer.canvas = newCanvas;
        layer.ctx = newCtx;
        layer.width = newWidth;
        layer.height = newHeight;
        layer.offsetX = newOffsetX;
        layer.offsetY = newOffsetY;
        layer.invalidateImageCache?.();
    }

    /**
     * Rotate a vector layer by transforming shape coordinates.
     * @private
     */
    _rotateVectorLayer(layer, degrees, oldDocWidth, oldDocHeight) {
        const centerX = oldDocWidth / 2;
        const centerY = oldDocHeight / 2;
        const rad = (degrees * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);

        // Rotate each shape's coordinates
        if (layer.shapes) {
            for (const shape of layer.shapes) {
                // Helper to rotate a point
                const rotatePoint = (x, y) => {
                    const dx = x - centerX;
                    const dy = y - centerY;
                    const newX = centerX + dx * cos - dy * sin;
                    const newY = centerY + dx * sin + dy * cos;
                    // Adjust for new document dimensions
                    const adjustX = this.width / 2 - centerX;
                    const adjustY = this.height / 2 - centerY;
                    return { x: newX + adjustX, y: newY + adjustY };
                };

                // Rotate based on shape type
                if (shape.x !== undefined && shape.y !== undefined) {
                    const rotated = rotatePoint(shape.x, shape.y);
                    shape.x = rotated.x;
                    shape.y = rotated.y;
                }
                if (shape.x1 !== undefined && shape.y1 !== undefined) {
                    const rotated = rotatePoint(shape.x1, shape.y1);
                    shape.x1 = rotated.x;
                    shape.y1 = rotated.y;
                }
                if (shape.x2 !== undefined && shape.y2 !== undefined) {
                    const rotated = rotatePoint(shape.x2, shape.y2);
                    shape.x2 = rotated.x;
                    shape.y2 = rotated.y;
                }
                // For rectangles, swap width/height for 90/270
                if (shape.width !== undefined && shape.height !== undefined && (degrees === 90 || degrees === 270)) {
                    const temp = shape.width;
                    shape.width = shape.height;
                    shape.height = temp;
                }
                // Rotate polygon/path points
                if (shape.points) {
                    shape.points = shape.points.map(p => rotatePoint(p.x, p.y));
                }
            }
        }

        // Re-render the layer
        layer.render?.();
    }

    /**
     * Rotate an SVG layer by adding a transform.
     * @private
     */
    _rotateSVGLayer(layer, degrees, oldDocWidth, oldDocHeight) {
        // Update offset similar to raster layer
        const oldOffsetX = layer.offsetX || 0;
        const oldOffsetY = layer.offsetY || 0;
        const oldWidth = layer.width;
        const oldHeight = layer.height;

        // Calculate rotation around document center
        const centerX = oldDocWidth / 2;
        const centerY = oldDocHeight / 2;
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

        const dx = layerCenterX - centerX;
        const dy = layerCenterY - centerY;
        const rad = (degrees * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        const newCenterX = centerX + dx * cos - dy * sin;
        const newCenterY = centerY + dx * sin + dy * cos;

        const adjustedCenterX = newCenterX - centerX + this.width / 2;
        const adjustedCenterY = newCenterY - centerY + this.height / 2;

        // For 90/270, swap layer dimensions
        let newWidth = oldWidth, newHeight = oldHeight;
        if (degrees === 90 || degrees === 270) {
            newWidth = oldHeight;
            newHeight = oldWidth;
        }

        layer.offsetX = Math.round(adjustedCenterX - newWidth / 2);
        layer.offsetY = Math.round(adjustedCenterY - newHeight / 2);
        layer.width = newWidth;
        layer.height = newHeight;

        // Add rotation transform to SVG
        if (layer.svgContent) {
            layer.rotation = (layer.rotation || 0) + degrees;
        }

        layer.render?.();
    }

    /**
     * Rotate a text layer.
     * @private
     */
    _rotateTextLayer(layer, degrees, oldDocWidth, oldDocHeight) {
        // Update offset similar to raster layer
        const oldOffsetX = layer.offsetX || 0;
        const oldOffsetY = layer.offsetY || 0;
        const oldWidth = layer.width;
        const oldHeight = layer.height;

        const centerX = oldDocWidth / 2;
        const centerY = oldDocHeight / 2;
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

        const dx = layerCenterX - centerX;
        const dy = layerCenterY - centerY;
        const rad = (degrees * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        const newCenterX = centerX + dx * cos - dy * sin;
        const newCenterY = centerY + dx * sin + dy * cos;

        const adjustedCenterX = newCenterX - centerX + this.width / 2;
        const adjustedCenterY = newCenterY - centerY + this.height / 2;

        // For 90/270, swap layer dimensions
        let newWidth = oldWidth, newHeight = oldHeight;
        if (degrees === 90 || degrees === 270) {
            newWidth = oldHeight;
            newHeight = oldWidth;
        }

        layer.offsetX = Math.round(adjustedCenterX - newWidth / 2);
        layer.offsetY = Math.round(adjustedCenterY - newHeight / 2);

        // Add rotation to text layer
        layer.rotation = (layer.rotation || 0) + degrees;

        layer.render?.();
    }

    /**
     * Create a new layer in this document.
     * Creates an empty 0x0 layer that auto-fits to content.
     * Use fillArea() after creation to fill specific regions.
     * @param {Object} [options]
     * @param {Object} [insertOptions]
     * @returns {Layer}
     */
    createLayer(options = {}, insertOptions = {}) {
        const layer = this.layerStack.addLayer(options, insertOptions);
        this.markModified();
        return layer;
    }

    /**
     * Export document state for serialization.
     */
    async serialize() {
        const layers = [];
        for (const layer of this.layerStack.layers) {
            layers.push(layer.serialize());
        }

        return {
            _version: Document.VERSION,
            _type: 'Document',
            id: this.id,
            name: this.name,
            width: this.width,
            height: this.height,
            dpi: this.dpi,
            foregroundColor: this.foregroundColor,
            backgroundColor: this.backgroundColor,
            activeLayerIndex: this.layerStack.activeLayerIndex,
            layers: layers,
            viewState: {
                zoom: this.zoom,
                panX: this.panX,
                panY: this.panY
            }
        };
    }

    /**
     * Migrate serialized data from older versions.
     * @param {Object} data - Serialized document data
     * @returns {Object} - Migrated data at current version
     */
    static migrate(data) {
        // Handle pre-versioned data
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Ensure viewState, colors exist
        if (data._version < 1) {
            data.viewState = data.viewState || { zoom: 1.0, panX: 0, panY: 0 };
            data.foregroundColor = data.foregroundColor || '#000000';
            data.backgroundColor = data.backgroundColor || '#FFFFFF';
            data._version = 1;
        }

        // Future migrations:
        // if (data._version < 2) { ... data._version = 2; }

        return data;
    }

    /**
     * Restore document from serialized state.
     * @param {Object} data
     * @returns {Promise<Document>}
     */
    static async deserialize(data, eventBus) {
        // Migrate to current version
        data = Document.migrate(data);

        const doc = new Document({
            width: data.width,
            height: data.height,
            name: data.name,
            eventBus
        });

        doc.id = data.id || doc.id;
        doc.dpi = data.dpi || 72;
        doc.foregroundColor = data.foregroundColor || '#000000';
        doc.backgroundColor = data.backgroundColor || '#FFFFFF';

        // Restore view state
        if (data.viewState) {
            doc.zoom = data.viewState.zoom || 1.0;
            doc.panX = data.viewState.panX || 0;
            doc.panY = data.viewState.panY || 0;
        }

        // Clear default layer and restore saved layers
        doc.layerStack.layers = [];
        for (const layerData of data.layers) {
            // Dispatch to correct layer type based on type field
            let layer;
            if (layerData.type === 'group' || layerData._type === 'LayerGroup') {
                const { LayerGroup } = await import('./LayerGroup.js');
                layer = LayerGroup.deserialize(layerData);
            } else if (layerData.type === 'text') {
                const { TextLayer } = await import('./TextLayer.js');
                layer = TextLayer.deserialize(layerData);
            } else if (layerData.type === 'vector') {
                const { VectorLayer } = await import('./VectorLayer.js');
                layer = VectorLayer.deserialize(layerData);
            } else if (layerData.type === 'svg') {
                const { SVGLayer } = await import('./SVGLayer.js');
                layer = await SVGLayer.deserialize(layerData);
            } else {
                const { Layer } = await import('./Layer.js');
                layer = await Layer.deserialize(layerData);
            }
            doc.layerStack.layers.push(layer);
        }

        doc.layerStack.activeLayerIndex = data.activeLayerIndex || 0;

        return doc;
    }

    /**
     * Get composite image as ImageData.
     */
    getCompositeImageData() {
        const canvas = document.createElement('canvas');
        canvas.width = this.width;
        canvas.height = this.height;
        const ctx = canvas.getContext('2d');

        // Draw all visible layers (bottom to top = last to first with index 0 = top)
        for (let i = this.layerStack.layers.length - 1; i >= 0; i--) {
            const layer = this.layerStack.layers[i];
            // Skip groups - they have no canvas
            if (layer.isGroup && layer.isGroup()) continue;
            // Use effective visibility (considers parent group visibility)
            if (!this.layerStack.isEffectivelyVisible(layer)) continue;
            // Use effective opacity
            ctx.globalAlpha = this.layerStack.getEffectiveOpacity(layer);
            const offsetX = layer.offsetX ?? 0;
            const offsetY = layer.offsetY ?? 0;
            ctx.drawImage(layer.canvas, offsetX, offsetY);
        }

        return ctx.getImageData(0, 0, this.width, this.height);
    }

    /**
     * Dispose of document resources.
     */
    dispose() {
        if (this._history) {
            this._history.clear();
        }
        if (this._layerStack) {
            // Clear layer canvases (skip groups - they have no canvas)
            for (const layer of this._layerStack.layers) {
                if (layer.canvas) {
                    layer.canvas.width = 0;
                    layer.canvas.height = 0;
                }
            }
            this._layerStack.layers = [];
        }
        this.eventBus.emit('document:disposed', { document: this });
    }
}
