# Save, Delete, and Restore Selection Masks

## Description
Allow users to save the current selection to a named channel/mask, restore it later, and delete saved selections. This is standard in Photoshop (Save Selection, Load Selection).

## Behavior
- **Select > Save Selection...** - Save current selection with a name
- **Select > Load Selection...** - Load a previously saved selection (replace, add, subtract, intersect)
- **Saved selections visible in Channels panel** (future)
- Selections saved with document (.sfr file)

## Implementation Notes
- Store selections as alpha masks (same format as current SelectionManager mask)
- Each saved selection needs: name, mask data, dimensions
- Load options:
  - Replace current selection
  - Add to current selection
  - Subtract from current selection
  - Intersect with current selection
- Save in document serialization format

## Data Structure
```javascript
document.savedSelections = [
  { name: "Selection 1", mask: Uint8Array, width: N, height: M },
  ...
]
```

## Menu Location
- Select > Save Selection...
- Select > Load Selection...
