# ToDataUrl

Convert compressed image to base64 data URL.

Takes a compressed image (from Encode filter) and produces a data URL
string suitable for web display. This is the final step in pipelines
that need web-ready output.

The result is an Image with the data URL stored, accessible via
`result.to_data_url()` which returns the cached URL without re-encoding.

Parameters:
    format: Output format ('jpeg', 'png', 'webp') - uses existing if compressed
    quality: Compression quality 1-100 (only used if re-encoding needed)

Examples:
    ToDataUrl()  # Use existing compression
    ToDataUrl(format='jpeg', quality=85)

    # In pipeline string:
    'resize(0.5)|encode(jpeg)|todataurl'
    'falsecolor(hot)|encode(png)|todataurl'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `format` | str | 'jpeg' | Output format ('jpeg', 'png', 'webp') - uses existing if compressed |
| `quality` | int | 85 | Compression quality 1-100 (only used if re-encoding needed) |

## Examples

```
jpeg
```
```
resize(0.5)|encode(jpeg)|todataurl
```
```
falsecolor(hot)|encode(png)|todataurl
```

## Frameworks

Native support: PIL, RAW
