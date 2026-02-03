# Bug: Rasterizing SVG layer - undo removes layer entirely

## Status: FIXED

## Problem
When rasterizing an SVG layer:
1. Undo history entry IS created
2. However, undoing does not restore the SVG layer
3. Instead, the layer is completely gone after undo

## Expected Behavior
Undoing rasterize should restore the original SVG layer with all its properties and content.

## Root Cause
The structural change capture was not saving the SVG layer state before rasterization. The `storeDeletedLayer()` call was missing.

## Fix Applied
Added `await app.history.storeDeletedLayer(layer)` before calling `rasterizeLayer()` in:
- `stagforge/frontend/js/editor/mixins/LayerOperations.js` - `rasterizeActiveLayer()`
- `stagforge/frontend/js/editor/mixins/FilterDialogManager.js` - `confirmRasterize()`

This stores the full serialized layer data (including SVG content) in the history snapshot, allowing proper restoration on undo.
