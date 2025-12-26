# Sato


![Sato example](../gallery/filters/sato.jpg)

Sato tubeness filter for 2D/3D tubular structure detection.

Similar to Frangi but uses different Hessian eigenvalue
combinations, often preferred for 3D data.

Requires: scikit-image (optional dependency)

Parameters:
    scale_min: Minimum sigma for Gaussian derivatives
    scale_max: Maximum sigma for Gaussian derivatives
    scale_step: Step size between scales
    black_ridges: If True, detect black ridges on white background

Example:
    'sato()' or 'sato(scale_min=0.5,scale_max=5)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `scale_min` | float | 1.0 | Minimum sigma for Gaussian derivatives |
| `scale_max` | float | 10.0 | Maximum sigma for Gaussian derivatives |
| `scale_step` | float | 2.0 | Step size between scales |
| `black_ridges` | bool | True | If True, detect black ridges on white background |

## Examples

```
sato()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
