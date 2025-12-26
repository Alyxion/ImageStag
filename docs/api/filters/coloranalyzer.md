# ColorAnalyzer

Analyze dominant colors in the image.

Results include average color and basic color distribution.

Example:
    ctx = FilterContext()
    ColorAnalyzer().apply(image, ctx)
    avg = ctx['colors']['average']  # (r, g, b) tuple

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `store_in_context` | bool | True |  |
| `store_in_metadata` | bool | False |  |
| `result_key` | str | 'colors' |  |

## Examples

```
colors
```

## Frameworks

Native support: RAW, CV
