# Erode


![Erode example](../gallery/filters/erode.jpg)

Morphological erosion.

Erodes away boundaries of foreground objects. Useful for removing
small white noise and detaching connected objects.

Parameters:
    kernel_size: Size of structuring element (default 3)
    shape: Shape of kernel ('rect', 'ellipse', 'cross')
    iterations: Number of times to apply erosion

Example:
    'erode(3)' or 'erode(kernel_size=5,iterations=2)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kernel_size` | int | 3 | Size of structuring element (default 3) |
| `shape` | str | 'rect' | Shape of kernel ('rect', 'ellipse', 'cross') |
| `iterations` | int | 1 | Number of times to apply erosion |

## Examples

```
erode(3)
```

## Frameworks

Native support: CV, RAW
