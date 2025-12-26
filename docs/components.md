# NiceGUI Components

ImageStag provides interactive NiceGUI components for building image processing applications.

## FilterDesigner

Visual node-based editor for building filter graphs:

```python
from nicegui import ui
from imagestag.components import FilterDesigner
from imagestag.filters import FilterGraph

@ui.page('/')
def main():
    designer = FilterDesigner()

    def on_execute():
        graph = designer.get_graph()
        if graph:
            result = graph.execute_designer()
            # Display result...

    ui.button('Execute', on_click=on_execute)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8080, show=False)
```

### Features

- Drag-and-drop node placement
- Visual connection drawing between ports
- Real-time parameter editing
- Filter search and categorization
- Graph serialization/deserialization
- Preview images at each node

### Methods

```python
# Get current graph
graph = designer.get_graph()

# Load graph from dict
designer.load_graph(graph_dict)

# Clear all nodes
designer.clear()

# Execute with placeholder images
result = designer.execute_preview()
```

## StreamView

High-performance video streaming component with multi-layer compositing. See [StreamView documentation](./stream_view.md) for full details.

```python
from nicegui import ui
from imagestag.components.stream_view import StreamView, VideoStream

@ui.page('/')
def main():
    view = StreamView(width=960, height=540, show_metrics=True)
    video = VideoStream('video.mp4', loop=True)
    view.add_layer(stream=video, fps=60, z_index=0)

    ui.button("Start", on_click=lambda: (video.start(), view.start()))

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8080, show=False)
```

### Key Features

- 1080p@60fps video streaming
- Multi-layer compositing with z-index
- SVG overlay with placeholder-based updates
- Per-layer timing/latency tracking
- Piggyback mode for zero-delay dependent layers
- Multi-output streams (one handler → multiple layers)

### Demo

```bash
python samples/stream_view_demo.py
```

## FilterExplorer

Interactive application for exploring and testing filters:

```python
from imagestag.tools import FilterExplorer

if __name__ in {'__main__', '__mp_main__'}:
    FilterExplorer.run(port=8080)
```

### Features

- Browse all available filters by category
- Live parameter adjustment with sliders
- Before/after image comparison
- Preset library with examples
- DSL input for quick testing
- Pipeline building interface

### Running FilterExplorer

```bash
# From command line
poetry run python -m imagestag.tools.filter_explorer

# Or programmatically
from imagestag.tools import FilterExplorer
FilterExplorer.run(port=8080, show=False)
```

## Integration Example

Full application with filter designer and live preview:

```python
from nicegui import ui
from imagestag import Image
from imagestag.components import FilterDesigner
from imagestag.samples import stag

@ui.page('/')
def main():
    with ui.row().classes('w-full'):
        # Left: Designer
        with ui.column().classes('w-2/3'):
            designer = FilterDesigner()

        # Right: Preview
        with ui.column().classes('w-1/3'):
            preview = ui.image().classes('w-full')

            async def update_preview():
                graph = designer.get_graph()
                if graph:
                    source = stag()
                    result = graph.execute(source)
                    data_url = result.to_data_url('jpeg', quality=80)
                    preview.set_source(data_url)

            ui.button('Preview', on_click=update_preview)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8080, show=False)
```

## Preset System

Pre-built filter graphs for common operations:

```python
from imagestag.tools import preset_registry

# List all presets
for preset in preset_registry.all_presets():
    print(f"{preset.key}: {preset.name}")

# Get specific preset
preset = preset_registry.get('face_detection')

# Create graph from preset
graph = preset.to_graph()

# Execute preset
result = graph.execute(image)
```

### Available Presets

| Key | Description |
|-----|-------------|
| `face_detection` | Detect and highlight faces |
| `circle_detection` | Detect circles with Hough transform |
| `gradient_blend` | Blend two images with gradient mask |
| `lens_correction` | Fix barrel/pincushion distortion |
| `thermal_view` | Apply thermal colormap |

### Preset Categories

- **Basic**: Simple filter applications
- **Detection**: Object/feature detection
- **Enhancement**: Image improvement
- **Effects**: Artistic effects
- **Compositing**: Multi-image operations

## Styling

Components use standard NiceGUI/Tailwind styling:

```python
designer = FilterDesigner().classes('w-full h-96')
```

## Events

FilterDesigner emits events for graph changes:

```python
designer = FilterDesigner()

@designer.on('graph_changed')
def on_change(e):
    print("Graph modified")

@designer.on('node_selected')
def on_select(e):
    print(f"Selected: {e.node_name}")
```
