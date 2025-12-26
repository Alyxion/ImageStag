# LBP


![LBP example](../gallery/filters/lbp.jpg)

Local Binary Pattern texture descriptor.

Computes LBP features at each pixel. LBP encodes
the local texture pattern by comparing each pixel
to its neighbors.

Requires: scikit-image (optional dependency)

Parameters:
    radius: Radius of the circle (default 1)
    n_points: Number of points on the circle (default 8)
    method: LBP method ('default', 'ror', 'uniform', 'nri_uniform', 'var')

Example:
    'lbp()' or 'lbp(radius=2,n_points=16)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `radius` | int | 1 | Radius of the circle (default 1) |
| `n_points` | int | 8 | Number of points on the circle (default 8) |
| `method` | str | 'default' | LBP method ('default', 'ror', 'uniform', 'nri_uniform', 'var') |

## Examples

```
lbp()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
