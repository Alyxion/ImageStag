# HistogramAnalyzer

Compute image histogram.

Results include per-channel histograms with 256 bins (0-255).

Example:
    ctx = FilterContext()
    HistogramAnalyzer().apply(image, ctx)
    red_hist = ctx['histogram']['red']  # 256 values

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `store_in_context` | bool | True |  |
| `store_in_metadata` | bool | False |  |
| `result_key` | str | 'histogram' |  |
| `bins` | int | 256 |  |

## Examples

```
histogram
```

## Frameworks

Native support: RAW, CV
