# Sample Color with Alt Key (Spring-loaded Eyedropper)

## Description
Holding Alt should temporarily activate the Eyedropper tool to sample a color from the canvas. Releasing Alt returns to the previous tool. This is standard in Photoshop, GIMP, Affinity, etc.

## Behavior
- **Hold Alt** - Cursor changes to eyedropper
- **Click while holding Alt** - Sample color at click position, set as foreground color
- **Release Alt** - Returns to previous tool
- Should work from most tools (Brush, Eraser, Fill, etc.)

## Implementation Notes
- Store current tool before switching
- On Alt down: switch to eyedropper mode, change cursor
- On click: sample color, update foreground color
- On Alt up: restore previous tool and cursor
- Consider: Alt+Click on color in Swatches panel behavior
