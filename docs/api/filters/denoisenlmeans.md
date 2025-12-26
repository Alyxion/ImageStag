# DenoiseNLMeans


![DenoiseNLMeans example](../gallery/filters/denoisenlmeans.jpg)

Non-local means denoising.

State-of-the-art denoising using patch matching. Finds similar
patches across the image and averages them, preserving detail
while removing noise. Slower but much better quality than
simple blur filters.

Requires: scikit-image (optional dependency)

Parameters:
    h: Filter strength (higher = more smoothing, 0.06-0.12 typical)
    patch_size: Size of patches to compare (default 5)
    patch_distance: Maximum distance to search for patches (default 6)
    fast_mode: Use faster but approximate algorithm (default True)

Example:
    'denoisenlmeans()' - default settings
    'denoisenlmeans(h=0.1,fast_mode=false)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `h` | float | 0.08 | Filter strength (higher = more smoothing, 0.06-0.12 typical) |
| `patch_size` | int | 5 | Size of patches to compare (default 5) |
| `patch_distance` | int | 6 | Maximum distance to search for patches (default 6) |
| `fast_mode` | bool | True | Use faster but approximate algorithm (default True) |

## Examples

```
denoisenlmeans()
```
```
denoisenlmeans(h=0.1,fast_mode=false)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
