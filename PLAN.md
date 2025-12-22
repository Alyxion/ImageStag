# ImageStag Development Plan

## Project Structure

```
imagestag/
├── filters/           # Filter system
│   ├── __init__.py
│   └── DESIGN.md      # Filter architecture
├── stage/             # Stage component
│   ├── __init__.py
│   └── DESIGN.md      # Stage architecture
└── ...
```

---

## Stage Component

A multi-layer compositing component for visualizing static and dynamic image content.

### Core Principles

1. **Layer-based composition** - Stack multiple image layers with z-order
2. **Flexible sources** - URL, data URL, Image object, dynamic providers
3. **Auto-sizing** - Stage size defaults to first loaded image dimensions
4. **Full-area default** - Layers fill entire stage by default
5. **Dynamic sources** - Single source can populate multiple layers simultaneously
6. **Python-native API** - No CSS strings, use classes and enums

### Layer Sources

**Static:**
- URL (`https://...`)
- Data URL (`data:image/png;base64,...`)
- File path
- Image object

**Dynamic:**
- ContentProvider interface
- Single source → multiple layers
- Delivery modes: sync, async, or background thread

### Layer Stack Example

```
┌─────────────────────────────────────┐
│  Layer 3: SVG overlay               │  ← top
├─────────────────────────────────────┤
│  Layer 2: PNG (transparency)        │
├─────────────────────────────────────┤
│  Layer 1: Dynamic content           │
├─────────────────────────────────────┤
│  Layer 0: JPG background            │  ← bottom
└─────────────────────────────────────┘
```

### Positioning (Python Classes/Enums Only)

```python
from imagestag import Anchor, Pos, Size, ResizeMode

# Anchors - enum
layer.anchor = Anchor.TOP_LEFT
layer.anchor = Anchor.CENTER
layer.anchor = Anchor.BOTTOM_RIGHT

# Position - class with factory methods
layer.pos = Pos(100, 50)              # absolute pixels
layer.pos = Pos.percent(10, 20)       # relative 10%, 20%

# Size - class with factory methods
layer.size = Size(400, 300)           # absolute pixels
layer.size = Size.percent(50, 100)    # 50% width, 100% height
layer.size = Size.auto()              # from content

# Resize mode - enum
layer.resize_mode = ResizeMode.FILL   # stretch (default)
layer.resize_mode = ResizeMode.FIT    # proportional, letterbox
layer.resize_mode = ResizeMode.COVER  # proportional, crop
layer.resize_mode = ResizeMode.NONE   # original size
```

### Zoom & Pan

Built-in viewport control with minimal setup:

**Simple usage (3 lines):**
```python
stage = Stage(url='photo.jpg', zoomable=True)
stage.zoom_range = (0.1, 10.0)  # 10% to 1000%
# That's it - mouse wheel zooms, drag pans
```

**Viewport control:**
```python
stage = Stage(width=800, height=600)
stage.add_layer(url='large_map.jpg')

# Enable zoom/pan
stage.zoomable = True
stage.pannable = True
stage.zoom_range = (0.5, 4.0)  # 50% to 400%

# Programmatic control
stage.zoom = 2.0              # Set zoom level
stage.pan = Pos(100, 50)      # Pan offset in pixels
stage.zoom_to_fit()           # Fit content in view
stage.zoom_to_point(Pos(x, y), zoom=3.0)  # Zoom to specific point
```

**Viewport class:**
```python
@dataclass
class Viewport:
    zoom: float = 1.0
    pan: Pos = field(default_factory=lambda: Pos(0, 0))
    zoom_min: float = 0.1
    zoom_max: float = 10.0
    buffer_margin: float = 0.1  # 10% extra rendering on each side

    def zoom_to_fit(self, content_size: Size, view_size: Size): ...
    def zoom_to_point(self, point: Pos, zoom: float): ...
    def screen_to_content(self, screen_pos: Pos) -> Pos: ...
    def content_to_screen(self, content_pos: Pos) -> Pos: ...
    def get_render_region(self, content_size: Size, view_size: Size) -> RenderRegion: ...
```

