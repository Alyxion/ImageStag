# AdjustSigmoid


![AdjustSigmoid example](../gallery/filters/adjustsigmoid.jpg)

Sigmoid (S-curve) contrast adjustment.

Applies sigmoid function for contrast enhancement.
Similar to curves adjustment in photo editors.

Requires: scikit-image (optional dependency)

Parameters:
    cutoff: Center point of the sigmoid (0.5 = midtones)
    gain: Steepness of the curve (higher = more contrast)
    inv: If True, apply inverse sigmoid (default False)

Example:
    'adjustsigmoid(cutoff=0.5,gain=10)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cutoff` | float | 0.5 | Center point of the sigmoid (0.5 = midtones) |
| `gain` | float | 10.0 | Steepness of the curve (higher = more contrast) |
| `inv` | bool | False | If True, apply inverse sigmoid (default False) |

## Examples

```
adjustsigmoid(cutoff=0.5,gain=10)
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
