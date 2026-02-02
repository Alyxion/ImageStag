/**
 * History - Memory-efficient undo/redo system using region-based patches.
 *
 * Instead of storing full layer snapshots, this system stores only the pixels
 * that changed within the affected region(s) of affected layer(s).
 *
 * Supports layer groups and structural changes (add/delete/reorder/group operations).
 */
import { Layer } from './PixelLayer.js';
import { LayerGroup } from './LayerGroup.js';
import { LayerEffect } from './LayerEffects.js';
import { layerRegistry } from './LayerRegistry.js';

/**
 * Represents changed pixels in a single layer region.
 */
class HistoryPatch {
    /**
     * @param {string} layerId - ID of affected layer
     * @param {number} x - Top-left X of affected region
     * @param {number} y - Top-left Y of affected region
     * @param {number} width - Width of affected region
     * @param {number} height - Height of affected region
     * @param {ImageData} beforeData - Pixels before the operation
     * @param {ImageData} afterData - Pixels after the operation
     */
    constructor(layerId, x, y, width, height, beforeData, afterData) {
        this.layerId = layerId;
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.beforeData = beforeData;
        this.afterData = afterData;
    }

    /**
     * Calculate memory usage in bytes.
     * Each ImageData stores RGBA (4 bytes per pixel), we store before + after.
     */
    get memorySize() {
        return this.width * this.height * 4 * 2;
    }
}

/**
 * Represents a complete history entry (one undoable action).
 */
class HistoryEntry {
    /**
     * @param {string} action - Description of the action
     */
    constructor(action) {
        this.action = action;
        this.timestamp = Date.now();
        this.patches = [];
        this.layerStructure = null; // For structural changes (add/delete/reorder)
        this.effectsChange = null;  // For layer effects changes { layerId, before, after }
        this._memorySize = 0;
    }

    addPatch(patch) {
        this.patches.push(patch);
        this._memorySize += patch.memorySize;
    }

    get memorySize() {
        const structureSize = this.layerStructure ? this.layerStructure.memorySize || 0 : 0;
        const effectsSize = this.effectsChange ? 1024 : 0; // Estimate for serialized effects
        return this._memorySize + structureSize + effectsSize;
    }
}

/**
 * Stores layer structure for undo/redo of structural changes.
 * Includes group hierarchy information.
 */
class LayerStructureSnapshot {
    constructor(layerStack, document = null) {
        this.docWidth = layerStack.width;
        this.docHeight = layerStack.height;
        this.layerOrder = layerStack.layers.map(l => l.id);
        this.activeIndex = layerStack.activeLayerIndex;
        this.layerMeta = layerStack.layers.map(l => ({
            id: l.id,
            name: l.name,
            type: l.type || (l.isGroup && l.isGroup() ? 'group' : 'raster'),
            parentId: l.parentId || null,
            width: l.width,
            height: l.height,
            offsetX: l.offsetX ?? 0,
            offsetY: l.offsetY ?? 0,
            rotation: l.rotation ?? 0,
            scaleX: l.scaleX ?? 1,
            scaleY: l.scaleY ?? 1,
            opacity: l.opacity,
            blendMode: l.blendMode,
            visible: l.visible,
            locked: l.locked,
            // Group-specific properties
            expanded: l.expanded ?? true,
            // Include serialized effects for undo/redo
            effects: l.effects ? l.effects.map(e => e.serialize()) : [],
            // SVG layer content (must be preserved through undo/redo)
            svgContent: l.svgContent || undefined,
            naturalWidth: l.naturalWidth || undefined,
            naturalHeight: l.naturalHeight || undefined
        }));
        this.deletedLayers = new Map(); // layerId -> full serialized layer data
        this.resizedLayers = new Map(); // layerId -> full serialized layer data (for resize undo)
        this.memorySize = 1024; // Base estimate for metadata

        // Capture saved selections from document (for selection save/load undo)
        if (document?.savedSelections) {
            this.savedSelections = document.savedSelections.map(sel => ({
                name: sel.name,
                mask: new Uint8Array(sel.mask),
                width: sel.width,
                height: sel.height
            }));
            this.memorySize += this.savedSelections.reduce((sum, s) => sum + s.mask.length, 0);
        } else {
            this.savedSelections = null;
        }
    }

    /**
     * Store full layer data for a layer that will be resized.
     * This captures the complete layer state including pixel data for undo.
     */
    async storeResizedLayer(layer) {
        const serialized = layer.serialize();
        this.resizedLayers.set(layer.id, serialized);

        // Estimate memory
        if (layer.width && layer.height) {
            this.memorySize += layer.width * layer.height * 4;
        }
    }

