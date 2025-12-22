# Stage Component Design

A multi-layer compositing component for visualizing static and dynamic image content.

## Core Principles

1. **Layer-based composition** - Stack multiple image layers with z-order
2. **Flexible sources** - Layers can use URLs, data URLs, or dynamic content sources
3. **Auto-sizing** - Stage size defaults to the first loaded image's dimensions
4. **Full-area default** - Layers fill the entire stage by default
5. **Dynamic sources** - A single source can populate multiple layers simultaneously

## Layer Sources

A layer can receive content from:

### Static Sources
- **URL** - Remote image (`https://example.com/image.jpg`)
- **Data URL** - Inline base64 (`data:image/png;base64,...`)
- **File path** - Local file (`/path/to/image.png`)
- **Image object** - ImageStag `Image` instance

### Dynamic Sources
- **Content provider** - Object that generates/updates layer content
- Can fill **multiple layers** from a single source
- Examples: video decoder, animation renderer, filter pipeline, game engine

## Layer Stack Example

```
┌─────────────────────────────────────┐
│  Layer 3: SVG overlay (UI/icons)    │  ← top (rendered last)
├─────────────────────────────────────┤
│  Layer 2: PNG (transparency)        │
├─────────────────────────────────────┤
│  Layer 1: Dynamic content           │  ← from content provider
├─────────────────────────────────────┤
│  Layer 0: JPG background            │  ← bottom (rendered first)
└─────────────────────────────────────┘
```

## Sizing Behavior

### Auto-Size (Default)
Stage dimensions are determined by:
1. First static image loaded, OR
2. First frame received from a dynamic source

```python
# Stage will be 1920x1080 if background.jpg is that size
stage = Stage()
stage.add_layer(url='background.jpg')
```

### Explicit Size
```python
stage = Stage(width=800, height=600)
```

### Resize Behavior
When stage size differs from layer content:
- **Default**: Layer scales to fill entire stage (stretch)
- **fit**: Scale proportionally to fit (may have letterboxing)
- **cover**: Scale proportionally to cover (may crop)
- **none**: Use original size (may overflow or not fill)

## Zoom & Pan

Built-in viewport control for navigating large content with minimal effort.

### Minimal Setup (3 Lines)

```python
from imagestag import Stage

stage = Stage(url='photo.jpg', zoomable=True)
stage.zoom_range = (0.1, 10.0)  # 10% to 1000%
# Mouse wheel zooms, drag pans - done!
```

### Buffer Margin

When zoomed out or panned, always render slightly more than visible to avoid edge artifacts and enable smooth panning:

```python
@dataclass
class ViewportConfig:
    buffer_margin: float = 0.1  # 10% extra on each side
    buffer_min_px: int = 50     # At least 50px buffer
    buffer_max_px: int = 500    # At most 500px buffer
```

This ensures:
- Zooming out shows content with a comfortable margin
- Panning doesn't reveal empty edges immediately
- Dynamic sources can pre-render just outside visible area

### Viewport Class

