# BilateralFilter


![BilateralFilter example](../gallery/filters/bilateralfilter.jpg)

Bilateral filter for edge-preserving smoothing.

Smooths images while keeping edges sharp by considering both
spatial distance and color similarity.

Parameters:
    d: Diameter of pixel neighborhood (use -1 for auto based on sigma)
    sigma_color: Filter sigma in color space (larger = more colors mixed)
    sigma_space: Filter sigma in coordinate space (larger = more distant pixels influence)

Example:
    'bilateralfilter(9,75,75)' - typical settings
    'bilateralfilter(d=-1,sigma_color=50,sigma_space=50)' - auto diameter

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `d` | int | 9 | Diameter of pixel neighborhood (use -1 for auto based on sigma) |
| `sigma_color` | float | 75.0 | Filter sigma in color space (larger = more colors mixed) |
| `sigma_space` | float | 75.0 | Filter sigma in coordinate space (larger = more distant pixels influence) |

## Examples

```
bilateralfilter(9,75,75)
```
```
bilateralfilter(d=-1,sigma_color=50,sigma_space=50)
```

## Frameworks

Native support: CV, RAW
