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
