# HoughLineDetector


![HoughLineDetector example](../gallery/filters/houghlinedetector.jpg)

Detect lines using probabilistic Hough transform.

Uses OpenCV's HoughLinesP to detect line segments.
Works best on edge-detected images.

Parameters:
    rho: Distance resolution in pixels (default 1.0)
    theta: Angle resolution in radians (default pi/180)
    threshold: Accumulator threshold (default 100)
    min_length: Minimum line length (default 50)
    max_gap: Maximum gap between line segments (default 10)

Example:
    'houghlinedetector(threshold=80,min_length=30)'

## Aliases

- `lines`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `rho` | float | 1.0 | Distance resolution in pixels (default 1.0) |
| `theta` | float | 0.0174533 | Angle resolution in radians (default pi/180) |
| `threshold` | int | 100 | Accumulator threshold (default 100) |
| `min_length` | float | 50.0 | Minimum line length (default 50) |
| `max_gap` | float | 10.0 | Maximum gap between line segments (default 10) |

## Examples

```
houghlinedetector(threshold=80,min_length=30)
```

## Frameworks

Native support: CV, RAW
