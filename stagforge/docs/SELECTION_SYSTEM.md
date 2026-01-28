# Selection System

The selection system uses a **global alpha mask** for all selection operations. This provides consistency across all selection tools and enables advanced selection features.

## Architecture

### Core Principle

All selection tools produce a single unified alpha mask. The mask is:
- **Global**: One selection for the entire document (not per-tool)
- **Alpha-based**: Uint8Array where 0 = not selected, 255 = fully selected
- **Persistent**: Remains visible when switching between tools
- **Document-sized**: Dimensions match the document (not individual layers)

### Components

```
SelectionManager (frontend/js/core/SelectionManager.js)
├── mask: Uint8Array           # The alpha mask
├── bounds: {x,y,w,h}          # Cached bounding box
├── outlinePolygons: Array     # Cached marching ants paths
└── antOffset: number          # Animation state

Selection Tools
├── SelectionTool (rectangular)  → generates mask
├── LassoTool (freeform)         → generates mask
├── MagicWandTool (color-based)  → generates mask
└── PolygonTool (future)         → generates mask

Operations (use mask)
├── Copy (Ctrl+C)
├── Cut (Ctrl+X)
├── Delete (Del)
├── Fill (bucket tool)
└── Filters
```

## SelectionManager API

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `mask` | Uint8Array | Alpha mask, length = width * height |
| `width` | number | Mask width (matches document) |
| `height` | number | Mask height (matches document) |
| `bounds` | Object | Cached bounding box {x, y, width, height} or null |
| `hasSelection` | boolean | True if any pixels are selected |

### Methods

```javascript
// Set selection from alpha mask
setMask(mask, width, height)

// Set rectangular selection
setRect(x, y, width, height)

// Set selection from polygon points
setPolygon(points)

// Set selection from flood fill result
setFloodFill(mask, width, height)

// Clear selection
clear()

// Select all
selectAll()

// Invert selection
invert()

// Get mask value at point
getMaskAt(x, y)

// Check if point is selected
isSelected(x, y)

// Get bounding box of selection
getBounds()

// Get outline polygons for marching ants
getOutlinePolygons()

// Apply selection to image data (returns masked pixels)
applyToImageData(imageData, offsetX, offsetY)

// Extract selected pixels from layer (handles transforms)
extractFromLayer(layer)

// Delete selected pixels from layer (handles transforms)
deleteFromLayer(layer)

// Restore the previous selection
reselect()
```

### Events

| Event | Data | Description |
|-------|------|-------------|
| `selection:changed` | `{ hasSelection, bounds }` | Selection mask changed |
| `selection:cleared` | `{}` | Selection was cleared |

## Mask Generation by Tool

### Rectangular Selection

```javascript
// Generate mask for rectangle
const mask = new Uint8Array(width * height);
for (let y = rect.y; y < rect.y + rect.height; y++) {
    for (let x = rect.x; x < rect.x + rect.width; x++) {
        mask[y * width + x] = 255;
    }
}
selectionManager.setMask(mask, width, height);
```

### Lasso Selection

Uses point-in-polygon test:

```javascript
// Generate mask from polygon points
const mask = new Uint8Array(width * height);
for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
        if (pointInPolygon(x, y, points)) {
            mask[y * width + x] = 255;
        }
    }
}
```

### Magic Wand Selection

Flood fill produces mask directly:

```javascript
// Flood fill already produces mask
const mask = floodSelect(imageData, startX, startY, tolerance);
selectionManager.setMask(mask, width, height);
```

## Marching Ants Visualization

The marching ants outline is derived from the alpha mask using contour tracing:

1. **Edge Detection**: Find pixels where mask transitions from 0 to 255
2. **Contour Tracing**: Follow edges to build polygon paths
3. **Rendering**: Draw paths with animated dashed stroke

```javascript
// Simplified marching squares for outline extraction
getOutlinePolygons() {
    if (!this.mask) return [];

    // Use marching squares algorithm to find contours
    const contours = marchingSquares(this.mask, this.width, this.height);
    return contours;
}
```

### Rendering

```javascript
drawMarchingAnts(ctx, docToScreen) {
    const polygons = this.getOutlinePolygons();

    ctx.setLineDash([4, 4]);

    // Black stroke
    ctx.strokeStyle = '#000000';
    ctx.lineDashOffset = -this.antOffset;
    for (const polygon of polygons) {
        this.drawPolygon(ctx, polygon, docToScreen);
    }

    // White stroke offset
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineDashOffset = -this.antOffset + 4;
    for (const polygon of polygons) {
        this.drawPolygon(ctx, polygon, docToScreen);
    }
}
```

