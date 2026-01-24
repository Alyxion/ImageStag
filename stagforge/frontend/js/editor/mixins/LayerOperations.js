/**
 * LayerOperations Mixin
 *
 * Handles layer CRUD operations: add, delete, duplicate, merge,
 * visibility toggle, group operations, and layer ordering.
 *
 * Required component data:
 *   - activeLayerId: String
 *   - activeLayerOpacity: Number
 *   - activeLayerBlendMode: String
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateLayerList(): Refreshes the layer list UI
 *   - updateLayerControls(): Updates layer property controls
 */
export const LayerOperationsMixin = {
    methods: {
        /**
         * Select a layer by ID
         * @param {string} layerId - Layer ID to select
         */
        selectLayer(layerId) {
            const app = this.getState();
            if (!app?.layerStack) return;
            const index = app.layerStack.getLayerIndex(layerId);
            if (index >= 0) {
                app.layerStack.setActiveLayer(index);
                this.activeLayerId = layerId;
                this.updateLayerControls();
            }
        },

        /**
         * Toggle layer visibility
         * @param {string} layerId - Layer ID to toggle
         */
        toggleLayerVisibility(layerId) {
            const app = this.getState();
            if (!app?.layerStack) return;
            const layer = app.layerStack.layers.find(l => l.id === layerId);
            if (layer) {
                // Use structural history for visibility changes (metadata, not pixels)
                app.history.beginCapture('Toggle Visibility', []);
                app.history.beginStructuralChange();
                layer.visible = !layer.visible;
                app.history.commitCapture();
                app.documentManager?.getActiveDocument()?.markModified();
                app.renderer.requestRender();
                this.updateLayerList();
            }
        },

        /**
         * Toggle group expanded/collapsed state
         * @param {string} groupId - Group layer ID
         */
        toggleGroupExpanded(groupId) {
            const app = this.getState();
            if (!app?.layerStack) return;
            app.layerStack.toggleGroupExpanded(groupId);
            this.updateLayerList();
        },

        /**
         * Create a new empty group
         */
        createGroup() {
            const app = this.getState();
            if (!app?.layerStack) return;
            app.history.beginCapture('Create Group', []);
            app.history.beginStructuralChange();
            const group = app.layerStack.createGroup({ name: 'New Group' });
            app.history.commitCapture();
            app.documentManager?.getActiveDocument()?.markModified();
            // Select the new group
            const index = app.layerStack.getLayerIndex(group.id);
            if (index >= 0) {
                app.layerStack.setActiveLayer(index);
            }
            this.updateLayerList();
        },

        /**
         * Group the currently selected layer(s)
         */
        groupSelectedLayers() {
            const app = this.getState();
            if (!app?.layerStack) return;
            // For now, group the active layer only
            // TODO: Support multi-select in the future
            const activeLayer = app.layerStack.getActiveLayer();
            if (!activeLayer || activeLayer.isGroup?.()) return;

            app.history.beginCapture('Group Layers', []);
            app.history.beginStructuralChange();
            const group = app.layerStack.createGroupFromLayers([activeLayer.id], 'Group');
            app.history.commitCapture();
            app.documentManager?.getActiveDocument()?.markModified();
            // Select the new group
            const index = app.layerStack.getLayerIndex(group.id);
            if (index >= 0) {
                app.layerStack.setActiveLayer(index);
            }
            this.updateLayerList();
            app.renderer.requestRender();
        },

        /**
         * Ungroup the currently selected group
         */
        ungroupSelectedLayers() {
            const app = this.getState();
            if (!app?.layerStack) return;
            const activeLayer = app.layerStack.getActiveLayer();
            if (!activeLayer || !activeLayer.isGroup?.()) return;

            app.history.beginCapture('Ungroup', []);
            app.history.beginStructuralChange();
            app.layerStack.ungroupLayers(activeLayer.id);
            app.history.commitCapture();
            app.documentManager?.getActiveDocument()?.markModified();
            this.updateLayerList();
            app.renderer.requestRender();
        },

        /**
         * Move active layer up in the stack (visually higher)
         */
        moveLayerUp() {
            const app = this.getState();
            if (!app?.layerStack) return;
            const index = app.layerStack.activeLayerIndex;
            if (index < app.layerStack.layers.length - 1) {
                app.history.beginCapture('Move Layer Up', []);
                app.history.beginStructuralChange();
                app.layerStack.moveLayerUp(index);
                app.history.commitCapture();
                app.documentManager?.getActiveDocument()?.markModified();
                this.updateLayerList();
                app.renderer.requestRender();
            }
        },

        /**
         * Move active layer down in the stack (visually lower)
         */
        moveLayerDown() {
            const app = this.getState();
            if (!app?.layerStack) return;
            const index = app.layerStack.activeLayerIndex;
            if (index > 0) {
                app.history.beginCapture('Move Layer Down', []);
                app.history.beginStructuralChange();
                app.layerStack.moveLayerDown(index);
                app.history.commitCapture();
                app.documentManager?.getActiveDocument()?.markModified();
                this.updateLayerList();
                app.renderer.requestRender();
            }
        },

        /**
         * Update the opacity of the active layer
         * @param {number|null} opacity - Opacity value (0-100) or null to use reactive data
         */
        updateLayerOpacity(opacity = null) {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (!layer) return;

            // Get the opacity value: from parameter (tablet mode) or from reactive data (desktop mode v-model)
            let newOpacity = opacity !== null ? opacity : this.activeLayerOpacity;

            // Validate and clamp the opacity value
            if (typeof newOpacity !== 'number' || isNaN(newOpacity)) {
                newOpacity = 100;
            }
            newOpacity = Math.max(0, Math.min(100, Math.round(newOpacity)));

            // Update both the reactive value and the layer
            this.activeLayerOpacity = newOpacity;
            layer.opacity = newOpacity / 100;
            app.renderer.requestRender();
        },

        /**
         * Update the blend mode of the active layer
         */
        updateLayerBlendMode() {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer) {
                layer.blendMode = this.activeLayerBlendMode;
                app.renderer.requestRender();
            }
        },

        /**
         * Add a new pixel layer (used by API and programmatic calls)
         */
        addLayer() {
            const app = this.getState();
            if (!app?.layerStack) return;
            app.history.beginCapture('New Layer', []);
            app.history.beginStructuralChange();
            app.layerStack.addLayer({ name: `Layer ${app.layerStack.layers.length + 1}` });
            app.history.commitCapture();
        },

        /**
         * Show add layer menu with options for different layer types (UI only)
         * @param {Event} event - Click event for positioning
         */
        showAddLayerMenuPopup(event) {
            this.showAddLayerMenu = true;
            if (event) {
                const rect = event.target.getBoundingClientRect();
                this.addLayerMenuPosition = {
                    left: rect.left + 'px',
                    bottom: (window.innerHeight - rect.top + 5) + 'px'
                };
            }
        },

        /**
         * Add a new pixel layer from the menu
         */
        addPixelLayer() {
            this.addLayer();
            this.showAddLayerMenu = false;
        },

        /**
         * Add a new vector layer
         */
        async addVectorLayer() {
            const app = this.getState();
            if (!app?.layerStack) return;
            const { VectorLayer } = await import('/static/js/core/VectorLayer.js');
            app.history.beginCapture('New Vector Layer', []);
            app.history.beginStructuralChange();
            const layer = new VectorLayer({
                width: app.layerStack.width,
                height: app.layerStack.height,
                name: `Vector ${app.layerStack.layers.length + 1}`
            });
            app.layerStack.addLayer(layer);
            app.history.commitCapture();
            this.showAddLayerMenu = false;
            this.updateLayerList();
        },

        /**
         * Show library dialog (modal with categories on left, items on right)
         */
        async showLibraryDialog() {
            // Close the add layer menu first
            this.showAddLayerMenu = false;
            this.showLibrarySubmenu = false;

            // Open the library dialog
            this.libraryDialogOpen = true;
            this.libraryItems = [];
            this.libraryLoading = true;
            this.librarySelectedCategory = null;

            try {
                // Fetch both image sources and SVG samples
                const [imagesRes, svgsRes] = await Promise.all([
                    fetch(`${this.apiBase}/images/sources`).catch(() => null),
                    fetch(`${this.apiBase}/svg-samples`).catch(() => null)
                ]);

                const items = [];

                // Add image sources (skimage samples)
                if (imagesRes?.ok) {
                    const imagesData = await imagesRes.json();
                    for (const source of imagesData.sources || []) {
                        for (const img of source.images || []) {
                            items.push({
                                type: 'image',
                                id: `${source.id}/${img.id}`,
                                name: img.name || img.id,
                                category: source.name || source.id
                            });
                        }
                    }
                }

                // Add SVG samples
                if (svgsRes?.ok) {
                    const svgsData = await svgsRes.json();
                    for (const svg of svgsData.samples || []) {
                        items.push({
                            type: 'svg',
                            id: svg.path,
                            name: svg.name,
                            category: `SVG: ${svg.category}`
                        });
                    }
                }

                this.libraryItems = items;

                // Select first category by default
                const categories = [...new Set(items.map(i => i.category))];
                if (categories.length > 0) {
                    this.librarySelectedCategory = categories[0];
                }
            } catch (err) {
                console.error('Failed to load library:', err);
            } finally {
                this.libraryLoading = false;
            }
        },

        /**
         * Close the library dialog
         */
        closeLibraryDialog() {
            this.libraryDialogOpen = false;
        },

        /**
         * Select a category in the library dialog
         * @param {string} category - Category name to select
         */
        selectLibraryCategory(category) {
            this.librarySelectedCategory = category;
        },

        /**
         * Add layer from library item
         * @param {Object} item - Library item with type and id
         */
        async addLayerFromLibrary(item) {
            const app = this.getState();
            if (!app?.layerStack) return;

            try {
                if (item.type === 'svg') {
                    await this.addSVGLayerFromLibrary(item.id);
                } else if (item.type === 'image') {
                    await this.addImageLayerFromLibrary(item.id);
                }
            } catch (err) {
                console.error('Failed to add layer from library:', err);
                this.statusMessage = 'Failed to add layer: ' + err.message;
            }

            this.showAddLayerMenu = false;
            this.showLibrarySubmenu = false;
            this.libraryDialogOpen = false;
        },

        /**
         * Add an SVG layer from the library
         * @param {string} path - SVG path (e.g., "openclipart/deer.svg")
         */
        async addSVGLayerFromLibrary(path) {
            const app = this.getState();
            if (!app?.layerStack) return;

            const response = await fetch(`${this.apiBase}/svg-samples/${path}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch SVG: ${response.status}`);
            }
            const svgContent = await response.text();

            const { SVGLayer } = await import('/static/js/core/SVGLayer.js');

            // Create a temporary layer to get natural dimensions
            const tempLayer = new SVGLayer({ width: 1, height: 1, svgContent });
            const naturalW = tempLayer.naturalWidth;
            const naturalH = tempLayer.naturalHeight;

            // Calculate dimensions preserving aspect ratio
            const docW = app.layerStack.width;
            const docH = app.layerStack.height;
            let targetW = naturalW;
            let targetH = naturalH;

            // Scale down if larger than document
            if (naturalW > docW || naturalH > docH) {
                const scale = Math.min(docW / naturalW, docH / naturalH);
                targetW = Math.round(naturalW * scale);
                targetH = Math.round(naturalH * scale);
            }

            // Center in document
            const offsetX = Math.round((docW - targetW) / 2);
            const offsetY = Math.round((docH - targetH) / 2);

            app.history.beginCapture('Add SVG Layer', []);
            app.history.beginStructuralChange();
            const layer = new SVGLayer({
                width: targetW,
                height: targetH,
                offsetX,
                offsetY,
                name: path.split('/').pop().replace('.svg', ''),
                svgContent: svgContent
            });
            await layer.render();
            app.layerStack.addLayer(layer);
            app.history.commitCapture();
            this.updateLayerList();
            app.renderer.requestRender();
        },

        /**
         * Add an image layer from the library
         * @param {string} id - Image ID (e.g., "skimage/astronaut")
         */
        async addImageLayerFromLibrary(id) {
            const app = this.getState();
            if (!app?.layerStack) return;

            const [sourceId, imageId] = id.split('/');
            const response = await fetch(`${this.apiBase}/images/${sourceId}/${imageId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch image: ${response.status}`);
            }

            // Parse binary response
            const buffer = await response.arrayBuffer();
            const view = new DataView(buffer);
            const metadataLength = view.getUint32(0, true);
            const metadataJson = new TextDecoder().decode(new Uint8Array(buffer, 4, metadataLength));
            const metadata = JSON.parse(metadataJson);
            const rgbaData = new Uint8ClampedArray(buffer, 4 + metadataLength);

            const { Layer } = await import('/static/js/core/Layer.js');
            app.history.beginCapture('Add Image Layer', []);
            app.history.beginStructuralChange();
            const layer = new Layer({
                width: metadata.width,
                height: metadata.height,
                name: metadata.name || imageId
            });

            const imageData = new ImageData(rgbaData, metadata.width, metadata.height);
            layer.ctx.putImageData(imageData, 0, 0);

            app.layerStack.addLayer(layer);
            app.history.commitCapture();
            this.updateLayerList();
            app.renderer.requestRender();
        },

        /**
         * Import a layer from base64-encoded data.
         * Supports raster images (PNG, WebP, AVIF), SVG, and vector JSON.
         *
         * @param {Object} params - Import parameters
         * @param {string} params.data - Base64 encoded data (with or without data URL prefix)
         * @param {string} params.content_type - MIME type (image/png, image/webp, image/avif, image/svg+xml, application/json)
         * @param {string} [params.name] - Optional layer name
         * @returns {Object} Result with success/error
         */
        async importLayer(params) {
            const app = this.getState();
            if (!app?.layerStack) {
                return { success: false, error: 'Editor not initialized' };
            }

            try {
                const { data, content_type, name } = params;

                // Handle data URL or raw base64
                let base64Data = data;
                if (data.startsWith('data:')) {
                    base64Data = data.split(',')[1];
                }

                if (content_type === 'application/json') {
                    // Vector layer from JSON shapes
                    return await this._importVectorLayer(base64Data, name);
                } else if (content_type === 'image/svg+xml') {
                    // SVG layer
                    return await this._importSVGLayer(base64Data, name);
                } else {
                    // Raster layer (PNG, WebP, AVIF)
                    return await this._importRasterLayer(base64Data, content_type, name);
                }
            } catch (e) {
                console.error('[importLayer] Error:', e);
                return { success: false, error: e.message };
            }
        },

        /**
         * Import a raster layer from base64 image data
         */
        async _importRasterLayer(base64Data, contentType, name) {
            const app = this.getState();
            const { Layer } = await import('/static/js/core/Layer.js');

            // Create image from base64
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = () => reject(new Error('Failed to load image'));
                img.src = `data:${contentType};base64,${base64Data}`;
            });

            app.history.beginCapture('Import Layer', []);
            app.history.beginStructuralChange();

            const layer = new Layer({
                width: img.width,
                height: img.height,
                name: name || 'Imported Layer'
            });

            layer.ctx.drawImage(img, 0, 0);

            app.layerStack.addLayer(layer);
            app.history.commitCapture();
            this.updateLayerList();
            app.renderer.requestRender();

            return { success: true, layerId: layer.id };
        },

        /**
         * Import an SVG layer from base64 SVG data
         */
        async _importSVGLayer(base64Data, name) {
            const app = this.getState();
            const { SVGLayer } = await import('/static/js/core/SVGLayer.js');

            // Decode base64 to SVG string
            const svgContent = atob(base64Data);

            // Create temporary layer to get dimensions
            const tempLayer = new SVGLayer({ width: 1, height: 1, svgContent });
            const naturalW = tempLayer.naturalWidth;
            const naturalH = tempLayer.naturalHeight;

            // Calculate dimensions preserving aspect ratio
            const docW = app.layerStack.width;
            const docH = app.layerStack.height;
            let targetW = naturalW;
            let targetH = naturalH;

            if (naturalW > docW || naturalH > docH) {
                const scale = Math.min(docW / naturalW, docH / naturalH);
                targetW = Math.round(naturalW * scale);
                targetH = Math.round(naturalH * scale);
            }

            const offsetX = Math.round((docW - targetW) / 2);
            const offsetY = Math.round((docH - targetH) / 2);

            app.history.beginCapture('Import SVG Layer', []);
            app.history.beginStructuralChange();

            const layer = new SVGLayer({
                width: targetW,
                height: targetH,
                offsetX,
                offsetY,
                name: name || 'Imported SVG',
                svgContent
            });
            await layer.render();

            app.layerStack.addLayer(layer);
            app.history.commitCapture();
            this.updateLayerList();
            app.renderer.requestRender();

            return { success: true, layerId: layer.id };
        },

        /**
         * Import a vector layer from base64 JSON shapes data
         */
        async _importVectorLayer(base64Data, name) {
            const app = this.getState();
            const { VectorLayer } = await import('/static/js/core/VectorLayer.js');

            // Decode base64 to JSON
            const jsonStr = atob(base64Data);
            const shapes = JSON.parse(jsonStr);

            app.history.beginCapture('Import Vector Layer', []);
            app.history.beginStructuralChange();

            const layer = new VectorLayer({
                width: app.layerStack.width,
                height: app.layerStack.height,
                name: name || 'Imported Vector'
            });

            // Add shapes to layer
            if (Array.isArray(shapes)) {
                for (const shape of shapes) {
                    layer.addShape(shape);
                }
            }

            app.layerStack.addLayer(layer);
            app.history.commitCapture();
            this.updateLayerList();
            app.renderer.requestRender();

            return { success: true, layerId: layer.id };
        },

        /**
         * Close add layer menu
         */
        closeAddLayerMenu() {
            this.showAddLayerMenu = false;
            this.showLibrarySubmenu = false;
        },

        /**
         * Delete the active layer
         */
        deleteLayer() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const activeLayer = app.layerStack.getActiveLayer();
            if (!activeLayer) return;

            // Check if it's a group
            if (activeLayer.isGroup?.()) {
                // Use the group delete method
                this.deleteGroup(activeLayer.id, false); // Keep children
                return;
            }

            // Structural change - use beginCapture/beginStructuralChange
            app.history.beginCapture('Delete Layer', []);
            app.history.beginStructuralChange();

            // If only one layer, delete it and create a new transparent one
            if (app.layerStack.layers.length <= 1) {
                app.layerStack.layers = [];
                app.layerStack.activeLayerIndex = -1;
                app.layerStack.addLayer({ name: 'Layer 1' });
                // Leave transparent (don't fill with white)
            } else {
                app.layerStack.removeLayer(app.layerStack.activeLayerIndex);
            }

            app.history.commitCapture();
            app.documentManager?.getActiveDocument()?.markModified();
            this.updateLayerList();
            app.renderer.requestRender();
        },

        /**
         * Delete a group
         * @param {string} groupId - Group ID to delete
         * @param {boolean} deleteChildren - If true, delete children; if false, move them out
         */
        deleteGroup(groupId, deleteChildren = false) {
            const app = this.getState();
            if (!app?.layerStack) return;

            // Structural change - use beginCapture/beginStructuralChange
            app.history.beginCapture(deleteChildren ? 'Delete Group with Children' : 'Delete Group', []);
            app.history.beginStructuralChange();

            app.layerStack.deleteGroup(groupId, deleteChildren);

            app.history.commitCapture();
            app.documentManager?.getActiveDocument()?.markModified();
            this.updateLayerList();
            app.renderer.requestRender();
        },

        /**
         * Duplicate the active layer
         */
        duplicateLayer() {
            const app = this.getState();
            if (!app?.layerStack) return;
            // Note: Duplicating layer is a structural change
            app.history.beginCapture('Duplicate Layer', []);
            app.history.beginStructuralChange();
            app.layerStack.duplicateLayer(app.layerStack.activeLayerIndex);
            app.history.commitCapture();
        },

        /**
         * Merge the active layer with the layer below it
         */
        mergeDown() {
            const app = this.getState();
            if (!app?.layerStack) return;
            if (app.layerStack.activeLayerIndex <= 0) return; // Can't merge bottom layer
            // Merge is both a structural change (removes a layer) and pixel change
            app.history.beginCapture('Merge Layers', []);
            app.history.beginStructuralChange();
            app.layerStack.mergeDown(app.layerStack.activeLayerIndex);
            app.history.commitCapture();
        },
    },
};

export default LayerOperationsMixin;