**RenderRegion for dynamic sources:**
```python
@dataclass
class RenderRegion:
    """Tells dynamic sources what area needs rendering."""
    x: int                    # Top-left X in content coordinates
    y: int                    # Top-left Y in content coordinates
    width: int                # Width to render (content pixels)
    height: int               # Height to render (content pixels)
    zoom: float               # Current zoom level
    content_size: Size        # Total content size
    view_size: Size           # View/screen size

    @property
    def bounds(self) -> tuple[int, int, int, int]: ...  # (x, y, x2, y2)
    @property
    def output_size(self) -> Size: ...  # Size after zoom applied
```

Dynamic sources receive RenderRegion to optimize rendering:
```python
class TimeBasedProvider:
    def render(self, time: float, region: RenderRegion | None = None) -> Image:
        """If region provided, only render that area."""

class FrameBasedProvider:
    def set_render_region(self, region: RenderRegion | None):
        """Called when viewport changes - adjust decoding accordingly."""
```

### Client Areas

Named regions within the stage:

```python
stage.define_area('sidebar', pos=Pos.percent(0, 0), size=Size.percent(20, 100))
stage.define_area('content', pos=Pos.percent(20, 0), size=Size.percent(80, 100))

layer = stage.add_layer(url='menu.png', area='sidebar')
```

---

## Time & Frame Management

### World Time

Stage provides global time in seconds for time-based animations:

```python
stage.time = 0.0  # world time in seconds
stage.time += delta_time
```

### Content Provider Types

**1. Time-Based Provider (sync/async)**
For procedural content, live drawing, SVG generation:

```python
class TimeBasedProvider:
    def render(self, time: float) -> Image:
        """Called with world time in seconds."""
        pass

    def render_layers(self, time: float) -> dict[int, Image]:
        """Provide multiple layers at once."""
        pass
```

**2. Frame-Based Provider (background thread)**
For video, streams - decoder runs in background thread:

```python
class FrameBasedProvider:
    def get_frame(self) -> tuple[int, Image]:
        """Returns (frame_index, image).
        Index used for change detection - skip redraw if unchanged.
        """
        pass

    @property
    def fps(self) -> float:
        """Target frame rate."""
        pass
```

### Synchronization Problem

Frontend timer and background decoder both at 30hz but slightly out of phase:

```
Frontend:  |--check--|--check--|--check--|
Decoder:     |--frame--|--frame--|--frame--|
                  ^ Frontend 1ms early → skips frame → visible lag
```

### Synchronization Solutions

1. **`threading.Event`** - Decoder signals frame ready, frontend can wait briefly
2. **Frame buffer (2-3 frames)** - Decoder stays ahead, absorbs timing jitter
3. **Brief wait on miss** - If no new frame, wait up to 5ms before giving up
4. **Sync statistics** - Track `sync_quality`, `effective_fps` to detect issues

```python
class FrameBasedProvider:
    def __init__(self):
        self._frame_ready = threading.Event()
        self._lock = threading.Lock()

    def get_frame(self, timeout: float | None = None) -> tuple[int, Image | None]:
        if timeout is not None:
            self._frame_ready.wait(timeout=timeout)
            self._frame_ready.clear()
        with self._lock:
            return (self._frame_index, self._current_frame)

    def wait_for_frame(self, timeout: float = 0.05) -> bool:
        return self._frame_ready.wait(timeout=timeout)
```

---

## Layer Dependencies & Filter Chains

Layers can depend on other layers for input (filters, detection overlays).
Each layer runs at its own rate - they don't need to be synchronized.

### Example: Surveillance Camera with Face Detection

```
┌─────────────────────────────────────────────────────┐
│  Layer 2: Face boxes overlay      (5 fps)           │  ← slow ML detection
├─────────────────────────────────────────────────────┤
│  Layer 1: GPU blur filter         (unbound)         │  ← as fast as GPU
├─────────────────────────────────────────────────────┤
│  Layer 0: Camera feed             (30 fps)          │  ← source
└─────────────────────────────────────────────────────┘
```

### Sync Modes

```python
class SyncMode(Enum):
    SYNCED = auto()      # 1:1 with input layer, process every frame
    INDEPENDENT = auto() # Own FPS, uses latest available input
    UNBOUND = auto()     # No FPS limit, as fast as possible (GPU-bound)
```

| Mode | Behavior | Use Case |
|------|----------|----------|
| `SYNCED` | Waits for input, processes every frame | Real-time filters matching source |
| `INDEPENDENT` | Own FPS, grabs latest input when ready | Slow detection (5fps) on fast video (30fps) |
| `UNBOUND` | As fast as possible, no sleep | GPU processing, benchmarks |

