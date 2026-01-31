# Bug: Marching lines and text bounds blurry at zoom levels

## Description
Marching ants (selection outline) and text layer bounding boxes are rendered at 100% scale and become blurry when zoomed in. At 400% zoom, they appear pixelated/blurry instead of sharp.

## Steps to Reproduce
1. Make a selection
2. Zoom in to 200% or 400%
3. Observe the marching ants line is blurry
4. Also observe text layer bounding boxes are blurry

## Expected Behavior
UI elements like selection outlines and bounding boxes should render sharply at any zoom level, as they are overlays not part of the image.

## Actual Behavior
These elements are rendered to a canvas at document resolution and then scaled, causing blur at higher zoom levels.

## Technical Notes
The selection outline and bounds should be:
1. Rendered at screen resolution, not document resolution
2. Or re-rendered when zoom changes
3. Using CSS/SVG overlays instead of canvas rendering

## Affected Files
- `stagforge/frontend/js/core/Renderer.js` - preview layer rendering
- `stagforge/frontend/js/core/SelectionManager.js` - outline rendering
- `stagforge/frontend/js/tools/TextTool.js` - bounding box rendering
