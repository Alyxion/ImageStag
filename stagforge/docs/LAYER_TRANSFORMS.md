# Layer Transforms

Stagforge supports layer transformations including rotation and scaling. This document covers the architecture, coordinate systems, and critical implementation details learned from solving painting issues on transformed layers.

## Transform Properties

Each layer has transform properties stored directly on the layer:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `rotation` | number | 0 | Rotation in degrees (clockwise) |
| `scaleX` | number | 1 | Horizontal scale factor |
| `scaleY` | number | 1 | Vertical scale factor |

### Rotation Pivot

**Critical:** Rotation and scaling occur around the layer's **canvas center**, not its top-left corner:

```
Pivot point = (offsetX + width/2, offsetY + height/2)
```

This means when a layer rotates:
- The canvas center stays fixed in document space
- The corners sweep out in an arc
- The layer's bounding box in document space becomes larger

### Checking for Transforms

```javascript
// Check if layer has any transformation applied
if (layer.hasTransform()) {
    // Layer is rotated or scaled
}

// hasTransform() implementation
hasTransform() {
    return this.rotation !== 0 || this.scaleX !== 1 || this.scaleY !== 1;
}
```

## Coordinate Systems

Understanding coordinate systems is essential for working with transformed layers.

### Document Coordinates

- Absolute position in the document
- Origin at document top-left (0, 0)
- Used by: tools, selections, mouse events
- **Never change** during layer modifications

### Layer Canvas Coordinates

- Position relative to layer's top-left corner
- Origin at (0, 0) within the layer's canvas
- Used by: canvas drawing operations (ctx.fillRect, etc.)
- **Change when layer expands** (offset changes)

### Coordinate Conversion

```javascript
// Document → Layer (where to draw on the canvas)
const local = layer.docToLayer(docX, docY);
// local.x, local.y are canvas coordinates

// Layer → Document (where a canvas point appears in the document)
const doc = layer.layerToDoc(canvasX, canvasY);
// doc.x, doc.y are document coordinates
```

### Transform Math

For a layer with rotation θ and scale (sx, sy):

**Document to Layer:**
```javascript
docToLayer(docX, docY) {
    const centerX = this.offsetX + this.width / 2;
    const centerY = this.offsetY + this.height / 2;

    // Translate to origin
    let x = docX - centerX;
    let y = docY - centerY;

    // Reverse rotation
    const radians = (-this.rotation * Math.PI) / 180;
    const cos = Math.cos(radians);
    const sin = Math.sin(radians);
    const rotX = x * cos - y * sin;
    const rotY = x * sin + y * cos;

    // Reverse scale and translate to canvas coords
    return {
        x: rotX / this.scaleX + this.width / 2,
        y: rotY / this.scaleY + this.height / 2
    };
}
```

**Layer to Document:**
```javascript
layerToDoc(canvasX, canvasY) {
    // Translate to center
    let x = (canvasX - this.width / 2) * this.scaleX;
    let y = (canvasY - this.height / 2) * this.scaleY;

    // Apply rotation
    const radians = (this.rotation * Math.PI) / 180;
    const cos = Math.cos(radians);
    const sin = Math.sin(radians);
    const rotX = x * cos - y * sin;
    const rotY = x * sin + y * cos;

    // Translate to document position
    const centerX = this.offsetX + this.width / 2;
    const centerY = this.offsetY + this.height / 2;

    return {
        x: rotX + centerX,
        y: rotY + centerY
    };
}
```

## Painting Tools on Transformed Layers

This section documents critical lessons learned from fixing painting on rotated layers.

### The Core Problem

When painting on a layer, the layer canvas may need to **expand** to fit new content. For non-transformed layers, this is straightforward. For transformed layers, expansion is complex because:

1. The layer's coordinate system is rotated relative to document space
2. Changing `offsetX/offsetY` affects where the rotation pivot is
3. The layer's bounding box in document space doesn't align with the canvas edges

### Lesson 1: Store Coordinates in Document Space

**Problem:** Tools stored `lastX/lastY` in layer-local coordinates. When the layer expanded mid-stroke (changing offsets), the coordinates became stale, causing strokes to jump or create long lines to the wrong position.

**Solution:** Always store cursor positions in **document coordinates**:

```javascript
onMouseDown(e, x, y, coords) {
    // WRONG: Layer coordinates change when layer expands
    // this.lastX = x - layer.offsetX;

    // CORRECT: Document coordinates are stable
    const docX = coords?.docX ?? x;
    const docY = coords?.docY ?? y;
    this.lastX = docX;
    this.lastY = docY;
}
```

