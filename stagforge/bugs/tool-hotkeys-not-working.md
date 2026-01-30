# Tool Hotkeys Do Not Work

## Description
None of the keyboard shortcuts for selecting tools seem to work (e.g., B for Brush, V for Move, E for Eraser, etc.).

## Steps to Reproduce
1. Open a document
2. Press B (should select Brush)
3. Press V (should select Move)
4. Press E (should select Eraser)
5. Observe: tools do not change

## Expected Behavior
Pressing tool shortcut keys should switch to the corresponding tool.

## Possible Causes
- Keyboard event handler not registered
- Focus issue (canvas or another element not receiving keyboard events)
- Key mappings not configured correctly
- Event propagation being stopped somewhere

## Affected Files
- `stagforge/frontend/js/editor/mixins/KeyboardEvents.js`
- `stagforge/frontend/js/tools/ToolManager.js`
