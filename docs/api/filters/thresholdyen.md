# ThresholdYen


![ThresholdYen example](../gallery/filters/thresholdyen.jpg)

Yen's maximum entropy thresholding.

Maximizes the entropy of the thresholded image.
Works well for images with uneven illumination.

Requires: scikit-image (optional dependency)

Parameters:
    nbins: Number of histogram bins (default 256)

Example:
    'thresholdyen()' or 'thresholdyen(nbins=128)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `nbins` | int | 256 | Number of histogram bins (default 256) |

## Examples

```
thresholdyen()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
