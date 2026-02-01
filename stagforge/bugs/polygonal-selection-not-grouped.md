# Bug: Polygonal Selection not in selection tool group

## Status: FIXED

## Description
The Polygonal Selection tool was reported as not being grouped with other selection tools.

## Analysis
The tool is correctly configured:
- `static group = 'selection'` in PolygonalSelectionTool.js (line 14)
- `static priority = 25` (between Lasso at 20 and MagicWand at 30)
- Properly included in allTools array in index.js

The tool is correctly grouped with other selection tools:
1. SelectionTool (priority 10)
2. LassoTool (priority 20)
3. PolygonalSelectionTool (priority 25)
4. MagicWandTool (priority 30)

All are in the 'selection' group accessible via the 'M' shortcut.

## Files Verified
- `stagforge/frontend/js/tools/PolygonalSelectionTool.js` - Correct group property
- `stagforge/frontend/js/tools/index.js` - Included in allTools
