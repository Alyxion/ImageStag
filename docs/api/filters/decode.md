# Decode

Decode compressed bytes to uncompressed pixel data.

Accepts any compressed format (JPEG, PNG, WebP, etc.) and outputs
uncompressed image data in the specified pixel format. Forces
decompression of compressed Image objects.

Parameters:
    format: Output pixel format ('RGB', 'BGR', 'RGBA', 'GRAY')

Examples:
    Decode(format='RGB')
    Decode(format='BGR')  # For OpenCV

    # In pipeline string:
    'encode(jpeg)|decode(RGB)'  # Encode then decode
    'decode(format=BGR)|some_cv_filter'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `format` | str | 'RGB' | Output pixel format ('RGB', 'BGR', 'RGBA', 'GRAY') |

## Examples

```
RGB
```
```
BGR
```
```
encode(jpeg)|decode(RGB)
```
```
decode(format=BGR)|some_cv_filter
```

## Frameworks

Native support: PIL, RAW
