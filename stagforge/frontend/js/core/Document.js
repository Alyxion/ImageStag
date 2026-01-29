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
