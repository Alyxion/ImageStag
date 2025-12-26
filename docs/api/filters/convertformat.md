# ConvertFormat

Convert image to a specific pixel format.

Useful for ensuring a specific format for downstream processing.

Parameters:
    format: Target pixel format ('RGB', 'BGR', 'RGBA', 'BGRA', 'GRAY', 'HSV')

Examples:
    ConvertFormat(format='BGR')  # For OpenCV
    ConvertFormat(format='GRAY')

    # In pipeline string:
    'convertformat(format=BGR)|blur(1.5)'
    'convertformat(BGR)'  # Short form

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `format` | str | 'RGB' | Target pixel format ('RGB', 'BGR', 'RGBA', 'BGRA', 'GRAY', 'HSV') |

## Examples

```
BGR
```
```
GRAY
```
```
convertformat(format=BGR)|blur(1.5)
```
```
convertformat(BGR)
```

## Frameworks

Native support: RAW, CV
