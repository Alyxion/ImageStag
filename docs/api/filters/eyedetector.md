# EyeDetector


![EyeDetector example](../gallery/filters/eyedetector.jpg)

Detect eyes in images using OpenCV Haar cascades.

Returns a GeometryList containing Rectangle geometries for each detected eye.
Use DrawGeometry combiner to visualize eyes on the original image.

Parameters:
    scale_factor: Scale factor for detection pyramid (default 1.1)
    min_neighbors: Minimum neighbors for detection (default 5)
    color: Rectangle color for visualization (default red)
    thickness: Line thickness for visualization (default 2)

Example:
    'eyedetector(min_neighbors=3)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `scale_factor` | float | 1.1 | Scale factor for detection pyramid (default 1.1) |
| `min_neighbors` | int | 5 | Minimum neighbors for detection (default 5) |
| `color` | any | '#FF0000' | Rectangle color for visualization (default red) |
| `thickness` | int | 2 | Line thickness for visualization (default 2) |

## Examples

```
eyedetector(min_neighbors=3)
```

## Frameworks

Native support: CV, RAW
