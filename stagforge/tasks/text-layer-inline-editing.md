# Text Layer Inline Editing

## Status: NOT IMPLEMENTED

## Current Problem
Text editing still happens in a popup window/dialog rather than directly on the canvas graphic.

## Expected Behavior
- Text renders directly on canvas at its actual position
- Clicking on text with Text tool enters inline edit mode
- Cursor appears in text at click position
- Can type to edit text in-place
- Selected text can have color changed via color picker
- Text properties (font, size, style) changeable while editing
- WYSIWYG editing - what you see is what you get
- No popup or floating editor windows

## Implementation Notes
- Render text directly to layer canvas position
- Use contenteditable or custom text input overlay positioned exactly over text
- Overlay must track zoom/pan to stay aligned with text
- Support text selection within the layer
- Color picker integration for changing text color
- Real-time preview of changes

## Related Bugs
- text-layer-edit-creates-new-instead-of-update.md - Editing creates new layer instead of updating
