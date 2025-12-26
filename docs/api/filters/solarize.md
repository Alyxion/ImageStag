# Solarize


![Solarize example](../gallery/filters/solarize.jpg)

Invert pixels above a threshold for a solarized effect.

Creates a partially inverted image, simulating the Sabattier effect
from darkroom photography.

Parameters:
    threshold: Pixel value threshold (0-255, default 128)

Example:
    'solarize()' or 'solarize(threshold=100)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `threshold` | int | 128 | Pixel value threshold (0-255, default 128) |

## Examples

```
solarize()
```

## Frameworks

Native support: PIL
