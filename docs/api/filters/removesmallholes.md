# RemoveSmallHoles


![RemoveSmallHoles example](../gallery/filters/removesmallholes.jpg)

Fill small holes in binary objects.

Fills holes (background regions surrounded by foreground)
that are smaller than the specified area.

Requires: scikit-image (optional dependency)

Parameters:
    area_threshold: Maximum hole size to fill
    connectivity: Pixel connectivity (1 = 4-connected, 2 = 8-connected)

Example:
    'removesmallholes(area_threshold=50)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `area_threshold` | int | 64 | Maximum hole size to fill |
| `connectivity` | int | 1 | Pixel connectivity (1 = 4-connected, 2 = 8-connected) |

## Examples

```
removesmallholes(area_threshold=50)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