## Operations Using Selection

### Copy (Ctrl+C)

```javascript
copy() {
    const layer = layerStack.getActiveLayer();
    const bounds = selectionManager.getBounds();
    if (!bounds) return;

    // Create clipboard canvas at selection bounds size
    const clipCanvas = document.createElement('canvas');
    clipCanvas.width = bounds.width;
    clipCanvas.height = bounds.height;
    const clipCtx = clipCanvas.getContext('2d');

    // Draw layer content
    clipCtx.drawImage(layer.canvas,
        bounds.x - layer.offsetX, bounds.y - layer.offsetY,
        bounds.width, bounds.height,
        0, 0, bounds.width, bounds.height);

    // Apply mask (clear unselected pixels)
    const imageData = clipCtx.getImageData(0, 0, bounds.width, bounds.height);
    for (let y = 0; y < bounds.height; y++) {
        for (let x = 0; x < bounds.width; x++) {
            const docX = bounds.x + x;
            const docY = bounds.y + y;
            const maskValue = selectionManager.getMaskAt(docX, docY);
            if (maskValue === 0) {
                const idx = (y * bounds.width + x) * 4;
                imageData.data[idx + 3] = 0; // Clear alpha
            }
        }
    }
    clipCtx.putImageData(imageData, 0, 0);

    clipboard.setContent(clipCanvas, bounds.x, bounds.y);
}
```

### Delete (Del)

```javascript
deleteSelection() {
    const layer = layerStack.getActiveLayer();
    const bounds = selectionManager.getBounds();
    if (!bounds) return;

    history.saveState('Delete');

    // Clear selected pixels
    const imageData = layer.ctx.getImageData(
        bounds.x - layer.offsetX, bounds.y - layer.offsetY,
        bounds.width, bounds.height
    );

    for (let y = 0; y < bounds.height; y++) {
        for (let x = 0; x < bounds.width; x++) {
            const docX = bounds.x + x;
            const docY = bounds.y + y;
            const maskValue = selectionManager.getMaskAt(docX, docY);
            if (maskValue > 0) {
                const idx = (y * bounds.width + x) * 4;
                imageData.data[idx] = 0;
                imageData.data[idx + 1] = 0;
                imageData.data[idx + 2] = 0;
                imageData.data[idx + 3] = 0;
            }
        }
    }

    layer.ctx.putImageData(imageData,
        bounds.x - layer.offsetX, bounds.y - layer.offsetY);

    history.finishState();
}
```

## Selection Menu

**Select Menu:**
- Select All (Ctrl+A)
- Deselect (Ctrl+D)
- Reselect (Ctrl+Shift+D) - restore last selection
- Inverse (Ctrl+Shift+I)
- ---
- Feather... (future)
- Modify > Expand... (future)
- Modify > Contract... (future)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+A | Select All |
| Ctrl+D | Deselect |
| Ctrl+Shift+D | Reselect (restore last) |
| Ctrl+Shift+I | Inverse selection |
| Delete | Delete selected pixels |
| Ctrl+C | Copy selected pixels |
| Ctrl+X | Cut selected pixels |

## Implementation Files

| File | Purpose |
|------|---------|
| `frontend/js/core/SelectionManager.js` | Core selection manager class |
| `frontend/js/core/MarchingSquares.js` | Contour extraction algorithm |
| `frontend/js/tools/SelectionTool.js` | Rectangular selection |
| `frontend/js/tools/LassoTool.js` | Freeform selection |
| `frontend/js/tools/MagicWandTool.js` | Color-based selection |
| `frontend/js/editor/mixins/SelectionOperations.js` | Copy/cut/delete operations |

## Layer Coordinate Handling

The selection mask is in **document coordinates**. When applying to layers:

```javascript
// Convert document coords to layer-local coords
const layerX = docX - layer.offsetX;
const layerY = docY - layer.offsetY;

// For transformed layers
if (layer.hasTransform()) {
    const local = layer.docToLayer(docX, docY);
    layerX = local.x;
    layerY = local.y;
}
```

### Transformed Layer Support

Selection operations (copy, cut, delete) work correctly on rotated and scaled layers. The key is using `layer.rasterizeToDocument()` to handle transforms.

