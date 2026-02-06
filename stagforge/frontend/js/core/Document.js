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
import { layerRegistry } from './LayerRegistry.js';

export class Document {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {number} options.width - Document width
     * @param {number} options.height - Document height
     * @param {number} [options.dpi=72] - Document DPI (dots per inch)
     * @param {string} [options.name] - Document name
     * @param {string} [options.icon] - Document icon (emoji)
     * @param {string} [options.color] - Document color (hex)
     * @param {Object} [options.eventBus] - Event bus for this document
     */
    constructor(options = {}) {
        this.id = crypto.randomUUID();
        this.name = options.name || 'Untitled';
        this.icon = options.icon || '🎨';
        this.color = options.color || '#E0E7FF';
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

        // Saved selections (alpha masks with names)
        this.savedSelections = [];

        // Change tracking (for API polling optimization)
        this.changeCounter = 0;
        this.lastChangeTimestamp = Date.now();
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
        this.changeCounter++;
        this.lastChangeTimestamp = Date.now();
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
     * @returns {Promise<void>}
     */
    async rotateCanvas(degrees) {
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
            await this._rotateLayer(layer, degrees, oldWidth, oldHeight);
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
     * Mirror the entire canvas horizontally or vertically.
     * This mirrors all layers.
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @returns {Promise<void>}
     */
    async mirrorCanvas(direction) {
        if (!['horizontal', 'vertical'].includes(direction)) {
            console.error('[Document] Invalid mirror direction:', direction);
            return;
        }

        // Mirror each layer
        for (const layer of this.layerStack.layers) {
            await this._mirrorLayer(layer, direction);
        }

        // Clear selection (mirroring selection mask is complex)
        if (this.selection?.clear) {
            this.selection.clear();
        }

        this.markModified();
        this.eventBus.emit('document:mirrored', {
            document: this,
            direction,
            width: this.width,
            height: this.height
        });
    }

    /**
     * Mirror a single layer by delegating to the layer's mirrorContent method.
     * Each layer type implements its own mirroring logic.
     * @private
     */
    async _mirrorLayer(layer, direction) {
        // All layer types implement mirrorContent (groups no-op)
        await layer.mirrorContent(direction, this.width, this.height);
    }

    /**
     * Rotate a single layer by delegating to the layer's rotateCanvas method.
     * Each layer type implements its own rotation logic.
     * @private
     */
    async _rotateLayer(layer, degrees, oldDocWidth, oldDocHeight) {
        // All layer types implement rotateCanvas (groups no-op)
        await layer.rotateCanvas(degrees, oldDocWidth, oldDocHeight, this.width, this.height);
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

    // ==================== SVG Export/Import ====================

    /**
     * Export the document as an SVG string with Stagforge metadata.
     * The SVG is a valid SVG file that can be viewed in any SVG viewer,
     * but also contains embedded Stagforge metadata for lossless round-trip.
     *
     * @returns {Promise<string>} SVG document string
     */
    async toSVG() {
        const {
            STAGFORGE_NAMESPACE,
            STAGFORGE_PREFIX,
            STAGFORGE_VERSION,
            createStagforgeSVGRoot,
            createDocumentMetadata,
            serializeXML
        } = await import('./svgExportUtils.js');

        // Create XML document
        const xmlDoc = document.implementation.createDocument('http://www.w3.org/2000/svg', 'svg', null);

        // Create root SVG element with Stagforge namespace
        const svg = createStagforgeSVGRoot(xmlDoc, this.width, this.height);

        // Add xlink namespace for image hrefs
        svg.setAttributeNS('http://www.w3.org/2000/xmlns/', 'xmlns:xlink', 'http://www.w3.org/1999/xlink');

        // Add document metadata
        const docProps = {
            id: this.id,
            name: this.name,
            icon: this.icon,
            color: this.color,
            dpi: this.dpi,
            foregroundColor: this.foregroundColor,
            backgroundColor: this.backgroundColor,
            activeLayerIndex: this.layerStack.activeLayerIndex,
            viewState: {
                zoom: this.zoom,
                panX: this.panX,
                panY: this.panY
            }
        };
        const metadata = createDocumentMetadata(xmlDoc, docProps);
        svg.appendChild(metadata);

        // Build layer elements in reverse order (bottom-to-top for SVG paint order)
        // In our layerStack, index 0 is TOP, so we need to reverse for SVG rendering
        const layers = this.layerStack.layers;

        // First, build a map of parent ID to children for groups
        const childrenByParent = new Map();
        for (const layer of layers) {
            if (layer.parentId) {
                if (!childrenByParent.has(layer.parentId)) {
                    childrenByParent.set(layer.parentId, []);
                }
                childrenByParent.get(layer.parentId).push(layer);
            }
        }

        // Recursive function to convert layer and its children
        const convertLayer = async (layer) => {
            if (layer.isGroup && layer.isGroup()) {
                // Get children of this group
                const children = childrenByParent.get(layer.id) || [];
                const childElements = [];
                // Process children in reverse order (bottom to top)
                for (let i = children.length - 1; i >= 0; i--) {
                    const childEl = await convertLayer(children[i]);
                    if (childEl) childElements.push(childEl);
                }
                return layer.toSVGElement(xmlDoc, childElements);
            } else {
                return layer.toSVGElement(xmlDoc);
            }
        };

        // Process root-level layers (those without parentId) in reverse order
        const rootLayers = layers.filter(l => !l.parentId);
        for (let i = rootLayers.length - 1; i >= 0; i--) {
            const layerEl = await convertLayer(rootLayers[i]);
            if (layerEl) {
                svg.appendChild(layerEl);
            }
        }

        // Replace the document element with our constructed SVG
        const oldRoot = xmlDoc.documentElement;
        if (oldRoot && oldRoot.parentNode) {
            oldRoot.parentNode.replaceChild(svg, oldRoot);
        } else {
            xmlDoc.appendChild(svg);
        }

        return serializeXML(xmlDoc);
    }

    /**
     * Create a Document from an SVG string with Stagforge metadata.
     *
     * @param {string} svgString - SVG document string
     * @param {Object} eventBus - Event bus for the document
     * @returns {Promise<Document>} Restored document
     */
    static async fromSVG(svgString, eventBus) {
        const {
            isStagforgeSVG,
            parseSVG,
            getDocumentMetadata,
            getLayerGroups,
            getLayerType,
            getLayerName,
            getPropertiesElement,
            stagforgeXMLToJSON,
            getImageElement,
            getInnerSVGContent,
            STAGFORGE_NAMESPACE
        } = await import('./svgExportUtils.js');

        // Validate that this is a Stagforge SVG
        if (!isStagforgeSVG(svgString)) {
            throw new Error('Not a Stagforge SVG document');
        }

        // Parse the SVG
        const xmlDoc = parseSVG(svgString);
        const svgRoot = xmlDoc.documentElement;

        // Get document dimensions
        const width = parseInt(svgRoot.getAttribute('width')) || 800;
        const height = parseInt(svgRoot.getAttribute('height')) || 600;

        // Get document metadata
        const docMeta = getDocumentMetadata(xmlDoc) || {};

        // Create the document
        const doc = new Document({
            width,
            height,
            name: docMeta.name || 'Imported',
            icon: docMeta.icon || '🎨',
            color: docMeta.color || '#E0E7FF',
            eventBus
        });

        // Restore document properties
        if (docMeta.id) doc.id = docMeta.id;
        doc.dpi = docMeta.dpi || 72;
        doc.foregroundColor = docMeta.foregroundColor || '#000000';
        doc.backgroundColor = docMeta.backgroundColor || '#FFFFFF';

        // Restore view state
        if (docMeta.viewState) {
            doc.zoom = docMeta.viewState.zoom || 1.0;
            doc.panX = docMeta.viewState.panX || 0;
            doc.panY = docMeta.viewState.panY || 0;
        }

        // Get all layer groups
        const layerGroups = getLayerGroups(xmlDoc);

        // Clear default layer
        doc.layerStack.layers = [];

        // Recursive function to parse a layer group element
        const parseLayerGroup = async (groupEl, parentId = null) => {
            const type = getLayerType(groupEl);
            const name = getLayerName(groupEl) || 'Layer';
            const id = groupEl.getAttribute('id');

            // Get properties
            const propsEl = getPropertiesElement(groupEl);
            const props = propsEl ? stagforgeXMLToJSON(propsEl) : {};

            // Override parentId from the current context
            props.parentId = parentId;
            if (id) props.id = id;

            let layer;

            if (type === 'group') {
                // Import LayerGroup and use its deserialize method
                const { LayerGroup } = await import('./LayerGroup.js');

                // Use deserialize for unified property handling
                layer = LayerGroup.deserialize({
                    ...props,
                    name: props.name || name,
                    parentId: parentId
                });

                // Add the group to layers first
                doc.layerStack.layers.push(layer);

                // Parse child layers (direct children of this group element with sf:type)
                for (const child of groupEl.children) {
                    if (child.namespaceURI === STAGFORGE_NAMESPACE) continue; // Skip sf:properties
                    if (child.tagName === 'g' && child.getAttributeNS(STAGFORGE_NAMESPACE, 'type')) {
                        await parseLayerGroup(child, layer.id);
                    }
                }

                return; // Group is already added
            }

            if (type === 'raster') {
                // Import PixelLayer and use its deserialize method for unified serialization
                const { PixelLayer } = await import('./PixelLayer.js');
                const imageEl = getImageElement(groupEl);

                // Get image data URL from embedded image element
                let imageData = null;
                if (imageEl) {
                    imageData = imageEl.getAttribute('href') || imageEl.getAttributeNS('http://www.w3.org/1999/xlink', 'href');
                }

                // Use deserialize for unified property handling
                layer = await PixelLayer.deserialize({
                    ...props,
                    name: props.name || name,
                    parentId: parentId,
                    imageData: imageData || props.imageData
                });
            }

            if (type === 'text') {
                // Import TextLayer and use its deserialize method
                const { TextLayer } = await import('./TextLayer.js');

                // Map x/y to offsetX/offsetY if needed
                const textProps = {
                    ...props,
                    name: props.name || name,
                    parentId: parentId,
                    offsetX: props.offsetX ?? props.x ?? 0,
                    offsetY: props.offsetY ?? props.y ?? 0
                };

                // Use deserialize for unified property handling
                layer = await TextLayer.deserialize(textProps);
            }

            if (type === 'svg') {
                // Import StaticSVGLayer and use its deserialize method
                const { StaticSVGLayer } = await import('./StaticSVGLayer.js');
                const { debakeSVGContent } = await import('./svgExportUtils.js');

                // "Debake" - extract the original SVG from the transform envelope
                // The SVG is stored only once in the visual representation, not duplicated in properties
                const svgContent = debakeSVGContent(groupEl) || props.svgData || props.svgContent || '';

                const svgProps = {
                    ...props,
                    name: props.name || name,
                    parentId: parentId,
                    svgContent: svgContent
                };

                // Use deserialize for unified property handling
                layer = await StaticSVGLayer.deserialize(svgProps);
            }

            if (layer) {
                doc.layerStack.layers.push(layer);
            }
        };

        // Parse all root layer groups (those directly under SVG root)
        // They are in SVG order (bottom to top), but we want them in our order (top to bottom)
        // So we need to reverse them when adding
        const rootGroups = [];
        for (const groupEl of layerGroups) {
            rootGroups.push(groupEl);
        }

        // Parse in SVG order, which adds layers bottom-to-top
        // We reverse at the end to get our top-to-bottom order
        for (const groupEl of rootGroups) {
            await parseLayerGroup(groupEl, null);
        }

        // Reverse layers to match our internal order (index 0 = top)
        doc.layerStack.layers.reverse();

        // Restore active layer index
        const activeIndex = docMeta.activeLayerIndex ?? 0;
        doc.layerStack.activeLayerIndex = Math.min(activeIndex, doc.layerStack.layers.length - 1);

        return doc;
    }

    /**
     * Convert Uint8Array to base64 string.
     * @private
     */
    _uint8ArrayToBase64(uint8Array) {
        let binary = '';
        const len = uint8Array.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(uint8Array[i]);
        }
        return btoa(binary);
    }

    /**
     * Convert base64 string to Uint8Array.
     * @private
     */
    static _base64ToUint8Array(base64) {
        const binary = atob(base64);
        const len = binary.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    }

    /**
     * Export document state for serialization.
     */
    async serialize() {
        const layers = [];
        for (const layer of this.layerStack.layers) {
            layers.push(layer.serialize());
        }

        // Serialize saved selections (convert Uint8Array to base64)
        const savedSelections = (this.savedSelections || []).map(sel => ({
            name: sel.name,
            width: sel.width,
            height: sel.height,
            mask: this._uint8ArrayToBase64(sel.mask)
        }));

        return {
            _version: Document.VERSION,
            _type: 'Document',
            id: this.id,
            name: this.name,
            icon: this.icon,
            color: this.color,
            width: this.width,
            height: this.height,
            dpi: this.dpi,
            foregroundColor: this.foregroundColor,
            backgroundColor: this.backgroundColor,
            activeLayerIndex: this.layerStack.activeLayerIndex,
            layers: layers,
            savedSelections: savedSelections,
            viewState: {
                zoom: this.zoom,
                panX: this.panX,
                panY: this.panY
            },
            changeCounter: this.changeCounter,
            lastChangeTimestamp: this.lastChangeTimestamp,
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
            icon: data.icon,
            color: data.color,
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
            // Use registry for polymorphic deserialization
            const layer = await layerRegistry.deserialize(layerData);
            doc.layerStack.layers.push(layer);
        }

        doc.layerStack.activeLayerIndex = data.activeLayerIndex || 0;

        // Restore saved selections (convert base64 back to Uint8Array)
        if (data.savedSelections && Array.isArray(data.savedSelections)) {
            doc.savedSelections = data.savedSelections.map(sel => ({
                name: sel.name,
                width: sel.width,
                height: sel.height,
                mask: Document._base64ToUint8Array(sel.mask)
            }));
        }

        // Restore change tracking
        doc.changeCounter = data.changeCounter ?? 0;
        doc.lastChangeTimestamp = data.lastChangeTimestamp ?? Date.now();

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