```python
from dataclasses import dataclass, field

@dataclass
class Viewport:
    """Controls zoom and pan state for a Stage."""

    zoom: float = 1.0                    # Current zoom level (1.0 = 100%)
    pan: Pos = field(default_factory=lambda: Pos(0, 0))  # Pan offset
    zoom_min: float = 0.1                # Minimum zoom (10%)
    zoom_max: float = 10.0               # Maximum zoom (1000%)
    zoom_step: float = 0.1               # Zoom increment per wheel tick

    def zoom_in(self, factor: float = 1.25):
        """Zoom in by factor."""
        self.zoom = min(self.zoom * factor, self.zoom_max)

    def zoom_out(self, factor: float = 1.25):
        """Zoom out by factor."""
        self.zoom = max(self.zoom / factor, self.zoom_min)

    def zoom_to_fit(self, content_size: Size, view_size: Size):
        """Adjust zoom to fit content in view."""
        scale_x = view_size.width / content_size.width
        scale_y = view_size.height / content_size.height
        self.zoom = min(scale_x, scale_y, self.zoom_max)
        self.pan = Pos(0, 0)

    def zoom_to_fill(self, content_size: Size, view_size: Size):
        """Adjust zoom to fill view (may crop)."""
        scale_x = view_size.width / content_size.width
        scale_y = view_size.height / content_size.height
        self.zoom = max(scale_x, scale_y)
        self.zoom = min(self.zoom, self.zoom_max)

    def zoom_to_point(self, point: Pos, target_zoom: float):
        """Zoom to specific level, keeping point centered."""
        # Adjust pan to keep point stationary
        old_zoom = self.zoom
        self.zoom = max(self.zoom_min, min(target_zoom, self.zoom_max))

        # Calculate pan adjustment
        zoom_ratio = self.zoom / old_zoom
        self.pan = Pos(
            int(point.x - (point.x - self.pan.x) * zoom_ratio),
            int(point.y - (point.y - self.pan.y) * zoom_ratio)
        )

    def reset(self):
        """Reset to default view."""
        self.zoom = 1.0
        self.pan = Pos(0, 0)

    def screen_to_content(self, screen_pos: Pos) -> Pos:
        """Convert screen coordinates to content coordinates."""
        return Pos(
            int((screen_pos.x - self.pan.x) / self.zoom),
            int((screen_pos.y - self.pan.y) / self.zoom)
        )

    def content_to_screen(self, content_pos: Pos) -> Pos:
        """Convert content coordinates to screen coordinates."""
        return Pos(
            int(content_pos.x * self.zoom + self.pan.x),
            int(content_pos.y * self.zoom + self.pan.y)
        )

    def clamp_pan(self, content_size: Size, view_size: Size):
        """Constrain pan to keep content visible."""
        scaled_w = content_size.width * self.zoom
        scaled_h = content_size.height * self.zoom

        # Allow panning but keep at least some content visible
        max_pan_x = max(0, scaled_w - view_size.width // 2)
        max_pan_y = max(0, scaled_h - view_size.height // 2)

        self.pan = Pos(
            max(-max_pan_x, min(self.pan.x, view_size.width // 2)),
            max(-max_pan_y, min(self.pan.y, view_size.height // 2))
        )

    def get_render_region(self, content_size: Size, view_size: Size,
                          buffer_margin: float = 0.1) -> 'RenderRegion':
        """Calculate what region of content needs rendering.

        Returns a RenderRegion that dynamic sources can use to optimize
        rendering - only generate pixels that will actually be visible
        (plus buffer margin).
        """
        # Visible area in content coordinates
        top_left = self.screen_to_content(Pos(0, 0))
        bottom_right = self.screen_to_content(Pos(view_size.width, view_size.height))

        # Add buffer margin
        buffer_x = int((bottom_right.x - top_left.x) * buffer_margin)
        buffer_y = int((bottom_right.y - top_left.y) * buffer_margin)

        return RenderRegion(
            x=max(0, top_left.x - buffer_x),
            y=max(0, top_left.y - buffer_y),
            width=min(content_size.width, bottom_right.x - top_left.x + 2 * buffer_x),
            height=min(content_size.height, bottom_right.y - top_left.y + 2 * buffer_y),
            zoom=self.zoom,
            content_size=content_size,
            view_size=view_size,
        )
```

### RenderRegion Class

Dynamic sources receive a `RenderRegion` that tells them exactly what to render:

```python
@dataclass
class RenderRegion:
    """Describes what region of content needs rendering."""

    x: int                    # Top-left X in content coordinates
    y: int                    # Top-left Y in content coordinates
    width: int                # Width to render (in content pixels)
    height: int               # Height to render (in content pixels)
    zoom: float               # Current zoom level
    content_size: Size        # Total content size
    view_size: Size           # View/screen size

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Return (x, y, x2, y2) bounds."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def output_size(self) -> Size:
        """Size of output image after zoom applied."""
        return Size(
            int(self.width * self.zoom),
            int(self.height * self.zoom)
        )

    def contains(self, x: int, y: int) -> bool:
        """Check if content coordinate is in render region."""
        return (self.x <= x < self.x + self.width and
                self.y <= y < self.y + self.height)

    def to_local(self, x: int, y: int) -> Pos:
        """Convert content coordinate to local render coordinate."""
        return Pos(x - self.x, y - self.y)
```

