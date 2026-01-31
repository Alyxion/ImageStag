# Bug: Load Selection not enabled after saving a selection

## Description
After saving a selection via Select > Save Selection, the "Load Selection" menu item remains disabled. Cannot test if loading works.

## Steps to Reproduce
1. Make a selection
2. Go to Select > Save Selection
3. Enter a name and save
4. Go to Select menu
5. Observe "Load Selection" is still disabled

## Expected Behavior
After saving at least one selection, "Load Selection" should become enabled.

## Actual Behavior
"Load Selection" remains disabled even after saving selections.

## Affected Files
- `stagforge/canvas_editor.js` - menu state conditions
- `stagforge/frontend/js/core/SelectionManager.js` - savedSelections tracking
