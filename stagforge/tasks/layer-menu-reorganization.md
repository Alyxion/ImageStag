# Layer Menu Reorganization

## Description
Reorganize the Layer menu to collect "new layer" options into a submenu, while keeping "New Layer from File" easily accessible in the layer panel as well.

## Proposed Menu Structure
```
Layer
├── New                          (submenu)
│   ├── New Pixel Layer
│   ├── New Vector Layer
│   ├── New Layer from File...
│   ├── New Layer from Clipboard
│   └── New Folder/Group
├── New Layer from File...       (also at top level for quick access)
├── ─────────────────
├── Duplicate Layer
├── Delete Layer
├── ...
```

## Layer Panel
- Keep the "+" button dropdown with all options
- Or: "+" creates pixel layer, dropdown arrow shows submenu
- "New Layer from File" should be easily accessible without going through submenus

## Implementation Notes
- Update Layer menu in `canvas_editor.js`
- Ensure layer panel has quick access to "from file" option
- Consider adding icons to submenu items
