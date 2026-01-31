# Bug: Concave polygons lead to broken marching lines

## Description
When a selection has concave shapes (shapes with inward curves or angles), the marching ants outline often renders incorrectly or appears broken.

## Steps to Reproduce
1. Use Polygonal Selection to create a concave shape (e.g., star, arrow, L-shape)
2. Or use Magic Wand on an image with concave selected regions
3. Observe the marching ants outline

## Expected Behavior
Marching ants should correctly follow the boundary of all selected regions, including concave areas.

## Actual Behavior
The outline may:
- Have gaps
- Cross over itself incorrectly
- Miss parts of the boundary
- Show extra lines inside the selection

## Technical Notes
The contour extraction uses Moore-neighbor boundary tracing in `rust/src/selection/contour.rs`. Concave shapes may cause the algorithm to:
- Miss interior boundaries
- Trace incorrectly at sharp concave vertices

## Affected Files
- `rust/src/selection/contour.rs` - extract_contours algorithm
- `stagforge/frontend/js/utils/MarchingSquares.js` - JS fallback
