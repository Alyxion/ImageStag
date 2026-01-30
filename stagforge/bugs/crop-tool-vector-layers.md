# Crop Tool Fails with Vector Layers

## Description
The Crop tool throws an error when applying crop if vector layers are present in the document.

## Steps to Reproduce
1. Create a document
2. Add a vector layer (or have any vector layer present)
3. Select the Crop tool
4. Draw a crop region
5. Press Enter to apply crop

## Error
```
CropTool.js:190 Uncaught TypeError: Cannot read properties of null (reading 'getImageData')
    at CropTool.applyCrop (CropTool.js:190:45)
    at CropTool.onKeyDown (CropTool.js:82:18)
    at Proxy.handleKeyDown (KeyboardEvents.js:195:42)
```

## Likely Cause
Vector layers (and possibly SVG layers) have `ctx = null` since they don't support direct pixel manipulation. The `applyCrop` method likely calls `layer.ctx.getImageData()` without checking if the layer is a raster layer first.

## Affected Files
- `stagforge/frontend/js/tools/CropTool.js` (line 190)

## Suggested Fix
Check layer type before calling `getImageData()`. For vector/SVG layers, either:
- Skip them (crop only affects raster layers)
- Rasterize them during crop
- Adjust their bounds/offset without pixel manipulation
