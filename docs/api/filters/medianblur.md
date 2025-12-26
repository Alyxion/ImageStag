# MedianBlur


![MedianBlur example](../gallery/filters/medianblur.jpg)

Median blur filter for noise removal.

Replaces each pixel with the median of neighboring pixels.
Effective for salt-and-pepper noise while preserving edges.

Parameters:
    ksize: Kernel size (must be odd, e.g., 3, 5, 7)

Example:
    'medianblur(5)' or 'medianblur(ksize=3)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `ksize` | int | 5 | Kernel size (must be odd, e.g., 3, 5, 7) |

## Examples

```
medianblur(5)
```

## Frameworks

Native support: CV, RAW
