# RegionAnalyzer

Analyze a specific region of the image.

Useful for checking specific areas (e.g., corners, center).

Example:
    # Analyze center 50x50 region
    ctx = FilterContext()
    RegionAnalyzer(x=100, y=100, width=50, height=50).apply(image, ctx)
    print(ctx['region']['brightness'])

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `store_in_context` | bool | True |  |
| `store_in_metadata` | bool | False |  |
| `result_key` | str | 'region' |  |
| `x` | int | 0 |  |
| `y` | int | 0 |  |
| `width` | int | 0 |  |
| `height` | int | 0 |  |

## Examples

```
region
```

## Frameworks

Native support: RAW, CV
