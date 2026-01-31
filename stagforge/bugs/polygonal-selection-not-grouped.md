# Bug: Polygonal Selection not in selection tool group

## Description
The Polygonal Selection tool is not grouped with other selection tools (Rectangular, Lasso, Magic Wand) in the toolbar.

## Steps to Reproduce
1. Look at the toolbar
2. Find the selection tools group
3. Polygonal Selection is separate or missing from the group

## Expected Behavior
Polygonal Selection should be in the same tool group as other selection tools, accessible via the 'M' shortcut group.

## Actual Behavior
Polygonal Selection is either in its own group or not properly accessible.

## Affected Files
- `stagforge/frontend/js/tools/PolygonalSelectionTool.js` - static group property
