# Hessian


![Hessian example](../gallery/filters/hessian.jpg)

Hessian-based ridge detection (general-purpose).

Computes the Hessian matrix eigenvalues at each pixel
to detect ridges and edges at multiple scales.

Requires: scikit-image (optional dependency)

Parameters:
    scale_min: Minimum sigma for Gaussian derivatives
    scale_max: Maximum sigma for Gaussian derivatives
    scale_step: Step size between scales
    beta: Threshold for distinguishing ridges from noise
    black_ridges: If True, detect black ridges on white background

Example:
    'hessian()' or 'hessian(scale_max=20)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `scale_min` | float | 1.0 | Minimum sigma for Gaussian derivatives |
| `scale_max` | float | 10.0 | Maximum sigma for Gaussian derivatives |
| `scale_step` | float | 2.0 | Step size between scales |
| `beta` | float | 0.5 | Threshold for distinguishing ridges from noise |
| `black_ridges` | bool | True | If True, detect black ridges on white background |

## Examples

```
hessian()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
