# AutoContrast


![AutoContrast example](../gallery/filters/autocontrast.jpg)

Automatically adjust contrast based on image histogram.

Normalizes the image contrast by remapping the darkest pixels to black
and lightest to white.

Parameters:
    cutoff: Percentage of lightest/darkest pixels to ignore (default 0)
    preserve_tone: If True, preserve overall tonal balance (default False)

Example:
    'autocontrast()' or 'autocontrast(cutoff=2)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cutoff` | float | 0.0 | Percentage of lightest/darkest pixels to ignore (default 0) |
| `preserve_tone` | bool | False | If True, preserve overall tonal balance (default False) |

## Examples

```
autocontrast()
```

## Frameworks

Native support: PIL
