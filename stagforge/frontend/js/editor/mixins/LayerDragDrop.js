/**
 * LayerDragDrop Mixin
 *
 * Handles layer drag-and-drop reordering in the layer panel.
 * Supports reordering within the list and dropping into groups.
 *
 * Required component data:
 *   - layerDragIndex: Number|null
 *   - layerDragOverIndex: Number|null
 *   - layerDragOverPosition: String|null ('top', 'bottom', 'into')
 *   - layerDragOverGroup: String|null
 *   - visibleLayers: Array (computed property)
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateLayerList(): Refreshes the layer list UI
 */
export const LayerDragDropMixin = {
    data() {
        return {
            _lastDragTargetId: null,
        };
    },

    methods: {
        /**
         * Handle drag start on a layer item
         * @param {number} idx - Index in visibleLayers
         * @param {Object} layer - Layer data object
         * @param {DragEvent} event - The drag event
         */
        onLayerDragStart(idx, layer, event) {
            this.layerDragIndex = idx;
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', layer.id);
            // Add dragging class after a small delay for visual feedback
            setTimeout(() => {
                event.target.classList.add('dragging');
            }, 0);
        },

        /**
         * Handle drag over a layer item
         * Determines drop position: before, after, or into (for groups)
         * @param {number} idx - Index in visibleLayers
         * @param {Object} layer - Layer data object
         * @param {DragEvent} event - The drag event
         */
        onLayerDragOver(idx, layer, event) {
            if (this.layerDragIndex === null) return;
            if (this.layerDragIndex === idx) {
                this.layerDragOverIndex = null;
                this.layerDragOverPosition = null;
                this.layerDragOverGroup = null;
                return;
            }

            // Get position within the element
            const rect = event.currentTarget.getBoundingClientRect();
            const y = event.clientY - rect.top;
            const height = rect.height;
            const edgeZone = height * 0.3; // Top/bottom 30% are edge zones

            // Store the target layer ID for drop handler (in case events fire out of order)
            this._lastDragTargetId = layer.id;

            // Determine position
            if (layer.isGroup && y > edgeZone && y < height - edgeZone) {
                // Middle of a group - drop INTO the group
                this.layerDragOverGroup = layer.id;
                this.layerDragOverIndex = idx;
                this.layerDragOverPosition = 'into';
            } else if (y < edgeZone) {
                // Top edge - insert BEFORE this item
                this.layerDragOverGroup = null;
                this.layerDragOverIndex = idx;
                this.layerDragOverPosition = 'top';
            } else {
                // Bottom edge - insert AFTER this item
                this.layerDragOverGroup = null;
                this.layerDragOverIndex = idx;
                this.layerDragOverPosition = 'bottom';
            }
        },

        /**
         * Handle drag leave from a layer item
         * @param {DragEvent} event - The drag event
         */
        onLayerDragLeave(event) {
            // Don't clear position during active drag - drop handler needs it
            // Only clear the visual indicator index when leaving all layer items
            const isStillInLayerItem = event.relatedTarget?.closest('.layer-item, .tablet-layer-item');
            if (!isStillInLayerItem) {
                this.layerDragOverIndex = null;
                this.layerDragOverGroup = null;
                // Keep layerDragOverPosition - drop handler will use it
            }
        },

        /**
         * Handle drop on a layer item
         * @param {number} idx - Index in visibleLayers
         * @param {Object} targetLayer - Target layer data object
         */
        onLayerDrop(idx, targetLayer) {
            if (this.layerDragIndex === null) return;
            if (this.layerDragIndex === idx) {
                this.onLayerDragEnd();
                return;
            }

            const app = this.getState();
            if (!app?.layerStack) return;

            // Capture position before any state changes
            const dropPosition = this.layerDragOverPosition || 'top';

            // Get source layer from visibleLayers (which is what the drag indices reference)
            const sourceLayerData = this.visibleLayers[this.layerDragIndex];
            if (!sourceLayerData) {
                this.onLayerDragEnd();
                return;
            }
            const sourceLayer = app.layerStack.getLayerById(sourceLayerData.id);
            if (!sourceLayer) {
                this.onLayerDragEnd();
                return;
            }

            // Get target layer - use passed targetLayer or fallback to last known target
            const targetId = targetLayer?.id || this._lastDragTargetId;
            if (!targetId) {
                this.onLayerDragEnd();
                return;
            }
            const targetLayerObj = app.layerStack.getLayerById(targetId);
            if (!targetLayerObj) {
                this.onLayerDragEnd();
                return;
            }

            // Don't move to same position
            if (sourceLayer.id === targetLayerObj.id) {
                this.onLayerDragEnd();
                return;
            }

            app.history.beginCapture('Move Layer', []);
            app.history.beginStructuralChange();

            if (dropPosition === 'into' && targetLayerObj.isGroup?.()) {
                // Drop INTO group
                app.layerStack.moveLayerToGroup(sourceLayer.id, targetLayerObj.id);
            } else {
                // Reorder: insert before or after target
                const sourceIdx = app.layerStack.getLayerIndex(sourceLayer.id);
                const targetIdx = app.layerStack.getLayerIndex(targetLayerObj.id);

                if (sourceIdx !== -1 && targetIdx !== -1 && sourceIdx !== targetIdx) {
                    // Remove from current position first
                    app.layerStack.layers.splice(sourceIdx, 1);

                    // Recalculate target index after removal
                    let insertIdx = app.layerStack.getLayerIndex(targetLayerObj.id);

                    // Adjust based on position:
                    // Array order matches visual order (index 0 = top)
                    // 'top' = insert BEFORE target (at insertIdx, target shifts down)
                    // 'bottom' = insert AFTER target (at insertIdx + 1)
                    if (dropPosition === 'bottom') {
                        insertIdx += 1;
                    }

                    // Clamp to valid range
                    insertIdx = Math.max(0, Math.min(insertIdx, app.layerStack.layers.length));

                    // Insert at the calculated position
                    app.layerStack.layers.splice(insertIdx, 0, sourceLayer);

                    // Set parent to match target's parent (same level)
                    sourceLayer.parentId = targetLayerObj.parentId;

                    // Update active layer index
                    const newSourceIdx = app.layerStack.getLayerIndex(sourceLayer.id);
                    app.layerStack.activeLayerIndex = newSourceIdx;
                }
            }

            app.history.commitCapture();
            app.documentManager?.getActiveDocument()?.markModified();
            this.updateLayerList();
            app.renderer.requestRender();
            this.onLayerDragEnd();
        },

        /**
         * Clean up drag state after drag operation ends
         */
        onLayerDragEnd() {
            this.layerDragIndex = null;
            this.layerDragOverIndex = null;
            this.layerDragOverPosition = null;
            this.layerDragOverGroup = null;
            this._lastDragTargetId = null;
        },
    },
};

export default LayerDragDropMixin;