Convert to layer coordinates only at draw time, **after** any expansion:

```javascript
// Expand layer first (may change offsets)
layer.expandToIncludeDocPoint(docX, docY, brushRadius);

// Convert AFTER expansion
const local = layer.docToLayer(docX, docY);
ctx.fillRect(local.x - radius, local.y - radius, size, size);
```

### Lesson 2: Expand in Layer-Local Space

**Problem:** The standard `expandToInclude(x, y, w, h)` takes document-space bounds. For a rotated layer, these bounds don't align with the canvas edges, causing:
- Layer expanding in wrong directions
- Layer "sliding" when painting near edges
- Layer never growing when painting outside

**Solution:** Created `expandToIncludeDocPoint(docX, docY, radius)`:

1. Convert the document point to layer-local coordinates
2. Check if local point + radius fits within current canvas
3. If not, expand the canvas in layer-local space
4. Recalculate offsets to preserve the layer's position in document space

```javascript
expandToIncludeDocPoint(docX, docY, radius) {
    // For non-transformed layers, delegate to simple method
    if (!this.hasTransform()) {
        this.expandToInclude(docX - radius, docY - radius, radius * 2, radius * 2);
        return;
    }

    // Convert to layer-local coordinates
    const local = this.docToLayer(docX, docY);

    // Check bounds in local space
    const minX = Math.floor(local.x - radius);
    const minY = Math.floor(local.y - radius);
    const maxX = Math.ceil(local.x + radius);
    const maxY = Math.ceil(local.y + radius);

    // ... expand canvas if needed, recalculate offsets
}
```

### Lesson 3: Preserve Document Position After Expansion

**Problem:** After expanding a rotated layer's canvas, the layer would "jump" because the offset calculation didn't account for rotation.

**Solution:** Remember where the old content center maps in document space, then calculate new offsets to put the new canvas center at the correct position:

```javascript
// Before expansion: remember where old content center appears in doc space
const oldContentCenter = { x: this.width / 2, y: this.height / 2 };
const oldDocPos = this.layerToDoc(oldContentCenter.x, oldContentCenter.y);

// ... expand canvas, copying old content to new position (dx, dy) ...

// After expansion: calculate offset so content stays in same doc position
// The old content center is now at (oldCenterX + dx, oldCenterY + dy) in new canvas
// This point must map to oldDocPos in document space

// Calculate the delta from new canvas center to where old content is
const newCenterX = this.width / 2;
const newCenterY = this.height / 2;
let deltaX = (oldContentCenter.x + dx) - newCenterX;
let deltaY = (oldContentCenter.y + dy) - newCenterY;

// Apply scale
deltaX *= this.scaleX;
deltaY *= this.scaleY;

// Apply rotation to the delta
const radians = (this.rotation * Math.PI) / 180;
const cos = Math.cos(radians);
const sin = Math.sin(radians);
const rotatedDeltaX = deltaX * cos - deltaY * sin;
const rotatedDeltaY = deltaX * sin + deltaY * cos;

// New offset: where the new center should be, minus the rotated delta
this.offsetX = Math.round(oldDocPos.x - newCenterX - rotatedDeltaX);
this.offsetY = Math.round(oldDocPos.y - newCenterY - rotatedDeltaY);
```

### Lesson 4: Avoid Micro-Expansions

**Problem:** When painting exactly on the edge of a layer, tiny movements would trigger many small expansions. Each expansion involves `Math.round()` calls, and these rounding errors accumulate, causing visible drift.

**Solution:** Add tolerance and padding:

```javascript
// Tolerance: don't expand if point is only slightly outside
const tolerance = 5; // pixels
if (minX >= -tolerance && minY >= -tolerance &&
    maxX <= this.width + tolerance && maxY <= this.height + tolerance) {
    return; // Close enough, don't expand
}

// Padding: when expanding, add extra space to reduce expansion frequency
const expansionPadding = Math.max(50, radius * 2);
const newMinX = Math.floor(Math.min(0, minX - expansionPadding));
const newMinY = Math.floor(Math.min(0, minY - expansionPadding));
```

### Lesson 5: Skip fitToContent for Transformed Layers

**Problem:** The History system calls `fitToContent()` after strokes complete. This method shrinks the layer canvas to fit the visible content and recalculates offsets. For transformed layers, the offset calculation was incorrect, causing the layer to jump when the mouse was released.

**Solution:** Skip auto-fit for transformed layers:

