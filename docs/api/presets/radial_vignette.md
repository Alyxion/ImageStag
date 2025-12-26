# Radial Vignette


![Radial Vignette example](../gallery/presets/radial_vignette.jpg)

Apply a radial vignette effect using multiply blend

**Category:** Effects

## Inputs

- **source**: RGB8, RGBA8

## DSL

```
[v: imgen radial color_start=#ffffff color_end=#000000 format=rgb]; blend a=source b=v mode=multiply opacity=0.7
```

## Usage

```python
from imagestag.tools.preset_registry import get_preset

preset = get_preset('radial_vignette')

# As graph
graph = preset.to_graph()
result = graph.execute(image)
```

## Graph Structure

```
source: PipelineSource
vignette: ImageGenerator(gradient_type=radial, angle=0, color_start=#FFFFFF, color_end=#000000, format=rgb, width=512, height=512, cx=0.5, cy=0.5)
blend: Blend(mode=MULTIPLY, opacity=0.7)
output: PipelineOutput
```
