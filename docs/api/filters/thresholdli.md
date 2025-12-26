# ThresholdLi


![ThresholdLi example](../gallery/filters/thresholdli.jpg)

Li's minimum cross-entropy thresholding.

Iteratively minimizes cross-entropy between foreground
and background. Often works better than Otsu for
non-bimodal histograms.

Requires: scikit-image (optional dependency)

Parameters:
    tolerance: Convergence tolerance (default 0.5)

Example:
    'thresholdli()' or 'thresholdli(tolerance=0.1)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `tolerance` | float | 0.5 | Convergence tolerance (default 0.5) |

## Examples

```
thresholdli()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
