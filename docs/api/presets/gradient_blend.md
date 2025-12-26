# Gradient Blend


![Gradient Blend example](../gallery/presets/gradient_blend.jpg)

Blend two images with a linear gradient mask

**Category:** Blend

## Inputs

- **source_a**: RGB8, RGBA8
- **source_b**: RGB8, RGBA8

## DSL

```
[m: size_match source_a source_b smaller aspect=fill]; [g: imgen linear color_start=#000000 color_end=#ffffff format=gray]; blend a=m.a b=m.b mask=g
```

## Usage

```python
from imagestag.tools.preset_registry import get_preset

preset = get_preset('gradient_blend')

# As graph
graph = preset.to_graph()
result = graph.execute(source_a=img1, source_b=img2)
```

## Graph Structure

```
source_a: PipelineSource
source_b: PipelineSource
size_match: SizeMatcher(mode=smaller, aspect=fill, crop=center, interp=linear, fill=#000000)
gradient: ImageGenerator(gradient_type=linear, angle=0, color_start=#000000, color_end=#FFFFFF, format=gray, width=512, height=512, cx=0.5, cy=0.5)
blend: Blend(mode=NORMAL, opacity=1.0)
output: PipelineOutput
```