### Stage Integration

```python
class Stage:
    def __init__(self,
                 width: int | None = None,
                 height: int | None = None,
                 url: str | None = None,
                 zoomable: bool = False,
                 pannable: bool | None = None):  # None = same as zoomable

        self.viewport = Viewport()
        self._zoomable = zoomable
        self._pannable = pannable if pannable is not None else zoomable

        if url:
            self.add_layer(url=url)

    @property
    def zoomable(self) -> bool:
        return self._zoomable

    @zoomable.setter
    def zoomable(self, value: bool):
        self._zoomable = value

    @property
    def pannable(self) -> bool:
        return self._pannable

    @pannable.setter
    def pannable(self, value: bool):
        self._pannable = value

    @property
    def zoom(self) -> float:
        return self.viewport.zoom

    @zoom.setter
    def zoom(self, value: float):
        self.viewport.zoom = max(self.viewport.zoom_min,
                                  min(value, self.viewport.zoom_max))

    @property
    def pan(self) -> Pos:
        return self.viewport.pan

    @pan.setter
    def pan(self, value: Pos):
        self.viewport.pan = value

    @property
    def zoom_range(self) -> tuple[float, float]:
        return (self.viewport.zoom_min, self.viewport.zoom_max)

    @zoom_range.setter
    def zoom_range(self, value: tuple[float, float]):
        self.viewport.zoom_min, self.viewport.zoom_max = value

    def zoom_to_fit(self):
        """Fit content in view."""
        content = self._get_content_size()
        self.viewport.zoom_to_fit(content, Size(self.width, self.height))

    def zoom_to_point(self, point: Pos, zoom: float):
        """Zoom to level, centering on point."""
        self.viewport.zoom_to_point(point, zoom)
```

### Input Handling

```python
class Stage:
    def on_wheel(self, event):
        """Handle mouse wheel for zoom."""
        if not self._zoomable:
            return

        # Zoom toward mouse position
        mouse_pos = Pos(event.x, event.y)
        if event.delta > 0:
            self.viewport.zoom_in()
        else:
            self.viewport.zoom_out()

        # Keep mouse position stable
        self.viewport.zoom_to_point(mouse_pos, self.viewport.zoom)

    def on_drag(self, event):
        """Handle mouse drag for pan."""
        if not self._pannable:
            return

        self.viewport.pan = Pos(
            self.viewport.pan.x + event.dx,
            self.viewport.pan.y + event.dy
        )
        self.viewport.clamp_pan(self._get_content_size(),
                                 Size(self.width, self.height))
```

### Examples

**Image viewer:**
```python
# Minimal - just enable zoom
stage = Stage(url='photo.jpg', zoomable=True)
```

**Map viewer with limits:**
```python
stage = Stage(width=800, height=600, zoomable=True)
stage.add_layer(url='world_map.jpg')
stage.zoom_range = (0.5, 8.0)  # 50% to 800%
stage.zoom_to_fit()  # Start fitted
```

**Programmatic navigation:**
```python
stage = Stage(url='blueprint.png', zoomable=True)

# Zoom to specific area
stage.zoom = 2.0
stage.pan = Pos(-500, -300)

# Or zoom to a point
stage.zoom_to_point(Pos(1000, 800), zoom=4.0)

# Reset view
stage.viewport.reset()
```

**Get content coordinates from click:**
```python
def on_click(event):
    screen_pos = Pos(event.x, event.y)
    content_pos = stage.viewport.screen_to_content(screen_pos)
    print(f"Clicked on content at {content_pos}")
```

## Layer Positioning

All positioning uses Python classes and enums - no CSS-style strings.

### Core Classes

