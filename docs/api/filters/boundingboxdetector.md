# BoundingBoxDetector

Base class for object detection that returns bounding boxes.

Subclass this to implement specific detectors (faces, objects, etc.).
Results are stored as a list of detected regions.

Each detection is a dict with:
    - box: (x, y, width, height)
    - confidence: float 0-1
    - label: str (optional)

Example:
    @register_filter
    @dataclass
    class FaceDetector(BoundingBoxDetector):
        result_key: str = 'faces'

        def detect(self, image: Image) -> list[dict]:
            # Use OpenCV, dlib, or ML model here
            return [{'box': (10, 20, 50, 50), 'confidence': 0.95}]

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `store_in_context` | bool | True |  |
| `store_in_metadata` | bool | False |  |
| `result_key` | str | 'detections' | str = 'faces' |
| `min_confidence` | float | 0.5 |  |

## Examples

```
faces
```
```
box
```

## Frameworks

Native support: RAW, CV
