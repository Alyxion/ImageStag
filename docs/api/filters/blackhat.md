# BlackHat


![BlackHat example](../gallery/filters/blackhat.jpg)

Black-hat transform (difference between closing and input).

Extracts small dark elements on bright background.

Parameters:
    kernel_size: Size of structuring element (default 9)
    shape: Shape of kernel ('rect', 'ellipse', 'cross')

Example:
    'blackhat(9)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kernel_size` | int | 9 | Size of structuring element (default 9) |
| `shape` | str | 'rect' | Shape of kernel ('rect', 'ellipse', 'cross') |

## Examples

```
blackhat(9)
```

## Frameworks

Native support: CV, RAW
