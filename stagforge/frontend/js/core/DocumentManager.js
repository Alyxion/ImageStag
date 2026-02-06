/**
 * DocumentManager - Manages multiple open documents.
 *
 * Handles:
 * - Creating/opening/closing documents
 * - Switching between active document
 * - Document tabs state
 * - Prompting for unsaved changes
 */
import { Document } from './Document.js';
import { generateDocumentIdentity } from '../utils/DocumentNameGenerator.js';

export class DocumentManager {
    /**
     * @param {Object} app - Application context
     */
    constructor(app) {
        this.app = app;
        this.documents = [];
        this.activeDocumentId = null;
        this.maxDocuments = 20;  // Limit to prevent memory issues

        // Subscribe to global events
        if (app.eventBus) {
            // Forward document events to main event bus
            app.eventBus.on('document:activate', (data) => {
                this.setActiveDocument(data.documentId);
            });
        }
    }

    /**
     * Get the currently active document.
     * @returns {Document|null}
     */
    getActiveDocument() {
        return this.documents.find(d => d.id === this.activeDocumentId) || null;
    }

    /**
     * Get a document by ID.
     * @param {string} id
     * @returns {Document|null}
     */
    getDocumentById(id) {
        return this.documents.find(d => d.id === id) || null;
    }

    /**
     * Create a new document.
     * @param {Object} options
     * @param {number} [options.width=800]
     * @param {number} [options.height=600]
     * @param {string} [options.name]
     * @param {string} [options.icon]
     * @param {string} [options.color]
     * @param {boolean} [options.activate=true]
     * @param {boolean} [options.empty=false] - If true, create document with no layers
     * @returns {Document}
     */
    createDocument(options = {}) {
        if (this.documents.length >= this.maxDocuments) {
            throw new Error(`Maximum number of documents (${this.maxDocuments}) reached`);
        }

        // Generate identity if not all provided
        const identity = this.generateNewDocumentIdentity();

        const doc = new Document({
            width: options.width || 800,
            height: options.height || 600,
            name: options.name || identity.name,
            icon: options.icon || identity.icon,
            color: options.color || identity.color,
            eventBus: this.createDocumentEventBus()
        });

        // Create initial background layer unless empty mode
        if (!options.empty) {
            const bgLayer = doc.createLayer({ name: 'Background' }, { atBottom: true });
            bgLayer.fillArea('#FFFFFF', 0, 0, doc.width, doc.height);
        }

        this.documents.push(doc);

        // Activate by default
        if (options.activate !== false) {
            this.setActiveDocument(doc.id, { isNewDocument: true });
        }

        this.app.eventBus?.emit('document:created', { document: doc });
        this.emitDocumentsChanged();

        return doc;
    }

    /**
     * Add an existing document to the manager.
     * Used for loading documents from files.
     * @param {Document} doc - The document to add
     */
    addDocument(doc) {
        if (this.documents.length >= this.maxDocuments) {
            throw new Error(`Maximum number of documents (${this.maxDocuments}) reached`);
        }

        // Ensure document has an event bus
        if (!doc.eventBus) {
            doc.eventBus = this.createDocumentEventBus();
        }

        this.documents.push(doc);
        this.app.eventBus?.emit('document:loaded', { document: doc });
        this.emitDocumentsChanged();
    }

