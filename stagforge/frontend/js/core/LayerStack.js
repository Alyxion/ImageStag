/**
 * LayerStack - Manages multiple layers with group support.
 *
 * Uses a flat array with parentId references for hierarchy.
 * Groups affect visibility and opacity of children.
 */
import { Layer } from './Layer.js';
import { VectorLayer } from './VectorLayer.js';
import { LayerGroup } from './LayerGroup.js';
import { BlendModes } from './BlendModes.js';

export class LayerStack {
    /**
     * @param {number} width - Document width
     * @param {number} height - Document height
     * @param {EventBus} eventBus - Event bus for notifications
     */
    constructor(width, height, eventBus) {
        this.width = width;
        this.height = height;
        this.eventBus = eventBus;
        this.layers = [];
        this.activeLayerIndex = -1;
    }

    /**
     * Add a new layer or add an existing layer instance.
     * @param {Object|Layer|VectorLayer} layerOrOptions - Layer instance or options
     * @returns {Layer|VectorLayer}
     */
    addLayer(layerOrOptions = {}) {
        let layer;

        // Check if it's already a Layer instance
        if (layerOrOptions instanceof Layer) {
            layer = layerOrOptions;
        } else {
            // Create a new Layer from options
            layer = new Layer({
                width: this.width,
                height: this.height,
                ...layerOrOptions
            });
        }

        this.layers.push(layer);
        this.activeLayerIndex = this.layers.length - 1;
        this.eventBus.emit('layer:added', { layer, index: this.activeLayerIndex });
        return layer;
    }

    /**
     * Set the active layer by ID.
     * @param {string} id - Layer ID
     */
    setActiveLayerById(id) {
        const index = this.getLayerIndex(id);
        if (index >= 0) {
            this.setActiveLayer(index);
        }
    }

    /**
     * Rasterize a vector layer in place.
     * @param {string} layerId - ID of the vector layer to rasterize
     * @returns {Layer|null} The new raster layer, or null if layer not found
     */
    rasterizeLayer(layerId) {
        const index = this.getLayerIndex(layerId);
        if (index < 0) return null;

        const layer = this.layers[index];

        // Only rasterize if it's a vector layer
        if (!layer.isVector || !layer.isVector()) return layer;

        // Rasterize the vector layer
        const rasterLayer = layer.rasterize();

        // Replace in the array
        this.layers[index] = rasterLayer;

        this.eventBus.emit('layer:rasterized', { layerId, index, layer: rasterLayer });
        return rasterLayer;
    }

    /**
     * Remove a layer by index.
     * @param {number} index
     * @returns {boolean}
     */
    removeLayer(index) {
        if (this.layers.length <= 1) return false; // Keep at least one layer
        if (index < 0 || index >= this.layers.length) return false;

        const [removed] = this.layers.splice(index, 1);
        this.activeLayerIndex = Math.min(this.activeLayerIndex, this.layers.length - 1);
        this.eventBus.emit('layer:removed', { layer: removed, index });
        return true;
    }

    /**
     * Move a layer from one position to another.
     * @param {number} fromIndex
     * @param {number} toIndex
     */
    moveLayer(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= this.layers.length) return;
        if (toIndex < 0 || toIndex >= this.layers.length) return;

        const [layer] = this.layers.splice(fromIndex, 1);
        this.layers.splice(toIndex, 0, layer);

        if (this.activeLayerIndex === fromIndex) {
            this.activeLayerIndex = toIndex;
        } else if (fromIndex < this.activeLayerIndex && toIndex >= this.activeLayerIndex) {
            this.activeLayerIndex--;
        } else if (fromIndex > this.activeLayerIndex && toIndex <= this.activeLayerIndex) {
            this.activeLayerIndex++;
        }

