# CLAHE


![CLAHE example](../gallery/filters/clahe.jpg)

Contrast Limited Adaptive Histogram Equalization.

Improves local contrast while limiting noise amplification.
Divides image into tiles and applies histogram equalization to each.

Parameters:
    clip_limit: Threshold for contrast limiting (default 2.0)
    tile_size: Size of grid for histogram equalization (default 8)

Example:
    'clahe()' - default settings
    'clahe(clip_limit=4.0,tile_size=16)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `clip_limit` | float | 2.0 | Threshold for contrast limiting (default 2.0) |
| `tile_size` | int | 8 | Size of grid for histogram equalization (default 8) |

## Examples

```
clahe()
```
```
clahe(clip_limit=4.0,tile_size=16)
```

## Frameworks

Native support: CV, RAW
