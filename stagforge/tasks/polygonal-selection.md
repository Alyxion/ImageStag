# Polygonal Selection Tool

## Description
Add a polygonal selection tool that allows users to create selections by clicking points to form a polygon. Each click adds a vertex, and the selection is completed by clicking near the starting point or pressing Enter.

## Behavior
- Click to add vertices
- Double-click or click near start point to close polygon
- Press Enter to complete selection
- Press Escape to cancel
- Backspace removes last vertex
- Should support adding to / subtracting from existing selection with Shift/Alt

## Implementation Notes
- Similar to Lasso but with straight line segments between points
- Store vertices as array of points
- Render preview lines while creating
- Convert to selection mask when completed
- Consider snap-to-angle with Shift held (45° increments)

## Related Files
- `stagforge/frontend/js/tools/LassoTool.js` (similar implementation pattern)
- `stagforge/frontend/js/core/SelectionManager.js`
