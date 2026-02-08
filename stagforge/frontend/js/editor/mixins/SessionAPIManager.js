/**
 * SessionAPIManager Mixin
 *
 * Handles Session API methods for Python integration:
 * - emitStateUpdate: Emit editor state to Python
 * - executeCommand: Execute commands from Python
 * - executeToolAction: Execute tool actions from Python
 * - Config API: getConfig, setConfig
 * - Layer Effects API: getLayerEffects, addLayerEffect, updateLayerEffect, removeLayerEffect
 *
 * Required component data:
 *   - docWidth: Number
 *   - docHeight: Number
 *   - fgColor: String
 *   - bgColor: String
 *   - zoom: Number
 *   - recentColors: Array
 *   - currentToolId: String
 *   - toolProperties: Array
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateLayerList(): Refreshes the layers panel
 *   - Various tool/layer methods
 */
import { CanvasEvent } from '/static/js/core/CanvasEvent.js';

export const SessionAPIManagerMixin = {
    methods: {
        /**
         * Emit state to Python for session tracking (multi-document format).
         * Uses WebSocket bridge if available, falls back to Vue $emit for NiceGUI.
         */
        emitStateUpdate() {
            // Use bridge if available (preferred method)
            if (this._bridge?.isConnected) {
                this.emitStateUpdateViaBridge();
                return;
            }

            // Fallback to Vue $emit for NiceGUI compatibility
            const app = this.getState();
            if (!app?.documentManager) return;

            // Build documents array from documentManager
            const documents = app.documentManager.documents.map(doc => ({
                id: doc.id,
                name: doc.name,
                width: doc.width,
                height: doc.height,
                active_layer_id: doc.layerStack?.layers[doc.layerStack.activeLayerIndex]?.id || null,
                is_modified: doc.isModified || false,
                created_at: doc.createdAt?.toISOString() || new Date().toISOString(),
                modified_at: doc.modifiedAt?.toISOString() || new Date().toISOString(),
                layers: doc.layerStack?.layers.map(layer => ({
                    id: layer.id,
                    name: layer.name,
                    type: layer.isGroup?.() ? 'group' : (layer.isVector?.() ? 'vector' : (layer.isText?.() ? 'text' : 'raster')),
                    visible: layer.visible,
                    locked: layer.locked,
                    opacity: layer.opacity,
                    blendMode: layer.blendMode,
                    width: layer.width || 0,
                    height: layer.height || 0,
                    offsetX: layer.offsetX || 0,
                    offsetY: layer.offsetY || 0,
                    parentId: layer.parentId || null,
                    // Transform properties
                    rotation: layer.rotation || 0,
                    scaleX: layer.scaleX ?? 1,
                    scaleY: layer.scaleY ?? 1,
                })) || [],
            }));

            const activeDoc = app.documentManager.getActiveDocument();

            this.$emit('state-update', {
                active_document_id: activeDoc?.id || null,
                documents: documents,
                active_tool: this.currentToolId,
                tool_properties: this.toolProperties.reduce((acc, p) => { acc[p.id] = p.value; return acc; }, {}),
                foreground_color: this.fgColor,
                background_color: this.bgColor,
                zoom: this.zoom,
                recent_colors: this.recentColors,
            });
        },

        /**
         * Execute editor commands from Python
         * @param {string} command - Command name
         * @param {Object} params - Command parameters
         * @returns {Object} Result with success/error
         */
        async executeCommand(command, params = {}) {
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                switch (command) {
                    case 'undo':
                        app.history.undo();
                        break;
                    case 'redo':
                        app.history.redo();
                        break;
                    case 'new_layer':
                        this.addLayer();
                        break;
                    case 'delete_layer':
                        this.deleteLayer();
                        break;
                    case 'duplicate_layer':
                        this.duplicateLayer();
                        break;
                    case 'merge_down':
                        this.mergeDown();
                        break;
                    case 'flatten':
                        app.history.saveState('Flatten Image');
                        app.layerStack.flattenAll();
                        app.history.finishState();
                        this.updateLayerList();
                        break;
                    case 'set_foreground_color':
                        if (params.color) this.setForegroundColor(params.color);
                        break;
                    case 'set_background_color':
                        if (params.color) this.setBackgroundColor(params.color);
                        break;
                    case 'select_tool':
                        if (params.tool_id) this.selectTool(params.tool_id);
                        break;
                    case 'apply_filter':
                        if (params.filter_id) this.applyFilter(params.filter_id, params.params || {});
                        break;
                    case 'new_document':
                        if (params.width && params.height) this.newDocument(params.width, params.height);
                        break;
                    // Selection commands
                    case 'select_all':
                        this.selectAll();
                        break;
                    case 'deselect':
                        this.deselect();
                        break;
                    case 'delete_selection':
                        this.deleteSelection();
                        break;
                    // Clipboard commands
                    case 'copy':
                        return { success: this.clipboardCopy() };
                    case 'copy_merged':
                        return { success: this.clipboardCopyMerged() };
                    case 'cut':
                        return { success: this.clipboardCut() };
                    case 'paste':
                        return { success: this.clipboardPaste() };
                    case 'paste_in_place':
                        return { success: this.clipboardPasteInPlace() };
                    // Browser storage (OPFS) commands - per-session auto-save
                    case 'list_stored_documents':
                        return this.listStoredDocuments();
                    case 'clear_stored_documents':
                        return this.clearStoredDocuments();
                    case 'delete_stored_document':
                        return this.deleteStoredDocument(params.document_id);
                    // Global document storage commands
                    case 'list_global_documents':
                        return await this.listGlobalDocuments();
                    case 'get_global_storage_stats':
                        return await this.getGlobalStorageStats();
                    case 'get_global_document_metadata':
                        return await this.getGlobalDocumentMetadata(params.document_id);
                    case 'get_global_document_thumbnail':
                        return await this.getGlobalDocumentThumbnail(params.document_id);
                    case 'delete_global_document':
                        return await this.deleteGlobalDocument(params.document_id);
                    case 'clear_global_documents':
                        return await this.clearGlobalDocuments();
                    case 'load_global_document':
                        return await this.loadGlobalDocument(params.document_id);
                    case 'load_from_queue':
                        return await this.loadFromUploadQueue(params.queue_id);
                    // Change tracking command
                    case 'get_document_changes':
                        return this.getDocumentChanges(params.document_id);
                    // Layer import command
                    case 'import_layer':
                        return this.importLayer(params);
                    // Layer update command
                    case 'update_layer':
                        return this.updateLayerProperties(params);
                    default:
                        return { success: false, error: `Unknown command: ${command}` };
                }
                return { success: true };
            } catch (e) {
                return { success: false, error: e.message };
            }
        },

        /**
         * Execute tool actions from Python
         * @param {string} toolId - Tool identifier
         * @param {string} action - Action name
         * @param {Object} params - Action parameters
         * @returns {Object} Result with success/error
         */
        executeToolAction(toolId, action, params = {}) {
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            const tool = app.toolManager.tools.get(toolId);
            if (!tool) return { success: false, error: `Tool not found: ${toolId}` };

            try {
                // Select the tool first if not already selected
                if (app.toolManager.currentTool !== tool) {
                    app.toolManager.select(toolId);
                }

                // If the tool has its own executeAction, use it
                if (tool.executeAction) {
                    const result = tool.executeAction(action, params);
                    if (result) {
                        this.emitStateUpdate();
                        return result;
                    }
                }

                // Fallback: Execute the action based on generic patterns
                const layer = app.layerStack.getActiveLayer();
                if (!layer) return { success: false, error: 'No active layer' };

                switch (action) {
                    case 'stroke':
                        // Draw a stroke along points
                        if (!params.points || params.points.length < 2) {
                            return { success: false, error: 'Need at least 2 points for stroke' };
                        }
                        const points = params.points;
                        // Simulate mouse events for the tool using CanvasEvent
                        tool.onMouseDown(CanvasEvent.fromLayerCoords(points[0][0], points[0][1], layer));
                        for (let i = 1; i < points.length; i++) {
                            tool.onMouseMove(CanvasEvent.fromLayerCoords(points[i][0], points[i][1], layer));
                        }
                        tool.onMouseUp(CanvasEvent.fromLayerCoords(points[points.length-1][0], points[points.length-1][1], layer));
                        break;

                    case 'fill':
                        // Flood fill at a point
                        if (params.point) {
                            tool.onMouseDown(CanvasEvent.fromLayerCoords(params.point[0], params.point[1], layer));
                            tool.onMouseUp(CanvasEvent.fromLayerCoords(params.point[0], params.point[1], layer));
                        }
                        break;

                    case 'translate':
                        // Move layer directly (not using tool)
                        if (params.dx !== undefined && params.dy !== undefined) {
                            app.history.saveState('Move');
                            const ctx = layer.ctx;
                            const imageData = ctx.getImageData(0, 0, this.docWidth, this.docHeight);
                            ctx.clearRect(0, 0, this.docWidth, this.docHeight);
                            ctx.putImageData(imageData, params.dx, params.dy);
                            app.history.finishState();
                        }
                        break;

                    case 'draw':
                        // Draw shape - fallback for tools without executeAction
                        if (params.start && params.end) {
                            tool.onMouseDown(CanvasEvent.fromLayerCoords(params.start[0], params.start[1], layer));
                            tool.onMouseMove(CanvasEvent.fromLayerCoords(params.end[0], params.end[1], layer));
                            tool.onMouseUp(CanvasEvent.fromLayerCoords(params.end[0], params.end[1], layer));
                        }
                        break;

                    default:
                        return { success: false, error: `Unknown action: ${action}` };
                }

                this.emitStateUpdate();
                return { success: true };
            } catch (e) {
                return { success: false, error: e.message };
            }
        },

        /**
         * Get UIConfig value(s) for API access
         * @param {string} path - Config path or null for full config
         * @returns {*} Config value or full config object
         */
        getConfig(path) {
            try {
                if (path) {
                    return UIConfig.get(path);
                } else {
                    return JSON.parse(JSON.stringify(UIConfig.config));
                }
            } catch (e) {
                return { error: e.message };
            }
        },

        /**
         * Set UIConfig value for API access
         * @param {string} path - Config path
         * @param {*} value - Value to set
         * @returns {Object} Result with success/error
         */
        setConfig(path, value) {
            try {
                UIConfig.set(path, value);

                // Re-render dynamic layers if rendering settings changed
                if (path.startsWith('rendering.')) {
                    this.reRenderDynamicLayers();
                }

                return { success: true, path, value };
            } catch (e) {
                return { error: e.message };
            }
        },

        // ==================== Layer Effects API Methods ====================

        /**
         * Get all effects for a layer
         * @param {string} layerId - Layer ID
         * @returns {Array} Serialized effects
         */
        getLayerEffects(layerId) {
            const app = this.getState();
            if (!app) return [];

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return [];

                return layer.effects.map(e => e.serialize());
            } catch (e) {
                console.error('getLayerEffects error:', e);
                return [];
            }
        },

        /**
         * Add an effect to a layer
         * @param {string} layerId - Layer ID
         * @param {string} effectType - Effect type (e.g., 'dropShadow')
         * @param {Object} params - Effect parameters
         * @returns {Object} Result with effect info
         */
        addLayerEffect(layerId, effectType, params = {}) {
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return { success: false, error: 'Layer not found' };

                // Get effect class from registry via window.LayerEffects
                const LayerEffects = window.LayerEffects;
                const EffectClass = LayerEffects?.effectRegistry?.[effectType];
                if (!EffectClass) {
                    return { success: false, error: `Unknown effect type: ${effectType}` };
                }

                // Create effect instance
                const effect = new EffectClass(params);

                // Add to layer
                layer.addEffect(effect);

                // Update UI
                this.updateLayerList();

                return { success: true, effect_id: effect.id, effect: effect.serialize() };
            } catch (e) {
                console.error('addLayerEffect error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Update an effect's parameters
         * @param {string} layerId - Layer ID
         * @param {string} effectId - Effect ID
         * @param {Object} params - New parameters
         * @returns {Object} Result with updated effect
         */
        updateLayerEffect(layerId, effectId, params = {}) {
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return { success: false, error: 'Layer not found' };

                const effect = layer.getEffect(effectId);
                if (!effect) return { success: false, error: 'Effect not found' };

                // Update parameters
                layer.updateEffect(effectId, params);

                return { success: true, effect: effect.serialize() };
            } catch (e) {
                console.error('updateLayerEffect error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Remove an effect from a layer
         * @param {string} layerId - Layer ID
         * @param {string} effectId - Effect ID
         * @returns {Object} Result with success/error
         */
        removeLayerEffect(layerId, effectId) {
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return { success: false, error: 'Layer not found' };

                const removed = layer.removeEffect(effectId);
                if (!removed) return { success: false, error: 'Effect not found' };

                // Update UI
                this.updateLayerList();

                return { success: true };
            } catch (e) {
                console.error('removeLayerEffect error:', e);
                return { success: false, error: e.message };
            }
        },

        // ==================== Browser Storage (OPFS) API Methods ====================

        /**
         * List all documents stored in OPFS browser storage
         * @returns {Object} Result with storage info
         */
        async listStoredDocuments() {
            const app = this.getState();
            if (!app?.autoSave) {
                return { success: false, error: 'AutoSave not initialized' };
            }

            try {
                const autoSave = app.autoSave;
                if (!autoSave.tabDir) {
                    return { success: true, result: { documents: [], files: [], tabId: null } };
                }

                // Load manifest
                const manifest = await autoSave.loadManifest();

                // List all files
                const files = [];
                for await (const entry of autoSave.tabDir.values()) {
                    if (entry.kind === 'file') {
                        try {
                            const file = await entry.getFile();
                            files.push({
                                name: entry.name,
                                size: file.size,
                                lastModified: file.lastModified,
                                lastModifiedDate: new Date(file.lastModified).toISOString(),
                            });
                        } catch (e) {
                            files.push({ name: entry.name, error: e.message });
                        }
                    }
                }

                return {
                    success: true,
                    result: {
                        tabId: autoSave.tabId,
                        manifest: manifest,
                        documents: manifest?.documents || [],
                        files: files,
                        lastSavedState: Object.fromEntries(autoSave.lastSavedState),
                    }
                };
            } catch (e) {
                console.error('listStoredDocuments error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Clear all documents from OPFS browser storage
         * @returns {Object} Result with success/error
         */
        async clearStoredDocuments() {
            const app = this.getState();
            if (!app?.autoSave) {
                return { success: false, error: 'AutoSave not initialized' };
            }

            try {
                await app.autoSave.clear();
                return { success: true };
            } catch (e) {
                console.error('clearStoredDocuments error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Delete a specific document from OPFS browser storage
         * @param {string} documentId - Document ID to delete
         * @returns {Object} Result with success/error
         */
        async deleteStoredDocument(documentId) {
            const app = this.getState();
            if (!app?.autoSave) {
                return { success: false, error: 'AutoSave not initialized' };
            }

            try {
                const autoSave = app.autoSave;
                if (!autoSave.tabDir) {
                    return { success: false, error: 'Storage not available' };
                }

                // Delete the document file
                const fileName = `doc_${documentId}.sfr`;
                try {
                    await autoSave.tabDir.removeEntry(fileName);
                } catch (e) {
                    if (e.name !== 'NotFoundError') {
                        throw e;
                    }
                }

                // Update manifest to remove the document
                const manifest = await autoSave.loadManifest();
                if (manifest) {
                    manifest.documents = manifest.documents.filter(d => d.id !== documentId);
                    await autoSave.saveManifest(manifest);
                }

                // Remove from lastSavedState
                autoSave.lastSavedState.delete(documentId);

                return { success: true };
            } catch (e) {
                console.error('deleteStoredDocument error:', e);
                return { success: false, error: e.message };
            }
        },

        // === Global Document Storage Methods ===

        /**
         * List all documents in global storage (shared across tabs).
         * @returns {Object} Result with documents, manifest, files, and stats
         */
        async listGlobalDocuments() {
            const app = this.getState();
            if (!app?.documentStorage) {
                return { success: false, error: 'DocumentStorage not initialized' };
            }

            try {
                const storage = app.documentStorage;
                await storage.ensureInitialized();

                // Get manifest
                const manifest = await storage.loadManifest();

                // List all files in storage
                const files = [];
                if (storage.rootDir) {
                    for await (const entry of storage.rootDir.values()) {
                        if (entry.kind === 'file') {
                            try {
                                const fileHandle = await storage.rootDir.getFileHandle(entry.name);
                                const file = await fileHandle.getFile();
                                files.push({
                                    name: entry.name,
                                    size: file.size,
                                    lastModified: file.lastModified,
                                    lastModifiedDate: new Date(file.lastModified).toISOString(),
                                });
                            } catch (e) {
                                files.push({ name: entry.name, error: e.message });
                            }
                        }
                    }
                }

                // Also include currently open documents
                const openDocuments = [];
                if (app.documentManager) {
                    for (const doc of app.documentManager.documents.values()) {
                        openDocuments.push({
                            id: doc.id,
                            name: doc.name,
                            width: doc.width,
                            height: doc.height,
                            layerCount: doc.layerStack?.layers?.length || 0,
                            isModified: doc.isModified || false,
                            isActive: doc.id === app.documentManager.activeDocumentId,
                        });
                    }
                }

                return {
                    success: true,
                    result: {
                        manifest: manifest,
                        documents: manifest?.documents || [],
                        files: files,
                        openDocuments: openDocuments,
                        isInitialized: storage.isInitialized,
                    }
                };
            } catch (e) {
                console.error('listGlobalDocuments error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Get storage statistics for global document storage.
         * @returns {Object} Result with storage stats
         */
        async getGlobalStorageStats() {
            const app = this.getState();
            if (!app?.documentStorage) {
                return { success: false, error: 'DocumentStorage not initialized' };
            }

            try {
                const stats = await app.documentStorage.getStorageStats();
                return { success: true, result: stats };
            } catch (e) {
                console.error('getGlobalStorageStats error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Get metadata for a specific document in global storage.
         * @param {string} documentId - Document ID
         * @returns {Object} Result with document metadata
         */
        async getGlobalDocumentMetadata(documentId) {
            const app = this.getState();
            if (!app?.documentStorage) {
                return { success: false, error: 'DocumentStorage not initialized' };
            }

            try {
                const manifest = await app.documentStorage.loadManifest();
                const docMeta = manifest?.documents?.find(d => d.id === documentId);

                if (!docMeta) {
                    return { success: false, error: `Document not found: ${documentId}` };
                }

                return { success: true, result: docMeta };
            } catch (e) {
                console.error('getGlobalDocumentMetadata error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Get thumbnail for a specific document in global storage.
         * @param {string} documentId - Document ID
         * @returns {Object} Result with base64 thumbnail
         */
        async getGlobalDocumentThumbnail(documentId) {
            const app = this.getState();
            if (!app?.documentStorage) {
                return { success: false, error: 'DocumentStorage not initialized' };
            }

            try {
                const thumbnailDataUrl = await app.documentStorage.getDocumentThumbnail(documentId);

                if (!thumbnailDataUrl) {
                    return { success: false, error: `Thumbnail not found for: ${documentId}` };
                }

                return { success: true, result: { dataUrl: thumbnailDataUrl } };
            } catch (e) {
                console.error('getGlobalDocumentThumbnail error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Delete a document from global storage.
         * @param {string} documentId - Document ID
         * @returns {Object} Result with success/error
         */
        async deleteGlobalDocument(documentId) {
            const app = this.getState();
            if (!app?.documentStorage) {
                return { success: false, error: 'DocumentStorage not initialized' };
            }

            try {
                const deleted = await app.documentStorage.deleteDocument(documentId);
                return { success: deleted };
            } catch (e) {
                console.error('deleteGlobalDocument error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Clear all documents from global storage.
         * @returns {Object} Result with count of deleted documents
         */
        async clearGlobalDocuments() {
            const app = this.getState();
            if (!app?.documentStorage) {
                return { success: false, error: 'DocumentStorage not initialized' };
            }

            try {
                const count = await app.documentStorage.deleteAllDocuments();
                return { success: true, result: { deletedCount: count } };
            } catch (e) {
                console.error('clearGlobalDocuments error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Load a document from the upload queue (temporary API storage).
         * @param {string} queueId - Queue ID from upload endpoint
         * @returns {Object} Result with new document info
         */
        async loadFromUploadQueue(queueId) {
            const app = this.getState();
            if (!app?.documentManager) {
                throw new Error('DocumentManager not initialized');
            }

            try {
                // Fetch SFR from API queue
                const response = await fetch(`/api/upload/queue/${queueId}`);
                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.detail || `Failed to fetch document: ${response.status}`);
                }

                // Get SFR as blob
                const blob = await response.blob();
                const docName = response.headers.get('X-Document-Name') || 'Uploaded Document';

                // Create a File object for FileManager
                const file = new File([blob], `${docName}.sfr`, { type: 'application/zip' });

                // Use FileManager to parse and load the SFR
                const { parseDocumentZip, processLayerImages } = await import('/static/js/core/FileManager.js');
                const { data, layerImages } = await parseDocumentZip(file);

                // Process layer images (convert blobs to data URLs)
                await processLayerImages(data, layerImages);

                // Build docData: merge pages (v3) or layers (v1/v2) into document
                const docData = data.document;
                if (data.pages && !docData.pages) docData.pages = data.pages;
                if (data.layers && !docData.layers && !docData.pages) docData.layers = data.layers;

                // Deserialize document (creates new instance with new UUID)
                const { Document } = await import('/static/js/core/Document.js');
                const doc = await Document.deserialize(docData, app.eventBus);

                // Add to document manager and make active
                app.documentManager.addDocument(doc);
                app.documentManager.setActiveDocument(doc.id);

                // Update renderer
                app.renderer.resize(doc.width, doc.height);
                app.renderer.fitToViewport();
                app.renderer.requestRender();

                // Emit state update
                this.emitStateUpdate();

                // Return just the document info - Python bridge wraps in {success, result}
                return {
                    id: doc.id,
                    name: doc.name,
                    width: doc.width,
                    height: doc.height,
                    layerCount: doc.layerStack?.layers?.length || 0,
                    queueId: queueId,
                };
            } catch (e) {
                console.error('loadFromUploadQueue error:', e);
                throw e;  // Let bridge wrap as {success: false, error: ...}
            }
        },

        /**
         * Load a document from global storage into a new editor tab.
         * @param {string} documentId - Document ID in storage
         * @returns {Object} Result with new document info
         */
        async loadGlobalDocument(documentId) {
            const app = this.getState();
            if (!app?.documentStorage) {
                throw new Error('DocumentStorage not initialized');
            }
            if (!app?.documentManager) {
                throw new Error('DocumentManager not initialized');
            }

            try {
                // Load document data and layer images from storage
                const result = await app.documentStorage.loadDocument(documentId);
                if (!result) {
                    throw new Error(`Document not found in storage: ${documentId}`);
                }

                const { data, layerImages } = result;

                // Process layer images (convert blobs to data URLs)
                const { processLayerImages } = await import('/static/js/core/FileManager.js');
                await processLayerImages(data, layerImages);

                // Build docData: merge pages (v3) or layers (v1/v2) into document
                const docData = data.document;
                if (data.pages && !docData.pages) docData.pages = data.pages;
                if (data.layers && !docData.layers && !docData.pages) docData.layers = data.layers;

                // Deserialize document (creates new instance with new UUID)
                const { Document } = await import('/static/js/core/Document.js');
                const doc = await Document.deserialize(docData, app.eventBus);

                // Add to document manager and make active
                app.documentManager.addDocument(doc);
                app.documentManager.setActiveDocument(doc.id);

                // Update renderer
                app.renderer.resize(doc.width, doc.height);
                app.renderer.fitToViewport();
                app.renderer.requestRender();

                // Emit state update
                this.emitStateUpdate();

                // Return just the document info - Python bridge wraps in {success, result}
                return {
                    id: doc.id,
                    name: doc.name,
                    width: doc.width,
                    height: doc.height,
                    layerCount: doc.layerStack?.layers?.length || 0,
                    storageId: documentId,
                };
            } catch (e) {
                console.error('loadGlobalDocument error:', e);
                throw e;  // Let bridge wrap as {success: false, error: ...}
            }
        },

        // === Change Tracking Methods ===

        /**
         * Get change tracking metadata for a document and its layers.
         * This is designed for efficient polling to detect what needs refreshing.
         * @param {string|number} documentId - Document ID, index, or 'current'
         * @returns {Object} Change tracking data
         */
        getDocumentChanges(documentId) {
            const app = this.getState();
            if (!app?.documentManager) {
                return { success: false, error: 'DocumentManager not initialized' };
            }

            // Resolve document
            let doc = null;
            if (documentId === 'current' || documentId === undefined) {
                doc = app.documentManager.getActiveDocument();
            } else if (typeof documentId === 'number') {
                const docs = Array.from(app.documentManager.documents.values());
                doc = docs[documentId];
            } else {
                doc = app.documentManager.getDocument(documentId);
            }

            if (!doc) {
                return { success: false, error: `Document not found: ${documentId}` };
            }

            // Build layer change tracking map
            const layers = {};
            for (const layer of doc.layerStack.layers) {
                layers[layer.id] = {
                    changeCounter: layer.changeCounter || 0,
                    lastChangeTimestamp: layer.lastChangeTimestamp || 0,
                };
            }

            return {
                success: true,
                document: {
                    id: doc.id,
                    changeCounter: doc.changeCounter || 0,
                    lastChangeTimestamp: doc.lastChangeTimestamp || 0,
                },
                layers: layers,
            };
        },

        /**
         * Update layer properties via API
         * @param {Object} params - Parameters including layer_id and properties to update
         * @returns {Object} Result with success/error
         */
        updateLayerProperties(params) {
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                // Find the layer by ID
                const layerId = params.layer_id;
                let layer = null;

                if (typeof layerId === 'number') {
                    // Index-based lookup
                    layer = app.layerStack.layers[layerId];
                } else {
                    // ID or name-based lookup
                    layer = app.layerStack.layers.find(l => l.id === layerId || l.name === layerId);
                }

                if (!layer) {
                    return { success: false, error: `Layer not found: ${layerId}` };
                }

                // Update basic properties
                if (params.name !== undefined) layer.name = params.name;
                if (params.opacity !== undefined) layer.opacity = params.opacity;
                if (params.blend_mode !== undefined) layer.blendMode = params.blend_mode;
                if (params.visible !== undefined) layer.visible = params.visible;
                if (params.locked !== undefined) layer.locked = params.locked;

                // Update position
                if (params.offset_x !== undefined) layer.offsetX = params.offset_x;
                if (params.offset_y !== undefined) layer.offsetY = params.offset_y;

                // Update transform properties
                if (params.rotation !== undefined) layer.rotation = params.rotation;
                if (params.scale_x !== undefined) layer.scaleX = params.scale_x;
                if (params.scale_y !== undefined) layer.scaleY = params.scale_y;

                // Update the layer list UI
                this.updateLayerList();
                this.emitStateUpdate();

                return { success: true };
            } catch (e) {
                console.error('updateLayerProperties error:', e);
                return { success: false, error: e.message };
            }
        },
    },
};

export default SessionAPIManagerMixin;
