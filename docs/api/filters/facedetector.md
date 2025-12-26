# FaceDetector


![FaceDetector example](../gallery/filters/facedetector.jpg)

Detect faces in images using OpenCV Haar cascades.

Returns a GeometryList containing Rectangle geometries for each detected face.
Use DrawGeometry combiner to visualize faces on the original image.

Uses multiple cascades (frontal, frontal-alt, profile) for better detection
of faces at various angles.

Parameters:
    scale_factor: Scale factor for detection pyramid (default 1.1)
    min_neighbors: Minimum neighbors for detection (default 5)
    min_size: Minimum face size as (width, height)
    use_profile: Also detect profile/side faces (default True)
    rotation_range: Max rotation angle for tilted faces (0=disabled, 15=try -15° to +15°)
    rotation_step: Step between rotation angles (default 5)
    color: Rectangle color for visualization (default green)
    thickness: Line thickness for visualization (default 2)

Example:
    # Detect and visualize:
    Source -> FaceDetector -+-> DrawGeometry -> Output
               |            |
               +-- (image) -+

    # In pipeline string:
    'facedetector(min_neighbors=3)'

## Aliases

- `face`
- `faces`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `scale_factor` | float | 1.1 | Scale factor for detection pyramid (default 1.1) |
| `min_neighbors` | int | 5 | Minimum neighbors for detection (default 5) |
| `min_size` | tuple | (30, 30) | Minimum face size as (width, height) |
| `use_profile` | bool | True | Also detect profile/side faces (default True) |
| `rotation_range` | int | 0 | Max rotation angle for tilted faces (0=disabled, 15=try -15° to +15°) |
| `rotation_step` | int | 5 | Step between rotation angles (default 5) |
| `color` | any | '#00FF00' | Rectangle color for visualization (default green) |
| `thickness` | int | 2 | Line thickness for visualization (default 2) |

## Examples

```
facedetector(min_neighbors=3)
```

## Frameworks

Native support: CV, RAW
