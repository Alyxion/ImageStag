# Sobel


![Sobel example](../gallery/filters/sobel.jpg)

Sobel edge detection.

Computes gradient using Sobel operator.

Parameters:
    dx: Order of derivative in x direction (0 or 1)
    dy: Order of derivative in y direction (0 or 1)
    kernel_size: Sobel kernel size (1, 3, 5, or 7)
    scale: Scale factor for computed values
    normalize: Normalize output to 0-255 range

Example:
    'sobel(1,0)' for horizontal edges
    'sobel(0,1)' for vertical edges
    'sobel(1,1)' for both directions

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `dx` | int | 1 | Order of derivative in x direction (0 or 1) |
| `dy` | int | 1 | Order of derivative in y direction (0 or 1) |
| `kernel_size` | int | 3 | Sobel kernel size (1, 3, 5, or 7) |
| `scale` | float | 1.0 | Scale factor for computed values |
| `normalize` | bool | True | Normalize output to 0-255 range |

## Examples

```
sobel(1,0)
```
```
sobel(0,1)
```
```
sobel(1,1)
```

## Frameworks

Native support: CV, RAW