```javascript
fitToContent() {
    // For transformed layers, skip auto-fit entirely
    // The math to preserve position while shrinking a rotated layer is complex
    // and the memory savings are minimal
    if (this.hasTransform()) {
        return false;
    }

    // ... existing fitToContent logic for non-transformed layers
}
```

This is an acceptable trade-off: transformed layers keep extra transparent padding, but the code is simpler and more reliable.

## Tool Implementation Pattern

All painting tools (Brush, Pencil, Smudge, Dodge, Burn, Blur, Sharpen, Sponge, Clone Stamp) follow this pattern:

```javascript
class MyPaintingTool extends Tool {
    // Store last position in document coordinates
    lastX = 0;
    lastY = 0;

    onMouseDown(e, x, y, coords) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Store DOCUMENT coordinates
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;
        this.lastX = docX;
        this.lastY = docY;

        this.app.history.saveState('MyTool');
        this.paintAtDocCoords(layer, docX, docY);
    }

    onMouseMove(e, x, y, coords) {
        // Update cursor overlay
        this.brushCursor.update(x, y, this.size);

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Use DOCUMENT coordinates
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        this.paintLineAtDocCoords(layer, this.lastX, this.lastY, docX, docY);

        this.lastX = docX;
        this.lastY = docY;
    }

    paintAtDocCoords(layer, docX, docY) {
        const radius = this.size / 2;

        // 1. Expand layer if needed (handles rotation correctly)
        if (layer.expandToIncludeDocPoint) {
            layer.expandToIncludeDocPoint(docX, docY, radius);
        }

        // 2. Convert to canvas coordinates AFTER expansion
        const hasTransform = layer.hasTransform?.();
        let canvasX, canvasY;
        if (hasTransform && layer.docToLayer) {
            const local = layer.docToLayer(docX, docY);
            canvasX = local.x;
            canvasY = local.y;
        } else {
            canvasX = docX - (layer.offsetX || 0);
            canvasY = docY - (layer.offsetY || 0);
        }

        // 3. Draw on canvas
        layer.ctx.beginPath();
        layer.ctx.arc(canvasX, canvasY, radius, 0, Math.PI * 2);
        layer.ctx.fill();
    }
}
```

## Summary of Pitfalls

| Problem | Symptom | Solution |
|---------|---------|----------|
| Layer-local coordinates become stale | First stroke creates long line | Store coordinates in document space |
| Document-space expansion bounds | Layer slides instead of growing | Use `expandToIncludeDocPoint()` |
| Offset calculation ignores rotation | Layer jumps after expansion | Apply rotation to offset delta |
| Many small expansions | Gradual drift while painting edges | Add tolerance (5px) and padding (50px) |
| fitToContent on transformed layers | Layer jumps on mouse release | Skip fitToContent for transformed layers |

## Testing Transformed Layers

When testing painting tools with transformed layers:

1. **Test inside bounds** - Painting inside the layer should work normally
2. **Test near edges** - Painting on the edge should expand without drift
3. **Test outside bounds** - Painting outside should expand correctly
4. **Test at various rotations** - 45°, 90°, 180°, arbitrary angles
5. **Test mouse release** - Layer shouldn't jump when releasing mouse
6. **Test undo/redo** - Should restore to exact previous state

## Future Considerations

### Not Yet Implemented

- **fitToContent for transformed layers**: Could be implemented with proper rotation math, but complexity vs. benefit is low
- **Transform around arbitrary pivot**: Currently always uses canvas center; user-defined pivot would require additional changes
- **Skew/shear transforms**: Not supported; would require extending the transform math

### Known Limitations

- Transformed layers may retain extra transparent padding after editing
- Very large rotations with continuous edge painting may still accumulate small rounding errors over extended use
- Clone Stamp source sampling doesn't account for layer transforms (samples document-space pixels)

## Layer Rasterization

Transformed layers require special handling when their content needs to be rendered to document space. This is needed for:
- Copy/paste operations
- Layer thumbnails
- Navigator preview
- Copy merged (Ctrl+Shift+C)

### getDocumentBounds()

Returns the axis-aligned bounding box of a transformed layer in document space.

```javascript
const bounds = layer.getDocumentBounds();
// Returns: { x, y, width, height }
```

**How it works:**
1. For non-transformed layers: returns `{ x: offsetX, y: offsetY, width, height }`
2. For transformed layers: transforms all 4 corners using `layerToDoc()` and finds the enclosing rectangle

