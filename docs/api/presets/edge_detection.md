# Edge Detection


![Edge Detection example](../gallery/presets/edge_detection.jpg)

Detect edges using Canny edge detector

**Category:** Basic

## Inputs

- **input**: RGB8, RGBA8, GRAY8

## DSL

```
canny 100 200
```

## Usage

```python
from imagestag.tools.preset_registry import get_preset

preset = get_preset('edge_detection')

# As pipeline
pipeline = preset.to_pipeline()
result = pipeline.apply(image)
```

## Graph Structure

```
input: PipelineSource
canny: Canny(threshold1=100, threshold2=200)
output: PipelineOutput
```