    /**
     * Store full layer data for a layer that will be deleted.
     * Works with regular layers, vector layers, and groups.
     */
    async storeDeletedLayer(layer) {
        const serialized = layer.serialize();
        this.deletedLayers.set(layer.id, serialized);

        // Estimate memory: groups are small, layers vary by size
        if (layer.isGroup && layer.isGroup()) {
            this.memorySize += 512; // Groups are just metadata
        } else if (layer.width && layer.height) {
            // base64 PNG is roughly 1.37x raw size, but varies
            this.memorySize += layer.width * layer.height * 4;
        }
    }
}

/**
 * Memory-efficient History manager with patch-based undo/redo.
 */
export class History {
    /**
     * @param {Object} app - Application reference
     * @param {Object} [options] - Configuration options
     */
    constructor(app, options = {}) {
        this.app = app;
        this.undoStack = [];
        this.redoStack = [];

        // Configuration
        this.maxEntries = options.maxEntries || 50;
        this.maxMemoryMB = options.maxMemoryMB || 256;
        this.maxMemoryBytes = this.maxMemoryMB * 1024 * 1024;

        // State tracking
        this.totalMemory = 0;
        this.currentCapture = null;
    }

    // ========== Memory Management ==========

    /**
     * Get current memory usage in MB.
     */
    get memoryUsageMB() {
        return this.totalMemory / (1024 * 1024);
    }

    /**
     * Get memory usage stats.
     */
    getMemoryUsage() {
        return {
            usedBytes: this.totalMemory,
            usedMB: this.memoryUsageMB,
            maxMB: this.maxMemoryMB,
            percentage: (this.totalMemory / this.maxMemoryBytes) * 100
        };
    }

    /**
     * Set maximum memory limit.
     */
    setMaxMemoryMB(mb) {
        this.maxMemoryMB = mb;
        this.maxMemoryBytes = mb * 1024 * 1024;
        this.enforceMemoryLimit();
    }

    /**
     * Set maximum entry count.
     */
    setMaxEntries(count) {
        this.maxEntries = count;
        this.enforceEntryLimit();
    }

    /**
     * Enforce memory limit by removing oldest entries.
     */
    enforceMemoryLimit() {
        while (this.totalMemory > this.maxMemoryBytes && this.undoStack.length > 0) {
            const removed = this.undoStack.shift();
            this.totalMemory -= removed.memorySize;
        }
    }

    /**
     * Enforce entry count limit.
     */
    enforceEntryLimit() {
        while (this.undoStack.length > this.maxEntries) {
            const removed = this.undoStack.shift();
            this.totalMemory -= removed.memorySize;
        }
    }

    // ========== Capture API (for optimized patch-based history) ==========

    /**
     * Begin capturing changes for a new history entry.
     * Call this BEFORE modifying any pixels.
     * Uses deferred capture for better performance when bounds are unknown.
     *
     * @param {string} action - Description of the action
     * @param {string[]} layerIds - IDs of layers that will be affected
     * @param {Object} [bounds] - Initial bounding box {x, y, width, height}
     */
    beginCapture(action, layerIds, bounds = null) {
        if (this.currentCapture) {
            console.warn('History: beginCapture called while capture in progress, committing previous');
            this.commitCapture();
        }

        this.currentCapture = {
            action: action,
            layers: new Map(),
            structureBefore: null
        };

        // Capture "before" state for each affected layer
        for (const layerId of layerIds) {
            const layer = this.app.layerStack.getLayerById(layerId);
            if (!layer) continue;

            // Skip non-pixel layers (vector, SVG) - they use structural changes instead
            if (!layer.ctx || !layer.canvas) continue;

            if (bounds) {
                // With known bounds, capture just that region immediately
                const captureBounds = {
                    x: Math.max(0, Math.floor(bounds.x)),
                    y: Math.max(0, Math.floor(bounds.y)),
                    width: Math.min(layer.width - Math.max(0, Math.floor(bounds.x)), Math.ceil(bounds.width)),
                    height: Math.min(layer.height - Math.max(0, Math.floor(bounds.y)), Math.ceil(bounds.height))
                };

                if (captureBounds.width <= 0 || captureBounds.height <= 0) continue;

                const beforeData = layer.ctx.getImageData(
                    captureBounds.x, captureBounds.y,
                    captureBounds.width, captureBounds.height
                );

                this.currentCapture.layers.set(layerId, {
                    bounds: captureBounds,
                    beforeData: beforeData,
                    originalBounds: { ...captureBounds },
                    snapshotCanvas: null
                });
            } else {
                // Deferred capture: create a canvas snapshot (GPU-accelerated via drawImage)
                // instead of copying all pixel data immediately with getImageData.
                // This is much faster for large canvases.
                const snapshotCanvas = document.createElement('canvas');
                snapshotCanvas.width = layer.width;
                snapshotCanvas.height = layer.height;
                const snapshotCtx = snapshotCanvas.getContext('2d');
                snapshotCtx.drawImage(layer.canvas, 0, 0);

                this.currentCapture.layers.set(layerId, {
                    bounds: { x: 0, y: 0, width: layer.width, height: layer.height },
                    beforeData: null,  // Will be extracted from snapshot on commit
                    originalBounds: {
                        x: 0, y: 0,
                        width: layer.width, height: layer.height,
                        offsetX: layer.offsetX, offsetY: layer.offsetY  // Store original offset
                    },
                    snapshotCanvas: snapshotCanvas
                });
            }
        }
    }

