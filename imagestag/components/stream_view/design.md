# StreamView Component Design

StreamView is a high-performance video streaming component for NiceGUI that supports multi-layer compositing, real-time metrics, zoom/pan navigation, and specialized lens overlays.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         StreamView                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ VideoStream │  │CustomStream │  │ StaticImage │  (Sources)   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              StreamViewLayer (per source)                │    │
│  │  • Producer thread (buffering)                           │    │
│  │  • Filter pipeline                                       │    │
│  │  • Frame resize to target size                           │    │
│  │  • JPEG/PNG encoding                                     │    │
│  │  • Timing metadata                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   WebSocket Transport                    │    │
│  │  • Base64 encoded frames                                 │    │
│  │  • Frame metadata (timing, dimensions, buffer status)    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              JavaScript Component (Vue)                  │    │
│  │  • Canvas compositing (z-order)                          │    │
│  │  • SVG overlay                                           │    │
│  │  • Zoom/pan with navigation window                       │    │
│  │  • Metrics panel                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Core Concepts

### 1. StreamView

The main container component that manages layers, handles events, and coordinates rendering.

```python
view = StreamView(
    width=1920,              # Display width in pixels
    height=1080,             # Display height in pixels
    show_metrics=True,       # Show performance overlay
    enable_zoom=True,        # Enable mouse wheel zoom
    min_zoom=1.0,            # Minimum zoom level
    max_zoom=10.0,           # Maximum zoom level
    show_nav_window=True,    # Show navigation thumbnail when zoomed
    nav_window_position="bottom-right",
    nav_window_size=(160, 90),
)
```

**Key Methods:**
- `add_layer()` - Add a new layer to the view
- `remove_layer()` - Remove a layer
- `set_size()` - Dynamically resize the view (updates all layers)
- `set_svg()` - Set SVG overlay template with placeholders
- `update_svg_values()` - Update SVG placeholder values
- `start()` / `stop()` - Control streaming
- `update_layer_position()` - Move/resize a layer

### 2. Image Streams

Abstract base class for frame sources. All streams implement `get_frame(timestamp)`.

#### VideoStream
OpenCV-based video file or camera capture with frame sharing support.

```python
video = VideoStream(
    path="/path/to/video.mp4",  # Or device index (0, 1, ...)
    loop=True,                   # Loop video files
    target_fps=60,               # Target frame rate
)

# Frame sharing - other streams can access the latest frame
frame = video.last_frame
timestamp = video.last_frame_timestamp

# Synchronous callbacks for dependent processing
video.on_frame(lambda frame, ts: process_frame(frame, ts))
```

#### CustomStream
User-provided render callback for procedural content or multi-output streams.

```python
# Single output
def render(timestamp: float) -> Image:
    return generate_frame(timestamp)

stream = CustomStream(render, mode="thread")

# Multi-output (e.g., detector producing boxes + heatmap)
def detect(timestamp: float) -> dict[str, Image]:
    return {
        "boxes": draw_boxes(...),
        "heatmap": generate_heatmap(...),
    }

stream = CustomStream(detect, mode="thread")
```

### 3. StreamViewLayer

A layer in the compositing stack with its own source, FPS, and processing pipeline.

```python
layer = view.add_layer(
    stream=video_stream,       # ImageStream source
    stream_output="boxes",     # For multi-output streams
    name="Video",              # Display name in metrics
    fps=60,                    # Target frame rate
    z_index=0,                 # Stacking order (higher = on top)
    pipeline=my_pipeline,      # Optional FilterPipeline
    buffer_size=4,             # Frame buffer size
    jpeg_quality=85,           # JPEG encoding quality
    use_png=False,             # Use PNG for transparency
    x=None, y=None,            # Position (None = full canvas)
    width=None, height=None,   # Size (None = full canvas)
    depth=1.0,                 # Parallax depth factor
    overscan=0,                # Extra pixels for smooth movement
    piggyback=False,           # Receive frames via inject_frame()
)
```

#### Layer Properties

| Property | Description |
|----------|-------------|
| `z_index` | Stacking order. Higher values render on top. |
| `depth` | Controls response to viewport zoom/pan (see Parallax section). |
| `overscan` | Extra pixels captured around display area for smooth movement. |
| `piggyback` | When True, layer receives frames via `inject_frame()` instead of producer thread. |
| `target_fps` | Desired update rate. Producer thread throttles to this rate. |
| `buffer_size` | Number of frames to buffer ahead. Higher = smoother but more latency. |

### 4. Frame Processing Pipeline

