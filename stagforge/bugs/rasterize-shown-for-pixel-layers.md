# Bug: Rasterize option shown for pixel layers

## Description
The "Rasterize Layer" menu option is shown and enabled for pixel (raster) layers, even though they are already rasterized.

## Steps to Reproduce
1. Create or select a pixel layer
2. Open Layer menu or right-click context menu
3. Observe "Rasterize Layer" is available

## Expected Behavior
"Rasterize Layer" should be hidden or disabled for pixel layers since they are already raster format.

## Actual Behavior
The option is shown and can be clicked (presumably does nothing or causes issues).

## Affected Files
- `stagforge/canvas_editor.js` - menu definition
- `stagforge/frontend/js/editor/mixins/LayerOperations.js` - menu state logic
