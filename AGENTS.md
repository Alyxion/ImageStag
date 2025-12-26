# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Windsurf, Cursor, etc.) when working with code in this repository.

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

## Thread Safety Rules

**This library MUST be thread-safe.** Filters and pipelines are designed to run in parallel executors.

### Fundamental Principles

1. **No Global State Mutation**: Filters MUST NOT modify global variables during `apply()` execution
2. **Immutable Filter Instances**: Filter parameters should not change after construction
3. **No Shared Mutable State**: Each thread must work with independent data

### What IS Thread-Safe

```python
# Class-level IMMUTABLE caches are OK (read-only after creation)
class FalseColor(Filter):
    _lut_cache: ClassVar[dict[str, np.ndarray]] = {}  # OK - cached LUTs are immutable arrays

    def _get_lut(self) -> np.ndarray:
        if key not in self._lut_cache:
            # Race condition on first access is acceptable - same value computed
            self._lut_cache[key] = self._compute_lut()  # OK - write once, read many
        return self._lut_cache[key]
```

### What is NOT Thread-Safe (AVOID)

```python
# BAD - Modifying instance state during apply()
class BadFilter(Filter):
    counter: int = 0

    def apply(self, image):
        self.counter += 1  # BAD - race condition in parallel execution
        return image

# BAD - Modifying global variables
_global_results = []

class BadFilter(Filter):
    def apply(self, image):
        _global_results.append(result)  # BAD - shared mutable state
        return image

# BAD - Modifying shared input data
class BadFilter(Filter):
    def apply(self, image):
        pixels = image.get_pixels()
        pixels[0, 0] = 255  # BAD if pixels is shared reference
        return Image(pixels)
```

### Thread-Safe Patterns

```python
# GOOD - Return new data, don't modify input
class GoodFilter(Filter):
    def apply(self, image):
        pixels = image.get_pixels().copy()  # Copy if modifying
        pixels[0, 0] = 255
        return Image(pixels)

# GOOD - Use local variables only
class GoodFilter(Filter):
    def apply(self, image):
        local_result = self._process(image)  # Local variable
        return local_result

# GOOD - Thread-local storage for truly necessary state
import threading
class StatefulFilter(Filter):
    _thread_local = threading.local()

    def apply(self, image):
        if not hasattr(self._thread_local, 'buffer'):
            self._thread_local.buffer = self._create_buffer()
        # Use thread-local buffer
```

### Parallel Executor Requirements

When filters run in `StreamingPipelineExecutor` or `BatchPipelineExecutor`:

1. **Same filter instance** may be called from multiple threads simultaneously
2. **Input images** may be processed in any order
3. **No assumptions** about execution order between stages

```python
# Pipeline stages run in separate threads
pipeline = FilterPipeline([
    Resize(scale=0.5),      # Thread 1
    FalseColor('hot'),      # Thread 2
    Encode('jpeg'),         # Thread 3
])

# All three filters may execute simultaneously on different frames
with StreamingPipelineExecutor(pipeline) as executor:
    for img in images:
        executor.submit(img)  # Frames flow through threads
```

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

### Framework Preservation

Filters should preserve the input framework when possible:

```python
@dataclass
class MyFilter(Filter):
    _preserve_framework: ClassVar[bool] = True  # PIL in → PIL out, CV in → CV out

    def apply(self, image):
        input_framework = image.framework
        # ... process ...
        if input_framework == ImsFramework.CV:
            return Image(result, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)
        return Image(result, pixel_format=PixelFormat.RGB)
```

Performance-critical filters (like `Resize`) may force a specific framework:

```python
@dataclass
class Resize(Filter):
    _preserve_framework: ClassVar[bool] = False  # Always uses OpenCV for 20x speedup
```

### Self-Documenting Filter Metadata

**Filters declare their own behavior via class attributes.** Don't hardcode filter names in external tools or scripts.

```python
@dataclass
class MyFilter(Filter):
    # Gallery/documentation metadata
    _gallery_skip: ClassVar[bool] = False       # Skip in gallery (needs special input)
    _gallery_sample: ClassVar[str | None] = None  # Specific sample image name
    _gallery_multi_output: ClassVar[bool] = False  # Outputs multiple images (show as grid)
    _gallery_synthetic: ClassVar[str | None] = None  # Needs synthetic image: 'lines', 'circles'

    # Port definitions for multi-input/output filters
    _input_ports: ClassVar[list[dict]] = [
        {'name': 'input', 'type': 'image'},
    ]
    _output_ports: ClassVar[list[dict]] = [
        {'name': 'output', 'type': 'image'},
    ]
```

Examples:

```python
# Geometry detectors need synthetic test images
@dataclass
class HoughCircleDetector(GeometryFilter):
    _gallery_synthetic: ClassVar[str] = 'circles'  # Gallery generator creates circles image

@dataclass
class HoughLineDetector(GeometryFilter):
    _gallery_synthetic: ClassVar[str] = 'lines'  # Gallery generator creates lines image

# Multi-output filters display as grids
@dataclass
class SplitChannels(Filter):
    _gallery_multi_output: ClassVar[bool] = True  # Show R/G/B as colored grid

# Filters requiring special inputs are skipped
@dataclass
class DrawGeometry(CombinerFilter):
    _gallery_skip: ClassVar[bool] = True  # Needs geometry input, can't demo standalone
```

**Principle**: Tools like `gallery_gen.py` inspect these class attributes rather than maintaining hardcoded lists. When adding a new filter with special requirements, set the appropriate `_gallery_*` attribute on the class itself.

## Git Commit Rules

**Do NOT include any of the following in commit messages:**
- `Co-Authored-By` lines
- `🤖 Generated with [Claude Code]` or similar attribution
- Any reference to Claude or AI assistance

Commit messages should be clean and appear as if written by the repository owner.

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
