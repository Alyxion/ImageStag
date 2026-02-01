# Bug: Rasterizing SVG layer - undo removes layer entirely

## Status: NOT FIXED

## Problem
When rasterizing an SVG layer:
1. Undo history entry IS created
2. However, undoing does not restore the SVG layer
3. Instead, the layer is completely gone after undo

## Expected Behavior
Undoing rasterize should restore the original SVG layer with all its properties and content.

## Root Cause
The structural change capture may not be properly saving the SVG layer state before rasterization.

## Files to Investigate
- `stagforge/frontend/js/editor/mixins/FilterDialogManager.js` - Rasterize confirmation
- `stagforge/frontend/js/core/History.js` - Layer structure snapshots
