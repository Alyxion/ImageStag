# FalseColor


![FalseColor example](../gallery/filters/falsecolor.jpg)

Apply false color using matplotlib colormaps.

Converts image to grayscale and maps values through a colormap.
RGB input is automatically converted to grayscale first.
Preserves input framework (PIL in → PIL out, CV in → CV out).

:param colormap: Matplotlib colormap name (e.g., 'viridis', 'hot', 'jet', 'inferno')
:param input_min: Minimum input value for normalization (default 0.0)
:param input_max: Maximum input value for normalization (default 255.0)
:param reverse: Reverse the colormap direction (default False)

Example:
    'falsecolor hot'
    'falsecolor viridis reverse=true'
    'falsecolor jet input_min=50 input_max=200'

Common colormaps:
    Sequential: viridis, plasma, inferno, magma, cividis
    Diverging: coolwarm, RdBu, seismic
    Thermal: hot, afmhot, gist_heat
    Other: jet, rainbow, turbo, gray

## Aliases

- `lava` → `FalseColor(colormap=hot)`
- `thermal` → `FalseColor(colormap=inferno)`
- `plasma` → `FalseColor(colormap=plasma)`
- `magma` → `FalseColor(colormap=magma)`
- `viridis` → `FalseColor(colormap=viridis)`
- `coolwarm` → `FalseColor(colormap=coolwarm)`
- `jet` → `FalseColor(colormap=jet)`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `colormap` | color | 'viridis' | Matplotlib colormap name (e.g., 'viridis', 'hot', 'jet', 'inferno') |
| `input_min` | float | 0.0 | Minimum input value for normalization (default 0.0) |
| `input_max` | float | 255.0 | Maximum input value for normalization (default 255.0) |
| `reverse` | bool | False | Reverse the colormap direction (default False) |

## Examples

```
falsecolor hot
```
```
falsecolor viridis reverse=true
```
```
falsecolor jet input_min=50 input_max=200
```

## Frameworks

Native support: CV, PIL, RAW
