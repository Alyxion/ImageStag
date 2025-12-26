# DenoiseTV


![DenoiseTV example](../gallery/filters/denoisetv.jpg)

Total Variation (Chambolle) denoising.

Edge-preserving denoising using TV regularization.
Good at preserving sharp edges while smoothing noise.

Requires: scikit-image (optional dependency)

Parameters:
    weight: Denoising weight (higher = more smoothing, 0.1-0.3 typical)
    n_iter_max: Maximum iterations (default 200)

Example:
    'denoisetv()' or 'denoisetv(weight=0.2)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `weight` | float | 0.1 | Denoising weight (higher = more smoothing, 0.1-0.3 typical) |
| `n_iter_max` | int | 200 | Maximum iterations (default 200) |

## Examples

```
denoisetv()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