    /**
     * Expand the capture bounds to include a new point.
     * Call this during continuous operations (e.g., brush drag).
     *
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {number} [radius=0] - Radius around the point to include
     */
    expandBounds(x, y, radius = 0) {
        if (!this.currentCapture) return;

        const padding = Math.ceil(radius);

        for (const [layerId, data] of this.currentCapture.layers) {
            const layer = this.app.layerStack.getLayerById(layerId);
            if (!layer) continue;

            const b = data.bounds;
            const newLeft = Math.max(0, Math.floor(x - padding));
            const newTop = Math.max(0, Math.floor(y - padding));
            const newRight = Math.min(layer.width, Math.ceil(x + padding));
            const newBottom = Math.min(layer.height, Math.ceil(y + padding));

            // Check if we need to expand
            const expandLeft = newLeft < b.x;
            const expandTop = newTop < b.y;
            const expandRight = newRight > b.x + b.width;
            const expandBottom = newBottom > b.y + b.height;

            if (expandLeft || expandTop || expandRight || expandBottom) {
                // Calculate new bounds
                const newBounds = {
                    x: Math.min(b.x, newLeft),
                    y: Math.min(b.y, newTop),
                    width: Math.max(b.x + b.width, newRight) - Math.min(b.x, newLeft),
                    height: Math.max(b.y + b.height, newBottom) - Math.min(b.y, newTop)
                };

                // We need to expand the beforeData to include new regions
                // Create new larger ImageData and copy existing data
                const newBeforeData = this.expandImageData(
                    data.beforeData, data.bounds,
                    newBounds, layer
                );

                data.bounds = newBounds;
                data.beforeData = newBeforeData;
            }
        }
    }

    /**
     * Expand ImageData to cover a larger region, filling new areas from layer.
     */
    expandImageData(oldData, oldBounds, newBounds, layer) {
        const newData = layer.ctx.createImageData(newBounds.width, newBounds.height);

        // Get the current pixels from the layer for the new region
        // (these are the "before" pixels that we haven't captured yet)
        const layerData = layer.ctx.getImageData(
            newBounds.x, newBounds.y,
            newBounds.width, newBounds.height
        );

        // Copy layer data as base
        newData.data.set(layerData.data);

        // Now overlay the old beforeData at the correct offset
        const offsetX = oldBounds.x - newBounds.x;
        const offsetY = oldBounds.y - newBounds.y;

        for (let y = 0; y < oldBounds.height; y++) {
            for (let x = 0; x < oldBounds.width; x++) {
                const oldIdx = (y * oldBounds.width + x) * 4;
                const newIdx = ((y + offsetY) * newBounds.width + (x + offsetX)) * 4;

                newData.data[newIdx] = oldData.data[oldIdx];
                newData.data[newIdx + 1] = oldData.data[oldIdx + 1];
                newData.data[newIdx + 2] = oldData.data[oldIdx + 2];
                newData.data[newIdx + 3] = oldData.data[oldIdx + 3];
            }
        }

        return newData;
    }

    /**
     * Record that a structural change will occur (layer add/delete/reorder).
     */
    beginStructuralChange() {
        if (!this.currentCapture) {
            this.beginCapture('Layer Change', []);
        }
        const doc = this.app.documentManager?.getActiveDocument();
        this.currentCapture.structureBefore = new LayerStructureSnapshot(this.app.layerStack, doc);
    }

    /**
     * Capture a structure snapshot that can be stored and used later.
     * Use with setStructureBefore() for deferred history capture.
     * @returns {LayerStructureSnapshot}
     */
    captureStructureSnapshot() {
        const doc = this.app.documentManager?.getActiveDocument();
        return new LayerStructureSnapshot(this.app.layerStack, doc);
    }

    /**
     * Set a pre-captured snapshot as the "before" state.
     * Use this when you need to capture state before changes, then commit later.
     * @param {LayerStructureSnapshot} snapshot - Previously captured snapshot
     */
    setStructureBefore(snapshot) {
        if (!this.currentCapture) {
            this.beginCapture('Layer Change', []);
        }
        this.currentCapture.structureBefore = snapshot;
    }

