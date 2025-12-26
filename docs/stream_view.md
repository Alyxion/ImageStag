# StreamView Component

High-performance NiceGUI component for 1080p@60fps video streaming with multi-layer compositing.

## Overview

StreamView is a custom NiceGUI component that provides:
- Real-time video streaming at 60fps
- Multi-layer compositing with z-index ordering
- SVG overlay with placeholder-based updates
- Per-layer timing/latency tracking
- Piggyback mode for zero-delay dependent layers

## Architecture

### Pull-Based Frame Delivery

```
JavaScript (Browser)                    Python (Server)
┌─────────────────────┐                ┌─────────────────────┐
│  requestAnimationFrame  │──request──▶│  Layer Buffer       │
│  per layer @ target fps │            │  (pre-rendered)     │
│                     │◀──base64────│                     │
│  Composite layers   │                │  Producer Thread    │
│  on canvas          │                │  (per layer)        │
└─────────────────────┘                └─────────────────────┘
```

### Layer Stack

```
┌─────────────────────────────────────┐
│     SVG Overlay (topmost)           │  ← Mouse coords, crosshairs
├─────────────────────────────────────┤
│     Thermal Layer (z=15)            │  ← Piggyback mode, follows mouse
├─────────────────────────────────────┤
│     Detection Boxes (z=10)          │  ← Multi-output stream
├─────────────────────────────────────┤
│     Heatmap (z=8)                   │  ← Multi-output stream
├─────────────────────────────────────┤
│     Watermark (z=5)                 │  ← Static PNG with alpha
├─────────────────────────────────────┤
│     Video (z=0)                     │  ← VideoStream @ 60fps
└─────────────────────────────────────┘
```

## File Structure

```
imagestag/components/stream_view/
├── __init__.py           # Public exports
├── stream_view.py        # Main StreamView component (NiceGUI Element)
├── stream_view.js        # Vue.js component (canvas, timing, events)
├── stream_view.css       # Styling, metrics overlay
├── layers.py             # StreamViewLayer, ImageStream, VideoStream, CustomStream
├── svg_overlay.py        # SVG template with placeholder replacement
├── metrics.py            # FPSCounter, PythonMetrics
└── timing.py             # FrameMetadata, FilterTiming for latency tracking
```

## Key Classes

### StreamView (stream_view.py)

Main component that manages layers and communicates with JavaScript.

```python
from imagestag.components.stream_view import StreamView, VideoStream

view = StreamView(width=960, height=540, show_metrics=True)

# Add video layer
video_stream = VideoStream('/path/to/video.mp4', loop=True)
view.add_layer(stream=video_stream, fps=60, z_index=0)

# Add static watermark
view.add_layer(image=watermark_img, z_index=5, use_png=True)

# Start playback
view.start()
```

### StreamViewLayer (layers.py)

Individual layer in the compositing stack.

```python
@dataclass
class StreamViewLayer:
    id: str                          # Unique identifier
    z_index: int                     # Stacking order
    target_fps: int                  # Update rate
    pipeline: FilterPipeline | None  # Per-layer filters

    # Source (exactly one, unless piggyback=True)
    stream: ImageStream | None
    url: str | None
    image: Image | None

    # Configuration
    buffer_size: int = 4             # Frames to buffer ahead
    jpeg_quality: int = 85
    use_png: bool = False            # For transparency
    piggyback: bool = False          # Direct injection mode

    # Position (for PIP windows)
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
```

### VideoStream (layers.py)

OpenCV-based video/camera source with frame sharing.

```python
class VideoStream(ImageStream):
    def __init__(self, path: str | int, *, loop: bool = True):
        ...

    # Frame sharing for dependent streams
    @property
    def last_frame(self) -> Image | None: ...

    def get_last_frame_with_timestamp(self) -> tuple[Image | None, float]: ...

    # Synchronous callback - runs in producer thread
    def on_frame(self, callback: Callable[[Image, float], None]) -> None: ...
```

### CustomStream (layers.py)

User-provided render handler with optional source dependency.

```python
# Single output
def render(t: float) -> Image:
    return generate_frame(t)

stream = CustomStream(render, mode='thread')

# Multi-output (one handler → multiple layers)
def detect(t: float) -> dict[str, Image]:
    return {'boxes': boxes_img, 'heatmap': heat_img}

stream = CustomStream(detect)
view.add_layer(stream=stream, stream_output='boxes', z_index=10)
view.add_layer(stream=stream, stream_output='heatmap', z_index=8)
```

## Timing System

### Birth-to-Display Latency

The timing system tracks every step from frame capture to display:

```
Python Side:
  capture_time ──▶ filter_timings[] ──▶ encode_start/end ──▶ send_time

JavaScript Side:
  receive_time ──▶ decode_ms ──▶ render_ms ──▶ display_time

Total Latency = display_time - capture_time
```