### Layer Linking

```python
stage = Stage()

# Layer 0: Camera feed at 30fps
camera = stage.add_layer(source=CameraProvider(fps=30), z=0)

# Layer 1: GPU blur - linked to camera, runs as fast as GPU allows
blur = stage.add_layer(
    source=GpuBlurFilter(),
    z=1,
    input_layer=camera,
    sync_mode=SyncMode.UNBOUND,
)

# Layer 2: Face detection - linked to camera, runs at 5fps independently
faces = stage.add_layer(
    source=FaceDetector(),
    z=2,
    input_layer=camera,
    sync_mode=SyncMode.INDEPENDENT,
    fps=5,
)
```

### Bottleneck Handling

Each layer tracks its own `effective_fps`. Slow layer dictates its own rate:
- Video at 30fps + GPU filter at 5fps = GPU layer updates at 5fps
- Video layer still updates at 30fps independently

### Multi-Layer Input

A filter can depend on multiple layers:

```python
class CompositeFilter(FilterProvider):
    def process_multi(self, inputs: dict[int, Image]) -> Image:
        background = inputs[0]
        foreground = inputs[1]
        mask = inputs[2]
        return composite(background, foreground, mask)

composite_layer = stage.add_layer(
    source=CompositeFilter(),
    input_layers=[layer_0, layer_1, layer_2],
)
```

---

## Filter System

See `imagestag/filters/DESIGN.md` for full details.

### Core Principles

- **Dataclass-based** - All filters are dataclasses with typed parameters
- **JSON-serializable** - Filters can be saved/loaded as JSON
- **Backend-agnostic** - Work with PIL, OpenCV, or RAW numpy
- **Chainable** - Compose via FilterPipeline
- **Registry** - `@register_filter` decorator for auto-registration

### Filter Categories

| Category | Filters |
|----------|---------|
| **Color** | Brightness, Contrast, Saturation, HueShift, Grayscale, GammaCorrection, ColorBalance, Invert, Threshold |
| **Blur/Sharpen** | GaussianBlur, BoxBlur, MedianBlur, BilateralFilter, Sharpen, UnsharpMask |
| **Edge Detection** | Canny, Sobel, Laplacian, EdgeEnhance |
| **Geometric** | Resize, Crop, CenterCrop, Rotate, Flip, Pad |
| **Lens Correction** | LensDistortionCorrection, PerspectiveCorrection, AffineTransform, Deskew |
| **Morphological** | Erode, Dilate, MorphOpen, MorphClose |
| **Compositing** | Blend (12 modes), Composite (with mask) |

### Base Filter Class

```python
@dataclass
class Filter(ABC):
    @abstractmethod
    def apply(self, image: Image) -> Image:
        pass

    @property
    def type(self) -> str:
        """Filter type name for serialization."""
        return self.__class__.__name__

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.AUTO

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> 'Filter':
        filter_type = data.pop('type')
        return FILTER_REGISTRY[filter_type](**data)
```

### Filter Pipeline

```python
pipeline = (
    FilterPipeline()
    .append(Resize(scale=0.5))
    .append(LensDistortionCorrection(k1=-0.15))
    .append(GaussianBlur(radius=2))
    .append(Sharpen(amount=1.5))
)

result = pipeline.apply(image)
```

### Serialization

**JSON:**
```json
{
  "type": "FilterPipeline",
  "filters": [
    {"type": "Resize", "scale": 0.5},
    {"type": "LensDistortionCorrection", "k1": -0.15, "k2": 0.02},
    {"type": "GaussianBlur", "radius": 1.5},
    {"type": "Brightness", "factor": 1.1}
  ]
}
```

**URL/String Format:**

Compact string format for URLs and quick usage:

```
resize(0.5)|blur(1.5)|brightness(1.1)
```

With named parameters:
```
resize(scale=0.5)|lens(k1=-0.15,k2=0.02)|blur(radius=1.5)
```

URL-safe (use `;` instead of `|`):
```
?filters=resize(0.5);blur(1.5);brightness(1.1)
```

**Parsing:**
```python
# From string
pipeline = FilterPipeline.parse("resize(0.5)|blur(1.5)|brightness(1.1)")

# From URL parameter
pipeline = FilterPipeline.parse(request.args.get('filters'))

# Equivalent to:
pipeline = FilterPipeline([
    Resize(scale=0.5),
    GaussianBlur(radius=1.5),
    Brightness(factor=1.1),
])
```

