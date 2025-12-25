# Filter System Design

Dataclass-based filter system supporting PIL, OpenCV, and custom backends.
Filters are JSON-serializable for persistence and transfer.

## Core Principles

1. **Dataclass-based** - All filters are dataclasses with typed parameters
2. **JSON-serializable** - Filters can be saved/loaded as JSON
3. **Backend-agnostic** - Work with PIL, OpenCV, or RAW numpy
4. **Chainable** - Filters can be composed into pipelines
5. **Format-flexible** - Work with Image objects, JPEG/PNG bytes, or numpy arrays

## Architecture Overview

```
Filter (base)
├── apply(image, context) -> Image      # Image-based processing
├── process(data, context) -> ImageData # Universal format processing
└── Format declarations (_accepted_formats, _output_format)

FilterPipeline
├── Sequential filter chain
├── Automatic format conversion between filters
└── String parsing: 'blur 2.0; brightness 1.2'

FilterGraph
├── Node-based filter graph with connections
├── Named nodes with explicit port connections
├── DSL parsing: '[f: facedetector]; drawgeometry input=source geometry=f'
├── Multi-input/multi-output filter support

FilterContext
├── Data passing between filters
├── Hierarchical (parent-child for branches)
└── Analyzer results storage

ImageData
├── Universal container (Image, bytes, numpy array)
├── Factory: from_image(), from_bytes(), from_array()
└── Output: to_image(), to_pil(), to_cv(), to_bytes(), to_array()
```

---

## Port Naming Conventions

Consistent naming across all filters for predictable DSL and graph connections.

### Source Nodes (Graph Inputs)

| Scenario | Node Names | Example |
|----------|------------|---------|
| Single input | `source` | `source -> blur -> output` |
| Dual inputs | `source_a`, `source_b` | `source_a, source_b -> size_match` |
| Named inputs | Descriptive names | `image`, `mask`, `reference` |

### Input Ports (Filter Inputs)

| Scenario | Port Names | Examples |
|----------|------------|----------|
| Single image input | `input` | DrawGeometry, ExtractRegions, MergeRegions, MaskApply |
| Dual image inputs | `a`, `b` | SizeMatcher, Blend, Composite |
| Image + geometry | `input`, `geometry` | DrawGeometry, ExtractRegions |
| Image + regions | `input`, `regions` | MergeRegions |
| Image + mask | `input`, `mask` | MaskApply |
| Optional inputs | `mask` (optional) | Blend with optional mask |

### Output Ports

| Scenario | Port Names | Examples |
|----------|------------|----------|
| Single output | `output` | Most filters |
| Dual outputs | `a`, `b` | SizeMatcher (resized versions) |
| Geometry output | `output` (type: geometry) | HoughCircleDetector, FaceDetector |

### Legacy Compatibility

All filters include fallback logic for legacy port names:

```python
# In apply_multi():
image = images.get('input') or images.get('image')  # 'image' for legacy
base = images.get('a') or images.get('base')        # 'base' for legacy
overlay = images.get('b') or images.get('overlay')  # 'overlay' for legacy
```

---

## Compact Pipeline DSL

Shell-like syntax for defining filter pipelines with minimal typing.

### Basic Syntax

```
filter arg1 arg2; filter2 arg1 key=value
```

- **`;`** separates statements (filters)
- **Space** separates arguments
- **`=`** for keyword arguments
- **`#`** prefix for hex colors: `#ff0000`

### Examples

```bash
# Linear pipeline
blur 2.0; brightness 1.2

# Multiple positional args
resize 0.5 0.5

# Keyword args
lens k1=-0.15 k2=0.02

# Named nodes with branches
[f: facedetector scale_factor=1.52]; drawgeometry input=source geometry=f
```

### Named Nodes

Define reusable nodes with `[name: filter args]`:

```bash
[m: size_match source_a source_b smaller]
[g: imgen linear #000 #fff format=gray]
blend a=m.a b=m.b mask=g
```

### Node References

