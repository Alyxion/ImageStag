# Hide UI with Tab Key

## Status: PARTIALLY WORKING

## Current Issues
1. **Need fullscreen mode** - Tab key capture requires fullscreen to work reliably
2. **UI remnants visible** - When hiding UI, the following still remain:
   - Sidebar
   - Empty menu bar
   - Bottom bar
3. **Canvas not scaled** - Canvas doesn't expand to fill the screen when UI is hidden

## Expected Behavior
- Tab toggles ALL UI elements off completely
- Canvas expands to fill the entire available space
- Clean, distraction-free viewing mode

## Current Implementation (KeyboardEvents.js)
- `handleKeyDown()` line 143-148: Tab key calls `toggleUIVisibility()`
- `toggleUIVisibility()` line 90-117: Saves and restores panel visibility state

## Panels That Should Be Hidden
- Menu bar (completely, not just empty)
- Tool panel / sidebar
- Right panel (layers, history, etc.)
- Bottom bar
- Document tabs

## Data Properties (canvas_editor.js)
- `_uiHidden` - Whether UI is currently hidden
- `_savedPanelState` - Saved visibility of each panel

## To Fix
- Request fullscreen mode when hiding UI
- Hide all UI elements including sidebar, menu, bottom bar
- Resize canvas container to fill viewport
- Exit fullscreen when showing UI again
