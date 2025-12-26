# MorphClose


![MorphClose example](../gallery/filters/morphclose.jpg)

Morphological closing (dilation followed by erosion).

Useful for closing small holes inside foreground objects.

Parameters:
    kernel_size: Size of structuring element (default 3)
    shape: Shape of kernel ('rect', 'ellipse', 'cross')

Example:
    'morphclose(5)' or 'morphclose(kernel_size=7,shape=ellipse)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kernel_size` | int | 3 | Size of structuring element (default 3) |
| `shape` | str | 'rect' | Shape of kernel ('rect', 'ellipse', 'cross') |

## Examples

```
morphclose(5)
```

## Frameworks

Native support: CV, RAW