- **`source`** - implicit first input
- **`source_a`**, **`source_b`** - dual inputs
- **`nodename`** - reference a named node's default output
- **`nodename.port`** - reference a specific output port

### Port Assignments

Assign node outputs to filter input ports:

```bash
# port=node syntax
drawgeometry input=source geometry=f

# port=node.port syntax
blend a=m.a b=m.b mask=g
```

---

## Filter Graph Architecture

### GraphNode

Represents a single node in the graph:

```python
@dataclass
class GraphNode:
    name: str
    filter: Filter | None = None
    source: PipelineSource | None = None
    output_spec: PipelineOutput | None = None
    is_output: bool = False
    editor: dict = field(default_factory=dict)  # x, y position
```

### GraphConnection

Defines a connection between nodes:

```python
@dataclass
class GraphConnection:
    from_node: str
    to_node: str
    from_port: str = 'output'
    to_port: str = 'input'
```

### Connection Formats (JSON)

```json
// Simple: default ports
{"from": "source", "to": "blur"}

// Named to_port
{"from": "source", "to": ["blend", "a"]}

// Named both ports
{"from": ["size_match", "a"], "to": ["blend", "a"]}
```

---

## Filter Types

### Single-Input Filters (Filter)

Standard filters with one image input and one image output:

```python
@dataclass
class GaussianBlur(Filter):
    radius: float = 2.0

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        ...
```

### Multi-Input Filters (CombinerFilter)

Filters that combine multiple inputs:

```python
@dataclass
class Blend(CombinerFilter):
    _input_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'Base/first image'},
        {'name': 'b', 'description': 'Overlay/second image'},
        {'name': 'mask', 'description': 'Alpha mask (optional)', 'optional': True},
    ]

    mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        ...
```

### Multi-Output Filters

Filters that produce multiple outputs:

```python
@dataclass
class SizeMatcher(CombinerFilter):
    _input_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'First image'},
        {'name': 'b', 'description': 'Second image'},
    ]
    _output_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'Resized first image'},
        {'name': 'b', 'description': 'Resized second image'},
    ]

    @classmethod
    def is_multi_output(cls) -> bool:
        return True

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> dict[str, Image]:  # Returns dict, not single Image
        ...
```

### Geometry Filters

Filters that output geometry (not images):

```python
@dataclass
class GeometryFilter(Filter):
    _output_ports: ClassVar[list[dict]] = [
        {'name': 'output', 'type': 'geometry'},
    ]

    @abstractmethod
    def detect(self, image: Image) -> GeometryList:
        ...

    def apply(self, image: Image, context: FilterContext | None = None) -> GeometryList:
        return self.detect(image)
```

---

## Preset System

### Preset Definition

Each preset defines both graph and DSL representations:

```python
@dataclass
class Preset:
    key: str                    # Unique identifier
    name: str                   # Human-readable name
    description: str            # Brief description
    category: PresetCategory    # Organization category
    graph: dict[str, Any]       # Node/connection structure
    dsl: str                    # Compact DSL string
    inputs: list[PresetInput]   # Input sources with samples
```

### DSL ↔ Graph Equivalence

DSL and graph must produce identical output. Verified by unit tests.

```python
# Graph execution
graph = preset.to_graph()
result_graph = graph.execute(image)

# DSL execution
dsl_graph = preset.to_dsl_graph()
result_dsl = dsl_graph.execute(image)

# Results must match
assert_images_equal(result_graph, result_dsl)
```

### Example: Face Detection Preset

**Graph representation:**
```python
graph={
    "nodes": {
        "source": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/group",
        },
        "detect_faces": {
            "class": "FaceDetector",
            "params": {"scale_factor": 1.52, "min_neighbors": 3},
        },
        "draw_boxes": {
            "class": "DrawGeometry",
            "params": {"color": "#FF0000", "thickness": 2},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
        },
    },
    "connections": [
        {"from": "source", "to": "detect_faces"},
        {"from": "source", "to": ["draw_boxes", "input"]},
        {"from": "detect_faces", "to": ["draw_boxes", "geometry"]},
        {"from": "draw_boxes", "to": "output"},
    ],
}
```

