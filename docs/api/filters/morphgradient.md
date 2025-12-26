# MorphGradient


![MorphGradient example](../gallery/filters/morphgradient.jpg)

Morphological gradient (difference between dilation and erosion).

Produces an outline of the object.

Parameters:
    kernel_size: Size of structuring element (default 3)
    shape: Shape of kernel ('rect', 'ellipse', 'cross')

Example:
    'morphgradient(3)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kernel_size` | int | 3 | Size of structuring element (default 3) |
| `shape` | str | 'rect' | Shape of kernel ('rect', 'ellipse', 'cross') |

## Examples

```
morphgradient(3)
```

## Frameworks

Native support: CV, RAW
