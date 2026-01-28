/**
 * ClipboardManager Mixin
 *
 * Handles clipboard operations (copy, cut, paste) and selection management.
 * Uses the global SelectionManager for all selection operations.
 *
 * Required component data:
 *   - statusMessage: String
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateLayerList(): Updates layer panel after paste
 */
export const ClipboardManagerMixin = {
    methods: {
        /**
         * Get the current selection bounds from SelectionManager.
         * @returns {Object|null} Selection bounds { x, y, width, height } or null
         */
        getSelection() {
            const app = this.getState();
            return app?.selectionManager?.getBounds() || null;
        },

        /**
         * Select the entire canvas using SelectionManager.
         */
        selectAll() {
            const app = this.getState();
            if (!app?.selectionManager) return;

            app.selectionManager.selectAll();
            app.selectionManager.startAnimation();
        },

        /**
         * Clear the current selection using SelectionManager.
         */
        deselect() {
            const app = this.getState();
            if (!app) return;

            // Clear pixel selection via SelectionManager
            app.selectionManager?.clear();

            // Clear vector shape selection
            const layer = app.layerStack?.getActiveLayer();
            if (layer?.isVector?.()) {
                layer.clearSelection();
                layer.render();
                app.renderer?.requestRender();
            }
        },

        /**
         * Restore previous selection (Reselect).
         */
        reselect() {
            const app = this.getState();
            if (!app?.selectionManager) return;

            app.selectionManager.reselect();
            app.selectionManager.startAnimation();
        },

        /**
         * Invert current selection.
         */
        invertSelection() {
            const app = this.getState();
            if (!app?.selectionManager) return;

            app.selectionManager.invert();
            app.selectionManager.startAnimation();
        },

        /**
         * Delete the selected area/shapes using SelectionManager mask.
         */
        deleteSelection() {
            const app = this.getState();
            if (!app) return;

            const layer = app.layerStack?.getActiveLayer();
            if (!layer || layer.locked) return;

            // Handle vector layer - delete selected shapes
            if (layer.isVector?.()) {
                const selectedIds = [...layer.selectedShapeIds];
                if (selectedIds.length > 0) {
                    app.history.saveState('Delete Shapes');
                    for (const id of selectedIds) {
                        layer.removeShape(id);
                    }
                    app.history.finishState();
                    app.renderer?.requestRender();
                    return;
                }
            }

            // Handle pixel layer - delete using SelectionManager mask
            if (!app.selectionManager?.hasSelection) return;

            app.history.saveState('Delete Selection');
            app.selectionManager.deleteFromLayer(layer);

            // Trim layer if it has trimToContent
            if (layer.trimToContent) {
                layer.trimToContent();
            }

            app.history.finishState();
            app.renderer?.requestRender();
        },

        /**
         * Copy current layer content to clipboard.
         * Uses SelectionManager for selection-based copy.
         * @returns {boolean} Success status
         */
        clipboardCopy() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const success = app.clipboard.copy();
            if (success) {
                this.statusMessage = 'Copied to clipboard';
            }
            return success;
        },

        /**
         * Copy merged visible content to clipboard.
         * Uses SelectionManager for selection-based copy.
         * @returns {boolean} Success status
         */
        clipboardCopyMerged() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const success = app.clipboard.copyMerged();
            if (success) {
                this.statusMessage = 'Copied merged to clipboard';
            }
            return success;
        },

        /**
         * Cut current layer content to clipboard.
         * Uses SelectionManager for selection-based cut.
         * @returns {boolean} Success status
         */
        clipboardCut() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const success = app.clipboard.cut();
            if (success) {
                this.statusMessage = 'Cut to clipboard';
                app.renderer?.requestRender();
            }
            return success;
        },

        /**
         * Paste clipboard content as new layer
         * @returns {boolean} Success status
         */
        async clipboardPaste() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            // Try internal buffer first, then system clipboard
            if (app.clipboard.hasContent()) {
                const success = app.clipboard.paste({ asNewLayer: true });
                if (success) {
                    this.statusMessage = 'Pasted as new layer';
                    this.updateLayerList();
                }
                return success;
            }

            // Try reading from system clipboard
            const systemSuccess = await app.clipboard.pasteFromSystem();
            if (systemSuccess) {
                this.statusMessage = 'Pasted from system clipboard';
                this.updateLayerList();
            }
            return systemSuccess;
        },

        /**
         * Paste clipboard content in original position
         * @returns {boolean} Success status
         */
        clipboardPasteInPlace() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const success = app.clipboard.pasteInPlace(true);
            if (success) {
                this.statusMessage = 'Pasted in place';
                this.updateLayerList();
            }
            return success;
        },
    },
};

export default ClipboardManagerMixin;
