# History System (Undo/Redo)

## Overview

The history system provides efficient undo/redo through automatic pixel diff detection. Tools don't need to track affected regions - the system handles all diffing automatically.

## Design Principles

### Automatic Diff Detection
Instead of storing full layer snapshots (memory-intensive), the system:
1. Captures layer state before modification
2. Compares before/after pixels automatically
3. Stores only the changed region (minimal bounding box)

### Simple Tool API
Tools use just two methods:
```javascript
// Before modifying pixels
this.app.history.saveState('Action Name');

// After modifying pixels
this.app.history.finishState();
```

The history system handles all optimization internally.

## Memory Efficiency

| Operation | Naive (Full Snapshot) | Optimized (Auto-Diff) |
|-----------|----------------------|----------------------|
| Small brush stroke | 8.3 MB | ~80 KB |
| Large brush stroke | 8.3 MB | ~2 MB |
| Fill (depends on area) | 8.3 MB | 0.5-4 MB |
| Filter on full layer | 8.3 MB | 8.3 MB |
| Filter on selection | 8.3 MB | Selection size only |
| Add empty layer | 8.3 MB | ~1 KB (metadata) |

## Data Structures

### HistoryPatch
Stores changed pixels for a single layer:
```javascript
{
    layerId: string,      // Which layer was affected
    x: number,            // Top-left X of changed region
    y: number,            // Top-left Y of changed region
    width: number,        // Width of changed region
    height: number,       // Height of changed region
    beforeData: ImageData,// Pixels before (for undo)
    afterData: ImageData  // Pixels after (for redo)
}
```

### HistoryEntry
Complete entry for one user action:
```javascript
{
    action: string,       // "Brush Stroke", "Fill", etc.
    timestamp: number,
    patches: [],          // Array of HistoryPatch
    layerStructure: null  // For add/delete/reorder operations
}
```

## API Reference

### Core Methods

| Method | Description |
|--------|-------------|
| `saveState(actionName)` | Capture layer state before modification |
| `finishState()` | Calculate diff and create history entry |
| `undo()` | Revert to previous state |
| `redo()` | Re-apply reverted change |

### Layer Structure Methods

| Method | Description |
|--------|-------------|
| `beginStructuralChange(actionName)` | Start tracking layer add/delete/reorder |
| `commitStructuralChange()` | Finish structural change |
| `captureStructureSnapshot()` | Get current layer structure for deferred commit |
| `setStructureBefore(snapshot)` | Set the "before" state for comparison |

### Layer Effects Methods

| Method | Description |
|--------|-------------|
| `captureEffectsBefore(layerId, effectsBefore)` | Capture effects state for a specific layer |
| `commitCapture()` | Commit the pending capture (effects or structure) |
| `restoreLayerEffects(layerId, serializedEffects)` | Restore effects from serialized data |

### Status Methods

| Method | Description |
|--------|-------------|
| `getStatus()` | Get undo/redo availability and memory usage |
| `canUndo()` | Returns true if undo is available |
| `canRedo()` | Returns true if redo is available |

## Usage in Tools

### Drawing Tools
```javascript
onMouseDown(e, x, y) {
    this.app.history.saveState('Brush Stroke');
    this.isDrawing = true;
}

onMouseMove(e, x, y) {
    if (!this.isDrawing) return;
    // Just draw - no history calls needed during drawing
    this.drawLine(layer, this.lastX, this.lastY, x, y);
}

onMouseUp(e, x, y) {
    if (this.isDrawing) {
        this.isDrawing = false;
        this.app.history.finishState();  // Diff calculated automatically
    }
}
```

### Fill Operations
```javascript
onMouseDown(e, x, y) {
    this.app.history.saveState('Fill');
    this.floodFill(layer, x, y);  // Fill can spread anywhere
    this.app.history.finishState();  // Diff finds exact filled region
}
```

### Filters
```javascript
async applyFilter(filterId, params) {
    this.app.history.saveState(`Filter: ${filterId}`);
    await backend.applyFilter(filterId, layer, params);
    this.app.history.finishState();
}
```

### Layer Effects Panel
```javascript
// When opening effects panel - capture initial state
showEffectsPanel(layer) {
    this._effectsLayerId = layer.id;
    this._effectsBefore = layer.effects
        ? layer.effects.map(e => e.serialize())
        : [];
    // ... show UI
}

// When closing effects panel - commit if changed
closeEffectsPanel() {
    const layer = this.app.layerStack.getLayerById(this._effectsLayerId);
    if (!layer) return;

    const effectsAfter = layer.effects
        ? layer.effects.map(e => e.serialize())
        : [];

    // Only create history entry if something changed
    if (JSON.stringify(this._effectsBefore) !== JSON.stringify(effectsAfter)) {
        this.app.history.beginCapture('Modify Layer Effects', []);
        this.app.history.captureEffectsBefore(this._effectsLayerId, this._effectsBefore);
        this.app.history.commitCapture();
        this.app.documentManager?.getActiveDocument()?.markModified();
    }

    this._effectsLayerId = null;
    this._effectsBefore = null;
}
```

