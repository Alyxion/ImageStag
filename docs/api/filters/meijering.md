# Meijering


![Meijering example](../gallery/filters/meijering.jpg)

Meijering neuriteness filter for neural structure detection.

Optimized for detecting neurites (nerve cell extensions) in
microscopy images. Uses a modification of the Frangi filter.

Requires: scikit-image (optional dependency)

Parameters:
    scale_min: Minimum sigma for Gaussian derivatives
    scale_max: Maximum sigma for Gaussian derivatives
    scale_step: Step size between scales
    black_ridges: If True, detect black ridges on white background

Example:
    'meijering()' or 'meijering(scale_min=0.5)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `scale_min` | float | 1.0 | Minimum sigma for Gaussian derivatives |
| `scale_max` | float | 10.0 | Maximum sigma for Gaussian derivatives |
| `scale_step` | float | 2.0 | Step size between scales |
| `black_ridges` | bool | True | If True, detect black ridges on white background |

## Examples

```
meijering()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
