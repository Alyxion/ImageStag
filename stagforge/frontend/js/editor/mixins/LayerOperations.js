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
         * Add a new layer
         */
        addLayer() {
            const app = this.getState();
            if (!app?.layerStack) return;
            // Note: Adding layer is a structural change
            app.history.saveState('New Layer');
            app.layerStack.addLayer({ name: `Layer ${app.layerStack.layers.length + 1}` });
            app.history.finishState();
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
            app.history.saveState('Duplicate Layer');
            app.layerStack.duplicateLayer(app.layerStack.activeLayerIndex);
            app.history.finishState();
        },

        /**
         * Merge the active layer with the layer below it
         */
        mergeDown() {
            const app = this.getState();
            if (!app?.layerStack) return;
            if (app.layerStack.activeLayerIndex <= 0) return; // Can't merge bottom layer
            // Merge modifies pixels in bottom layer
            app.history.saveState('Merge Layers');
            app.layerStack.mergeDown(app.layerStack.activeLayerIndex);
            app.history.finishState();
        },
    },
};

export default LayerOperationsMixin;
