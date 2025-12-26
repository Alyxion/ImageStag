# LensDistortion


![LensDistortion example](../gallery/filters/lensdistortion.jpg)

Apply or correct radial lens distortion.

Uses the Brown-Conrady distortion model with radial coefficients.
Positive k1 creates barrel distortion, negative creates pincushion.

Parameters:
    k1: Primary radial distortion coefficient (default 0)
    k2: Secondary radial distortion coefficient (default 0)
    k3: Tertiary radial distortion coefficient (default 0)
    p1: First tangential distortion coefficient (default 0)
    p2: Second tangential distortion coefficient (default 0)

Common values:
    - Barrel distortion correction: k1=-0.1 to -0.3
    - Pincushion distortion correction: k1=0.1 to 0.3
    - Fish-eye effect: k1=-0.5 or stronger

Example:
    'lensdistortion(k1=-0.2)' - correct moderate barrel distortion
    'lensdistortion(k1=0.3)' - apply pincushion effect

For coordinate mapping between distorted and undistorted space:
    result, transform = filter.apply_with_transform(image)
    undist_pt = transform.forward((100, 200))  # distorted -> undistorted
    dist_pt = transform.inverse((150, 180))    # undistorted -> distorted

## Aliases

- `lens`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `k1` | float | 0.0 | Primary radial distortion coefficient (default 0) |
| `k2` | float | 0.0 | Secondary radial distortion coefficient (default 0) |
| `k3` | float | 0.0 | Tertiary radial distortion coefficient (default 0) |
| `p1` | float | 0.0 | First tangential distortion coefficient (default 0) |
| `p2` | float | 0.0 | Second tangential distortion coefficient (default 0) |

## Examples

```
lensdistortion(k1=-0.2)
```
```
lensdistortion(k1=0.3)
```

## Frameworks

Native support: CV, RAW
