# ContourDetector


![ContourDetector example](../gallery/filters/contourdetector.jpg)

Detect contours in images.

Returns a GeometryList containing Polygon geometries for each detected contour.
Works best on binary or edge-detected images.

Parameters:
    threshold: Threshold value for binarization (0 = use input as-is)
    min_area: Minimum contour area to include
    color: Contour color for visualization (default green)
    thickness: Line thickness for visualization (default 2)

Example:
    'contourdetector(threshold=128,min_area=200)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `threshold` | int | 0 | Threshold value for binarization (0 = use input as-is) |
| `min_area` | float | 100.0 | Minimum contour area to include |
| `color` | any | '#00FF00' | Contour color for visualization (default green) |
| `thickness` | int | 2 | Line thickness for visualization (default 2) |

## Examples

```
contourdetector(threshold=128,min_area=200)
```

## Frameworks

Native support: CV, RAW
