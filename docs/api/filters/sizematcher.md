# SizeMatcher

Match dimensions of two images.

Takes two images and resizes them to matching dimensions based on
the selected mode. Handles aspect ratio mismatches with fit/fill/stretch.

Returns a dict with 'a' and 'b' keys containing the resized images.

## Aliases

- `size_match`
- `sizematch`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | any | SizeMatchMode.SMALLER |  |
| `aspect` | any | AspectMode.FILL |  |
| `crop` | any | CropPosition.CENTER |  |
| `interp` | int | InterpolationMethod.LINEAR |  |
| `fill` | str | '#000000' |  |

## Input Ports

- **a**: First image
- **b**: Second image

## Output Ports

- **a**: Resized first image
- **b**: Resized second image

## Frameworks

Native support: PIL, RAW, CV