    /**
     * Create an event bus that forwards to the main app event bus.
     */
    createDocumentEventBus() {
        const self = this;
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
                // Local listeners
                if (listeners.has(event)) {
                    for (const cb of listeners.get(event)) {
                        cb(data);
                    }
                }
                // Forward to app event bus with document context
                self.app.eventBus?.emit(event, { ...data, fromDocument: true });
            }
        };
    }

    /**
     * Generate a unique identity for a new document.
     * Uses memorable art-themed names like "Velvet Sunset" with matching icon and color.
     * @returns {{name: string, icon: string, color: string}}
     */
    generateNewDocumentIdentity() {
        const existingNames = new Set(this.documents.map(d => d.name));
        const maxAttempts = 100;

        for (let i = 0; i < maxAttempts; i++) {
            const identity = generateDocumentIdentity();
            if (!existingNames.has(identity.name)) {
                return identity;
            }
        }

        // Fallback if we can't find a unique name (very unlikely with 28,000+ combinations)
        let index = 1;
        let name = 'Untitled';
        while (existingNames.has(name)) {
            name = `Untitled ${index}`;
            index++;
        }
        return { name, icon: '🎨', color: '#E0E7FF' };
    }

    /**
     * Set the active document.
     * @param {string} documentId
     * @param {Object} [options]
     * @param {boolean} [options.isNewDocument=false] - Whether this is a newly created document
     */
    setActiveDocument(documentId, options = {}) {
        const doc = this.getDocumentById(documentId);
        if (!doc) {
            console.warn(`Document ${documentId} not found`);
            return;
        }

        const previousDoc = this.getActiveDocument();
        if (previousDoc?.id === documentId) return;

        // Save view state of previous document
        if (previousDoc && this.app.renderer) {
            previousDoc.zoom = this.app.renderer.zoom;
            previousDoc.panX = this.app.renderer.panX;
            previousDoc.panY = this.app.renderer.panY;
        }

        this.activeDocumentId = documentId;

        // Update app context to point to new document
        this.updateAppContext(doc, options.isNewDocument || false);

        this.app.eventBus?.emit('document:activated', {
            document: doc,
            previousDocument: previousDoc
        });
        this.emitDocumentsChanged();
    }

    /**
     * Update the app context to use the active document.
     * @param {Document} doc
     * @param {boolean} isNewDocument - Whether this is a newly created document
     */
    updateAppContext(doc, isNewDocument = false) {
        if (!this.app) return;

        // Update app references
        this.app.layerStack = doc.layerStack;
        this.app.history = doc.history;
        this.app.width = doc.width;
        this.app.height = doc.height;
        this.app.canvasWidth = doc.width;
        this.app.canvasHeight = doc.height;
        this.app.foregroundColor = doc.foregroundColor;
        this.app.backgroundColor = doc.backgroundColor;

        // Update history's app reference so it can access renderer
        if (doc.history) {
            doc.history.app = this.app;
        }

        // Update renderer
        if (this.app.renderer) {
            this.app.renderer.layerStack = doc.layerStack;
            this.app.renderer.resize(doc.width, doc.height);

            // For new documents, fit to viewport; otherwise restore saved view state
            if (isNewDocument || (doc.zoom === 1.0 && doc.panX === 0 && doc.panY === 0)) {
                this.app.renderer.fitToViewport();
                // Save the fitted view state back to document
                doc.zoom = this.app.renderer.zoom;
                doc.panX = this.app.renderer.panX;
                doc.panY = this.app.renderer.panY;
            } else {
                this.app.renderer.zoom = doc.zoom;
                this.app.renderer.panX = doc.panX;
                this.app.renderer.panY = doc.panY;
                this.app.renderer.updateDynamicLayerScale();
            }
            this.app.renderer.requestRender();
        }
    }

    /**
     * Close a document.
     * @param {string} documentId
     * @param {boolean} [force=false] - Close without prompting for unsaved changes
     * @returns {boolean} - Whether the document was closed
     */
    closeDocument(documentId, force = false) {
        const doc = this.getDocumentById(documentId);
        if (!doc) return false;

        // Check for unsaved changes
        if (!force && doc.modified) {
            // Emit event to let UI show confirmation dialog
            this.app.eventBus?.emit('document:close-requested', {
                document: doc,
                callback: (confirmed) => {
                    if (confirmed) {
                        this.forceCloseDocument(documentId);
                    }
                }
            });
            return false;
        }

        return this.forceCloseDocument(documentId);
    }

    /**
     * Force close a document without prompting.
     * @param {string} documentId
     * @returns {boolean}
     */
    forceCloseDocument(documentId) {
        const idx = this.documents.findIndex(d => d.id === documentId);
        if (idx === -1) return false;

        const doc = this.documents[idx];

        // Save to global document storage before closing
        if (this.app.documentStorage) {
            this.app.documentStorage.saveDocument(doc).catch(err => {
                console.warn('[DocumentManager] Failed to save document to storage:', err);
            });
        }

        // If closing active document, switch to another or set to null
        if (this.activeDocumentId === documentId) {
            if (this.documents.length > 1) {
                // Switch to next or previous document
                const newIdx = idx < this.documents.length - 1 ? idx + 1 : idx - 1;
                this.setActiveDocument(this.documents[newIdx].id);
            } else {
                // Last document being closed - set to null (empty state)
                this.activeDocumentId = null;
                // Update app references to reflect empty state
                if (this.app) {
                    this.app.layerStack = null;
                    this.app.history = null;
                    if (this.app.renderer) {
                        this.app.renderer.layerStack = null;
                        this.app.renderer.requestRender();
                    }
                    // Clear auto-save data since user explicitly closed all documents
                    if (this.app.autoSave) {
                        this.app.autoSave.clear();
                    }
                }
                this.app.eventBus?.emit('document:changed', { document: null });
            }
        }

        // Remove and dispose
        this.documents.splice(idx, 1);
        doc.dispose();

        this.app.eventBus?.emit('document:closed', { documentId });
        this.emitDocumentsChanged();

        return true;
    }

    /**
     * Close all documents.
     * @param {boolean} [force=false]
     */
    closeAllDocuments(force = false) {
        const docs = [...this.documents];
        for (const doc of docs) {
            this.closeDocument(doc.id, force);
        }
    }

    /**
     * Check if any document has unsaved changes.
     */
    hasUnsavedChanges() {
        return this.documents.some(d => d.modified);
    }

    /**
     * Get list of documents for UI.
     */
    getDocumentList() {
        return this.documents.map(doc => ({
            id: doc.id,
            name: doc.name,
            icon: doc.icon,
            color: doc.color,
            displayName: doc.displayName,
            modified: doc.modified,
            width: doc.width,
            height: doc.height,
            isActive: doc.id === this.activeDocumentId
        }));
    }

    /**
     * Emit documents changed event.
     */
    emitDocumentsChanged() {
        this.app.eventBus?.emit('documents:changed', {
            documents: this.getDocumentList(),
            activeDocumentId: this.activeDocumentId
        });
    }

    /**
     * Move document tab.
     * @param {number} fromIndex
     * @param {number} toIndex
     */
    reorderDocument(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= this.documents.length) return;
        if (toIndex < 0 || toIndex >= this.documents.length) return;

        const [doc] = this.documents.splice(fromIndex, 1);
        this.documents.splice(toIndex, 0, doc);

        this.emitDocumentsChanged();
    }

    /**
     * Duplicate a document.
     * @param {string} documentId
     * @returns {Document}
     */
    async duplicateDocument(documentId) {
        const source = this.getDocumentById(documentId);
        if (!source) return null;

        const serialized = await source.serialize();
        serialized.id = crypto.randomUUID();
        serialized.name = `${source.name} (copy)`;

        const duplicate = await Document.deserialize(serialized, this.createDocumentEventBus());
        this.documents.push(duplicate);
        this.setActiveDocument(duplicate.id);

        this.app.eventBus?.emit('document:created', { document: duplicate });
        this.emitDocumentsChanged();

        return duplicate;
    }
}
