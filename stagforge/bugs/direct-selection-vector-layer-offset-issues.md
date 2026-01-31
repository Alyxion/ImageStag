# Bug: Direct Selection tool has issues with offset vector layers

## Description
The Direct Selection tool and general drawing in vector layers has odd behavior when the layer has an offset (origin other than 0,0). Shape interactions and transformations appear broken.

## Steps to Reproduce
1. Create a new document (e.g., 800x600)
2. Create a vector layer
3. Move the vector layer to have offsetX=200, offsetY=200
4. Draw shapes on this offset layer
5. Try to select and move shapes with Direct Selection tool
6. Observe incorrect behavior

## Expected Behavior
- Shapes should be selectable and movable correctly regardless of layer offset
- Coordinate transformations should account for layer offset

## Actual Behavior
- Selection may miss shapes
- Moving shapes may jump to wrong positions
- Transformations may be applied incorrectly

## Technical Notes
The issue is likely in coordinate conversion between:
- Document coordinates (mouse position)
- Layer coordinates (shape storage)
- Canvas coordinates (rendering)

Need to verify `docToCanvas` and `canvasToDoc` are used correctly in DirectSelectTool.

## Affected Files
- `stagforge/frontend/js/tools/DirectSelectTool.js`
- `stagforge/frontend/js/core/VectorLayer.js`

## Test Required
Create automated test that:
1. Creates vector layer at non-zero offset
2. Adds shapes
3. Interacts with Direct Selection tool
4. Verifies shape positions are correct
