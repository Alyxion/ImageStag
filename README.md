# ImageStag

A fast and efficient image processing and visualization library for Python.

## Installation

```bash
pip install imagestag
```

## Quick Start

```python
from imagestag import Image, Canvas, Color

# Load and process an image
img = Image("photo.jpg")
img = img.resize((800, 600)).apply_filter("blur", radius=2)
img.save("output.png")

# Create graphics with Canvas
canvas = Canvas(400, 300)
canvas.fill(Color.WHITE)
canvas.draw_circle((200, 150), 50, fill=Color.RED)
canvas.to_image().save("drawing.png")
```

## Features

- **High-performance Rust core** for compute-intensive operations
- **Multiple pixel formats** (RGB, RGBA, grayscale, float32)
- **Image filters** (blur, sharpen, edge detection, color adjustments)
- **Geometry primitives** (rectangles, circles, ellipses, lines, polygons)
- **Canvas drawing** with fonts and text rendering
- **Video/camera streams** with real-time processing
- **ASCII art rendering** for terminal visualization

## Sub-packages

| Package | Description | License |
|---------|-------------|---------|
| **imagestag** | Core image processing library | MIT |
| [stagforge](./stagforge) | Browser-based image editor add-on | Elastic License 2.0 |

## Licensing

### ImageStag – MIT License

The core library is fully permissive. Use it in commercial projects, modify it,
keep your code closed source—no restrictions.

See [LICENSE-MIT.txt](./LICENSE-MIT.txt)

### StagForge – Elastic License 2.0

StagForge is an optional add-on. You may use it commercially with one limitation:
**you may not offer StagForge as a hosted service** where it forms the primary offering.

See [LICENSE-ELv2.txt](./LICENSE-ELv2.txt)
