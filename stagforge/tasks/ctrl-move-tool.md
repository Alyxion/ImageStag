# Temporary Move Tool with Ctrl Key

## Description
Holding Ctrl should temporarily activate the Move tool to reposition layers or selections. Releasing Ctrl returns to the previous tool. This is standard in Photoshop.

## Behavior
- **Hold Ctrl** - Cursor changes to move cursor
- **Drag while holding Ctrl** - Move the active layer (or selection contents if selection active)
- **Release Ctrl** - Returns to previous tool
- Should work from most tools

## Implementation Notes
- Store current tool before switching
- On Ctrl down: switch to move mode, change cursor
- On drag: move layer or selection
- On Ctrl up: restore previous tool and cursor
- Consider interaction with other Ctrl shortcuts (Ctrl+Z, Ctrl+C, etc.) - those should still work
