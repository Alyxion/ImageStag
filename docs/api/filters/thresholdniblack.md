# ThresholdNiblack


![ThresholdNiblack example](../gallery/filters/thresholdniblack.jpg)

Niblack's local thresholding.

Computes threshold for each pixel based on local mean
and standard deviation. Better for uneven illumination
than global thresholds.

Requires: scikit-image (optional dependency)

Parameters:
    window_size: Size of local window (must be odd)
    k: Sensitivity parameter (typically -0.2 to 0.2)

Example:
    'thresholdniblack(window_size=25,k=0.2)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `window_size` | int | 15 | Size of local window (must be odd) |
| `k` | float | 0.2 | Sensitivity parameter (typically -0.2 to 0.2) |

## Examples

```
thresholdniblack(window_size=25,k=0.2)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