```python
from imagestag import Anchor, Pos, Size, ResizeMode

# Anchor enum
class Anchor(Enum):
    TOP_LEFT = auto()
    TOP_CENTER = auto()
    TOP_RIGHT = auto()
    CENTER_LEFT = auto()
    CENTER = auto()
    CENTER_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_CENTER = auto()
    BOTTOM_RIGHT = auto()

# Position class
class Pos:
    def __init__(self, x: int, y: int): ...           # absolute pixels
    @classmethod
    def percent(cls, x: float, y: float) -> Pos: ...  # relative %

# Size class
class Size:
    def __init__(self, width: int, height: int): ...            # absolute pixels
    @classmethod
    def percent(cls, width: float, height: float) -> Size: ...  # relative %
    @classmethod
    def auto(cls) -> Size: ...                                  # from content

# Resize mode enum
class ResizeMode(Enum):
    FILL = auto()   # stretch to fit (default)
    FIT = auto()    # proportional, may letterbox
    COVER = auto()  # proportional, may crop
    NONE = auto()   # original size
```

### Default: Fill Entire Area
```python
layer = stage.add_layer(url='image.png')
# Layer fills 100% width and 100% height
```

### Anchored Positioning
Position layer relative to stage edges/center:

```python
from imagestag import Anchor

# Anchor to bottom-right corner
layer = stage.add_layer(url='logo.png', anchor=Anchor.BOTTOM_RIGHT)

# Anchor to center
layer = stage.add_layer(url='sprite.png', anchor=Anchor.CENTER)
```

### Relative Positioning (Percentages)
```python
from imagestag import Pos

# Position at 10% from left, 20% from top
layer = stage.add_layer(url='icon.png', pos=Pos.percent(10, 20))
```

### Absolute Positioning (Pixels)
```python
from imagestag import Pos

# Position at exact pixel coordinates
layer = stage.add_layer(url='icon.png', pos=Pos(100, 50))
```

### Client Areas
Define named regions within the stage:

```python
from imagestag import Pos, Size

# Define a client area
stage.define_area('sidebar', pos=Pos.percent(0, 0), size=Size.percent(20, 100))
stage.define_area('content', pos=Pos.percent(20, 0), size=Size.percent(80, 100))

# Place layer within a client area
layer = stage.add_layer(url='menu.png', area='sidebar')
```

### Size Constraints
```python
from imagestag import Size

# Fixed size
layer = stage.add_layer(url='thumb.png', size=Size(100, 100))

# Percentage of stage
layer = stage.add_layer(url='banner.png', size=Size.percent(50, 100))

# Auto size from content
layer = stage.add_layer(url='photo.png', size=Size.auto())

# Max constraints
layer = stage.add_layer(url='photo.png', max_size=Size(400, 300))
```

### Resize Mode
```python
from imagestag import ResizeMode

layer = stage.add_layer(url='bg.jpg', resize_mode=ResizeMode.COVER)
```

## Dynamic Content Sources

Dynamic content can be delivered **sync**, **async**, or from a **background thread**.

### Time Management

The Stage maintains a **world time** (in seconds) that content providers can use:

```python
stage = Stage()
stage.time = 0.0  # world time in seconds

# Advance time (e.g., in game loop or animation frame)
stage.time += delta_time
```

### Content Provider Types

#### 1. Time-Based Provider (sync/async)
For procedural content, live drawing, SVG generation:

```python
from imagestag import TimeBasedProvider, Image, RenderRegion

class AnimatedBackground(TimeBasedProvider):
    def render(self, time: float, region: RenderRegion | None = None) -> Image:
        """Called with world time in seconds. Returns rendered content.

        Args:
            time: World time in seconds
            region: Optional render region. If provided, only render
                    the specified area for efficiency. If None, render
                    full content.

        Returns:
            Rendered image. If region was provided, image should be
            region.width x region.height pixels (content coordinates).
        """
        if region:
            # Optimized: only render visible area + buffer
            return create_gradient_region(hue, region.bounds)
        else:
            # Full render
            hue = (time * 30) % 360
            return create_gradient(hue)

    def render_layers(self, time: float, region: RenderRegion | None = None) -> dict[int, Image]:
        """Optional: provide multiple layers at once."""
        return {
            0: self.render_background(time, region),
            1: self.render_particles(time, region),
        }
```