    /**
     * Capture effects state for a specific layer (before changes).
     * More efficient than full structure snapshot for effect-only changes.
     * @param {string} layerId - The layer ID
     * @param {Array} effectsBefore - Serialized effects array from before changes
     */
    captureEffectsBefore(layerId, effectsBefore) {
        if (!this.currentCapture) {
            this.beginCapture('Modify Layer Effects', []);
        }
        this.currentCapture.effectsChange = {
            layerId,
            before: effectsBefore
        };
    }

    /**
     * Store a layer that will be deleted (for undo).
     */
    async storeDeletedLayer(layer) {
        if (!this.currentCapture?.structureBefore) {
            this.beginStructuralChange();
        }
        await this.currentCapture.structureBefore.storeDeletedLayer(layer);
    }

    /**
     * Store a layer that will be resized (for undo).
     * This captures the full layer content before resize.
     */
    async storeResizedLayer(layer) {
        if (!this.currentCapture?.structureBefore) {
            this.beginStructuralChange();
        }
        await this.currentCapture.structureBefore.storeResizedLayer(layer);
    }

    /**
     * Commit the current capture, creating a history entry.
     * Call this AFTER all modifications are complete.
     */
    commitCapture() {
        if (!this.currentCapture) return;

        const entry = new HistoryEntry(this.currentCapture.action);

        // Track layers that need auto-fit - these use structural changes, not patches
        const layersToFit = [];

        // First pass: identify pixel layers with fitToContent - ALL pixel layers auto-fit
        for (const [layerId, data] of this.currentCapture.layers) {
            const layer = this.app.layerStack.getLayerById(layerId);
            if (!layer) continue;
            if (!layer.ctx) continue;

            // All pixel layers with fitToContent method need auto-fit handling
            if (layer.fitToContent) {
                layersToFit.push({ layerId, layer, data });
            }
        }

        // For layers that will auto-fit, capture the "before" state using structural changes
        // This stores the full layer data including current bounds
        if (layersToFit.length > 0 && !this.currentCapture.structureBefore) {
            const doc = this.app.documentManager?.getActiveDocument();
            this.currentCapture.structureBefore = new LayerStructureSnapshot(this.app.layerStack, doc);
        }

        if (layersToFit.length > 0) {
            // Store full layer data for layers BEFORE any modifications
            // We need to use the snapshot canvas taken in beginCapture, not the current layer state
            for (const { layerId, layer, data } of layersToFit) {
                // Get the original dimensions and snapshot from beginCapture
                const snapshotCanvas = data.snapshotCanvas;
                const originalBounds = data.originalBounds;

                if (snapshotCanvas && originalBounds) {
                    // Serialize using the original snapshot data
                    const serialized = {
                        ...layer.serialize(),  // Get base layer properties
                        // Override with original dimensions and offset
                        width: originalBounds.width,
                        height: originalBounds.height,
                        offsetX: originalBounds.offsetX ?? layer.offsetX,
                        offsetY: originalBounds.offsetY ?? layer.offsetY,
                    };
                    // Re-encode the snapshot canvas as imageData
                    if (originalBounds.width > 0 && originalBounds.height > 0) {
                        serialized.imageData = snapshotCanvas.toDataURL('image/png');
                    } else {
                        serialized.imageData = '';
                    }
                    this.currentCapture.structureBefore.resizedLayers.set(layer.id, serialized);
                    if (originalBounds.width && originalBounds.height) {
                        this.currentCapture.structureBefore.memorySize += originalBounds.width * originalBounds.height * 4;
                    }
                } else {
                    // Fallback: use current layer serialization
                    const serialized = layer.serialize();
                    this.currentCapture.structureBefore.resizedLayers.set(layer.id, serialized);
                    if (layer.width && layer.height) {
                        this.currentCapture.structureBefore.memorySize += layer.width * layer.height * 4;
                    }
                }
            }
        }

        // Apply fitToContent to all pixel layers BEFORE capturing patches/after state
        for (const { layer } of layersToFit) {
            layer.fitToContent();
        }

        // Create set of layer IDs that use structural changes (all pixel layers)
        const structuralLayerIds = new Set(layersToFit.map(l => l.layerId));

        // Create patches for non-pixel layers only
        // Pixel layers use structural changes for full state preservation (auto-fit)
        for (const [layerId, data] of this.currentCapture.layers) {
            const layer = this.app.layerStack.getLayerById(layerId);
            if (!layer) continue;

            // Skip non-pixel layers
            if (!layer.ctx) continue;

            // Skip pixel layers - they use structural changes instead (all layers auto-fit)
            if (structuralLayerIds.has(layerId)) continue;

            const bounds = data.bounds;
            const afterData = layer.ctx.getImageData(
                bounds.x, bounds.y,
                bounds.width, bounds.height
            );

            // Get beforeData - either from direct capture or from deferred snapshot
            let beforeData = data.beforeData;
            if (!beforeData && data.snapshotCanvas) {
                // Deferred capture: extract beforeData from snapshot now
                const snapshotCtx = data.snapshotCanvas.getContext('2d');
                beforeData = snapshotCtx.getImageData(
                    bounds.x, bounds.y,
                    bounds.width, bounds.height
                );
                // Clean up snapshot canvas
                data.snapshotCanvas = null;
            }

            if (!beforeData) continue;

            // Only create patch if pixels actually changed
            if (!this.imageDataEquals(beforeData, afterData)) {
                // Optionally shrink bounds to actual changes
                const tightBounds = this.shrinkToChanges(beforeData, afterData, bounds);

                if (tightBounds) {
                    const tightBefore = this.extractRegion(beforeData, bounds, tightBounds);
                    const tightAfter = this.extractRegion(afterData, bounds, tightBounds);

                    const patch = new HistoryPatch(
                        layerId,
                        tightBounds.x, tightBounds.y,
                        tightBounds.width, tightBounds.height,
                        tightBefore,
                        tightAfter
                    );
                    entry.addPatch(patch);
                }
            }
        }

        // Handle structural changes
        if (this.currentCapture.structureBefore) {
            const doc = this.app.documentManager?.getActiveDocument();
            const afterSnapshot = new LayerStructureSnapshot(this.app.layerStack, doc);

            // If there were resized layers, also store their current (after) state for redo
            if (this.currentCapture.structureBefore.resizedLayers.size > 0) {
                for (const [layerId] of this.currentCapture.structureBefore.resizedLayers) {
                    const layer = this.app.layerStack.getLayerById(layerId);
                    if (layer) {
                        const serialized = layer.serialize();
                        afterSnapshot.resizedLayers.set(layerId, serialized);
                        // Update memory estimate
                        if (layer.width && layer.height) {
                            afterSnapshot.memorySize += layer.width * layer.height * 4;
                        }
                    }
                }
            }

            entry.layerStructure = {
                before: this.currentCapture.structureBefore,
                after: afterSnapshot
            };
        }

        // Handle effects-only changes (more efficient than full structure)
        if (this.currentCapture.effectsChange) {
            const { layerId, before } = this.currentCapture.effectsChange;
            const layer = this.app.layerStack.getLayerById(layerId);
            if (layer) {
                const after = layer.effects ? layer.effects.map(e => e.serialize()) : [];
                entry.effectsChange = { layerId, before, after };
            }
        }

        // Only add entry if something changed
        if (entry.patches.length > 0 || entry.layerStructure || entry.effectsChange) {
            this.pushEntry(entry);
        }

        this.currentCapture = null;
    }

