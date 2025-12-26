# Watershed


![Watershed example](../gallery/filters/watershed.jpg)

Watershed segmentation from markers.

Grows regions from seed points (markers) using watershed
algorithm. Requires markers via context['watershed_markers'].

Requires: scikit-image (optional dependency)

Parameters:
    compactness: Higher values make segments more compact
    watershed_line: Include a one-pixel line between segments

Example:
    'watershed()' or 'watershed(compactness=0.1)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `compactness` | float | 0.0 | Higher values make segments more compact |
| `watershed_line` | bool | False | Include a one-pixel line between segments |

## Examples

```
watershed()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
