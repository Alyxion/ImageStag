# Blend

Blend two branches together using a blend mode.

Optionally accepts a mask image as third input to control
per-pixel blending. White areas in the mask show more overlay,
black areas show more base.

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | any | BlendMode.NORMAL |  |
| `opacity` | float | 1.0 |  |

## Input Ports

- **a**: Base/first image
- **b**: Overlay/second image
- **mask**: Alpha mask (optional)

## Frameworks

Native support: RAW, CV
