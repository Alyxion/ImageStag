# MatchHistograms

Match histogram to a reference image.

Transforms image colors to match the color distribution
of a reference image. Useful for style transfer and
color grading.

Requires: scikit-image (optional dependency)

Note: Pass reference image via context['histogram_reference']

Parameters:
    channel_axis: Axis for color channels (default 2 for RGB)

Example:
    'matchhistograms()'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `channel_axis` | int | 2 | Axis for color channels (default 2 for RGB) |

## Examples

```
matchhistograms()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
