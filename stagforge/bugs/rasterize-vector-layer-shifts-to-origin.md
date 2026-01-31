# Bug: Rasterizing vector layer shifts content to origin (0,0)

## Description
When rasterizing a vector layer that has an offset (not at 0,0), the rasterized content shifts to the document origin instead of maintaining its position.

## Steps to Reproduce
1. Create a new document
2. Add a vector layer
3. Draw shapes at a non-origin position (e.g., center of document)
4. Rasterize the layer
5. Observe the content jumps to 0,0

## Expected Behavior
The rasterized content should remain at the same visual position in the document. The layer's offsetX/offsetY should be preserved.

## Actual Behavior
Content shifts to top-left corner (0,0). The layer offset is lost during rasterization.

## Affected Files
- `stagforge/frontend/js/editor/mixins/LayerOperations.js` - rasterizeLayer method
- Needs to preserve layer.offsetX/offsetY when creating the raster replacement