    /**
     * Abort the current capture without creating an entry.
     */
    abortCapture() {
        this.currentCapture = null;
    }

    // ========== Legacy API (simple full-layer snapshots) ==========

    /**
     * Save current state to history (legacy API for simple operations).
     * This captures full layer states - use beginCapture/commitCapture for better performance.
     *
     * @param {string} [action='edit'] - Description of the action
     */
    saveState(action = 'edit') {
        try {
            const activeLayer = this.app.layerStack.getActiveLayer();
            if (!activeLayer) {
                console.warn('History.saveState: no active layer');
                return;
            }

            // For vector/SVG layers, use structural changes instead of pixel patches
            if (activeLayer.isVector?.() || activeLayer.isSVG?.()) {
                this.beginCapture(action, []);
                this.beginStructuralChange();
            } else {
                // Use patch-based capture for pixel layers
                this.beginCapture(action, [activeLayer.id]);
            }
        } catch (e) {
            console.error('History.saveState error:', e);
        }
    }

    /**
     * Mark the end of an operation started with saveState.
     * Call this after modifications are complete.
     */
    finishState() {
        this.commitCapture();
    }

    // ========== Stack Management ==========

    /**
     * Push an entry to the undo stack with limit enforcement.
     */
    pushEntry(entry) {
        // Clear redo stack
        this.clearRedoStack();

        // Enforce memory limit
        while (this.totalMemory + entry.memorySize > this.maxMemoryBytes &&
               this.undoStack.length > 0) {
            const removed = this.undoStack.shift();
            this.totalMemory -= removed.memorySize;
        }

        // Enforce entry count limit
        while (this.undoStack.length >= this.maxEntries) {
            const removed = this.undoStack.shift();
            this.totalMemory -= removed.memorySize;
        }

        // Add the new entry
        this.undoStack.push(entry);
        this.totalMemory += entry.memorySize;

        this.app.eventBus.emit('history:changed', this.getStatus());
    }

    /**
     * Clear the redo stack and reclaim memory.
     */
    clearRedoStack() {
        for (const entry of this.redoStack) {
            this.totalMemory -= entry.memorySize;
        }
        this.redoStack = [];
    }

