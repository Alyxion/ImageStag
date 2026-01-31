# Bug: Rasterizing a layer does not create an undo entry

## Description
When rasterizing a vector, text, or SVG layer, no undo history entry is created. The operation cannot be undone.

## Steps to Reproduce
1. Create a vector or text layer
2. Right-click and select "Rasterize Layer" (or use Layer menu)
3. Try to undo (Ctrl+Z)

## Expected Behavior
Undo should restore the layer to its original type (vector/text/SVG).

## Actual Behavior
Undo does nothing or undoes a previous unrelated action.

## Affected Files
- `stagforge/frontend/js/editor/mixins/LayerOperations.js` - rasterizeLayer method
