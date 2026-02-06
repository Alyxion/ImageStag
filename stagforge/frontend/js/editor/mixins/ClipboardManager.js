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
         * Fill the current selection (or entire document bounds if no selection) with a color.
         * This operation can expand the layer to cover the fill area.
         * @param {string} hexColor - Color in hex format (#RRGGBB)
         */
        fillSelectionWithColor(hexColor) {
            const app = this.getState();
            if (!app) return;

            const layer = app.layerStack?.getActiveLayer();
            if (!layer || layer.locked) return;

            // Don't fill vector or SVG layers
            if (layer.isVector?.() || layer.isSVG?.()) {
                this.statusMessage = 'Cannot fill vector/SVG layers';
                return;
            }

            app.history.saveState('Fill');

            // Parse hex color
            const r = parseInt(hexColor.slice(1, 3), 16);
            const g = parseInt(hexColor.slice(3, 5), 16);
            const b = parseInt(hexColor.slice(5, 7), 16);

            const selectionManager = app.selectionManager;
            const hasSelection = selectionManager?.hasSelection;

            // Get document dimensions
            const docWidth = app.layerStack.width;
            const docHeight = app.layerStack.height;

            if (hasSelection) {
                // Fill only selected pixels using mask
                const bounds = selectionManager.getBounds();
                if (!bounds) {
                    app.history.abortCapture();
                    return;
                }

                // Expand layer to cover selection bounds (layer can grow to fit selection)
                layer.expandToInclude(bounds.x, bounds.y, bounds.width, bounds.height);

                // Get layer-local bounds after expansion
                const offsetX = layer.offsetX || 0;
                const offsetY = layer.offsetY || 0;

                const localLeft = Math.max(0, bounds.x - offsetX);
                const localTop = Math.max(0, bounds.y - offsetY);
                const localRight = Math.min(layer.width, bounds.x + bounds.width - offsetX);
                const localBottom = Math.min(layer.height, bounds.y + bounds.height - offsetY);

                if (localRight <= localLeft || localBottom <= localTop) {
                    app.history.abortCapture();
                    return; // No overlap with layer
                }

                const width = localRight - localLeft;
                const height = localBottom - localTop;
                const imageData = layer.ctx.getImageData(localLeft, localTop, width, height);

                for (let y = 0; y < height; y++) {
                    for (let x = 0; x < width; x++) {
                        const docX = localLeft + offsetX + x;
                        const docY = localTop + offsetY + y;
                        const maskValue = selectionManager.getMaskAt(docX, docY);
                        if (maskValue > 0) {
                            const idx = (y * width + x) * 4;
                            // Blend based on mask alpha
                            const alpha = maskValue / 255;
                            imageData.data[idx] = Math.round(r * alpha + imageData.data[idx] * (1 - alpha));
                            imageData.data[idx + 1] = Math.round(g * alpha + imageData.data[idx + 1] * (1 - alpha));
                            imageData.data[idx + 2] = Math.round(b * alpha + imageData.data[idx + 2] * (1 - alpha));
                            imageData.data[idx + 3] = Math.max(imageData.data[idx + 3], maskValue);
                        }
                    }
                }

                layer.ctx.putImageData(imageData, localLeft, localTop);
            } else {
                // No selection - expand layer to document bounds and fill entire area
                layer.expandToInclude(0, 0, docWidth, docHeight);
                layer.ctx.fillStyle = hexColor;
                layer.ctx.fillRect(0, 0, layer.width, layer.height);
            }

            layer.invalidateImageCache();
            app.history.finishState();
            this.statusMessage = hasSelection ? 'Filled selection' : 'Filled layer';
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
