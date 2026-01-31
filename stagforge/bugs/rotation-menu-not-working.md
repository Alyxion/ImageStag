# Bug: Rotation menu items have no effect

## Description
The Image menu rotation options (Rotate 90° CW, Rotate 90° CCW, Rotate 180°) do nothing when clicked.

## Steps to Reproduce
1. Open a document with content
2. Go to Image menu
3. Click "Rotate 90° CW" (or CCW or 180°)
4. Observe no change

## Expected Behavior
The entire canvas and all layers should rotate by the specified angle.

## Actual Behavior
Nothing happens. No visible change, no console errors.

## Possible Cause
The menu items may not be properly connected to the `rotateCanvas()` method, or the method itself may have issues.

## Affected Files
- `stagforge/canvas_editor.js` - menu definitions
- `stagforge/frontend/js/editor/mixins/MenuManager.js` - rotateCanvas method
