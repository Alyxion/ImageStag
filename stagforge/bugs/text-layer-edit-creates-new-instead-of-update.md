# Bug: Editing text layer creates new layer instead of updating

## Status: FIXED

## Root Cause
1. In `deactivate()`, the code tried to deselect `editingLayer` after calling `commitText()`, but `commitText` calls `cleanup()` which sets `editingLayer = null`
2. Event listener binding used `.bind(this)` each time, creating new function references, so the listener was never properly removed

## Fix Applied
1. Store `editingLayer` reference before calling `commitText()` in `deactivate()`
2. Use stored reference to properly deselect the layer after commit
3. Store bound event handler once in constructor (`this._boundOnLayerActivated`)
4. Use the stored reference for both `on` and `off` calls

## Files Modified
- `stagforge/frontend/js/tools/TextTool.js` - Fixed deactivate logic and event binding
