# DrawGeometry


![DrawGeometry example](../gallery/filters/drawgeometry.jpg)

Draw geometries onto an image.

Combines an image with a GeometryList, drawing each geometry
using its metadata styles (color, thickness, filled).

Inputs:
    image: Base image to draw on
    geometry: GeometryList containing shapes to draw

Parameters:
    use_geometry_styles: Use per-geometry colors/thickness (default True)
    color: Default color as hex string (e.g., "#FF0000")
    thickness: Default line thickness

Example:
    Source -> FaceDetector -> DrawGeometry -> Output
                  |              ^
                  +-- (image) ---+

## Aliases

- `draw`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `color` | color | '#00FF00' | Default color as hex string (e.g., "#FF0000") |
| `thickness` | int | 2 | Default line thickness |

## Input Ports

- **input**: Base image
- **geometry**: Geometries to draw

## Frameworks

Native support: CV, RAW
