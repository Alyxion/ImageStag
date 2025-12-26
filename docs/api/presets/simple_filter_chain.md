# Simple Filter Chain


![Simple Filter Chain example](../gallery/presets/simple_filter_chain.jpg)

Apply blur and brightness adjustment to an image

**Category:** Basic

## Inputs

- **input**: RGB8, RGBA8, GRAY8

## DSL

```
blur 2.0; brightness 1.2
```

## Usage

```python
from imagestag.tools.preset_registry import get_preset

preset = get_preset('simple_filter_chain')

# As pipeline
pipeline = preset.to_pipeline()
result = pipeline.apply(image)
```

## Graph Structure

```
input: PipelineSource
blur: GaussianBlur(radius=2.0)
brighten: Brightness(factor=1.2)
output: PipelineOutput
```