**DSL representation:**
```
[f: facedetector scale_factor=1.52 min_neighbors=3]; drawgeometry input=source geometry=f color=#ff0000 thickness=2
```

---

## Processing Methods

### apply() - Image-based (traditional)
```python
result_image = filter.apply(input_image, context)
result_image = pipeline.apply(input_image)
```

### process() - Format-flexible (universal)
```python
# Input can be Image, JPEG bytes, or numpy array
data = ImageData.from_bytes(jpeg_bytes)
data = ImageData.from_array(cv_frame, pixel_format='BGR')
data = ImageData.from_image(image)

# Process through pipeline
result = pipeline.process(data)

# Output in any format
jpeg_out = result.to_bytes()     # Compressed bytes
cv_array = result.to_cv()        # BGR numpy array
pil_img = result.to_pil()        # PIL Image
image = result.to_image()        # ImageStag Image
```

### Graph Execution
```python
# Single input
result = graph.execute(image)

# Multiple inputs
result = graph.execute(source_a=img1, source_b=img2)

# Designer mode (uses placeholder images)
result = graph.execute_designer()
```

---

## Format System

### FormatSpec
Describes image format: pixel format, bit depth, compression.

```python
FormatSpec.RGB         # RGB pixel data
FormatSpec.BGR         # OpenCV-style BGR
FormatSpec.GRAY        # Grayscale
FormatSpec.JPEG        # JPEG compressed
FormatSpec.PNG         # PNG compressed
FormatSpec.ANY         # Accepts any format
```

### Filter Format Declarations
Filters can declare what formats they accept and produce:
- `_accepted_formats` - List of acceptable input formats
- `_output_format` - Format this filter produces
- `_implicit_conversion` - Auto-convert incompatible inputs (default: True)
- `_native_imagedata` - Filter overrides process() for direct format handling

---

## Filter Categories

### Basic Filters
| Filter | Parameters | Description |
|--------|------------|-------------|
| Brightness | factor (0-2+) | Adjust brightness |
| Contrast | factor (0-2+) | Adjust contrast |
| Saturation | factor (0-2+) | Adjust saturation |
| Grayscale | - | Convert to grayscale |
| Invert | - | Invert colors |
| Threshold | value, method | Binary threshold |

### Blur & Sharpen
| Filter | Parameters | Description |
|--------|------------|-------------|
| GaussianBlur | radius, sigma | Gaussian blur |
| BoxBlur | radius | Box blur |
| Sharpen | amount | Sharpen image |
| UnsharpMask | radius, percent | Unsharp mask |

### Geometric
| Filter | Parameters | Description |
|--------|------------|-------------|
| Resize | scale or size | Resize image |
| Crop | x, y, width, height | Crop region |
| Rotate | angle, expand | Rotate image |
| Flip | horizontal, vertical | Mirror image |
| LensDistortion | k1, k2, k3, p1, p2 | Radial lens distortion |
| Perspective | src_points, dst_points | Perspective transform |

### Size Matching
| Filter | Parameters | Description |
|--------|------------|-------------|
| SizeMatcher | mode, aspect, crop, interp, fill | Match two images to same size |

**SizeMatcher Modes:**
- `smaller` - Use smaller dimensions
- `bigger` - Use larger dimensions
- `source` - Match to first image (a)
- `other` - Match to second image (b)

**Aspect Modes:**
- `fill` - Crop to fill (no borders)
- `fit` - Letterbox (add borders)
- `stretch` - Distort to fit

### Combiners
| Filter | Inputs | Description |
|--------|--------|-------------|
| Blend | a, b, mask (optional) | Blend with mode (normal, multiply, screen, etc.) |
| Composite | a, b, mask | Composite foreground over background |
| MaskApply | input, mask | Apply mask as alpha channel |

### Geometry Detection
| Filter | Output Type | Description |
|--------|-------------|-------------|
| HoughCircleDetector | GeometryList (circles) | Detect circles via Hough transform |
| HoughLineDetector | GeometryList (lines) | Detect lines via Hough transform |
| FaceDetector | GeometryList (rectangles) | Haar cascade face detection |

