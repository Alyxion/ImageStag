# EqualizeHist


![EqualizeHist example](../gallery/filters/equalizehist.jpg)

Histogram equalization to improve contrast.

Enhances contrast by spreading out the most frequent intensity values.
Works on grayscale images; for color images, converts to YCrCb and
equalizes only the luminance channel.

Parameters:
    per_channel: If True, equalize each RGB channel independently (default False)

Example:
    'equalizehist()' or 'equalizehist(per_channel=true)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `per_channel` | bool | False | If True, equalize each RGB channel independently (default False) |

## Examples

```
equalizehist()
```

## Frameworks

Native support: CV, RAW