```javascript
getDocumentBounds() {
    if (!this.hasTransform()) {
        return { x: this.offsetX, y: this.offsetY, width: this.width, height: this.height };
    }

    // Transform all 4 corners
    const corners = [
        this.layerToDoc(0, 0),
        this.layerToDoc(this.width, 0),
        this.layerToDoc(this.width, this.height),
        this.layerToDoc(0, this.height)
    ];

    // Find enclosing rectangle
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const corner of corners) {
        minX = Math.min(minX, corner.x);
        minY = Math.min(minY, corner.y);
        maxX = Math.max(maxX, corner.x);
        maxY = Math.max(maxY, corner.y);
    }

    return {
        x: Math.floor(minX), y: Math.floor(minY),
        width: Math.ceil(maxX) - Math.floor(minX),
        height: Math.ceil(maxY) - Math.floor(minY)
    };
}
```

### rasterizeToDocument(clipBounds?)

Renders the layer content to document coordinate space with all transforms applied. Uses canvas 2D transforms with high-quality bicubic interpolation.

```javascript
const result = layer.rasterizeToDocument();
// Returns: { canvas, bounds: {x,y,width,height}, ctx }

// With clipping to selection bounds:
const result = layer.rasterizeToDocument({ x: 100, y: 100, width: 200, height: 200 });
```

**How it works:**

For non-transformed layers, simply copies the relevant portion:
```javascript
ctx.drawImage(this.canvas, srcX, srcY, width, height, 0, 0, width, height);
```

For transformed layers, uses canvas transforms for high-quality rendering:
```javascript
// Enable high-quality interpolation (bicubic)
ctx.imageSmoothingEnabled = true;
ctx.imageSmoothingQuality = 'high';

// Calculate layer center in document space
const cx = this.width / 2;
const cy = this.height / 2;
const docCx = this.offsetX + cx;
const docCy = this.offsetY + cy;

// Apply transforms in reverse order
ctx.translate(-outputBounds.x, -outputBounds.y);  // Output position
ctx.translate(docCx, docCy);                       // Move to rotation center
ctx.rotate(this.rotation * Math.PI / 180);         // Apply rotation
ctx.scale(this.scaleX, this.scaleY);               // Apply scale
ctx.translate(-cx, -cy);                           // Move to layer origin
ctx.drawImage(this.canvas, 0, 0);                  // Draw layer content
```

**Why canvas transforms instead of pixel-by-pixel sampling:**
- Canvas 2D with `imageSmoothingQuality: 'high'` uses bicubic interpolation
- Pixel-by-pixel with `docToLayer()` would be nearest-neighbor (jagged edges)
- Canvas transforms are hardware-accelerated and much faster

### renderThumbnail(maxWidth, maxHeight, docSize?)

Renders a thumbnail of the layer with transforms applied. Used by the layer panel and navigator.

```javascript
const thumb = layer.renderThumbnail(40, 40);
// Returns: { canvas, width, height }

// Render thumbnail relative to document bounds:
const thumb = layer.renderThumbnail(40, 40, { width: 800, height: 600 });
```

**Algorithm:**
1. Get document bounds of the layer (using `getDocumentBounds()`)
2. Calculate scale to fit within thumbnail size
3. Use `rasterizeToDocument()` to get transformed content
4. Scale down to thumbnail size

```javascript
renderThumbnail(maxWidth, maxHeight, docSize = null) {
    const docBounds = this.getDocumentBounds();

    // Use document size or layer bounds for reference
    const refWidth = docSize?.width || docBounds.width;
    const refHeight = docSize?.height || docBounds.height;

    const scale = Math.min(maxWidth / refWidth, maxHeight / refHeight);
    const thumbWidth = Math.ceil(refWidth * scale);
    const thumbHeight = Math.ceil(refHeight * scale);

    const thumbCanvas = document.createElement('canvas');
    thumbCanvas.width = thumbWidth;
    thumbCanvas.height = thumbHeight;
    const ctx = thumbCanvas.getContext('2d');

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    // Rasterize layer to document space
    const rasterized = this.rasterizeToDocument();

    // Draw scaled to thumbnail
    const drawX = (rasterized.bounds.x - (docSize ? 0 : docBounds.x)) * scale;
    const drawY = (rasterized.bounds.y - (docSize ? 0 : docBounds.y)) * scale;
    const drawW = rasterized.bounds.width * scale;
    const drawH = rasterized.bounds.height * scale;

    ctx.drawImage(rasterized.canvas, drawX, drawY, drawW, drawH);

    return { canvas: thumbCanvas, width: thumbWidth, height: thumbHeight };
}
```

