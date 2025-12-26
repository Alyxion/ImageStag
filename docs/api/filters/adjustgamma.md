# AdjustGamma


![AdjustGamma example](../gallery/filters/adjustgamma.jpg)

Gamma correction for exposure adjustment.

Applies power-law (gamma) transformation:
- gamma < 1: brighten shadows, compress highlights
- gamma > 1: darken image, expand highlights
- gamma = 1: no change

Requires: scikit-image (optional dependency)

Parameters:
    gamma: Gamma value (default 1.0)
    gain: Multiplicative factor (default 1.0)

Example:
    'adjustgamma(0.5)' - brighten shadows
    'adjustgamma(2.0)' - darken image

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `gamma` | float | 1.0 | Gamma value (default 1.0) |
| `gain` | float | 1.0 | Multiplicative factor (default 1.0) |

## Examples

```
adjustgamma(0.5)
```
```
adjustgamma(2.0)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
