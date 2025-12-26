# Felzenszwalb


![Felzenszwalb example](../gallery/filters/felzenszwalb.jpg)

Felzenszwalb's efficient graph-based segmentation.

Produces segments that are more irregular than SLIC
but often better match object boundaries.

Requires: scikit-image (optional dependency)

Parameters:
    scale: Free parameter controlling segment size
    sigma: Gaussian pre-smoothing width
    min_size: Minimum segment size

Example:
    'felzenszwalb()' or 'felzenszwalb(scale=200,min_size=50)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `scale` | float | 100.0 | Free parameter controlling segment size |
| `sigma` | float | 0.5 | Gaussian pre-smoothing width |
| `min_size` | int | 50 | Minimum segment size |

## Examples

```
felzenszwalb()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
