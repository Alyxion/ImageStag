# Gradient Fill Shifted on Offset Layers

## Status: OPEN

## Description
When using the Gradient tool on a layer that is not at position (0, 0), the gradient preview and final result are drawn shifted by the layer's offset amount toward the top-left.

## Steps to Reproduce
1. Create a new document
2. Create or move a layer so its offset is not (0, 0), e.g. offset (50, 50)
3. Make a selection (optional)
4. Use the Gradient tool to draw a gradient on that layer
5. Observe both the preview and the finalized gradient are shifted

## Expected Behavior
The gradient should align with the mouse drag positions in document space, regardless of the layer's offset.

## Actual Behavior
The gradient appears shifted toward the top-left by the layer's offset amount. Both the live preview and the committed result show this shift.

## Likely Cause
The Gradient tool operates in document coordinates (`docX`/`docY`) and draws to a document-sized preview canvas, but when compositing onto the layer it draws at `-offsetX, -offsetY`. The start/end coordinates used to define the gradient may not be correctly accounting for this offset, causing the gradient origin to be misplaced.

## Affected Files
- `stagforge/frontend/js/tools/GradientTool.js`
