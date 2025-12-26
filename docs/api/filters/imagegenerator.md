# ImageGenerator


![ImageGenerator example](../gallery/filters/imagegenerator.jpg)

Generate gradient images for masks and effects.

Creates linear or radial gradients that can be used as blend masks.
Can take dimensions from an input image or use specified width/height.

Parameters:
    gradient_type: "solid", "linear", or "radial"
    angle: Degrees for linear gradient (0=left-to-right, 90=top-to-bottom)
    color_start: Start color as hex string (e.g., "#000000")
    color_end: End color as hex string (e.g., "#FFFFFF")
    format: "gray", "rgb", or "rgba"
    width, height: Dimensions when no input image provided
    cx, cy: Center point for radial gradient (0-1)

## Aliases

- `imgen`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `gradient_type` | str | 'linear' | "solid", "linear", or "radial" |
| `angle` | float | 0.0 | Degrees for linear gradient (0=left-to-right, 90=top-to-bottom) |
| `color_start` | any | '#000000' | Start color as hex string (e.g., "#000000") |
| `color_end` | any | '#FFFFFF' | End color as hex string (e.g., "#FFFFFF") |
| `format` | str | 'gray' | "gray", "rgb", or "rgba" width, height: Dimensions when no input image provided cx, cy: Center point for radial gradient (0-1) |
| `width` | int | 512 |  |
| `height` | int | 512 |  |
| `cx` | float | 0.5 |  |
| `cy` | float | 0.5 |  |

## Frameworks

Native support: RAW
