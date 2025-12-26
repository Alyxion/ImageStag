# GaborBank


![GaborBank example](../gallery/filters/gaborbank.jpg)

Apply a bank of Gabor filters at multiple orientations.

Creates a multi-orientation texture response by applying
Gabor filters at evenly spaced angles and combining the
maximum response.

Requires: scikit-image (optional dependency)

Parameters:
    frequency: Spatial frequency of the filter
    n_orientations: Number of orientation angles (default 4)

Example:
    'gaborbank(frequency=0.1)' or 'gaborbank(n_orientations=8)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `frequency` | float | 0.1 | Spatial frequency of the filter |
| `n_orientations` | int | 4 | Number of orientation angles (default 4) |

## Examples

```
gaborbank(frequency=0.1)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
