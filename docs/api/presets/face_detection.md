# Face Detection


![Face Detection example](../gallery/presets/face_detection.jpg)

Detect faces in group photo and draw bounding boxes

**Category:** Detection

## Inputs

- **source**: RGB8, RGBA8

## DSL

```
[f: facedetector scale_factor=1.52 min_neighbors=3 rotation_range=15 rotation_step=7]; drawgeometry input=source geometry=f color=#ff0000 thickness=2
```

## Usage

```python
from imagestag.tools.preset_registry import get_preset

preset = get_preset('face_detection')

# As graph
graph = preset.to_graph()
result = graph.execute(image)
```

## Graph Structure

```
source: PipelineSource
detect_faces: FaceDetector(scale_factor=1.52, min_neighbors=3, rotation_range=15, rotation_step=7)
draw_boxes: DrawGeometry(color=#FF0000, thickness=2)
output: PipelineOutput
```
