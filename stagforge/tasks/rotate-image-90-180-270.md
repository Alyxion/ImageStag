# Rotate Image by 90/180/270 Degrees

## Description
Add the ability to rotate the entire image/canvas by 90°, 180°, or 270° (clockwise). This is a destructive operation that affects all layers and changes document dimensions for 90°/270° rotations.

## Behavior
- **Image > Rotate Canvas > 90° CW** - Rotate clockwise
- **Image > Rotate Canvas > 90° CCW** - Rotate counter-clockwise
- **Image > Rotate Canvas > 180°** - Flip upside down
- Document dimensions swap for 90°/270° (width ↔ height)
- All layers are rotated together
- Should be undoable

## Implementation Notes

### Raster Layers
- Rotate canvas content using standard canvas rotation
- Swap width/height for 90°/270°
- Update layer offsets appropriately

### Vector Layers
- Rotate all shape coordinates around document center
- Update shape properties (rectangles become rotated rectangles, etc.)
- Or: transform coordinate system

### SVG Layers
- Modify internal SVG transform matrix
- Add rotation transform to root SVG element
- Preserve original SVG content, apply rotation via wrapper transform
- Example: `<g transform="rotate(90, cx, cy)">...original content...</g>`

### Selection
- Clear or rotate selection mask accordingly

## Menu Location
- Image > Rotate Canvas > 90° Clockwise
- Image > Rotate Canvas > 90° Counter-Clockwise
- Image > Rotate Canvas > 180°
