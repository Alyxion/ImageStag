# Bug: Editing text layer creates new layer instead of updating

## Description
When clicking on an existing text layer to edit it:
1. The layer is selected and text appears in the edit field
2. But confirming the change creates a NEW text layer instead of updating the existing one
3. After stopping editing and selecting other tools, the bounding box remains on screen

## Steps to Reproduce
1. Create a text layer with some text
2. Switch to another tool
3. Switch back to Text tool
4. Click on the existing text layer
5. Modify the text in the editor
6. Click confirm or press Enter
7. Observe a new layer is created instead of updating

## Expected Behavior
- Editing an existing text layer should update that layer's content
- Bounding box should disappear when switching tools or deselecting

## Actual Behavior
- A new text layer is created with the modified content
- The original layer remains unchanged
- Bounding box persists after tool switch

## Affected Files
- `stagforge/frontend/js/tools/TextTool.js` - edit mode and commit logic
- `stagforge/frontend/js/core/TextLayer.js` - layer update methods
