# Bug: Merge Down enabled for bottom layer

## Status: FIXED

## Root Cause
The menu item didn't check if the active layer was the bottom layer.

## Fix Applied
1. Added `canMergeDown` computed property that checks if the active layer index is less than `layers.length - 1`
2. Updated menu item to use `:class="{ disabled: !canMergeDown }"` and click guard

## Files Modified
- `stagforge/canvas_editor.js` - Added computed property and updated menu item