**Example: Tile-based map with region optimization:**

```python
class TileMapProvider(TimeBasedProvider):
    def __init__(self, tile_size: int = 256):
        self.tile_size = tile_size
        self.tile_cache: dict[tuple[int, int], Image] = {}

    def render(self, time: float, region: RenderRegion | None = None) -> Image:
        if region is None:
            return self._render_full()

        # Only load/render tiles that intersect the render region
        result = Image.create(region.width, region.height, PixelFormat.RGBA)

        tile_x_start = region.x // self.tile_size
        tile_x_end = (region.x + region.width) // self.tile_size + 1
        tile_y_start = region.y // self.tile_size
        tile_y_end = (region.y + region.height) // self.tile_size + 1

        for tx in range(tile_x_start, tile_x_end):
            for ty in range(tile_y_start, tile_y_end):
                tile = self._get_tile(tx, ty)
                # Calculate where this tile goes in the output
                dest_x = tx * self.tile_size - region.x
                dest_y = ty * self.tile_size - region.y
                result.paste(tile, dest_x, dest_y)

        return result
```

#### 2. Frame-Based Provider (background thread)
For video, streams, or any content decoded in a background thread:

```python
from imagestag import FrameBasedProvider, Image, RenderRegion

class VideoDecoder(FrameBasedProvider):
    def __init__(self, path: str, fps: float = 30.0):
        self._fps = fps
        self._frame_index = 0
        self._current_frame: Image | None = None
        self._render_region: RenderRegion | None = None
        # Start background decoder thread...

    @property
    def fps(self) -> float:
        """Target frame rate for decoding."""
        return self._fps

    @property
    def frame_index(self) -> int:
        """Current frame index. Used for change detection."""
        return self._frame_index

    def set_render_region(self, region: RenderRegion | None):
        """Update the region to decode/render.

        Called by Stage when viewport changes. Provider can use this
        to optimize decoding - e.g., only decode tiles in view,
        or reduce decode resolution when zoomed out.
        """
        self._render_region = region

    def get_frame(self) -> tuple[int, Image]:
        """Returns (frame_index, image).

        Stage uses frame_index to detect changes:
        - Same index as before → skip redraw
        - Different index → redraw required

        If a render region was set, the returned image should be
        cropped/optimized for that region.
        """
        return (self._frame_index, self._current_frame)

    def get_layers(self) -> dict[int, tuple[int, Image]]:
        """Optional: provide multiple layers with indices."""
        return {
            0: (self._bg_index, self._background),
            1: (self._fg_index, self._foreground),
        }
```

**Example: Region-aware video decoder (only decode visible tiles):**

```python
class TiledVideoDecoder(FrameBasedProvider):
    """Decodes only the visible portion of a large video."""

    def set_render_region(self, region: RenderRegion | None):
        self._render_region = region
        # Notify decode thread to adjust what it's decoding
        self._region_changed.set()

    def _decode_loop(self):
        while self._running:
            region = self._render_region

            if region:
                # Only decode visible area + buffer
                frame = self._decode_region(
                    x=region.x, y=region.y,
                    width=region.width, height=region.height
                )
            else:
                # Full frame decode
                frame = self._decode_full()

            with self._lock:
                self._frame_index += 1
                self._current_frame = frame
            self._frame_ready.set()
```

#### 3. Async Provider
For content fetched asynchronously:

```python
from imagestag import AsyncProvider, Image

class RemoteImageProvider(AsyncProvider):
    async def fetch(self) -> Image:
        """Fetch content asynchronously."""
        data = await http_client.get(self.url)
        return Image(data)

    async def fetch_layers(self) -> dict[int, Image]:
        """Fetch multiple layers asynchronously."""
        pass
```

### Frame Index for Change Detection

The frame index mechanism allows efficient rendering:

```python
class Stage:
    def render(self):
        for layer in self.layers:
            if isinstance(layer.source, FrameBasedProvider):
                index, image = layer.source.get_frame()

                # Skip if frame hasn't changed
                if index == layer._last_frame_index:
                    continue

                layer._last_frame_index = index
                layer._cached_image = image

            # ... composite layer
```

