# Encode

Encode image to compressed bytes.

Supports all standard image formats: JPEG, PNG, WebP, BMP, GIF.
The result is an Image with compressed data that can be efficiently
transported through pipelines without re-encoding.

Parameters:
    format: Output format ('jpeg', 'png', 'webp', 'bmp', 'gif')
    quality: Compression quality 1-100 (for JPEG/WebP, default 90)

Examples:
    Encode(format='jpeg', quality=85)
    Encode(format='png')

    # In pipeline string:
    'resize(0.5)|encode(format=jpeg,quality=85)'
    'blur(1.5)|encode(format=png)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `format` | str | 'jpeg' | Output format ('jpeg', 'png', 'webp', 'bmp', 'gif') |
| `quality` | int | 90 | Compression quality 1-100 (for JPEG/WebP, default 90) |

## Examples

```
jpeg
```
```
png
```
```
resize(0.5)|encode(format=jpeg,quality=85)
```
```
blur(1.5)|encode(format=png)
```

## Frameworks

Native support: PIL
