# Grow and Shrink Selection

## Description
Add the ability to expand or contract the current selection by a specified number of pixels.

## Behavior
- **Select > Modify > Grow...** - Expand selection outward by N pixels
- **Select > Modify > Shrink...** - Contract selection inward by N pixels
- Should show dialog to input pixel amount
- Works with any selection shape (rectangle, lasso, magic wand result, etc.)

## Implementation Notes
- Grow: dilate the selection mask
- Shrink: erode the selection mask
- Use morphological operations on the selection mask
- Preserve feathering if present, or apply after grow/shrink
- Edge case: shrinking more than selection size should clear selection

## Menu Location
- Select > Modify > Grow...
- Select > Modify > Shrink...
- (Could also add Contract, Expand, Border, Smooth, Feather here)