        this.eventBus.emit('layer:moved', { fromIndex, toIndex });
    }

    /**
     * Duplicate a layer.
     * @param {number} index
     * @returns {Layer|null}
     */
    duplicateLayer(index) {
        if (index < 0 || index >= this.layers.length) return null;

        const original = this.layers[index];
        const cloned = original.clone();
        this.layers.splice(index + 1, 0, cloned);
        this.activeLayerIndex = index + 1;
        this.eventBus.emit('layer:duplicated', { original, cloned, index: index + 1 });
        return cloned;
    }

    /**
     * Merge a layer with the one below it.
     * @param {number} index
     * @returns {boolean}
     */
    mergeDown(index) {
        if (index <= 0 || index >= this.layers.length) return false;

        const upper = this.layers[index];
        const lower = this.layers[index - 1];

        // Composite upper onto lower
        lower.ctx.globalAlpha = upper.opacity;
        lower.ctx.globalCompositeOperation = BlendModes.toCompositeOperation(upper.blendMode);
        lower.ctx.drawImage(upper.canvas, 0, 0);
        lower.ctx.globalAlpha = 1.0;
        lower.ctx.globalCompositeOperation = 'source-over';

        this.layers.splice(index, 1);
        this.activeLayerIndex = index - 1;
        this.eventBus.emit('layer:merged', { index });
        return true;
    }

    /**
     * Flatten all layers into one.
     * @returns {Layer}
     */
    flattenAll() {
        const resultLayer = new Layer({
            width: this.width,
            height: this.height,
            name: 'Flattened'
        });

        // Fill with white background
        resultLayer.ctx.fillStyle = '#FFFFFF';
        resultLayer.ctx.fillRect(0, 0, this.width, this.height);

        // Composite all visible layers (bottom to top)
        for (const layer of this.layers) {
            if (!layer.visible) continue;
            resultLayer.ctx.globalAlpha = layer.opacity;
            resultLayer.ctx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
            resultLayer.ctx.drawImage(layer.canvas, 0, 0);
        }

        resultLayer.ctx.globalAlpha = 1.0;
        resultLayer.ctx.globalCompositeOperation = 'source-over';

        this.layers = [resultLayer];
        this.activeLayerIndex = 0;
        this.eventBus.emit('layer:flattened');
        return resultLayer;
    }

    /**
     * Get the currently active layer.
     * @returns {Layer|null}
     */
    getActiveLayer() {
        return this.layers[this.activeLayerIndex] || null;
    }

    /**
     * Set the active layer by index.
     * @param {number} index
     */
    setActiveLayer(index) {
        if (index >= 0 && index < this.layers.length) {
            this.activeLayerIndex = index;
            this.eventBus.emit('layer:activated', { index, layer: this.layers[index] });
        }
    }

    /**
     * Get layer by ID.
     * @param {string} id
     * @returns {Layer|null}
     */
    getLayerById(id) {
        return this.layers.find(l => l.id === id) || null;
    }

    /**
     * Get index of a layer by ID.
     * @param {string} id
     * @returns {number}
     */
    getLayerIndex(id) {
        return this.layers.findIndex(l => l.id === id);
    }

    // ========== Group Helper Methods ==========

    /**
     * Get direct children of a group.
     * @param {string} groupId - Group ID (null for root level)
     * @returns {Array<Layer|VectorLayer|LayerGroup>}
     */
    getChildren(groupId) {
        return this.layers.filter(l => l.parentId === groupId);
    }

    /**
     * Get all descendants of a group (recursive).
     * @param {string} groupId - Group ID
     * @returns {Array<Layer|VectorLayer|LayerGroup>}
     */
    getDescendants(groupId) {
        const descendants = [];
        const children = this.getChildren(groupId);

        for (const child of children) {
            descendants.push(child);
            if (child.isGroup && child.isGroup()) {
                descendants.push(...this.getDescendants(child.id));
            }
        }

        return descendants;
    }

    /**
     * Get the parent group of a layer.
     * @param {Layer|VectorLayer|LayerGroup} layer
     * @returns {LayerGroup|null}
     */
    getParentGroup(layer) {
        if (!layer.parentId) return null;
        const parent = this.getLayerById(layer.parentId);
        return (parent && parent.isGroup && parent.isGroup()) ? parent : null;
    }

    /**
     * Check if a layer is effectively visible (considering parent groups).
     * @param {Layer|VectorLayer|LayerGroup} layer
     * @returns {boolean}
     */
    isEffectivelyVisible(layer) {
        if (!layer.visible) return false;

        // Check parent chain
        let current = layer;
        while (current.parentId) {
            const parent = this.getLayerById(current.parentId);
            if (!parent) break;
            if (!parent.visible) return false;
            current = parent;
        }

        return true;
    }

    /**
     * Get the effective opacity of a layer (multiplied through parent chain).
     * @param {Layer|VectorLayer|LayerGroup} layer
     * @returns {number}
     */
    getEffectiveOpacity(layer) {
        let opacity = layer.opacity;

        // Multiply opacity through parent chain (if not passthrough mode)
        let current = layer;
        while (current.parentId) {
            const parent = this.getLayerById(current.parentId);
            if (!parent) break;
            // Only multiply if group has a specific blend mode (not passthrough)
            if (parent.blendMode !== 'passthrough') {
                opacity *= parent.opacity;
            }
            current = parent;
        }

        return opacity;
    }

    /**
     * Check if a layer is locked (considering parent groups).
     * @param {Layer|VectorLayer|LayerGroup} layer
     * @returns {boolean}
     */
    isEffectivelyLocked(layer) {
        if (layer.locked) return true;

        // Check parent chain
        let current = layer;
        while (current.parentId) {
            const parent = this.getLayerById(current.parentId);
            if (!parent) break;
            if (parent.locked) return true;
            current = parent;
        }

        return false;
    }

    // ========== Group Operations ==========

    /**
     * Create an empty group.
     * @param {Object} [options] - Group options
     * @param {string} [options.name] - Group name
     * @param {string} [options.parentId] - Parent group ID
     * @param {number} [options.insertIndex] - Where to insert in layers array
     * @returns {LayerGroup}
     */
    createGroup(options = {}) {
        const group = new LayerGroup({
            name: options.name || 'New Group',
            parentId: options.parentId || null,
            opacity: options.opacity ?? 1.0,
            blendMode: options.blendMode || 'passthrough',
            visible: options.visible ?? true,
            locked: options.locked ?? false,
            expanded: options.expanded ?? true
        });

        // Insert at specified index or at end
        const index = options.insertIndex ?? this.layers.length;
        this.layers.splice(index, 0, group);

        // Update active layer index if needed
        if (index <= this.activeLayerIndex) {
            this.activeLayerIndex++;
        }

        this.eventBus.emit('layer:group-created', { group, index });
        return group;
    }

    /**
     * Create a group from selected layers.
     * Moves the selected layers into the new group.
     * @param {string[]} layerIds - IDs of layers to group
     * @param {string} [groupName] - Optional name for the group
     * @returns {LayerGroup|null}
     */
    createGroupFromLayers(layerIds, groupName = 'Group') {
        if (!layerIds || layerIds.length === 0) return null;

        // Find the minimum index of selected layers (where group will be inserted)
        let minIndex = this.layers.length;
        const selectedLayers = [];

        for (const id of layerIds) {
            const index = this.getLayerIndex(id);
            if (index >= 0) {
                minIndex = Math.min(minIndex, index);
                selectedLayers.push(this.layers[index]);
            }
        }

        if (selectedLayers.length === 0) return null;

        // Determine parent (all selected layers should have same parent)
        // Use the parent of the first selected layer
        const parentId = selectedLayers[0].parentId;

        // Create the group
        const group = this.createGroup({
            name: groupName,
            parentId: parentId,
            insertIndex: minIndex
        });

        // Move selected layers into the group
        for (const layer of selectedLayers) {
            layer.parentId = group.id;
        }

        this.eventBus.emit('layer:grouped', { group, layerIds });
        return group;
    }

    /**
     * Dissolve a group, moving its children to the group's parent.
     * @param {string} groupId - ID of the group to ungroup
     * @returns {boolean}
     */
    ungroupLayers(groupId) {
        const groupIndex = this.getLayerIndex(groupId);
        if (groupIndex < 0) return false;

        const group = this.layers[groupIndex];
        if (!group.isGroup || !group.isGroup()) return false;

        // Get group's parent
        const parentId = group.parentId;

        // Get children and move them to parent
        const children = this.getChildren(groupId);
        for (const child of children) {
            child.parentId = parentId;
        }

        // Remove the group itself
        this.layers.splice(groupIndex, 1);

        // Adjust active layer index
        if (this.activeLayerIndex > groupIndex) {
            this.activeLayerIndex--;
        } else if (this.activeLayerIndex === groupIndex) {
            this.activeLayerIndex = Math.min(groupIndex, this.layers.length - 1);
        }

        this.eventBus.emit('layer:ungrouped', { groupId, children, parentId });
        return true;
    }

    /**
     * Move a layer into a group.
     * @param {string} layerId - ID of the layer to move
     * @param {string|null} groupId - ID of the target group (null for root)
     * @returns {boolean}
     */
    moveLayerToGroup(layerId, groupId) {
        const layer = this.getLayerById(layerId);
        if (!layer) return false;

        // Verify target is a valid group (or null for root)
        if (groupId !== null) {
            const group = this.getLayerById(groupId);
            if (!group || !group.isGroup || !group.isGroup()) return false;

            // Prevent moving a group into itself or its descendants
            if (layer.isGroup && layer.isGroup()) {
                const descendants = this.getDescendants(layer.id);
                if (descendants.some(d => d.id === groupId) || layer.id === groupId) {
                    return false;
                }
            }
        }

        const oldParentId = layer.parentId;
        layer.parentId = groupId;

        this.eventBus.emit('layer:moved-to-group', { layerId, groupId, oldParentId });
        return true;
    }

    /**
     * Remove a layer from its parent group (move to root).
     * @param {string} layerId - ID of the layer to move to root
     * @returns {boolean}
     */
    removeLayerFromGroup(layerId) {
        return this.moveLayerToGroup(layerId, null);
    }

    /**
     * Delete a group with options for handling children.
     * @param {string} groupId - ID of the group to delete
     * @param {boolean} [deleteChildren=false] - If true, delete children too
     * @returns {boolean}
     */
    deleteGroup(groupId, deleteChildren = false) {
        const groupIndex = this.getLayerIndex(groupId);
        if (groupIndex < 0) return false;

        const group = this.layers[groupIndex];
        if (!group.isGroup || !group.isGroup()) return false;

        if (deleteChildren) {
            // Delete all descendants first (in reverse order to maintain indices)
            const descendants = this.getDescendants(groupId);
            for (const desc of descendants.reverse()) {
                const idx = this.getLayerIndex(desc.id);
                if (idx >= 0) {
                    this.layers.splice(idx, 1);
                    if (this.activeLayerIndex > idx) {
                        this.activeLayerIndex--;
                    }
                }
            }
        } else {
            // Move children to group's parent
            const children = this.getChildren(groupId);
            for (const child of children) {
                child.parentId = group.parentId;
            }
        }

        // Remove the group
        this.layers.splice(groupIndex, 1);

        // Adjust active layer index
        if (this.activeLayerIndex >= groupIndex) {
            this.activeLayerIndex = Math.max(0, Math.min(this.activeLayerIndex - 1, this.layers.length - 1));
        }

        // Ensure at least one layer exists
        if (this.layers.length === 0) {
            const newLayer = new Layer({ width: this.width, height: this.height, name: 'Layer 1' });
            this.layers.push(newLayer);
            this.activeLayerIndex = 0;
        }

        this.eventBus.emit('layer:group-deleted', { groupId, deleteChildren });
        return true;
    }

    // ========== Layer Reordering ==========

    /**
     * Move a layer up in z-order (towards the top/front).
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerUp(index) {
        if (index < 0 || index >= this.layers.length - 1) return false;
        return this.moveLayerToIndex(index, index + 1);
    }

    /**
     * Move a layer down in z-order (towards the bottom/back).
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerDown(index) {
        if (index <= 0 || index >= this.layers.length) return false;
        return this.moveLayerToIndex(index, index - 1);
    }

    /**
     * Move a layer to the top of the stack (or top of its parent group).
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerToTop(index) {
        if (index < 0 || index >= this.layers.length) return false;
        const layer = this.layers[index];

        // Find the top position within the same parent
        let topIndex = this.layers.length - 1;
        if (layer.parentId) {
            // Find the last layer with the same parent
            for (let i = this.layers.length - 1; i >= 0; i--) {
                if (this.layers[i].parentId === layer.parentId) {
                    topIndex = i;
                    break;
                }
            }
        }

        if (index === topIndex) return false;
        return this.moveLayerToIndex(index, topIndex);
    }

    /**
     * Move a layer to the bottom of the stack (or bottom of its parent group).
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerToBottom(index) {
        if (index < 0 || index >= this.layers.length) return false;
        const layer = this.layers[index];

        // Find the bottom position within the same parent
        let bottomIndex = 0;
        if (layer.parentId) {
            // Find the first layer with the same parent
            for (let i = 0; i < this.layers.length; i++) {
                if (this.layers[i].parentId === layer.parentId) {
                    bottomIndex = i;
                    break;
                }
            }
        }

        if (index === bottomIndex) return false;
        return this.moveLayerToIndex(index, bottomIndex);
    }

    /**
     * Move a layer to a specific index.
     * @param {number} fromIndex - Current index
     * @param {number} toIndex - Target index
     * @returns {boolean}
     */
    moveLayerToIndex(fromIndex, toIndex) {
        if (fromIndex < 0 || fromIndex >= this.layers.length) return false;
        if (toIndex < 0 || toIndex >= this.layers.length) return false;
        if (fromIndex === toIndex) return false;

        const [layer] = this.layers.splice(fromIndex, 1);
        this.layers.splice(toIndex, 0, layer);

        // Update active layer index
        if (this.activeLayerIndex === fromIndex) {
            this.activeLayerIndex = toIndex;
        } else if (fromIndex < this.activeLayerIndex && toIndex >= this.activeLayerIndex) {
            this.activeLayerIndex--;
        } else if (fromIndex > this.activeLayerIndex && toIndex <= this.activeLayerIndex) {
            this.activeLayerIndex++;
        }

        this.eventBus.emit('layer:reordered', { fromIndex, toIndex });
        return true;
    }

    // ========== Layer Visibility/Opacity Changes ==========

    /**
     * Toggle visibility of a layer.
     * @param {string} layerId - Layer ID
     * @returns {boolean} New visibility state
     */
    toggleLayerVisibility(layerId) {
        const layer = this.getLayerById(layerId);
        if (!layer) return false;

        layer.visible = !layer.visible;
        this.eventBus.emit('layer:visibility-changed', { layerId, visible: layer.visible });
        return layer.visible;
    }

    /**
     * Set layer opacity.
     * @param {string} layerId - Layer ID
     * @param {number} opacity - New opacity (0.0-1.0)
     * @returns {boolean}
     */
    setLayerOpacity(layerId, opacity) {
        const layer = this.getLayerById(layerId);
        if (!layer) return false;

        layer.opacity = Math.max(0, Math.min(1, opacity));
        this.eventBus.emit('layer:opacity-changed', { layerId, opacity: layer.opacity });
        return true;
    }

    /**
     * Set layer blend mode.
     * @param {string} layerId - Layer ID
     * @param {string} blendMode - New blend mode
     * @returns {boolean}
     */
    setLayerBlendMode(layerId, blendMode) {
        const layer = this.getLayerById(layerId);
        if (!layer) return false;

        layer.blendMode = blendMode;
        this.eventBus.emit('layer:blendmode-changed', { layerId, blendMode });
        return true;
    }

    /**
     * Toggle layer lock state.
     * @param {string} layerId - Layer ID
     * @returns {boolean} New lock state
     */
    toggleLayerLock(layerId) {
        const layer = this.getLayerById(layerId);
        if (!layer) return false;

        layer.locked = !layer.locked;
        this.eventBus.emit('layer:lock-changed', { layerId, locked: layer.locked });
        return layer.locked;
    }

    /**
     * Toggle group expanded state.
     * @param {string} groupId - Group ID
     * @returns {boolean} New expanded state
     */
    toggleGroupExpanded(groupId) {
        const group = this.getLayerById(groupId);
        if (!group || !group.isGroup || !group.isGroup()) return false;

        group.expanded = !group.expanded;
        this.eventBus.emit('layer:group-expanded', { groupId, expanded: group.expanded });
        return group.expanded;
    }

    /**
     * Rename a layer or group.
     * @param {string} layerId - Layer ID
     * @param {string} newName - New name
     * @returns {boolean}
     */
    renameLayer(layerId, newName) {
        const layer = this.getLayerById(layerId);
        if (!layer) return false;

        layer.name = newName;
        this.eventBus.emit('layer:renamed', { layerId, name: newName });
        return true;
    }

    /**
     * Add a group to the layer stack.
     * @param {LayerGroup} group - The group to add
     * @returns {LayerGroup}
     */
    addGroup(group) {
        this.layers.push(group);
        this.eventBus.emit('layer:added', { layer: group, index: this.layers.length - 1 });
        return group;
    }
}
