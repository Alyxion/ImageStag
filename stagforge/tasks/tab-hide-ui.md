# Hide UI with Tab Key

## Description
Pressing Tab should toggle visibility of all UI panels (toolbox, layers, properties, etc.) to show only the canvas. This allows for distraction-free viewing and is standard in Photoshop, GIMP, etc.

## Behavior
- **Tab** - Toggle all panels on/off
- **Shift+Tab** - (optional) Toggle only side panels, keep toolbar

## Implementation Notes
- Store panel visibility state before hiding
- Restore exact state when showing again
- Canvas should expand to fill available space
- Cursor and tool functionality should remain active
