# Text Layer Inline Editing Improvements

## Description
Text should always be displayed directly on the canvas in its real position (not in a floating/hovering editor). Text should be editable inline, with the ability to change color and other properties.

## Current Behavior
- Text editing may use a separate floating view
- Text may not be editable after creation
- Color changes may not work

## Expected Behavior
- Text renders directly on canvas at its actual position
- Clicking on text with Text tool enters inline edit mode
- Cursor appears in text, can type to edit
- Selected text can have color changed via color picker
- Text properties (font, size, style) changeable while editing
- WYSIWYG editing - what you see is what you get

## Implementation Notes
- Render text directly to layer canvas position
- Use contenteditable or custom text input overlay positioned exactly over text
- Support text selection within the layer
- Color picker integration for changing text color
- Real-time preview of changes

## Related
- Bug: text-layer-not-editable-on-reclick.md
