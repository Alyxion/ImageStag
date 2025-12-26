# Skeletonize


![Skeletonize example](../gallery/filters/skeletonize.jpg)

Reduce binary shapes to 1-pixel-wide skeleton.

Computes the skeleton of a binary image using morphological thinning.
Useful for shape analysis, path finding, and topology extraction.

Requires: scikit-image (optional dependency)

Parameters:
    method: Skeletonization method ('zhang' or 'lee')

Example:
    'skeletonize()' or 'skeletonize(method=lee)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `method` | str | 'zhang' | Skeletonization method ('zhang' or 'lee') |

## Examples

```
skeletonize()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
