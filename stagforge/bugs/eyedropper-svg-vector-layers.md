# Eyedropper Does Not Work on SVG and Vector Layers

## Description
When using the Eyedropper tool on SVG or Vector layers, the color is not selected/sampled.

## Steps to Reproduce
1. Create or import an SVG layer
2. Or create a Vector layer with colored shapes
3. Select the Eyedropper tool
4. Click on a colored area of the SVG/Vector layer
5. Observe: foreground color does not change

## Expected Behavior
The eyedropper should sample the visible color at the click position, regardless of layer type.

## Likely Cause
Eyedropper may be reading from the layer's canvas directly, but SVG/Vector layers render differently or have `ctx = null`.

## Suggested Fix
Sample from the composite canvas (rendered view) instead of individual layer canvas, or handle SVG/Vector layers specially.
