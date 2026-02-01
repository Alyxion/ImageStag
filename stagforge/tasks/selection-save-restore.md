# Save, Delete, and Restore Selection Masks

## Status: NOT WORKING

## Current Issue
Load Selection functionality is not working. See related bug: `load-selection-not-enabled-after-save.md`

## Implementation (Code Complete)

### SelectionManager Methods (SelectionManager.js)
- `saveSelection(name)` - Save current selection with a name (with undo support)
- `loadSelection(name, mode)` - Load selection with replace/add/subtract/intersect modes
- `deleteSavedSelection(name)` - Delete a saved selection (with undo support)
- `getSavedSelections()` - Get list of saved selections

### History Support (History.js)
- `LayerStructureSnapshot` captures `savedSelections` from document
- Save/delete operations create history entries via `beginStructuralChange/commitCapture`
- Undo/redo restores saved selections list to previous state

### UI (canvas_editor.js)
- **Select > Save Selection...** - Opens dialog to name and save current selection
- **Select > Load Selection...** - Opens dialog to load/delete saved selections
- Load dialog supports modes: Replace, Add, Subtract, Intersect

### Document Persistence (Document.js)
- Saved selections serialized with document (base64-encoded mask data)
- Restored on document load
- `hasSavedSelections` state updated on document switch

## Data Structure
```javascript
document.savedSelections = [
  { name: "Selection 1", mask: Uint8Array, width: N, height: M },
  ...
]
```

## Files Modified
- `stagforge/frontend/js/core/SelectionManager.js`
- `stagforge/frontend/js/core/Document.js`
- `stagforge/frontend/js/core/History.js`
- `stagforge/frontend/js/editor/mixins/ImageOperations.js`
- `stagforge/canvas_editor.js`