Each layer can have a filter pipeline applied before encoding:

```python
from imagestag.filters import FilterPipeline, Resize, FalseColor

pipeline = FilterPipeline([
    Resize((640, 480)),
    FalseColor(colormap="hot"),
])

view.add_layer(stream=video, pipeline=pipeline)
```

### 5. Target Size & Bandwidth Optimization

Layers automatically resize frames to match their display size before encoding, reducing bandwidth:

```python
# Full-canvas layer at 720p view → frames resized to 1280x720
view = StreamView(width=1280, height=720)
view.add_layer(stream=video)  # Frames resized to 1280x720

# When view resizes, layers update automatically
view.set_size(1920, 1080)  # Now frames resize to 1920x1080
```

For positioned layers, frames resize to the layer's explicit dimensions:
```python
view.add_layer(stream=video, width=200, height=150)  # Always 200x150
```

## Depth & Parallax System

The `depth` property controls how layers respond to viewport zoom/pan:

| Depth | Behavior | Use Case |
|-------|----------|----------|
| `0.0` | Fixed - doesn't move with viewport | HUD, overlays, crosshairs |
| `1.0` | Content - follows viewport exactly | Main video/image (default) |
| `0.5` | Parallax background - moves at 50% speed | Distant backgrounds |
| `2.0` | Parallax foreground - moves at 200% speed | Close foreground elements |

```python
# Fixed overlay (depth=0) - stays in place when zooming
view.add_layer(stream=hud_stream, depth=0.0, z_index=100)

# Main content (depth=1) - zooms normally
view.add_layer(stream=video, depth=1.0, z_index=0)

# Background (depth=0.5) - parallax effect
view.add_layer(stream=bg_stream, depth=0.5, z_index=-1)
```

## Overscan System

For positioned layers that move (like lenses), overscan provides extra pixels around the visible area to prevent showing stale content during movement:

```python
lens_layer = view.add_layer(
    stream=lens_stream,
    x=100, y=100,
    width=200, height=150,
    overscan=32,  # 32px extra on each side
)
```

When `overscan=32`:
- Actual frame size: 264×214 (200+64, 150+64)
- Display clips to: 200×150
- Movement up to 32px shows valid content from the overscan buffer

The layer tracks an "anchor position" - where the content was centered when captured. JavaScript uses this to offset the image correctly during movement.

## Piggyback Mode

For dependent layers that need zero-delay synchronization with a source, use piggyback mode:

```python
# Layer receives frames via inject_frame() instead of producer thread
lens_layer = view.add_layer(
    piggyback=True,
    buffer_size=1,
    # ... other options
)

# Inject frames from source's on_frame callback
def on_frame(frame, timestamp):
    processed = process(frame)
    encoded = encode_to_base64(processed)
    lens_layer.inject_frame(
        encoded=encoded,
        birth_time=timestamp,
        step_timings={"crop_ms": 0.5, "encode_ms": 1.2},
        anchor_x=100, anchor_y=100,
    )

video_stream.on_frame(on_frame)
```

## Lens System

Lenses are specialized overlays that show transformed views of another layer (e.g., thermal view, magnifier).

```python
from imagestag.components.stream_view import (
    create_thermal_lens,
    create_magnifier_lens,
)

# Thermal lens - false color visualization
thermal = create_thermal_lens(
    view=view,
    video_layer=video_layer,
    name="Thermal",
    colormap="hot",
    width=200, height=150,
    overscan=32,
    mask_feather=16,
    z_index=15,
)
thermal.attach(video_stream)

# Magnifier lens - zoom with barrel distortion
magnifier = create_magnifier_lens(
    view=view,
    video_layer=video_layer,
    name="Magnifier",
    zoom_factor=2.5,
    barrel_strength=0.4,
    width=200, height=150,
)
magnifier.attach(video_stream)

# Move lens on mouse move
@view.on_mouse_move
def on_mouse(e):
    thermal.move_to(e.x, e.y)
```

### Lens Features

- **Frame sharing**: Lenses use `VideoStream.on_frame()` for synchronous processing
- **Piggyback mode**: Zero-delay frame injection
- **Overscan**: Smooth movement without stale content
- **Mask shapes**: Circle, ellipse, rounded rectangle with feathering
- **Partial off-screen**: Lenses can extend beyond view edges

## SVG Overlay System

Dynamic SVG overlay with Python-controlled placeholders:

