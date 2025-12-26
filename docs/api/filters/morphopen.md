# MorphOpen


![MorphOpen example](../gallery/filters/morphopen.jpg)

Morphological opening (erosion followed by dilation).

Useful for removing small objects/noise while preserving shape and
size of larger objects.

Parameters:
    kernel_size: Size of structuring element (default 3)
    shape: Shape of kernel ('rect', 'ellipse', 'cross')

Example:
    'morphopen(5)' or 'morphopen(kernel_size=7,shape=ellipse)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kernel_size` | int | 3 | Size of structuring element (default 3) |
| `shape` | str | 'rect' | Shape of kernel ('rect', 'ellipse', 'cross') |

## Examples

```
morphopen(5)
```

## Frameworks

Native support: CV, RAW
