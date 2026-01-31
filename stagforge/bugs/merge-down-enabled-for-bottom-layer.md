# Bug: Merge Down enabled for bottom layer

## Description
The "Merge Down" option is enabled in both the Layer menu and layer panel context menu when the bottom-most layer is selected. There is no layer below to merge into.

## Steps to Reproduce
1. Create a document with multiple layers
2. Select the bottom layer (index 0)
3. Open Layer menu or right-click layer in panel
4. Observe "Merge Down" is enabled

## Expected Behavior
"Merge Down" should be disabled when the bottom layer is selected.

## Actual Behavior
The option is enabled and may cause errors or unexpected behavior when clicked.

## Affected Files
- `stagforge/canvas_editor.js` - menu definition
- `stagforge/frontend/js/editor/mixins/LayerOperations.js` - mergeDown method and menu state
