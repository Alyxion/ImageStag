# ImageStats

Compute basic image statistics.

Results include per-channel mean, std, min, max, and overall brightness.

Example:
    pipeline = FilterPipeline([
        ImageStats(result_key='stats'),
        Brightness(factor=1.5),
    ])
    ctx = FilterContext()
    result = pipeline.apply(image, ctx)
    print(ctx['stats']['brightness'])  # Average brightness

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `store_in_context` | bool | True |  |
| `store_in_metadata` | bool | False |  |
| `result_key` | str | 'stats' |  |

## Examples

```
stats
```
```
stats
```

## Frameworks

Native support: RAW, CV