### Thread Safety & Synchronization

#### The Timing Problem

If frontend timer and background decoder both run at 30hz but are slightly out of phase:

```
Frontend:  |--check--|--check--|--check--|--check--|
Decoder:     |--frame--|--frame--|--frame--|--frame--|
                   ^
                   Frontend checks 1ms BEFORE frame is ready
                   → skips frame → visible lag/stutter
```

#### Solution: Intelligent Synchronization

**1. Frame Ready Event**

Decoder signals when a new frame is available. Frontend can wait briefly:

```python
class FrameBasedProvider:
    def __init__(self):
        self._frame_ready = threading.Event()
        self._lock = threading.Lock()
        self._frame_index = 0
        self._current_frame = None

    def get_frame(self, timeout: float | None = None) -> tuple[int, Image | None]:
        """Get current frame, optionally waiting for next one.

        Args:
            timeout: Max seconds to wait for new frame.
                     None = don't wait, return current immediately.

        Returns:
            (frame_index, image) or (frame_index, None) if no frame yet.
        """
        if timeout is not None:
            # Wait for new frame signal (with timeout)
            self._frame_ready.wait(timeout=timeout)
            self._frame_ready.clear()

        with self._lock:
            return (self._frame_index, self._current_frame)

    def wait_for_frame(self, timeout: float = 0.05) -> bool:
        """Wait until a new frame is available.

        Returns True if frame ready, False if timeout.
        """
        return self._frame_ready.wait(timeout=timeout)

    def _decode_loop(self):
        """Background decoder thread."""
        while self._running:
            frame = decode_next_frame()
            with self._lock:
                self._frame_index += 1
                self._current_frame = frame
            self._frame_ready.set()  # Signal: new frame available
            time.sleep(1.0 / self._fps)
```

**2. Frontend Sync Strategy**

```python
class Stage:
    def update(self):
        """Called by frontend timer (e.g., ui.timer at 30hz)."""
        for layer in self.layers:
            provider = layer.source
            if not isinstance(provider, FrameBasedProvider):
                continue

            last_index = layer._last_frame_index

            # Strategy: wait briefly if we expect a frame soon
            # This prevents skipping frames due to microsecond timing
            index, image = provider.get_frame()

            if index == last_index:
                # No new frame yet - wait a tiny bit
                # (frame should arrive within 1-2ms if decoder is on schedule)
                if provider.wait_for_frame(timeout=0.005):  # 5ms max wait
                    index, image = provider.get_frame()

            if index != last_index and image is not None:
                layer._last_frame_index = index
                layer._cached_image = image
                layer._needs_redraw = True
```

**3. Adaptive Frame Buffer**

Keep decoder slightly ahead to absorb timing jitter:

```python
class BufferedFrameProvider(FrameBasedProvider):
    def __init__(self, fps: float, buffer_frames: int = 2):
        self._buffer: deque[tuple[int, Image]] = deque(maxlen=buffer_frames)
        self._fps = fps

    def get_frame(self) -> tuple[int, Image | None]:
        """Get oldest buffered frame (FIFO)."""
        with self._lock:
            if self._buffer:
                return self._buffer.popleft()
            return (-1, None)

    def _decode_loop(self):
        """Decoder stays buffer_frames ahead."""
        while self._running:
            frame = decode_next_frame()
            with self._lock:
                self._buffer.append((self._frame_index, frame))
                self._frame_index += 1
            self._frame_ready.set()

            # Slow down if buffer is full (consumer is behind)
            while len(self._buffer) >= self._buffer.maxlen:
                time.sleep(0.001)
```

**4. Timing Statistics**

Track sync quality to detect issues:

```python
class FrameBasedProvider:
    def __init__(self):
        self._frames_delivered = 0
        self._frames_skipped = 0
        self._last_delivery_time = 0.0

    @property
    def sync_quality(self) -> float:
        """Percentage of frames successfully delivered (0.0-1.0)."""
        total = self._frames_delivered + self._frames_skipped
        return self._frames_delivered / total if total > 0 else 1.0

    @property
    def effective_fps(self) -> float:
        """Actual FPS being achieved."""
        pass
```

