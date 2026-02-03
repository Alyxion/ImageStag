# Filter Shifts Position of Rotated Layers

## Status: OPEN

## Description
When applying a filter that produces output larger than the input layer (e.g., blur, glow effects), the layer position shifts incorrectly if the layer is rotated.

## Steps to Reproduce
1. Create a layer with content
2. Rotate the layer (e.g., 45 degrees)
3. Apply a filter that expands the canvas (e.g., Gaussian blur with large radius)
4. Observe that the layer position has shifted

## Expected Behavior
The layer content should remain visually in the same position after applying the filter. The expanded canvas area should extend equally around the original content.

## Actual Behavior
The layer shifts position, likely because the filter expansion doesn't account for the rotation transform when calculating the new offset.

## Likely Cause
When a filter expands the layer canvas, the offset adjustment probably uses simple arithmetic that doesn't account for the rotation center point. The expansion should be calculated in document space considering the layer's transform.

## Affected Files
- Likely in filter application code
- Possibly `stagforge/frontend/js/editor/mixins/FilterDialogManager.js`
- Or layer effect application code
