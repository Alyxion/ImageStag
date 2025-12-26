# MedianFilter


![MedianFilter example](../gallery/filters/medianfilter.jpg)

Median filter using PIL.

Picks the median pixel value in a window of the given size.
Alternative to MedianBlur for PIL-native processing.

Parameters:
    size: Window size (default 3)

Example:
    'medianfilter(5)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `size` | int | 3 | Window size (default 3) |

## Examples

```
medianfilter(5)
```

## Frameworks

Native support: PIL