### Layer Dependencies & Filter Chains

Layers can depend on other layers for input (e.g., filters, detection overlays).
Each layer runs at its own rate - they don't need to be synchronized.

#### Example: Surveillance Camera with Face Detection

```
┌─────────────────────────────────────────────────────┐
│  Layer 2: Face boxes overlay      (5 fps)           │  ← slow detection
├─────────────────────────────────────────────────────┤
│  Layer 1: GPU blur filter         (as fast as GPU)  │  ← GPU-bound
├─────────────────────────────────────────────────────┤
│  Layer 0: Camera feed             (30 fps)          │  ← source
└─────────────────────────────────────────────────────┘

Layer 1 depends on Layer 0 (applies blur to camera)
Layer 2 depends on Layer 0 (detects faces in camera)
```

#### Layer Linking

```python
from imagestag import Stage, Layer, SyncMode

stage = Stage()

# Layer 0: Camera feed at 30fps
camera = stage.add_layer(source=CameraProvider(fps=30), z=0)

# Layer 1: GPU blur filter - linked to camera, runs as fast as GPU allows
blur_filter = stage.add_layer(
    source=GpuBlurFilter(),
    z=1,
    input_layer=camera,           # depends on layer 0
    sync_mode=SyncMode.UNBOUND,   # no FPS limit, GPU-bound
)

# Layer 2: Face detection - linked to camera, runs at 5fps independently
face_overlay = stage.add_layer(
    source=FaceDetector(),
    z=2,
    input_layer=camera,           # depends on layer 0
    sync_mode=SyncMode.INDEPENDENT,
    fps=5,                        # own rate, uses latest camera frame
)
```

#### Sync Modes

```python
from enum import Enum, auto

class SyncMode(Enum):
    SYNCED = auto()      # Process every source frame (1:1 with input layer)
    INDEPENDENT = auto() # Own FPS, uses latest available input frame
    UNBOUND = auto()     # No FPS limit, process as fast as possible (GPU-bound)
```

| Mode | Behavior | Use Case |
|------|----------|----------|
| `SYNCED` | Waits for input, processes every frame | Real-time filters that must match source |
| `INDEPENDENT` | Own FPS, grabs latest input when ready | Slow detection (5fps) on fast video (30fps) |
| `UNBOUND` | As fast as possible, no sleep | GPU processing, benchmarks |

#### Filter Layer Interface

```python
from imagestag import FilterProvider, Image

class FilterProvider:
    """Base class for layers that process another layer's content."""

    def process(self, input_frame: Image, frame_index: int) -> Image:
        """Process input frame and return result.

        Args:
            input_frame: Image from the input layer
            frame_index: Source frame index (for caching decisions)

        Returns:
            Processed image
        """
        pass


class GpuBlurFilter(FilterProvider):
    def __init__(self, radius: int = 5):
        self.radius = radius

    def process(self, input_frame: Image, frame_index: int) -> Image:
        # GPU blur - takes whatever time GPU needs
        return gpu_blur(input_frame, self.radius)


class FaceDetector(FilterProvider):
    def __init__(self):
        self._last_boxes = []

    def process(self, input_frame: Image, frame_index: int) -> Image:
        # Slow ML detection - runs at own pace
        self._last_boxes = detect_faces(input_frame)
        # Return transparent overlay with face boxes
        return draw_boxes(input_frame.size, self._last_boxes)
```

#### Bottleneck Handling

When a slow layer depends on a fast layer, the slow layer dictates its own effective FPS:

```python
# Video at 30fps, GPU filter can only do 5fps
# Result: Layer 0 updates at 30fps, Layer 1 updates at 5fps

class Stage:
    def get_layer_effective_fps(self, layer: Layer) -> float:
        """Get actual FPS a layer is achieving."""
        return layer._effective_fps

# Each layer tracks its own timing
class Layer:
    def __init__(self):
        self._frame_times: deque[float] = deque(maxlen=30)

    @property
    def effective_fps(self) -> float:
        if len(self._frame_times) < 2:
            return 0.0
        duration = self._frame_times[-1] - self._frame_times[0]
        return len(self._frame_times) / duration if duration > 0 else 0.0
```

