# RescaleIntensity


![RescaleIntensity example](../gallery/filters/rescaleintensity.jpg)

Rescale image intensity to a specified range.

Linearly scales pixel values to fit within a new range.
Useful for normalizing image contrast.

Requires: scikit-image (optional dependency)

Parameters:
    in_range: Input range ('image' = actual range, 'dtype' = dtype range)
    out_range: Output range ('dtype' = full dtype range, or tuple)

Example:
    'rescaleintensity()' - stretch to full range

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `in_range` | str | 'image' | Input range ('image' = actual range, 'dtype' = dtype range) |
| `out_range` | str | 'dtype' | Output range ('dtype' = full dtype range, or tuple) |

## Examples

```
rescaleintensity()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