```python
view.set_svg(
    '''
    <svg viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
        <circle cx="{x}" cy="{y}" r="20" fill="red"/>
        <text x="{x}" y="{y}">{label}</text>
    </svg>
    ''',
    {'x': 960, 'y': 540, 'label': 'Center'}
)

# Update values dynamically
@view.on_mouse_move
def on_mouse(e):
    view.update_svg_values(x=e.x, y=e.y, label=f"{e.x}, {e.y}")
```

## Zoom & Pan

When `enable_zoom=True`:

| Control | Action |
|---------|--------|
| Mouse wheel | Zoom in/out centered on cursor |
| Drag | Pan when zoomed in |
| Double-click | Reset zoom to 1x |
| Nav window click | Jump to position |

```python
# Programmatic zoom control
view.set_zoom(2.0, center_x=0.5, center_y=0.5)
view.reset_zoom()
```

Server-side cropping: When zoomed, Python crops frames to the visible viewport before encoding, reducing bandwidth.

## Metrics System

The metrics overlay provides real-time performance monitoring:

### Header (Always Visible)
- Display FPS
- Total bandwidth
- Active layer count
- Zoom level (when zoomed)

### Layers Table
| Column | Description |
|--------|-------------|
| Name | Layer display name |
| Type | Source type + format (VID/J, GEN/P, etc.) |
| FPS | Actual frame rate (target in tooltip) |
| Latency | Total birth-to-display latency |
| Rate | Current bandwidth |

### Expanded Layer Details
- **Latency breakdown**: Python / Network / JS with visual bar
- **Filter timing**: Per-filter durations
- **Resolution**: Transferred frame dimensions
- **Bandwidth**: Average frame size, total transferred
- **Buffer**: Current/max buffer occupancy

### Graph Modes
- **Latency**: Total latency over time per layer
- **FPS**: Frame rate history per layer
- **Bandwidth**: Transfer rate over time

### Controls
- **Pause**: Freeze metrics display
- **Export**: Download last 30 seconds as JSON
- **Minimize**: Collapse to header only
- **Drag/Resize**: Reposition and resize panel

## Timing Metadata

Each frame carries metadata through the pipeline:

```python
@dataclass
class FrameMetadata:
    frame_id: int
    capture_time: float      # When frame was captured
    filter_timings: list     # Per-filter durations
    encode_start: float
    encode_end: float
    send_time: float         # When sent via WebSocket
    frame_bytes: int         # Encoded size
    frame_width: int         # Transferred dimensions
    frame_height: int
    buffer_length: int       # Buffer occupancy when added
    buffer_capacity: int
    anchor_x: int            # For overscan layers
    anchor_y: int
    nav_thumbnail: str       # Base64 thumbnail for nav window
```

JavaScript adds:
- `js_receive_time`: When received
- `js_decode_start/end`: Image decode timing
- `js_render_time`: When drawn to canvas

## Event Handling

```python
@view.on_mouse_move
def on_move(e: StreamViewMouseEventArguments):
    # e.x, e.y - screen coordinates
    # e.source_x, e.source_y - source image coordinates
    # e.viewport - current viewport state
    pass

@view.on_mouse_click
def on_click(e: StreamViewMouseEventArguments):
    pass

@view.on_viewport_change
def on_viewport(e: StreamViewViewportEventArguments):
    # e.viewport - new viewport state
    # e.prev_viewport - previous viewport
    pass
```

## File Structure

```
stream_view/
├── __init__.py          # Public exports
├── stream_view.py       # Main StreamView component
├── stream_view.js       # Vue component (canvas, metrics, events)
├── stream_view.css      # Styling (metrics panel, zoom UI)
├── layers.py            # ImageStream, VideoStream, CustomStream, StreamViewLayer
├── lens.py              # Lens class and factory functions
├── timing.py            # FrameMetadata, FilterTiming
├── metrics.py           # FPSCounter, PythonMetrics
└── design.md            # This document
```

## Performance Considerations

1. **Frame resizing**: Frames are resized to display size before encoding, reducing bandwidth significantly at lower resolutions.

2. **Buffer sizing**: Higher `buffer_size` = smoother playback but more latency. Default of 4 works well for 60fps.

3. **JPEG vs PNG**: Use JPEG for opaque content (faster, smaller). Use PNG only when alpha transparency is needed.

4. **Piggyback mode**: Eliminates producer thread scheduling delay for dependent layers like lenses.

5. **Overscan**: Adds processing overhead but prevents visual artifacts during movement.

6. **Server-side cropping**: When zoomed, only the visible portion is transferred, reducing bandwidth proportionally to zoom level.
