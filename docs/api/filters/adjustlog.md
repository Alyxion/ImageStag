# AdjustLog


![AdjustLog example](../gallery/filters/adjustlog.jpg)

Logarithmic correction for exposure adjustment.

Applies logarithmic transformation to expand dark regions.
Useful for images with high dynamic range.

Requires: scikit-image (optional dependency)

Parameters:
    gain: Multiplicative factor (default 1.0)
    inv: If True, apply inverse log transform (default False)

Example:
    'adjustlog()' or 'adjustlog(gain=1.5)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `gain` | float | 1.0 | Multiplicative factor (default 1.0) |
| `inv` | bool | False | If True, apply inverse log transform (default False) |

## Examples

```
adjustlog()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