#### Multi-Layer Input

A filter can depend on multiple layers:

```python
class CompositeFilter(FilterProvider):
    """Combines multiple input layers."""

    def process_multi(self, inputs: dict[int, Image]) -> Image:
        """Process multiple input layers.

        Args:
            inputs: {layer_z: image} for each input layer
        """
        background = inputs[0]
        foreground = inputs[1]
        mask = inputs[2]
        return composite(background, foreground, mask)

# Usage
composite_layer = stage.add_layer(
    source=CompositeFilter(),
    z=3,
    input_layers=[layer_0, layer_1, layer_2],  # multiple inputs
)

### Example: Video Source

```python
class VideoSource(ContentProvider):
    def __init__(self, video_path):
        self.video = load_video(video_path)

    def get_layers(self):
        frame = self.video.current_frame()
        return {
            0: frame.background,  # Decoded background
            1: frame.foreground,  # Alpha-masked foreground
        }

# Usage
video = VideoSource('movie.mp4')
stage = Stage(source=video)
```

### Example: Filter Pipeline

```python
class FilterPipeline(ContentProvider):
    def __init__(self, source_image):
        self.original = source_image
        self.brightness = 1.0
        self.show_edges = False

    def get_layers(self):
        layers = {0: self.original}
        if self.show_edges:
            layers[1] = detect_edges(self.original)
        return layers

# Usage
pipeline = FilterPipeline(my_image)
stage = Stage(source=pipeline)

# Toggle edge overlay
pipeline.show_edges = True
pipeline.notify_update()
```

## API Summary

### Stage Creation
```python
# Auto-size from content
stage = Stage()

# Explicit size
stage = Stage(width=800, height=600)

# From dynamic source
stage = Stage(source=my_content_provider)
```

### Adding Layers
```python
# Simple - fills entire stage
stage.add_layer(url='background.jpg')
stage.add_layer(data_url='data:image/png;base64,...')
stage.add_layer(image=my_image_object)

# With positioning
stage.add_layer(url='logo.png', anchor='bottom-right', width=100, height=50)

# With explicit z-index
stage.add_layer(url='overlay.svg', z=10)
```

### Layer Management
```python
# Get layer by index
layer = stage.layer(0)

# Update layer source
layer.url = 'new_image.jpg'

# Toggle visibility
layer.visible = False

# Set opacity
layer.opacity = 0.5

# Remove layer
stage.remove_layer(0)
```

### Rendering
```python
# Render all layers to Image
result = stage.render()

# Render to specific format
png_bytes = stage.to_png()
jpeg_bytes = stage.to_jpeg(quality=85)
```

## Implementation Phases

### Phase 1: Core Structure
- [ ] Stage class with width/height
- [ ] Layer class with source (URL, data URL, Image)
- [ ] Layer z-ordering
- [ ] Auto-size from first image
- [ ] Basic render (composite all layers)

### Phase 2: Positioning
- [ ] Anchor-based positioning
- [ ] Relative positioning (percentages)
- [ ] Absolute positioning (pixels)
- [ ] Size constraints (width, height, max)

### Phase 3: Layer Properties
- [ ] Visibility toggle
- [ ] Opacity
- [ ] Resize modes (fill, fit, cover, none)

### Phase 4: Client Areas
- [ ] Define named areas
- [ ] Place layers in areas
- [ ] Area-relative positioning

### Phase 5: Dynamic Sources
- [ ] ContentProvider interface
- [ ] Update notifications
- [ ] Multi-layer sources

## Open Questions

1. **Layer z-index**: Auto-increment or require explicit?
2. **Async loading**: How to handle layers that load at different times?
3. **Error handling**: What if a URL fails to load?
4. **Caching**: Cache loaded images? Invalidation strategy?
