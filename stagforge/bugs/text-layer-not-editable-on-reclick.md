# Cannot Edit Text Layer When Clicking On It Again

## Description
When clicking on an existing text layer with the Text tool, the text does not become editable. Users cannot re-edit text after it has been created.

## Steps to Reproduce
1. Create a text layer with some text
2. Click elsewhere to deselect/finish editing
3. Select the Text tool
4. Click on the text layer again
5. Observe: text is not editable, no cursor appears

## Expected Behavior
Clicking on an existing text layer with the Text tool should:
- Select that text layer
- Enter edit mode
- Show cursor in text
- Allow editing the text content

## Affected Files
- `stagforge/frontend/js/tools/TextTool.js`
- `stagforge/frontend/js/core/TextLayer.js`
