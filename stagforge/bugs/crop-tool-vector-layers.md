# Crop Tool Issues with Undo and Selection

## Status: PARTIALLY WORKING

Crop operation itself works, but there are serious issues:

## Current Problems
1. **Undo damages document** - Undoing a crop operation causes damage to the document
2. **Selection issues** - Serious errors with selection handling during crop

## Proposed Fix
- Full document copy should be created before crop operation
- This ensures undo can properly restore the complete document state

## Notes
- Basic crop functionality works
- SVG layer offset handling is correct
- The issue is with history/undo implementation, not the crop logic itself
