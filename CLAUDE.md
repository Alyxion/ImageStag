# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ImageStag is a Python library focused on efficient, high-performance image processing and visualization. The core `Image` class supports multiple storage frameworks (PIL, RAW numpy, OpenCV) and various pixel formats (RGB, RGBA, BGR, BGRA, GRAY, HSV).

## Build and Development Commands

```bash
# Install dependencies
poetry install

# After manually adding a dependency, run
poetry lock && poetry install

# Run tests
poetry run pytest tests/ -v

# Run a single test
poetry run pytest tests/test_image.py::test_load -v

# Run the interactive NiceGUI demo
poetry run python samples/image_demo.py

# Add a new dependency
poetry add <package>
```

## Architecture

- **Package Manager**: Poetry
- **Python Version**: 3.12+
- **Main Package**: `imagestag/`
- **Tests**: `tests/`
- **Samples**: `samples/` - Interactive demos using NiceGUI
- **Media**: `imagestag/media/samples/` - Sample images (stag.jpg)

### Core Classes

- `Image` - Main image class supporting loading, manipulation, and encoding
- `PixelFormat` - Enum for pixel formats (RGB, RGBA, BGR, BGRA, GRAY, HSV)
- `ImsFramework` - Storage framework selection (PIL, RAW, CV)
- `InterpolationMethod` - Resize interpolation methods
- `Color/Colors` - Color definitions and common color constants
- `Size2D/Pos2D/Bounding2D` - Geometry helper classes

### Image Storage Frameworks

- **PIL** (default): Uses Pillow internally, best for general use
- **RAW**: Uses numpy arrays in RGB/RGBA order, fast pixel access
- **CV**: Uses numpy arrays in BGR/BGRA order (OpenCV convention)

## NiceGUI Development Rules

This repository uses NiceGUI and Poetry for interactive demos.

- Always use `poetry run ...` to run scripts
- Keep NiceGUI on port 8080. If blocked, kill the process using nice-vibes MCP tools
- NiceGUI hot-reloads on file changes - no need to restart the server
- Do not open a browser automatically (use `show=False` in `ui.run()`)
- Prefer nice-vibes MCP tools for docs, samples, and component details
- Use `capture_url_screenshot` from nice-vibes to verify visual changes

### NiceGUI Best Practices

- Always use `@ui.page('/')` decorator for pages
- Use dataclasses for state management
- Use data binding (`bind_value()`, `bind_text()`) instead of manual UI updates
- Use `ui.header()` for app headers
- Include main guard: `if __name__ in {'__main__', '__mp_main__'}:`