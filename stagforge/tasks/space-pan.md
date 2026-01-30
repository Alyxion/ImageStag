# Pan with Spacebar (Spring-loaded Hand Tool)

## Description
Holding Space should temporarily activate the Hand/Pan tool. Releasing Space returns to the previous tool. This is standard in all major image editors.

## Behavior
- **Hold Space** - Cursor changes to hand, dragging pans the canvas
- **Release Space** - Returns to previous tool
- Should work regardless of current tool
- Should work even during an operation (e.g., mid-brush stroke pauses, pan, then continues)

## Implementation Notes
- Store current tool before switching
- On Space down: switch to pan mode, change cursor
- On Space up: restore previous tool and cursor
- Handle edge case: Space released while mouse is down (complete pan, then restore tool)
