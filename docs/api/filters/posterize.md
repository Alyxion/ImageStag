# Posterize


![Posterize example](../gallery/filters/posterize.jpg)

Reduce the number of bits per color channel.

Creates a posterized/banded effect by reducing color depth.

Parameters:
    bits: Number of bits to keep per channel (1-8, default 4)

Example:
    'posterize(4)' - keep 4 bits per channel (16 levels)
    'posterize(bits=2)' - keep 2 bits (4 levels, strong effect)

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `bits` | int | 4 | Number of bits to keep per channel (1-8, default 4) |

## Examples

```
posterize(4)
```
```
posterize(bits=2)
```

## Frameworks

Native support: PIL