See [LAYER_TRANSFORMS.md](./LAYER_TRANSFORMS.md) for detailed documentation on:
- `getDocumentBounds()` - Get axis-aligned bounding box
- `rasterizeToDocument()` - Render layer to document space with transforms
- `docToLayer()` / `layerToDoc()` - Coordinate conversion

### extractFromLayer(layer)

Extracts selected pixels from a layer, handling transforms correctly:

```javascript
extractFromLayer(layer) {
    const bounds = this.getBounds();
    if (!bounds) return null;

    // Rasterize layer to document space (handles rotation/scale)
    const rasterized = layer.rasterizeToDocument(bounds);

    // Create extraction canvas at selection bounds size
    const extractCanvas = document.createElement('canvas');
    extractCanvas.width = bounds.width;
    extractCanvas.height = bounds.height;
    const extractCtx = extractCanvas.getContext('2d');

    // Draw rasterized content at correct position
    const drawX = rasterized.bounds.x - bounds.x;
    const drawY = rasterized.bounds.y - bounds.y;
    extractCtx.drawImage(rasterized.canvas, drawX, drawY);

    // Apply selection mask (clear unselected pixels)
    const imageData = extractCtx.getImageData(0, 0, bounds.width, bounds.height);
    for (let y = 0; y < bounds.height; y++) {
        for (let x = 0; x < bounds.width; x++) {
            const maskValue = this.getMaskAt(bounds.x + x, bounds.y + y);
            if (maskValue === 0) {
                const idx = (y * bounds.width + x) * 4;
                imageData.data[idx + 3] = 0;
            }
        }
    }
    extractCtx.putImageData(imageData, 0, 0);

    return { canvas: extractCanvas, imageData, bounds };
}
```

### deleteFromLayer(layer)

Deletes selected pixels from a layer, handling transforms:

```javascript
deleteFromLayer(layer) {
    const bounds = this.getBounds();
    if (!bounds) return;

    // Check if layer overlaps selection bounds
    const layerBounds = layer.getDocumentBounds?.() || {
        x: layer.offsetX, y: layer.offsetY,
        width: layer.width, height: layer.height
    };

    // Calculate overlap region
    const overlapX = Math.max(bounds.x, layerBounds.x);
    const overlapY = Math.max(bounds.y, layerBounds.y);
    const overlapX2 = Math.min(bounds.x + bounds.width, layerBounds.x + layerBounds.width);
    const overlapY2 = Math.min(bounds.y + bounds.height, layerBounds.y + layerBounds.height);

    if (overlapX >= overlapX2 || overlapY >= overlapY2) return;

    // For each pixel in overlap, convert to layer coords and clear
    const hasTransform = layer.hasTransform?.();
    const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);

    for (let docY = overlapY; docY < overlapY2; docY++) {
        for (let docX = overlapX; docX < overlapX2; docX++) {
            const maskValue = this.getMaskAt(docX, docY);
            if (maskValue === 0) continue;

            // Convert document coords to layer-local coords
            let layerX, layerY;
            if (hasTransform && layer.docToLayer) {
                const local = layer.docToLayer(docX, docY);
                layerX = Math.round(local.x);
                layerY = Math.round(local.y);
            } else {
                layerX = docX - layer.offsetX;
                layerY = docY - layer.offsetY;
            }

            // Clear pixel if within layer bounds
            if (layerX >= 0 && layerX < layer.width &&
                layerY >= 0 && layerY < layer.height) {
                const idx = (layerY * layer.width + layerX) * 4;
                imageData.data[idx] = 0;
                imageData.data[idx + 1] = 0;
                imageData.data[idx + 2] = 0;
                imageData.data[idx + 3] = 0;
            }
        }
    }

    layer.ctx.putImageData(imageData, 0, 0);
}
```

**Note:** After cut operations, `trimToContent()` is called but skipped for transformed layers to prevent position drift. See [LAYER_TRANSFORMS.md](./LAYER_TRANSFORMS.md#trimtocontent-behavior).

## Future Extensions

### Feathered Selections
The alpha mask supports values 0-255, enabling soft/feathered edges:
```javascript
// Feather by distance from edge
mask[idx] = Math.max(0, 255 - distance * featherAmount);
```

### Selection Channels
Store named selections for later use:
```javascript
selectionManager.saveChannel('highlights');
selectionManager.loadChannel('highlights');
```

### Selection from Layer
Create selection from layer transparency:
```javascript
selectionManager.fromLayerAlpha(layer);
```