### Geometry Processing
| Filter | Inputs | Description |
|--------|--------|-------------|
| DrawGeometry | input, geometry | Draw geometries on image |
| ExtractRegions | input, geometry | Crop regions to ImageList |
| MergeRegions | input, regions | Paste processed regions back |

### Image Generation
| Filter | Parameters | Description |
|--------|------------|-------------|
| ImageGenerator | gradient_type, colors, format, size | Generate gradient images |

---

## Coordinate Transforms

Both `LensDistortion` and `Perspective` filters can return a coordinate transform
object for bidirectional point mapping via `apply_with_transform()`:

```python
# Apply filter and get transform
result, transform = LensDistortion(k1=-0.2).apply_with_transform(image)

# Map points from original (distorted) to corrected coordinates
corrected_pt = transform.forward((100, 200))

# Map points from corrected back to original coordinates
original_pt = transform.inverse((150, 180))

# Batch transform multiple points efficiently
corrected_pts = transform.forward_points([(10, 10), (50, 50), (90, 30)])
original_pts = transform.inverse_points(corrected_pts)
```

---

## JSON Serialization

### Pipeline
```json
{
  "type": "FilterPipeline",
  "filters": [
    {"type": "Resize", "scale": 0.5},
    {"type": "GaussianBlur", "radius": 1.5},
    {"type": "Encode", "format": "jpeg", "quality": 85}
  ]
}
```

### Graph
```json
{
  "nodes": {
    "source": {
      "class": "PipelineSource",
      "type": "IMAGE",
      "formats": ["RGB8", "RGBA8"]
    },
    "blur": {
      "class": "GaussianBlur",
      "params": {"radius": 2.0}
    },
    "output": {
      "class": "PipelineOutput",
      "type": "IMAGE",
      "name": "output"
    }
  },
  "connections": [
    {"from": "source", "to": "blur"},
    {"from": "blur", "to": "output"}
  ]
}
```

---

## Filter Aliases

Common shorthand names for filters:

| Alias | Filter Class |
|-------|--------------|
| `blur`, `gaussian` | GaussianBlur |
| `gray`, `grey` | Grayscale |
| `lens` | LensDistortion |
| `imgen` | ImageGenerator |
| `facedetector` | FaceDetector |
| `houghcircledetector` | HoughCircleDetector |
| `drawgeometry` | DrawGeometry |
| `extractregions` | ExtractRegions |
| `mergeregions` | MergeRegions |
| `size_match` | SizeMatcher |

---

## Implementation Status

### Completed
- [x] Filter base class with JSON serialization
- [x] FilterPipeline with string parsing
- [x] FilterContext and FilterGraph
- [x] Format system (FormatSpec, ImageData, process())
- [x] Basic filters (Brightness, Contrast, Saturation, etc.)
- [x] Blur & Sharpen filters
- [x] Geometric transforms (Resize, Crop, Rotate, Flip)
- [x] Lens correction (LensDistortion, Perspective)
- [x] Edge detection (Canny, Sobel, Laplacian, EdgeEnhance)
- [x] Morphological operations
- [x] Detection filters (FaceDetector, EyeDetector, ContourDetector)
- [x] Format converters (Encode, Decode, ConvertFormat)
- [x] Analyzer filters
- [x] Compositing (BlendMode, Blend, Composite, MaskApply)
- [x] Multi-input/multi-output filters (CombinerFilter)
- [x] SizeMatcher with all modes
- [x] Geometry detection (Hough circles/lines, face detection)
- [x] Geometry processing (DrawGeometry, ExtractRegions, MergeRegions)
- [x] ImageGenerator for gradients
- [x] Compact DSL with named nodes and port references
- [x] Preset system with graph/DSL equivalence
- [x] Consistent port naming conventions

### Planned
- [ ] Advanced threshold (Otsu, adaptive)
- [ ] Color space conversions (LAB, HSL)
- [ ] Noise reduction (bilateral, non-local means)
- [ ] Video frame support
- [ ] Batch processing utilities
