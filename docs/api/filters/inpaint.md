# Inpaint


![Inpaint example](../gallery/filters/inpaint.jpg)

Biharmonic inpainting to fill missing regions.

Fills holes or damaged regions using biharmonic interpolation.
Requires a mask image specifying which pixels to fill.

Requires: scikit-image (optional dependency)

Parameters:
    mask_threshold: Threshold to binarize mask (0-255)

Note: Pass the mask via context['inpaint_mask'] as a numpy array
or Image where white pixels indicate regions to fill.

Example:
    'inpaint()' or 'inpaint(mask_threshold=128)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mask_threshold` | int | 128 | Threshold to binarize mask (0-255) |

## Examples

```
inpaint()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
