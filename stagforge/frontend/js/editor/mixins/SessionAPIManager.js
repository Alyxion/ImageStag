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
        executeCommand(command, params = {}) {
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
                    // Browser storage (OPFS) commands
                    case 'list_stored_documents':
                        return this.listStoredDocuments();
                    case 'clear_stored_documents':
                        return this.clearStoredDocuments();
                    case 'delete_stored_document':
                        return this.deleteStoredDocument(params.document_id);
                    // Layer import command
                    case 'import_layer':
                        return this.importLayer(params);
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
                        // Simulate mouse events for the tool
                        tool.onMouseDown({ button: 0 }, points[0][0], points[0][1]);
                        for (let i = 1; i < points.length; i++) {
                            tool.onMouseMove({ button: 0 }, points[i][0], points[i][1]);
                        }
                        tool.onMouseUp({ button: 0 }, points[points.length-1][0], points[points.length-1][1]);
                        app.renderer.requestRender();
                        break;

                    case 'fill':
                        // Flood fill at a point
                        if (params.point) {
                            tool.onMouseDown({ button: 0 }, params.point[0], params.point[1]);
                            tool.onMouseUp({ button: 0 }, params.point[0], params.point[1]);
                            app.renderer.requestRender();
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
                            app.renderer.requestRender();
                        }
                        break;

                    case 'draw':
                        // Draw shape - fallback for tools without executeAction
                        if (params.start && params.end) {
                            tool.onMouseDown({ button: 0 }, params.start[0], params.start[1]);
                            tool.onMouseMove({ button: 0 }, params.end[0], params.end[1]);
                            tool.onMouseUp({ button: 0 }, params.end[0], params.end[1]);
                            app.renderer.requestRender();
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

                // Re-render vector layers if rendering settings changed
                if (path.startsWith('rendering.')) {
                    this.reRenderVectorLayers();
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

                // Trigger re-render
                app.renderer.requestRender();
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

                // Trigger re-render
                app.renderer.requestRender();

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

                // Trigger re-render
                app.renderer.requestRender();
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
    },
};

export default SessionAPIManagerMixin;
