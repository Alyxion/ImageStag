# AdaptiveThreshold


![AdaptiveThreshold example](../gallery/filters/adaptivethreshold.jpg)

Adaptive thresholding based on local image regions.

Computes threshold for each pixel based on its neighborhood,
handling uneven lighting better than global thresholding.

Parameters:
    max_value: Value assigned to pixels exceeding threshold (default 255)
    method: 'mean' or 'gaussian' - how to compute local threshold
    block_size: Size of neighborhood (must be odd, default 11)
    c: Constant subtracted from mean/weighted mean (default 2)

Example:
    'adaptivethreshold()' - default settings
    'adaptivethreshold(method=gaussian,block_size=15,c=5)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `max_value` | int | 255 | Value assigned to pixels exceeding threshold (default 255) |
| `method` | str | 'gaussian' | 'mean' or 'gaussian' - how to compute local threshold |
| `block_size` | int | 11 | Size of neighborhood (must be odd, default 11) |
| `c` | float | 2.0 | Constant subtracted from mean/weighted mean (default 2) |

## Examples

```
adaptivethreshold()
```
```
adaptivethreshold(method=gaussian,block_size=15,c=5)
```

## Frameworks

Native support: CV, RAW
