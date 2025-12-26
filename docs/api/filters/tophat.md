# TopHat


![TopHat example](../gallery/filters/tophat.jpg)

Top-hat transform (difference between input and opening).

Extracts small bright elements on dark background.

Parameters:
    kernel_size: Size of structuring element (default 9)
    shape: Shape of kernel ('rect', 'ellipse', 'cross')

Example:
    'tophat(9)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kernel_size` | int | 9 | Size of structuring element (default 9) |
| `shape` | str | 'rect' | Shape of kernel ('rect', 'ellipse', 'cross') |

## Examples

```
tophat(9)
```

## Frameworks

Native support: CV, RAW
