# RemoveSmallObjects


![RemoveSmallObjects example](../gallery/filters/removesmallobjects.jpg)

Remove small connected regions from binary image.

Filters objects by area threshold - much more intuitive than
iterating morphological operations.

Requires: scikit-image (optional dependency)

Parameters:
    min_size: Minimum object size in pixels to keep
    connectivity: Pixel connectivity (1 = 4-connected, 2 = 8-connected)

Example:
    'removesmallobjects(min_size=100)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `min_size` | int | 64 | Minimum object size in pixels to keep |
| `connectivity` | int | 1 | Pixel connectivity (1 = 4-connected, 2 = 8-connected) |

## Examples

```
removesmallobjects(min_size=100)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
