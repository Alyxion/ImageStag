/**
 * LayerStack - Manages multiple layers with group support.
 *
 * Uses a flat array with parentId references for hierarchy.
 * Groups affect visibility and opacity of children.
 *
 * Layer order: Index 0 = topmost layer (visually on top), higher index = lower layer.
 * Renderer draws from last to first (bottom to top).
 */
import { Layer } from './Layer.js';
import { DynamicLayer } from './DynamicLayer.js';
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
     * @param {Object|Layer} layerOrOptions - Layer instance or options
     * @param {Object} [insertOptions] - Insertion options
     * @param {boolean} [insertOptions.atBottom=false] - Insert at bottom instead of top
     * @returns {Layer}
     */
    addLayer(layerOrOptions = {}, insertOptions = {}) {
        let layer;

        // Check if it's already a Layer instance (including DynamicLayer subclasses like SVGLayer)
        if (layerOrOptions instanceof Layer || layerOrOptions instanceof DynamicLayer) {
            layer = layerOrOptions;
        } else {
            // Create a new Layer from options
            // Default to 0x0 - all layers auto-fit to content
            layer = new Layer({
                width: 0,
                height: 0,
                ...layerOrOptions
            });
        }

        if (insertOptions.atBottom) {
            // Insert at end (bottom of stack)
            this.layers.push(layer);
            this.activeLayerIndex = this.layers.length - 1;
            this.eventBus.emit('layer:added', { layer, index: this.activeLayerIndex });
        } else {
            // Insert at index 0 (top of stack)
            this.layers.unshift(layer);
            this.activeLayerIndex = 0;
            this.eventBus.emit('layer:added', { layer, index: 0 });
        }
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

        // Only rasterize if it's a vector, SVG, or text layer
        const isVec = layer.isVector?.();
        const isSvg = layer.isSVG?.();
        const isText = layer.isText?.();
        if (!isVec && !isSvg && !isText) return layer;

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
        // Insert at same index (duplicate appears on top of original visually)
        this.layers.splice(index, 0, cloned);
        this.activeLayerIndex = index;
        this.eventBus.emit('layer:duplicated', { original, cloned, index: index });
        return cloned;
    }

    /**
     * Merge a layer with the one below it.
     * @param {number} index
     * @returns {boolean}
     */
    mergeDown(index) {
        // With index 0 = top, "below" means index + 1
        if (index < 0 || index >= this.layers.length - 1) return false;

        const upper = this.layers[index];
        const lower = this.layers[index + 1];

        const uOx = upper.offsetX ?? 0, uOy = upper.offsetY ?? 0;
        const lOx = lower.offsetX ?? 0, lOy = lower.offsetY ?? 0;

        // Compute bounding box covering both layers in document space
        const minX = Math.min(uOx, lOx);
        const minY = Math.min(uOy, lOy);
        const maxX = Math.max(uOx + upper.width, lOx + lower.width);
        const maxY = Math.max(uOy + upper.height, lOy + lower.height);
        const newW = maxX - minX;
        const newH = maxY - minY;

        // If the merged bounds differ from the lower layer, expand it
        if (newW !== lower.width || newH !== lower.height || minX !== lOx || minY !== lOy) {
            const tmpCanvas = document.createElement('canvas');
            tmpCanvas.width = newW;
            tmpCanvas.height = newH;
            const tmpCtx = tmpCanvas.getContext('2d');

            // Draw existing lower content at its relative position
            tmpCtx.drawImage(lower.canvas, lOx - minX, lOy - minY);

            // Composite upper onto it
            tmpCtx.globalAlpha = upper.opacity;
            tmpCtx.globalCompositeOperation = BlendModes.toCompositeOperation(upper.blendMode);
            tmpCtx.drawImage(upper.canvas, uOx - minX, uOy - minY);

            // Replace lower canvas content
            lower.canvas.width = newW;
            lower.canvas.height = newH;
            lower.width = newW;
            lower.height = newH;
            lower.offsetX = minX;
            lower.offsetY = minY;
            lower.ctx.drawImage(tmpCanvas, 0, 0);
        } else {
            // Same bounds — just composite upper at the right offset
            lower.ctx.globalAlpha = upper.opacity;
            lower.ctx.globalCompositeOperation = BlendModes.toCompositeOperation(upper.blendMode);
            lower.ctx.drawImage(upper.canvas, uOx - lOx, uOy - lOy);
            lower.ctx.globalAlpha = 1.0;
            lower.ctx.globalCompositeOperation = 'source-over';
        }

        lower.invalidateImageCache?.();
        lower.invalidateEffectCache?.();

        this.layers.splice(index, 1);
        this.activeLayerIndex = index; // Now points to the merged (lower) layer
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

        // Composite all visible layers (bottom to top = last to first in array)
        for (let i = this.layers.length - 1; i >= 0; i--) {
            const layer = this.layers[i];
            if (!layer.visible) continue;
            // Skip groups - they have no canvas
            if (layer.isGroup && layer.isGroup()) continue;
            resultLayer.ctx.globalAlpha = layer.opacity;
            resultLayer.ctx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
            resultLayer.ctx.drawImage(layer.canvas, layer.offsetX ?? 0, layer.offsetY ?? 0);
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
     * @returns {Array<Layer|LayerGroup>}
     */
    getChildren(groupId) {
        return this.layers.filter(l => l.parentId === groupId);
    }

    /**
     * Get all descendants of a group (recursive).
     * @param {string} groupId - Group ID
     * @returns {Array<Layer|LayerGroup>}
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
     * @param {Layer|LayerGroup} layer
     * @returns {LayerGroup|null}
     */
    getParentGroup(layer) {
        if (!layer.parentId) return null;
        const parent = this.getLayerById(layer.parentId);
        return (parent && parent.isGroup && parent.isGroup()) ? parent : null;
    }

    /**
     * Check if a layer is effectively visible (considering parent groups).
     * @param {Layer|LayerGroup} layer
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
     * @param {Layer|LayerGroup} layer
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
     * @param {Layer|LayerGroup} layer
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

        // Insert at specified index or at top (index 0)
        const index = options.insertIndex ?? 0;
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
    // Note: Index 0 = top, higher index = lower in stack

    /**
     * Move a layer up in z-order (towards the top/front).
     * With index 0 = top, moving up means decreasing index.
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerUp(index) {
        if (index <= 0 || index >= this.layers.length) return false;
        return this.moveLayerToIndex(index, index - 1);
    }

    /**
     * Move a layer down in z-order (towards the bottom/back).
     * With index 0 = top, moving down means increasing index.
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerDown(index) {
        if (index < 0 || index >= this.layers.length - 1) return false;
        return this.moveLayerToIndex(index, index + 1);
    }

    /**
     * Move a layer to the top of the stack (or top of its parent group).
     * With index 0 = top, top means index 0 (or first with same parent).
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerToTop(index) {
        if (index < 0 || index >= this.layers.length) return false;
        const layer = this.layers[index];

        // Find the top position within the same parent (lowest index)
        let topIndex = 0;
        if (layer.parentId) {
            // Find the first layer with the same parent
            for (let i = 0; i < this.layers.length; i++) {
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
     * With index 0 = top, bottom means highest index (or last with same parent).
     * @param {number} index - Index of the layer to move
     * @returns {boolean}
     */
    moveLayerToBottom(index) {
        if (index < 0 || index >= this.layers.length) return false;
        const layer = this.layers[index];

        // Find the bottom position within the same parent (highest index)
        let bottomIndex = this.layers.length - 1;
        if (layer.parentId) {
            // Find the last layer with the same parent
            for (let i = this.layers.length - 1; i >= 0; i--) {
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
        // Insert at top (index 0)
        this.layers.unshift(group);
        this.eventBus.emit('layer:added', { layer: group, index: 0 });
        return group;
    }
}
