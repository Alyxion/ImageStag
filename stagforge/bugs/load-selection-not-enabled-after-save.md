# Bug: Load Selection not enabled after saving a selection

## Status: FIXED

## Root Cause
Two issues:
1. ImageOperations.js was using `this.documentManager` which was not defined in the mixin context
2. SelectionManager.js was using `activeDocument` as a property, but it's a method called `getActiveDocument()`

## Fix Applied
1. Updated ImageOperations.js methods to use `this.getState()?.documentManager` instead of `this.documentManager`
2. Updated SelectionManager.js to call `getActiveDocument()` instead of accessing `activeDocument` as a property:
   - `saveSelection()` - line 461
   - `loadSelection()` - line 497
   - `deleteSavedSelection()` - line 549
   - `getSavedSelections()` - line 565

## Files Modified
- `stagforge/frontend/js/editor/mixins/ImageOperations.js` - Fixed documentManager access pattern
- `stagforge/frontend/js/core/SelectionManager.js` - Fixed getActiveDocument() calls
