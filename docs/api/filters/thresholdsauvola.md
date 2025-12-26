# ThresholdSauvola


![ThresholdSauvola example](../gallery/filters/thresholdsauvola.jpg)

Sauvola's local thresholding.

Improved version of Niblack that normalizes the local
standard deviation. Better for document images and
text binarization.

Requires: scikit-image (optional dependency)

Parameters:
    window_size: Size of local window (must be odd)
    k: Sensitivity parameter (typically 0.2 to 0.5)
    r: Dynamic range of standard deviation (default 128)

Example:
    'thresholdsauvola(window_size=25,k=0.35)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `window_size` | int | 15 | Size of local window (must be odd) |
| `k` | float | 0.2 | Sensitivity parameter (typically 0.2 to 0.5) |
| `r` | float | 128.0 | Dynamic range of standard deviation (default 128) |

## Examples

```
thresholdsauvola(window_size=25,k=0.35)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
