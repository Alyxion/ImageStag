# MinFilter


![MinFilter example](../gallery/filters/minfilter.jpg)

Minimum filter - picks the darkest pixel in a window.

Useful for removing light noise and expanding dark areas.

Parameters:
    size: Window size (default 3)

Example:
    'minfilter(3)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `size` | int | 3 | Window size (default 3) |

## Examples

```
minfilter(3)
```

## Frameworks

Native support: PIL
