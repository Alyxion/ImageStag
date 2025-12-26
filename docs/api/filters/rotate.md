# Rotate


![Rotate example](../gallery/filters/rotate.jpg)

Rotate image by angle in degrees.

For 90°, 180°, 270° rotations, uses fast transpose operations.
For other angles, uses interpolation with optional canvas expansion.

Supports multiple backends for optimal performance on fixed angles.

Parameters:
    angle: Rotation in degrees, counter-clockwise (0, 90, 180, 270, or any)
    expand: If True, expand canvas to fit rotated image (only for non-90° angles)
    fill: Background color as hex string, e.g., '#000000' (only for non-90° angles)
    backend: Processing backend ('auto', 'pil', 'cv', 'numpy')

Example:
    'rotate 90'      - rotate 90° CCW (fast)
    'rotate 180'     - rotate 180° (fast)
    'rotate -90'     - rotate 90° CW (fast)
    'rotate 45'      - rotate 45° with interpolation
    'rotate 45 expand=true' - rotate with canvas expansion

Aliases:
    'rot90', 'rot180', 'rot270' - shortcuts for fixed angles
    'rotcw', 'rotccw' - 90° clockwise/counter-clockwise

## Aliases

- `rot90` → `Rotate(angle=90)`
- `rot180` → `Rotate(angle=180)`
- `rot270` → `Rotate(angle=270)`
- `rotcw` → `Rotate(angle=-90)`
- `rotccw` → `Rotate(angle=90)`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `angle` | float | 0.0 | Rotation in degrees, counter-clockwise (0, 90, 180, 270, or any) |
| `expand` | bool | False | If True, expand canvas to fit rotated image (only for non-90° angles) |
| `fill` | any | '#000000' | Background color as hex string, e.g., '#000000' (only for non-90° angles) |
| `backend` | str | 'auto' | Processing backend ('auto', 'pil', 'cv', 'numpy') |

## Examples

```
rotate 90
```
```
rotate 180
```
```
rotate -90
```
```
rotate 45
```
```
rotate 45 expand=true
```
```
rot90
```
```
rotcw
```

## Frameworks

Native support: PIL, CV, RAW
