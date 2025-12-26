# MaxFilter


![MaxFilter example](../gallery/filters/maxfilter.jpg)

Maximum filter - picks the brightest pixel in a window.

Useful for removing dark noise and expanding bright areas.

Parameters:
    size: Window size (default 3)

Example:
    'maxfilter(3)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `size` | int | 3 | Window size (default 3) |

## Examples

```
maxfilter(3)
```

## Frameworks

Native support: PIL