    // ========== Undo/Redo Operations ==========

    /**
     * Undo the last action.
     */
    async undo() {
        if (this.undoStack.length === 0) return false;

        const entry = this.undoStack.pop();
        this.totalMemory -= entry.memorySize;

        // Apply patches in reverse (restore beforeData)
        for (const patch of entry.patches) {
            const layer = this.app.layerStack.getLayerById(patch.layerId);
            if (layer) {
                layer.ctx.putImageData(patch.beforeData, patch.x, patch.y);
            }
        }

        // Handle structural changes
        if (entry.layerStructure) {
            await this.restoreLayerStructure(entry.layerStructure.before);
        }

        // Handle effects-only changes (restore "before" state)
        if (entry.effectsChange) {
            this.restoreLayerEffects(entry.effectsChange.layerId, entry.effectsChange.before);
        }

        // Move to redo stack
        this.redoStack.push(entry);
        this.totalMemory += entry.memorySize;

        this.app.renderer.requestRender();
        this.app.eventBus.emit('history:changed', this.getStatus());
        this.app.eventBus.emit('layers:restored');
        return true;
    }

    /**
     * Redo the last undone action.
     */
    async redo() {
        if (this.redoStack.length === 0) return false;

        const entry = this.redoStack.pop();
        this.totalMemory -= entry.memorySize;

        // Apply patches forward (restore afterData)
        for (const patch of entry.patches) {
            const layer = this.app.layerStack.getLayerById(patch.layerId);
            if (layer) {
                layer.ctx.putImageData(patch.afterData, patch.x, patch.y);
            }
        }

        // Handle structural changes
        if (entry.layerStructure) {
            await this.restoreLayerStructure(entry.layerStructure.after);
        }

        // Handle effects-only changes (restore "after" state)
        if (entry.effectsChange) {
            this.restoreLayerEffects(entry.effectsChange.layerId, entry.effectsChange.after);
        }

        // Move back to undo stack
        this.undoStack.push(entry);
        this.totalMemory += entry.memorySize;

        this.app.renderer.requestRender();
        this.app.eventBus.emit('history:changed', this.getStatus());
        this.app.eventBus.emit('layers:restored');
        return true;
    }

