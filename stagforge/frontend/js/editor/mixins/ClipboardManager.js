/**
 * ClipboardManager Mixin
 *
 * Handles clipboard operations (copy, cut, paste) and selection management.
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
         * Get the current selection bounds
         * @returns {Object|null} Selection bounds { x, y, width, height } or null
         */
        getSelection() {
            const app = this.getState();
            const selectionTool = app?.toolManager?.tools.get('selection');
            return selectionTool?.getSelection() || null;
        },

        /**
         * Select the entire canvas
         */
        selectAll() {
            const app = this.getState();
            const selectionTool = app?.toolManager?.tools.get('selection');
            if (selectionTool) {
                selectionTool.selectAll();
                // Switch to selection tool
                app.toolManager.select('selection');
            }
        },

        /**
         * Clear the current selection
         */
        deselect() {
            const app = this.getState();
            if (!app) return;

            // Clear pixel selection
            const selectionTool = app.toolManager?.tools.get('selection');
            selectionTool?.clearSelection();

            // Clear vector shape selection
            const layer = app.layerStack?.getActiveLayer();
            if (layer?.isVector?.()) {
                layer.clearSelection();
                layer.render();
                app.renderer.requestRender();
            }
        },

        /**
         * Delete the selected area/shapes
         */
        deleteSelection() {
            const app = this.getState();
            if (!app) return;

            const layer = app.layerStack.getActiveLayer();
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
                    app.renderer.requestRender();
                    return;
                }
            }

            // Handle pixel layer - delete selection area
            // Selection is in document coordinates, need to convert to layer canvas coords
            const selection = this.getSelection();

            if (selection && selection.width > 0 && selection.height > 0) {
                // Convert document coords to layer canvas coords
                const localCoords = layer.docToCanvas(selection.x, selection.y);
                let canvasX = Math.floor(localCoords.x);
                let canvasY = Math.floor(localCoords.y);
                let width = Math.ceil(selection.width);
                let height = Math.ceil(selection.height);

                // Clamp to layer bounds
                const clampedLeft = Math.max(0, canvasX);
                const clampedTop = Math.max(0, canvasY);
                const clampedRight = Math.min(layer.width, canvasX + width);
                const clampedBottom = Math.min(layer.height, canvasY + height);

                width = clampedRight - clampedLeft;
                height = clampedBottom - clampedTop;

                if (width > 0 && height > 0) {
                    app.history.saveState('Delete Selection');
                    layer.ctx.clearRect(clampedLeft, clampedTop, width, height);
                    // Auto-fit is handled by history.finishState() -> commitCapture()
                    app.history.finishState();
                    app.renderer.requestRender();
                }
            }
        },

        /**
         * Copy current layer content to clipboard
         * @returns {boolean} Success status
         */
        clipboardCopy() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const selection = this.getSelection();
            const success = app.clipboard.copy(selection);
            if (success) {
                this.statusMessage = 'Copied to clipboard';
            }
            return success;
        },

        /**
         * Copy merged visible content to clipboard
         * @returns {boolean} Success status
         */
        clipboardCopyMerged() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const selection = this.getSelection();
            const success = app.clipboard.copyMerged(selection);
            if (success) {
                this.statusMessage = 'Copied merged to clipboard';
            }
            return success;
        },

        /**
         * Cut current layer content to clipboard
         * @returns {boolean} Success status
         */
        clipboardCut() {
            const app = this.getState();
            if (!app?.clipboard) return false;

            const selection = this.getSelection();
            const success = app.clipboard.cut(selection);
            if (success) {
                this.statusMessage = 'Cut to clipboard';
                app.renderer.requestRender();
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
