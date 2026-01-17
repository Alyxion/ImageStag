# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Windsurf, Cursor, etc.) when working with code in this repository.

## Project Overview

ImageStag is a Python library focused on efficient, high-performance image processing and visualization. The core `Image` class supports multiple storage frameworks (PIL, RAW numpy, OpenCV) and various pixel formats (RGB, RGBA, BGR, BGRA, GRAY, HSV).

## Build and Development Commands

```bash
# Install dependencies (includes building Rust extension)
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

## Rust Extension

ImageStag includes high-performance Rust extensions for image processing. The Rust code is in `rust/` and is built automatically via maturin.

### Building the Rust Extension

```bash
# Build release wheel (for distribution)
maturin build --release

# Build and install in development mode
maturin develop

# Build with specific Python
maturin build --release -i python3.13
```

### Rust Module Location

The compiled extension is installed as `imagestag.imagestag_rust`.

**Image Format**: All Rust filters use **RGBA format only** (not BGR). This is a design decision for consistency and simplicity.

**Data Types**: Filters support both:
- `u8` - 8-bit per channel (0-255)
- `f32` - Float per channel (0.0-1.0)

### Available Rust Filters

#### Basic Operations
- `threshold_gray(image, threshold)` - Binary thresholding for grayscale
- `invert_rgba(image)` - Invert RGB, preserve alpha
- `premultiply_alpha(image)` - Convert straight alpha to premultiplied
- `unpremultiply_alpha(image)` - Convert premultiplied to straight alpha

#### Blur Filters
- `gaussian_blur_rgba(image, sigma)` - Gaussian blur using separable convolution
- `box_blur_rgba(image, radius)` - Fast box blur

#### Layer Effects (can expand canvas)
- `drop_shadow_rgba(image, offset_x, offset_y, blur_radius, color, opacity, expand)` - Drop shadow
- `drop_shadow_rgba_f32(...)` - Float version
- `stroke_rgba(image, width, color, opacity, position, expand)` - Stroke/outline effect
  - `position`: "outside", "inside", or "center"
- `stroke_rgba_f32(...)` - Float version

#### Lighting Effects
- `bevel_emboss_rgba(image, depth, angle, altitude, highlight_color, highlight_opacity, shadow_color, shadow_opacity, style)` - 3D bevel effect
  - `style`: "outer_bevel", "inner_bevel", "emboss", "pillow_emboss"
- `inner_glow_rgba(image, radius, color, opacity, choke)` - Glow inside shape edges
- `outer_glow_rgba(image, radius, color, opacity, spread, expand)` - Glow outside shape edges
- `inner_shadow_rgba(image, offset_x, offset_y, blur_radius, choke, color, opacity)` - Shadow inside shape edges
- `inner_shadow_rgba_f32(...)` - Float version
- `color_overlay_rgba(image, color, opacity)` - Solid color overlay preserving alpha
- `color_overlay_rgba_f32(...)` - Float version

### Layer Effects Python OOP API

For a cleaner interface, use the OOP wrappers in `imagestag.layer_effects`:

```python
from imagestag.layer_effects import DropShadow, Stroke, OuterGlow, InnerShadow, ColorOverlay

# Create and apply effect
shadow = DropShadow(blur=5, offset_x=10, offset_y=10, color=(0, 0, 0), opacity=0.75)
result = shadow.apply(image_rgba)  # Returns EffectResult

# Access results
output = result.image      # Output array (may be larger than input)
offset_x = result.offset_x  # X position shift
offset_y = result.offset_y  # Y position shift

# All effects support these pixel formats:
# - RGB8: uint8 (0-255), 3 channels
# - RGBA8: uint8 (0-255), 4 channels
# - RGBf32: float32 (0.0-1.0), 3 channels
# - RGBAf32: float32 (0.0-1.0), 4 channels
```

Available effect classes:
- `DropShadow(blur, offset_x, offset_y, color, opacity)`
- `InnerShadow(blur, offset_x, offset_y, choke, color, opacity)`
- `OuterGlow(radius, color, opacity, spread)`
- `InnerGlow(radius, color, opacity, choke)`
- `BevelEmboss(depth, angle, altitude, highlight_color, highlight_opacity, shadow_color, shadow_opacity, style)`
- `Stroke(width, color, opacity, position)`
- `ColorOverlay(color, opacity)`

### Filter Architecture

Filters can produce **output images with different dimensions than input**. This is essential for effects like drop shadows, strokes, and glows that extend beyond the original bounds.

```python
# Low-level Rust API (direct function calls)
from imagestag.imagestag_rust import drop_shadow_rgba

# Input: 100x100 RGBA image
result = drop_shadow_rgba(image, offset_x=10, offset_y=10, blur_radius=5)
# Output: 132x132 RGBA image (expanded to fit shadow)
```

The `expand` parameter controls how much padding is added. If not specified, filters auto-calculate based on effect parameters.

### Rust Module Structure

```
rust/src/
├── lib.rs                 # PyO3 module definition, function registration
└── filters/
    ├── mod.rs             # Filter submodule declarations
    ├── core.rs            # Shared utilities (blur, SDF, blending, canvas expansion)
    ├── basic.rs           # threshold, invert, alpha premultiply
    ├── blur.rs            # gaussian_blur, box_blur
    ├── drop_shadow.rs     # Drop shadow effect
    ├── stroke.rs          # Stroke/outline effect
    └── lighting.rs        # Bevel, emboss, inner/outer glow
```

### Adding New Rust Filters

1. Create filter file in `rust/src/filters/` (e.g., `my_filter.rs`)
2. Add `pub mod my_filter;` to `rust/src/filters/mod.rs`
3. Write filter function with `#[pyfunction]` attribute:
   ```rust
   use ndarray::Array3;
   use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
   use pyo3::prelude::*;

   #[pyfunction]
   #[pyo3(signature = (image, param1=1.0, param2=(0, 0, 0)))]
   pub fn my_filter_rgba<'py>(
       py: Python<'py>,
       image: PyReadonlyArray3<'py, u8>,
       param1: f32,
       param2: (u8, u8, u8),
   ) -> Bound<'py, PyArray3<u8>> {
       let input = image.as_array();
       // ... process ...
       result.into_pyarray(py)
   }
   ```
4. Import and register in `rust/src/lib.rs`:
   ```rust
   use filters::my_filter::my_filter_rgba;

   #[pymodule]
   fn imagestag_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
       m.add_function(wrap_pyfunction!(my_filter_rgba, m)?)?;
       Ok(())
   }
   ```
5. Rebuild with `maturin develop`
6. Optionally add Python wrapper in `imagestag/` for convenience

### Dependencies

- Rust toolchain (rustc, cargo)
- maturin (`pip install maturin`)
- PyO3 for Python bindings
- ndarray for array operations
- numpy (Python) for array interop

## Architecture

- **Package Manager**: Poetry + Maturin (for Rust)
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
