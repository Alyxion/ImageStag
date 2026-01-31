# Bug: Adding vector shape to text layer throws TypeError

## Description
When attempting to draw a vector shape (rect, ellipse, etc.) while a text layer is selected, instead of creating a new vector layer, the tool tries to call `addShape` on the text layer which doesn't have this method.

## Steps to Reproduce
1. Create a text layer
2. Keep the text layer selected
3. Switch to Rectangle tool (or other shape tool) in vector mode
4. Try to draw a rectangle

## Error Message
```
TypeError: layer.addShape is not a function
    at RectTool.createVectorShape (RectTool.js:158:15)
    at RectTool.onMouseUp (RectTool.js:95:18)
    at Proxy.handleMouseUp (CanvasEvents.js:168:42)
```

## Expected Behavior
The tool should detect that the current layer is not a vector layer and either:
1. Automatically create a new vector layer for the shape
2. Or show a message asking user to create/select a vector layer

## Actual Behavior
JavaScript error, shape is not created.

## Affected Files
- `stagforge/frontend/js/tools/RectTool.js:158` - createVectorShape method
- `stagforge/frontend/js/tools/EllipseTool.js` - likely same issue
- `stagforge/frontend/js/tools/LineTool.js` - likely same issue
- `stagforge/frontend/js/tools/PolygonTool.js` - likely same issue

## Fix Approach
In `createVectorShape`, check if layer has `addShape` method. If not:
```javascript
if (!layer || typeof layer.addShape !== 'function') {
    // Create new vector layer and add shape to it
    const vectorLayer = new VectorLayer({...});
    app.layerStack.addLayer(vectorLayer);
    vectorLayer.addShape(shape);
}
```
