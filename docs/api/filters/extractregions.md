# ExtractRegions


![ExtractRegions example](../gallery/filters/extractregions.jpg)

Extract image regions based on geometry bounding boxes.

Takes an image and GeometryList, crops out each region as a
separate ImageList. The ImageList contains metadata for each region
so it can be merged back later.

Inputs:
    image: Source image to crop from
    geometry: GeometryList defining regions

Parameters:
    padding: Extra pixels around each bounding box (default 0)
    min_size: Minimum region size (skip smaller regions)

Outputs:
    output: ImageList with cropped regions and metadata

## Aliases

- `extract`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `padding` | int | 0 | Extra pixels around each bounding box (default 0) |
| `min_size` | int | 1 | Minimum region size (skip smaller regions) |

## Input Ports

- **input**: Source image
- **geometry**: Regions to extract

## Frameworks

Native support: RAW, CV
