# Face Blur


![Face Blur example](../gallery/presets/face_blur.jpg)

Detect faces and blur them for privacy using region pipeline

**Category:** Effects

## Inputs

- **source**: RGB8, RGBA8

## DSL

```
[f: facedetector scale_factor=1.52 min_neighbors=3 rotation_range=15 rotation_step=7]; [e: extractregions input=source geometry=f padding=10]; [b: blur 15.0]; mergeregions input=source regions=b blend_edges=false
```

## Usage

```python
from imagestag.tools.preset_registry import get_preset

preset = get_preset('face_blur')

# As graph
graph = preset.to_graph()
result = graph.execute(image)
```

## Graph Structure

```
source: PipelineSource
detect_faces: FaceDetector(scale_factor=1.52, min_neighbors=3, rotation_range=15, rotation_step=7)
extract: ExtractRegions(padding=10)
blur_regions: GaussianBlur(radius=15.0)
merge: MergeRegions(blend_edges=False)
output: PipelineOutput
```