### FrameMetadata (timing.py)

```python
@dataclass
class FrameMetadata:
    frame_id: int
    capture_time: float      # When frame was captured (ms, perf_counter based)
    filter_timings: list[FilterTiming]
    encode_start: float
    encode_end: float
    send_time: float

    # Populated by JavaScript
    receive_time: float
    js_decode_ms: float
    js_render_ms: float
```

### Metrics Display

The JS component shows real-time metrics:
```
Birth→Display Latency (ms)
Video:    15.2ms  (py:8.5 + net:5.0 + js:1.7)
Thermal:  10.7ms  (py:5.1 + net:5.0 + js:0.5)  Crop:0.1 Filter:1.1 Enc:0.2
Δ Thermal-Video: -4.6ms
```

## Piggyback Mode

### Problem

Dependent layers (like a thermal lens that processes video frames) had ~18ms delay even with:
- Frame sharing via `last_frame` property
- Synchronous `on_frame` callbacks
- Pre-encoded data

**Root cause**: Each layer's producer thread runs on its own schedule.

### Solution

Piggyback mode allows direct frame injection, bypassing the producer thread:

```python
# Create thermal layer with piggyback=True (no producer thread)
thermal_layer = view.add_layer(
    piggyback=True,
    fps=60,
    z_index=15,
    buffer_size=1,
    x=100, y=100,
    width=200, height=150,
)

# Inject frames directly from video's on_frame callback
def process_and_inject(frame: Image, capture_time: float) -> None:
    # Process frame
    thermal = apply_thermal_filter(frame)
    encoded = encode_to_base64(thermal)

    # Inject directly into layer's buffer
    thermal_layer.inject_frame(
        encoded=encoded,
        birth_time=capture_time,
        step_timings={'filter_ms': 1.2, 'enc_ms': 0.3}
    )

video_stream.on_frame(process_and_inject)
```

### Results

| Metric | Before (separate thread) | After (piggyback) |
|--------|--------------------------|-------------------|
| Delta  | +18.8ms (thermal behind) | -4.6ms (thermal ahead) |

The negative delta means thermal is ready *before* video because it's processed first in video's thread.

## SVG Overlay

Placeholder-based SVG for efficient updates:

```python
# Set template with placeholders
view.set_svg('''
    <svg viewBox="0 0 960 540">
        <circle cx="{x}" cy="{y}" r="20" fill="red"/>
        <text x="10" y="30">{label}</text>
    </svg>
''', {'x': 480, 'y': 270, 'label': 'Ready'})

# Fast update on mouse move
@view.on_mouse_move
def handle(e):
    view.update_svg_values(x=e.x, y=e.y)
```

## Usage Examples

### Basic Video Playback

```python
from nicegui import ui
from imagestag.components.stream_view import StreamView, VideoStream

view = StreamView(width=960, height=540, show_metrics=True)
video = VideoStream('video.mp4', loop=True)
view.add_layer(stream=video, fps=60, z_index=0)

ui.button("Start", on_click=lambda: (video.start(), view.start()))
ui.button("Stop", on_click=lambda: (view.stop(), video.stop()))

ui.run()
```

### Thermal Lens with Piggyback Mode

See `samples/stream_view_demo.py` for complete implementation.

Key pattern:
1. Create video layer normally
2. Create thermal layer with `piggyback=True`
3. Register `on_frame` callback on video stream
4. In callback: process frame, encode, call `thermal_layer.inject_frame()`

### Multi-Output Stream

```python
def detector(t: float) -> dict[str, Image]:
    # Single processing pass produces multiple outputs
    boxes = draw_detection_boxes()
    heatmap = generate_attention_heatmap()
    return {'boxes': boxes, 'heatmap': heatmap}

stream = CustomStream(detector, mode='thread')

# Multiple layers share the same stream
view.add_layer(stream=stream, stream_output='boxes', fps=10, z_index=20)
view.add_layer(stream=stream, stream_output='heatmap', fps=10, z_index=15)
```

## Performance Tips

1. **Buffer size**: Use `buffer_size=4` for video, `buffer_size=1` for dependent layers
2. **JPEG quality**: Lower quality = faster encode, smaller payload (try 75-85)
3. **PNG for alpha**: Only use `use_png=True` when transparency is needed
4. **Piggyback mode**: Use for dependent layers that must sync with a source
5. **Frame sharing**: Use `video_stream.last_frame` for read-only access to current frame

## Test Media

Download Big Buck Bunny test video:
```bash
python scripts/download_test_media.py
```

Location: `tmp/media/big_buck_bunny_1080p_h264.mov`

## Running the Demo

```bash
python samples/stream_view_demo.py

# Or with custom video
python samples/stream_view_demo.py /path/to/video.mp4
```

Open http://localhost:8080 in browser.
