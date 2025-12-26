# SLIC


![SLIC example](../gallery/filters/slic.jpg)

Simple Linear Iterative Clustering superpixels.

Fast superpixel segmentation that groups pixels into
compact, nearly uniform regions. Useful for pre-processing
before further analysis.

Requires: scikit-image (optional dependency)

Parameters:
    n_segments: Approximate number of superpixels (default 100)
    compactness: Balance between color proximity and space proximity
    sigma: Gaussian smoothing before segmentation
    start_label: Label of first superpixel (default 0)
    mask: Optional binary mask (via context['slic_mask'])

Example:
    'slic()' or 'slic(n_segments=200,compactness=20)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `n_segments` | int | 100 | Approximate number of superpixels (default 100) |
| `compactness` | float | 10.0 | Balance between color proximity and space proximity |
| `sigma` | float | 1.0 | Gaussian smoothing before segmentation |
| `start_label` | int | 0 | Label of first superpixel (default 0) |

## Examples

```
slic()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
