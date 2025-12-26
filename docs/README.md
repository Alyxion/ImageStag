# ImageStag Documentation

ImageStag is a high-performance Python library for image processing and visualization. It provides a flexible, composable filter system with support for multiple backends (PIL, OpenCV, NumPy).

## Documentation Index

| Document | Description |
|----------|-------------|
| [Image Class](./image.md) | Core Image class, pixel formats, frameworks |
| [Filters](./filters.md) | Complete filter reference by category |
| [Pipelines](./pipelines.md) | Sequential filter chains with auto-conversion |
| [Filter Graphs](./graphs.md) | Node-based graphs with branching and multi-I/O |
| [DSL Reference](./dsl.md) | Compact text syntax for filters and graphs |
| [Parallel Execution](./parallel.md) | Thread-safe executors for high-throughput |
| [Benchmarking](./benchmarking.md) | Performance measurement utilities |
| [Components](./components.md) | NiceGUI components for interactive apps |
| [StreamView](./stream_view.md) | High-performance video streaming component |

## Quick Start

```python
from imagestag import Image
from imagestag.filters import Resize, FalseColor, FilterPipeline

# Load and process an image
img = Image.load("photo.jpg")

# Apply single filter
resized = Resize(scale=0.5).apply(img)

# Build pipeline
pipeline = FilterPipeline([
    Resize(size=(1920, 1080)),
    FalseColor(colormap='viridis'),
])
result = pipeline.apply(img)

# Save result
result.save("output.jpg", quality=90)
```

## Key Features

- **Multi-framework support**: PIL, OpenCV (CV), and raw NumPy backends
- **60+ filters**: Color, blur, geometric, edge detection, morphology, and more
- **Composable pipelines**: Chain filters with automatic format conversion
- **Filter graphs**: DAG-based processing with branching and merging
- **Parallel execution**: Stage-parallel and data-parallel executors
- **Thread-safe**: Designed for concurrent processing
- **Serializable**: JSON import/export for filters, pipelines, and graphs
- **Compact DSL**: Text-based filter definitions
