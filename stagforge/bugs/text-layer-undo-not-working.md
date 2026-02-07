# Text Layer Creation Not Undoable

## Status: OPEN

## Description
When creating a new text layer and then pressing Undo (Ctrl+Z), the text layer does not disappear. Undo should remove the newly created layer.

## Steps to Reproduce
1. Create a new document
2. Select the Text tool
3. Click on the canvas to create a new text layer
4. Type some text
5. Press Ctrl+Z to undo

## Expected Behavior
The text layer should be removed, reverting to the state before it was created.

## Actual Behavior
The text layer remains. Undo does not remove it.

## Likely Cause
The text layer creation may not be saving a history state before adding the layer, or the history system may not support structural changes like adding/removing layers (it primarily tracks pixel diffs on existing layers).

## Affected Files
- `stagforge/frontend/js/tools/TextTool.js`
- `stagforge/frontend/js/core/History.js`