**String Format Rules:**
- Filters separated by `|` or `;`
- Parameters in parentheses
- Positional args map to primary parameter (e.g., `blur(1.5)` → `radius=1.5`)
- Named args with `=`
- Filter names are case-insensitive, matched to registry

### Filter Graphs (Branching & Combining)

For complex operations with multiple branches:

```
[main: resize(0.5)|blur(1.5)]
[mask: grayscale|threshold(128)]
blend(main, mask, mode=multiply)
```

**Compact single-line:**
```
[a:resize(0.5)|blur(1.5)][b:gray|threshold(128)]blend(a,b,multiply)
```

**Python API:**
```python
from imagestag.filters import FilterGraph, Blend, BlendMode

graph = FilterGraph()

# Define branches
main = graph.branch('main', [Resize(scale=0.5), GaussianBlur(radius=1.5)])
mask = graph.branch('mask', [Grayscale(), Threshold(value=128)])

# Combine branches
graph.output = Blend(inputs=[main, mask], mode=BlendMode.MULTIPLY)

result = graph.apply(image)
```

**Graph from string:**
```python
graph = FilterGraph.parse("""
    [main: resize(0.5)|blur(1.5)]
    [mask: gray|threshold(128)]
    blend(main, mask, multiply)
""")
```

**JSON format:**
```json
{
  "type": "FilterGraph",
  "branches": {
    "main": [
      {"type": "Resize", "scale": 0.5},
      {"type": "GaussianBlur", "radius": 1.5}
    ],
    "mask": [
      {"type": "Grayscale"},
      {"type": "Threshold", "value": 128}
    ]
  },
  "output": {
    "type": "Blend",
    "inputs": ["main", "mask"],
    "mode": "multiply"
  }
}
```

### Stage Integration

Filters integrate as layer sources:

```python
from imagestag.filters import FilterPipeline, GaussianBlur

pipeline = FilterPipeline([GaussianBlur(radius=2)])
stage.add_layer(source=pipeline, input_layer=camera, sync_mode=SyncMode.SYNCED)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Filter base class with JSON serialization
- [ ] Filter registry with `@register_filter`
- [ ] FilterPipeline
- [ ] Stage class with width/height
- [ ] Layer class with source

### Phase 2: Layer System
- [ ] Static sources (URL, data URL, Image)
- [ ] Positioning classes (Anchor, Pos, Size enums)
- [ ] Z-ordering
- [ ] Auto-size from first image
- [ ] ResizeMode enum
- [ ] Client areas

### Phase 3: Basic Filters
- [ ] Color: Brightness, Contrast, Saturation, Grayscale
- [ ] Blur: GaussianBlur, MedianBlur
- [ ] Sharpen: Sharpen, UnsharpMask
- [ ] Geometric: Resize, Crop, Rotate, Flip

### Phase 4: Dynamic Content
- [ ] TimeBasedProvider interface
- [ ] FrameBasedProvider interface
- [ ] threading.Event synchronization
- [ ] Frame buffer
- [ ] Sync statistics (sync_quality, effective_fps)

### Phase 5: Layer Dependencies
- [ ] Layer linking (input_layer)
- [ ] SyncMode enum (SYNCED, INDEPENDENT, UNBOUND)
- [ ] FilterProvider interface (process method)
- [ ] Multi-layer input (input_layers)
- [ ] Per-layer effective_fps tracking

### Phase 6: Advanced Filters
- [ ] Edge detection: Canny, Sobel, Laplacian
- [ ] Threshold (binary, Otsu, adaptive)
- [ ] Morphological: Erode, Dilate, Open, Close
- [ ] LensDistortionCorrection (Brown-Conrady model)
- [ ] PerspectiveCorrection (4-point transform)
- [ ] AffineTransform
- [ ] Deskew

### Phase 7: Compositing
- [ ] BlendMode enum (12 modes)
- [ ] Blend filter
- [ ] Composite filter (with mask)

---

## Open Questions

1. **Layer z-index**: Auto-increment or require explicit?
2. **Async loading**: How to handle layers that load at different times?
3. **Error handling**: What if a URL fails to load?
4. **Caching**: Cache loaded images? Invalidation strategy?

---

## Notes

<!-- Add your notes here -->