    /**
     * Restore effects for a specific layer from serialized data.
     * @param {string} layerId - The layer ID
     * @param {Array} serializedEffects - Array of serialized effect objects
     */
    restoreLayerEffects(layerId, serializedEffects) {
        const layer = this.app.layerStack.getLayerById(layerId);
        if (!layer) return;

        layer.effects = serializedEffects
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);
        layer._effectCacheVersion = (layer._effectCacheVersion || 0) + 1;
    }

    /**
     * Restore layer structure from a snapshot.
     * Handles layers, vector layers, and groups.
     */
    async restoreLayerStructure(snapshot) {
        const layerStack = this.app.layerStack;

        // First, restore any resized layers from full serialized data
        if (snapshot.resizedLayers && snapshot.resizedLayers.size > 0) {
            for (const [layerId, serialized] of snapshot.resizedLayers) {
                const existingLayer = layerStack.getLayerById(layerId);
                if (existingLayer) {
                    // Restore from serialized data
                    const restoredLayer = await this.deserializeLayer(serialized);
                    if (restoredLayer) {
                        // Copy restored content to existing layer
                        existingLayer.width = restoredLayer.width;
                        existingLayer.height = restoredLayer.height;
                        existingLayer.offsetX = restoredLayer.offsetX ?? 0;
                        existingLayer.offsetY = restoredLayer.offsetY ?? 0;

                        // For pixel layers with ctx, restore canvas content
                        if (existingLayer.ctx && existingLayer.canvas && restoredLayer.canvas) {
                            existingLayer.canvas.width = restoredLayer.width;
                            existingLayer.canvas.height = restoredLayer.height;
                            existingLayer.ctx.drawImage(restoredLayer.canvas, 0, 0);
                        }
                        // For SVG layers (use internal canvas)
                        else if (existingLayer._canvas && existingLayer._ctx && restoredLayer._canvas) {
                            existingLayer._canvas.width = restoredLayer.width;
                            existingLayer._canvas.height = restoredLayer.height;
                            existingLayer._ctx.drawImage(restoredLayer._canvas, 0, 0);
                            // For SVG layers, also restore svgContent if available
                            if (restoredLayer.svgContent !== undefined) {
                                existingLayer.svgContent = restoredLayer.svgContent;
                                existingLayer.naturalWidth = restoredLayer.naturalWidth;
                                existingLayer.naturalHeight = restoredLayer.naturalHeight;
                            }
                            await existingLayer.render?.();
                        }

                        existingLayer.invalidateImageCache?.();
                        existingLayer.invalidateEffectCache?.();
                    }
                }
            }
        }

        // Restore layer metadata including offsets, effects, and group properties
        for (const meta of snapshot.layerMeta) {
            const layer = layerStack.getLayerById(meta.id);
            if (layer) {
                // Skip metadata restore for resized layers (already fully restored above)
                if (snapshot.resizedLayers?.has(meta.id)) {
                    continue;
                }

                layer.name = meta.name;
                layer.parentId = meta.parentId || null;
                layer.offsetX = meta.offsetX ?? 0;
                layer.offsetY = meta.offsetY ?? 0;
                layer.rotation = meta.rotation ?? 0;
                layer.scaleX = meta.scaleX ?? 1;
                layer.scaleY = meta.scaleY ?? 1;
                layer.opacity = meta.opacity;
                layer.blendMode = meta.blendMode;
                layer.visible = meta.visible;
                layer.locked = meta.locked;

                // Restore group-specific properties
                if (layer.isGroup && layer.isGroup()) {
                    layer.expanded = meta.expanded ?? true;
                }

                // Restore SVG layer content
                if (meta.svgContent !== undefined && layer.type === 'svg') {
                    layer.svgContent = meta.svgContent;
                    layer.naturalWidth = meta.naturalWidth ?? 0;
                    layer.naturalHeight = meta.naturalHeight ?? 0;
                }

                // Re-render text and SVG layers after restoring rotation/offset
                if ((layer.isText?.() || layer.isSVG?.()) && layer.render) {
                    layer.render();
                }

                // Restore effects
                if (meta.effects) {
                    layer.effects = meta.effects
                        .map(e => LayerEffect.deserialize(e))
                        .filter(e => e !== null);
                    layer._effectCacheVersion = (layer._effectCacheVersion || 0) + 1;
                }
            }
        }

        // Restore layer order
        const newOrder = [];
        for (const id of snapshot.layerOrder) {
            let layer = layerStack.getLayerById(id);
            if (layer) {
                newOrder.push(layer);
            } else if (snapshot.deletedLayers.has(id)) {
                // Recreate deleted layer/group
                const serialized = snapshot.deletedLayers.get(id);
                layer = await this.deserializeLayer(serialized);
                if (layer) {
                    newOrder.push(layer);
                }
            }
        }

        layerStack.layers = newOrder;
        layerStack.activeLayerIndex = Math.min(snapshot.activeIndex, newOrder.length - 1);

        // Restore document dimensions if snapshot has them
        if (snapshot.docWidth && snapshot.docHeight) {
            layerStack.width = snapshot.docWidth;
            layerStack.height = snapshot.docHeight;
            this.app.width = snapshot.docWidth;
            this.app.height = snapshot.docHeight;
            this.app.canvasWidth = snapshot.docWidth;
            this.app.canvasHeight = snapshot.docHeight;
            this.app.renderer?.resize(snapshot.docWidth, snapshot.docHeight);

            // Update the Document object for serialization/auto-save
            const doc = this.app.documentManager?.getActiveDocument();
            if (doc) {
                doc.width = snapshot.docWidth;
                doc.height = snapshot.docHeight;
            }
        }

        // Restore saved selections if snapshot has them
        if (snapshot.savedSelections !== null) {
            const doc = this.app.documentManager?.getActiveDocument();
            if (doc) {
                doc.savedSelections = snapshot.savedSelections.map(sel => ({
                    name: sel.name,
                    mask: new Uint8Array(sel.mask),
                    width: sel.width,
                    height: sel.height
                }));
                this.app.eventBus?.emit('selection:saved', {});
            }
        }
    }

    /**
     * Deserialize a layer from snapshot data.
     * Uses the layer registry for polymorphic deserialization.
     * @param {Object} serialized - Serialized layer data
     * @returns {Promise<Layer|LayerGroup>}
     */
    async deserializeLayer(serialized) {
        return layerRegistry.deserialize(serialized);
    }

    // ========== Utility Methods ==========

    /**
     * Check if two ImageData objects are equal.
     */
    imageDataEquals(a, b) {
        if (a.width !== b.width || a.height !== b.height) return false;
        const len = a.data.length;
        for (let i = 0; i < len; i++) {
            if (a.data[i] !== b.data[i]) return false;
        }
        return true;
    }

    /**
     * Find the tightest bounds that contain all changes.
     */
    shrinkToChanges(beforeData, afterData, bounds) {
        let minX = bounds.width, minY = bounds.height;
        let maxX = -1, maxY = -1;

        for (let y = 0; y < bounds.height; y++) {
            for (let x = 0; x < bounds.width; x++) {
                const i = (y * bounds.width + x) * 4;
                if (beforeData.data[i] !== afterData.data[i] ||
                    beforeData.data[i + 1] !== afterData.data[i + 1] ||
                    beforeData.data[i + 2] !== afterData.data[i + 2] ||
                    beforeData.data[i + 3] !== afterData.data[i + 3]) {
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        if (maxX < 0) return null; // No changes

        return {
            x: bounds.x + minX,
            y: bounds.y + minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }

    /**
     * Extract a sub-region from ImageData.
     */
    extractRegion(imageData, srcBounds, targetBounds) {
        const offsetX = targetBounds.x - srcBounds.x;
        const offsetY = targetBounds.y - srcBounds.y;
        const newData = new ImageData(targetBounds.width, targetBounds.height);

        for (let y = 0; y < targetBounds.height; y++) {
            for (let x = 0; x < targetBounds.width; x++) {
                const srcIdx = ((y + offsetY) * srcBounds.width + (x + offsetX)) * 4;
                const dstIdx = (y * targetBounds.width + x) * 4;

                newData.data[dstIdx] = imageData.data[srcIdx];
                newData.data[dstIdx + 1] = imageData.data[srcIdx + 1];
                newData.data[dstIdx + 2] = imageData.data[srcIdx + 2];
                newData.data[dstIdx + 3] = imageData.data[srcIdx + 3];
            }
        }

        return newData;
    }

    // ========== Status & Display Methods ==========

    /**
     * Get current history status.
     */
    getStatus() {
        return {
            canUndo: this.undoStack.length > 0,
            canRedo: this.redoStack.length > 0,
            undoCount: this.undoStack.length,
            redoCount: this.redoStack.length,
            memoryUsageMB: this.memoryUsageMB,
            maxMemoryMB: this.maxMemoryMB
        };
    }

    canUndo() {
        return this.undoStack.length > 0;
    }

    canRedo() {
        return this.redoStack.length > 0;
    }

    /**
     * Get all history entries for display.
     */
    getEntries() {
        const entries = [];

        // Past states (undo stack)
        for (const entry of this.undoStack) {
            entries.push({
                name: entry.action || 'Edit',
                type: this.getActionType(entry.action),
                memoryKB: Math.round(entry.memorySize / 1024),
                isCurrent: false,
                isFuture: false
            });
        }

        // Current state marker
        entries.push({
            name: 'Current State',
            type: 'current',
            memoryKB: 0,
            isCurrent: true,
            isFuture: false
        });

        // Future states (redo stack, reversed)
        for (let i = this.redoStack.length - 1; i >= 0; i--) {
            const entry = this.redoStack[i];
            entries.push({
                name: entry.action || 'Edit',
                type: this.getActionType(entry.action),
                memoryKB: Math.round(entry.memorySize / 1024),
                isCurrent: false,
                isFuture: true
            });
        }

        return entries;
    }

    getCurrentIndex() {
        return this.undoStack.length;
    }

    getUndoEntry() {
        if (this.undoStack.length === 0) return null;
        const entry = this.undoStack[this.undoStack.length - 1];
        return {
            name: entry.action || 'Edit',
            type: this.getActionType(entry.action)
        };
    }

    getRedoEntry() {
        if (this.redoStack.length === 0) return null;
        const entry = this.redoStack[this.redoStack.length - 1];
        return {
            name: entry.action || 'Edit',
            type: this.getActionType(entry.action)
        };
    }

    getActionType(action) {
        if (!action) return 'edit';
        const lower = action.toLowerCase();
        if (lower.includes('brush') || lower.includes('draw') || lower.includes('paint')) return 'brush';
        if (lower.includes('erase')) return 'erase';
        if (lower.includes('fill')) return 'fill';
        if (lower.includes('layer')) return 'layer';
        if (lower.includes('move') || lower.includes('transform')) return 'transform';
        if (lower.includes('filter')) return 'filter';
        if (lower.includes('select')) return 'selection';
        if (lower.includes('line') || lower.includes('rect') || lower.includes('circle') || lower.includes('shape')) return 'shape';
        if (lower.includes('new') || lower.includes('document')) return 'document';
        return 'edit';
    }

    /**
     * Jump to a specific history state.
     */
    async jumpTo(index) {
        const currentIndex = this.getCurrentIndex();

        if (index < currentIndex) {
            const steps = currentIndex - index;
            for (let i = 0; i < steps; i++) {
                await this.undo();
            }
        } else if (index > currentIndex) {
            const steps = index - currentIndex;
            for (let i = 0; i < steps; i++) {
                await this.redo();
            }
        }
    }

    /**
     * Clear all history.
     */
    clear() {
        this.undoStack = [];
        this.redoStack = [];
        this.totalMemory = 0;
        this.currentCapture = null;
        this.app.eventBus.emit('history:changed', this.getStatus());
    }
}
