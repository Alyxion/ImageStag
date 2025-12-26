# MergeRegions

Merge processed regions back into original image.

Takes the original image and an ImageList containing processed
region crops with metadata. Uses the metadata to paste regions
back at their original positions.

Inputs:
    original: Original full image
    regions: ImageList with processed regions (contains position metadata)

Parameters:
    blend_edges: Feather edges for smooth blending (default False)
    feather_size: Edge feathering radius (default 5)

## Aliases

- `merge`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `blend_edges` | bool | False | Feather edges for smooth blending (default False) |
| `feather_size` | int | 5 | Edge feathering radius (default 5) |

## Input Ports

- **input**: Original image
- **regions**: ImageList with regions

## Frameworks

Native support: RAW, CV
