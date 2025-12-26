# ThresholdOtsu


![ThresholdOtsu example](../gallery/filters/thresholdotsu.jpg)

Otsu's automatic thresholding.

Computes the optimal threshold to separate foreground
from background by maximizing inter-class variance.
Works well when histogram is bimodal.

Requires: scikit-image (optional dependency)

Parameters:
    nbins: Number of histogram bins (default 256)

Example:
    'thresholdotsu()' or 'thresholdotsu(nbins=128)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `nbins` | int | 256 | Number of histogram bins (default 256) |

## Examples

```
thresholdotsu()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
