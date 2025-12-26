# Gabor


![Gabor example](../gallery/filters/gabor.jpg)

Gabor filter for texture analysis.

Applies a Gabor filter which is useful for texture
classification and edge detection at specific
orientations and frequencies.

Requires: scikit-image (optional dependency)

Parameters:
    frequency: Spatial frequency of the filter (0.1 typical)
    theta: Orientation in radians (0 = horizontal)
    sigma_x: Standard deviation in x direction
    sigma_y: Standard deviation in y direction
    mode: Filter response mode ('real' or 'magnitude')

Example:
    'gabor(frequency=0.1)' or 'gabor(frequency=0.2,theta=0.785)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `frequency` | float | 0.1 | Spatial frequency of the filter (0.1 typical) |
| `theta` | float | 0.0 | Orientation in radians (0 = horizontal) |
| `sigma_x` | float | None | Standard deviation in x direction |
| `sigma_y` | float | None | Standard deviation in y direction |
| `mode` | str | 'magnitude' | Filter response mode ('real' or 'magnitude') |

## Examples

```
gabor(frequency=0.1)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