## Memory Management

### Configuration
```javascript
const history = new History(app, {
    maxEntries: 50,      // Max undo steps
    maxMemoryMB: 256     // Memory cap
});
```

### Automatic Eviction
When limits are exceeded, oldest entries are discarded automatically.

## Layer Structure Changes

For add/delete/reorder operations, the system stores:
- Layer order (array of IDs)
- Active layer ID
- Layer metadata (name, opacity, blendMode, etc.)
- Full pixel data only for deleted layers

## Events

The history system emits events for UI updates:
- `history:changed` - Undo/redo state changed
- `layers:restored` - Layers restored from history

## Layer Effects Changes

Layer effects (drop shadow, stroke, glow, etc.) use a specialized history mechanism that captures only the effects for the specific layer being modified, rather than full structure snapshots.

### Efficient Effects Tracking

Instead of storing the entire layer structure, effects changes store only:
- The layer ID
- Serialized effects before the change
- Serialized effects after the change

This provides significant memory savings when users frequently modify effects.

### HistoryEntry for Effects

```javascript
{
    action: "Modify Layer Effects",
    timestamp: number,
    patches: [],           // Empty for effects-only changes
    layerStructure: null,  // Not used for effects
    effectsChange: {       // NEW: Layer-specific effects
        layerId: string,
        before: [],        // Serialized effects before
        after: []          // Serialized effects after
    }
}
```

### How Effects History Works

1. **Panel Opens**: Capture initial effects state for the layer
   ```javascript
   const effectsBefore = layer.effects.map(e => e.serialize());
   app.history.captureEffectsBefore(layer.id, effectsBefore);
   ```

2. **User Modifies Effects**: Changes made in the effects panel (add, remove, modify)

3. **Panel Closes**: Compare and commit if changed
   ```javascript
   const effectsAfter = layer.effects.map(e => e.serialize());
   if (JSON.stringify(effectsBefore) !== JSON.stringify(effectsAfter)) {
       app.history.commitCapture();
       document.markModified();  // Triggers auto-save
   }
   ```

### Undo/Redo for Effects

When undoing/redoing effects changes:
```javascript
// Undo: Restore effects to "before" state
restoreLayerEffects(entry.effectsChange.layerId, entry.effectsChange.before);

// Redo: Restore effects to "after" state
restoreLayerEffects(entry.effectsChange.layerId, entry.effectsChange.after);
```

The `restoreLayerEffects` method:
1. Finds the layer by ID
2. Deserializes each effect using `LayerEffect.deserialize()`
3. Replaces the layer's effects array
4. Invalidates the effect cache to trigger re-render

### Benefits

| Approach | Memory per Entry | Complexity |
|----------|-----------------|------------|
| Full structure snapshot | ~50KB+ | High |
| Layer-specific effects | ~1-5KB | Low |

### Multiple Changes = Single Entry

All changes made while the effects panel is open (adding effects, modifying parameters, removing effects) result in a **single history entry** when the panel closes. This matches user expectations - "undo" reverts all changes from that editing session.

## Layer Groups

Layer groups are tracked in history through enhanced structure snapshots:

### LayerStructureSnapshot

Structure snapshots now include group-specific properties:

```javascript
{
    layerMeta: [
        {
            id: string,
            name: string,
            type: 'raster' | 'vector' | 'text' | 'group',
            parentId: string | null,  // Parent group ID
            expanded: boolean,        // For groups only
            opacity: number,
            blendMode: string,
            visible: boolean,
            locked: boolean
        }
    ],
    activeLayerIndex: number,
    deletedLayers: Map  // Serialized data for recreating deleted layers
}
```

### Tracked Operations

All group operations are undoable:

- Creating groups (`createGroup`, `createGroupFromLayers`)
- Deleting groups (`deleteGroup`)
- Moving layers to/from groups (`moveLayerToGroup`, `removeLayerFromGroup`)
- Ungrouping (`ungroupLayers`)
- Reordering layers (`moveLayerUp`, `moveLayerDown`, `moveLayerToTop`, `moveLayerToBottom`)
- Toggling visibility (`toggleLayerVisibility`)
- Changing properties (`setLayerOpacity`, `setLayerBlendMode`, `toggleLayerLock`)

### Restoring Groups

When undoing/redoing:

1. `restoreLayerStructure()` checks the `type` field
2. Groups are recreated via `LayerGroup.deserialize()`
3. `parentId` relationships are restored
4. `expanded` state is restored for groups

```javascript
// In restoreLayerStructure()
if (type === 'group' || type === 'LayerGroup') {
    return LayerGroup.deserialize(serialized);
} else if (type === 'svg' || type === 'StaticSVGLayer') {
    return StaticSVGLayer.deserialize(serialized);
} else {
    return Layer.deserialize(serialized);
}
```

## Status Information

```javascript
history.getStatus()
// Returns:
{
    canUndo: boolean,
    canRedo: boolean,
    undoCount: number,
    redoCount: number,
    memoryUsedMB: number,
    memoryMaxMB: number,
    memoryPercent: number
}
```
