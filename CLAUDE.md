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

## Filter Design Principles

### Color Parameters

**Always use the `Color` class for color parameters in filters.** Never use raw tuples like `tuple[int, int, int]` or plain strings.

```python
# CORRECT - Use Color type with default_factory
from imagestag.color import Color, Colors
from dataclasses import dataclass, field

@dataclass
class MyFilter(Filter):
    fill: Color = field(default_factory=lambda: Colors.BLACK)

    def __post_init__(self):
        # Accept string input and convert to Color
        if isinstance(self.fill, str):
            self.fill = Color(self.fill)

# INCORRECT - Don't use raw tuples or strings
@dataclass
class MyFilter(Filter):
    fill_color: tuple[int, int, int] = (0, 0, 0)  # BAD
    fill: str = '#000000'  # BAD - loses type safety
```

Benefits:
- **Type safety**: The `Color` class provides proper type checking
- **Flexibility**: Accepts hex strings (`"#FF0000"`), tuples, and Color objects
- **Auto-detection**: Filter designer automatically renders color picker for `Color` typed fields
- **Serialization**: `Filter.to_dict()` automatically converts `Color` to hex strings for JSON

### Filter Consolidation

**One class per functionality.** Don't create multiple classes for variations of the same operation.

```python
# CORRECT - Single class with parameters
@dataclass
class Rotate(Filter):
    angle: float = 0.0  # Any angle, auto-detects 90° multiples for fast path

# Use parameterized aliases for shortcuts
register_alias('rot90', Rotate, angle=90)
register_alias('rot180', Rotate, angle=180)

# INCORRECT - Multiple classes for same operation
class Rotate90(Filter): ...   # BAD
class Rotate180(Filter): ...  # BAD
class Rotate270(Filter): ...  # BAD
```

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

### Testing NiceGUI Apps

- Start apps in background with `run_in_background=true`, wait 2 seconds for startup
- Use nice-vibes `capture_url_screenshot` to verify visual changes
- NiceGUI renders completely via JavaScript - use longer wait times (4+ seconds) for complex components
- For interactive testing, use query parameters to control state (e.g., `?filter=blur&radius=5`)
- Never use curl or direct HTTP requests to test NiceGUI apps
- Do not open browser automatically during testing