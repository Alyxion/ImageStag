# ModeFilter


![ModeFilter example](../gallery/filters/modefilter.jpg)

Mode filter - picks the most common pixel in a window.

Useful for removing isolated pixels and creating a posterized effect.

Parameters:
    size: Window size (default 3)

Example:
    'modefilter(5)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `size` | int | 3 | Window size (default 3) |

## Examples

```
modefilter(5)
```

## Frameworks

Native support: PIL