### trimToContent() Behavior

The `trimToContent()` method shrinks a layer canvas to fit its visible content. For transformed layers, this is skipped:

```javascript
trimToContent(padding = 0) {
    // Skip for transformed layers - the math to recompute offsets
    // while preserving document position is complex and error-prone
    if (this.hasTransform()) {
        return;
    }

    // ... proceed with normal trimming for non-transformed layers
}
```

**Why skip for transformed layers:**
- After trimming, the layer's offset must be recalculated to keep content in the same document position
- For rotated layers, this requires complex trigonometry similar to `expandToIncludeDocPoint()`
- The memory savings are minimal compared to the complexity and bug risk
- Cut operations call `trimToContent()` after deleting pixels, so this prevents layer jumping

## Usage in Copy/Paste

### Copy from Layer (Ctrl+C)

The `SelectionManager.extractFromLayer()` method uses `rasterizeToDocument()`:

```javascript
extractFromLayer(layer) {
    const bounds = this.getBounds();

    // Rasterize layer with transforms, clipped to selection bounds
    const rasterized = layer.rasterizeToDocument(bounds);

    // Create extraction canvas at selection bounds size
    const extractCanvas = document.createElement('canvas');
    extractCanvas.width = bounds.width;
    extractCanvas.height = bounds.height;
    const ctx = extractCanvas.getContext('2d');

    // Draw rasterized content at correct position
    const drawX = rasterized.bounds.x - bounds.x;
    const drawY = rasterized.bounds.y - bounds.y;
    ctx.drawImage(rasterized.canvas, drawX, drawY);

    // Apply selection mask
    // ...
}
```

### Copy Merged (Ctrl+Shift+C)

The `Clipboard.copyMerged()` method composites all visible layers using `rasterizeToDocument()`:

```javascript
for (let i = layerStack.layers.length - 1; i >= 0; i--) {
    const layer = layerStack.layers[i];
    if (!layer.visible) continue;
    if (layer.isGroup && layer.isGroup()) continue;

    // Rasterize handles transforms automatically
    const rasterized = layer.rasterizeToDocument(clipBounds);

    ctx.globalAlpha = layer.opacity;
    const drawX = rasterized.bounds.x - clipBounds.x;
    const drawY = rasterized.bounds.y - clipBounds.y;
    ctx.drawImage(rasterized.canvas, drawX, drawY);
}
```

## Usage in Thumbnails and Navigator

### Layer Thumbnails (PreviewUpdateManager)

```javascript
if (layer.renderThumbnail) {
    const thumb = layer.renderThumbnail(thumbSize, thumbSize);
    ctx.drawImage(thumb.canvas, 0, 0);
} else if (layer.canvas) {
    // Fallback for layers without renderThumbnail (groups, etc.)
}
```

### Navigator Preview (NavigatorManager)

```javascript
for (let i = layers.length - 1; i >= 0; i--) {
    const layer = layers[i];
    if (layer.isGroup && layer.isGroup()) continue;
    if (!layerStack.isEffectivelyVisible(layer)) continue;

    ctx.globalAlpha = layerStack.getEffectiveOpacity(layer);

    if (layer.hasTransform && layer.hasTransform() && layer.rasterizeToDocument) {
        // Use rasterizeToDocument for transformed layers
        const rasterized = layer.rasterizeToDocument();
        const drawX = rasterized.bounds.x * scale;
        const drawY = rasterized.bounds.y * scale;
        const drawW = rasterized.bounds.width * scale;
        const drawH = rasterized.bounds.height * scale;
        ctx.drawImage(rasterized.canvas, drawX, drawY, drawW, drawH);
    } else if (layer.canvas) {
        // Simple path for non-transformed layers
        const offsetX = (layer.offsetX ?? 0) * scale;
        const offsetY = (layer.offsetY ?? 0) * scale;
        ctx.drawImage(layer.canvas, offsetX, offsetY,
                      layer.width * scale, layer.height * scale);
    }
}
```

## Summary

| Method | Purpose | Interpolation |
|--------|---------|---------------|
| `getDocumentBounds()` | Get AABB of transformed layer | N/A |
| `rasterizeToDocument()` | Render layer to document space | Bicubic (high-quality) |
| `renderThumbnail()` | Create preview thumbnail | Bicubic (high-quality) |

These methods provide a single authoritative way to handle layer transforms throughout the codebase, ensuring consistency in copy/paste, thumbnails, and navigator rendering.
