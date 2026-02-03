# ImageStag Development Guide

This repository contains two packages:

| Package | Description | License | Docs |
|---------|-------------|---------|------|
| **imagestag** | Core image processing library | MIT | [docs/](./docs/) |
| **stagforge** | Browser-based image editor | ELv2 | [stagforge/CLAUDE.md](./stagforge/CLAUDE.md) |

## Quick Start

```bash
# Install all dependencies (both packages)
poetry install

# Run imagestag tests
poetry run pytest tests/ --ignore=tests/stagforge

# Run stagforge tests
poetry run pytest tests/stagforge/

# Run stagforge editor
poetry run python -m stagforge.main
```

## Package Structure

```
ImageStag/
├── imagestag/           # Core library (MIT)
│   ├── api/             # ImageStag API (mountable FastAPI app)
│   ├── filters/         # Image filters (Python + JS/WASM)
│   │   └── js/          # JavaScript filter implementations
│   ├── layer_effects/   # Effect classes
│   ├── parity/          # Cross-platform parity testing
│   │   ├── js/          # JavaScript test runner
│   │   └── tests/       # Parity test registrations
│   ├── samples/         # Sample images and SVGs
│   ├── components/      # UI components
│   └── streams/         # Video/camera streams
├── stagforge/           # Image editor (ELv2)
│   ├── api/             # REST API
│   ├── frontend/        # JS/CSS frontend
│   ├── rendering/       # Python rendering
│   └── CLAUDE.md        # Stagforge dev guide
├── rust/                # Rust extensions (PyO3 + WASM)
│   └── src/filters/     # Rust filter implementations
└── tests/
    └── stagforge/       # Stagforge tests
```

## Package Separation (IMPORTANT)

**ImageStag** and **Stagforge** must remain cleanly separated. Code should be placed in the correct package based on its purpose:

### ImageStag (`imagestag/`)
General-purpose image processing library. Code here should be:
- **Reusable** outside of the Stagforge editor
- **Independent** of editor-specific UI or tools
- **Publishable** as a standalone MIT-licensed package

Contains:
- **Filters** - Image manipulation algorithms (grayscale, blur, sharpen, etc.)
- **Layer effects** - Visual effects (drop shadow, glow, stroke)
- **Rendering utilities** - General-purpose rendering (Lanczos resampling, etc.)
- **WASM bindings** - Cross-platform Rust/WASM modules
- **API** - Mountable FastAPI for samples and filters
- **Parity testing** - Cross-platform algorithm verification

### Stagforge (`stagforge/`)
Browser-based image editor. Code here is:
- **Editor-specific** - Only needed in the Stagforge application
- **Tool implementations** - Interactive editing tools (brush, selection, shapes)
- **UI components** - Editor dialogs, panels, menus

Contains:
- **Tools** - Interactive editing tools (brush, eraser, selection, etc.)
- **Selection algorithms** - Editor-specific selection handling (lasso, magic wand UI)
- **Document management** - Multi-document support, history, auto-save
- **Editor UI** - Dialogs, layer panels, tool options
- **Editor API** - REST endpoints for session/document management

### Decision Guide

| If the code... | Place in... |
|----------------|-------------|
| Is a pure image processing algorithm | `imagestag/filters/` |
| Provides visual layer effects | `imagestag/layer_effects/` |
| Is reusable WASM/Rust for any app | `imagestag/wasm/` |
| Is an interactive editing tool | `stagforge/frontend/js/tools/` |
| Manages editor-specific state | `stagforge/frontend/js/core/` |
| Handles editor UI (dialogs, panels) | `stagforge/frontend/js/` |

## ImageStag Core

See [docs/](./docs/) for detailed documentation:
- [Image class](./docs/image.md)
- [Filters](./docs/filters.md)
- [Components](./docs/components.md)
- [Stream View](./docs/stream_view.md)
- [Benchmarking](./docs/benchmarking.md)
- [Parity Testing](./docs/parity-testing.md)

### ImageStag API

ImageStag provides a mountable FastAPI application at `/imgstag/`:

```python
from imagestag.api import create_api
app.mount("/imgstag", create_api())
```

API endpoints:
- `GET /imgstag/samples` - List all available samples
- `GET /imgstag/samples/skimage/{name}.{format}` - Dynamic skimage rendering
- `GET /imgstag/samples/images/{filename}` - Static sample images
- `GET /imgstag/samples/svgs/{category}/{filename}` - Sample SVGs

### Cross-Platform Filters (Rust → Python + WASM)

Filters in `imagestag/filters/` can have cross-platform implementations:

1. **Rust core** (`rust/src/filters/`) - Shared algorithm
2. **Python binding** - PyO3 via `imagestag_rust` module
3. **JavaScript/WASM** - wasm-bindgen for browser use

Example: `grayscale` filter has implementations in:
- `rust/src/filters/grayscale.rs` - Core Rust implementation
- `imagestag/filters/grayscale.py` - Python wrapper (uses Rust or pure Python fallback)
- `imagestag/filters/js/grayscale.js` - JavaScript wrapper (uses WASM or pure JS fallback)

### Filter and Layer Effect Class Requirements

**Every filter and layer effect must have a proper class implementation.**

#### Filters (`imagestag/filters/`)

Filters must derive from one of these base classes:

| Base Class | Use Case | Output Type |
|------------|----------|-------------|
| `Filter` | Image-to-image transformations | `Image` |
| `GeometryFilter` | Geometry detection (contours, faces, circles) | `GeometryList` |
| `AnalyzerFilter` | Analysis without modification | `Image` (unchanged) |

**Required structure:**

```python
from dataclasses import dataclass
from typing import ClassVar
from imagestag.filters.base import Filter, register_filter, FilterContext
from imagestag.definitions import ImsFramework

@register_filter
@dataclass
class MyFilter(Filter):
    """Filter description.

    Parameters:
        param1: Description of parameter.
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]
    _primary_param: ClassVar[str] = 'param1'  # For compact syntax 'myfilter 5'

    param1: float = 1.0

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        # Implementation using Rust backend or pure Python
        from imagestag import imagestag_rust
        # ...
        return result_image
```

**For geometry detection filters:**

```python
from imagestag.filters.geometry import GeometryFilter

@register_filter
@dataclass
class MyDetector(GeometryFilter):
    """Detect shapes in images."""

    def detect(self, image: 'Image') -> 'GeometryList':
        # Return GeometryList with detected shapes
        from imagestag.geometry_list import GeometryList, Polygon
        # ...
        return geometry_list
```

**Standalone functions vs Filter classes:**

- **Standalone functions** (e.g., `grayscale(image)`) operate on raw numpy arrays
- **Filter classes** (e.g., `Grayscale()`) wrap standalone functions for the filter pipeline
- Both can coexist - the class calls the standalone function internally

#### Layer Effects (`imagestag/layer_effects/`)

Layer effects must derive from `LayerEffect`:

```python
from imagestag.layer_effects.base import LayerEffect, EffectResult, Expansion

class MyEffect(LayerEffect):
    """Non-destructive visual effect."""

    effect_type = "my_effect"
    display_name = "My Effect"

    def __init__(self, enabled: bool = True, opacity: float = 1.0,
                 blend_mode: str = "normal", **params):
        super().__init__(enabled, opacity, blend_mode)
        # Store effect-specific parameters

    def get_expansion(self) -> Expansion:
        """Return canvas expansion needed (for shadows, glows, etc.)."""
        return Expansion(top=0, right=0, bottom=0, left=0)

    def apply(self, image: np.ndarray, format = None) -> EffectResult:
        """Apply effect and return result with offset."""
        # Implementation
        return EffectResult(image=result, offset_x=0, offset_y=0)
```

### Building Rust Code

**Important:** When making changes to any Rust files in `rust/src/`, you must rebuild for BOTH Python and WASM:

```bash
# Rebuild for Python (PyO3) - platform-specific wheel
poetry run maturin develop --release

# Rebuild for JavaScript/WASM - architecture-independent bytecode
wasm-pack build rust/ --target web --out-dir ../imagestag/wasm --features wasm --no-default-features
```

Both commands must be run after any Rust changes to ensure Python and JavaScript have the same implementation. Forgetting to rebuild one platform will cause parity test failures.

**Note:** WASM is architecture-independent bytecode - the same `.wasm` file works on ARM64 and AMD64. The JavaScript runtime (browser/Node.js) JIT-compiles it to native code. Python wheels are platform-specific and need separate builds per architecture.

### Parity Testing

Cross-platform filters must produce identical output. Use the parity testing framework:

```bash
# Run all parity tests (Python + JavaScript) in one command
poetry run python scripts/run_all_parity_tests.py

# Optional: Run separately
node imagestag/parity/js/run_tests.js      # JavaScript tests only
poetry run pytest tests/test_filter_parity.py -v  # Python tests only
```

The unified script runs Python tests, JavaScript tests, and generates comparison reports.
Flags: `--no-python`, `--no-js`, `--no-compare`

Test artifacts are saved to `tmp/parity/` in the project root for easy inspection.
See [docs/parity-testing.md](./docs/parity-testing.md) for details.

## Stagforge Editor

See [stagforge/CLAUDE.md](./stagforge/CLAUDE.md) for comprehensive development guide covering:
- Architecture (JS-first, Python backend)
- Adding tools and filters
- API endpoints
- Testing guidelines
- Cross-platform rendering

Additional docs in [stagforge/docs/](./stagforge/docs/):
- [API Reference](./stagforge/docs/API.md)
- [Architecture](./stagforge/docs/ARCHITECTURE.md)
- [Tools](./stagforge/docs/TOOLS.md)
- [Testing](./stagforge/docs/TESTING.md)
- [Vector Rendering](./stagforge/docs/VECTOR_RENDERING.md)

## Publishing

```bash
# Publish imagestag to PyPI (poetry delegates to maturin for Rust)
poetry build
poetry publish

# Publish stagforge to PyPI (uses setuptools for flat layout + assets)
cd stagforge
pip install build
python -m build
twine upload dist/*
```

**Note:** ImageStag uses maturin (via poetry) for Rust compilation. Stagforge uses setuptools because its Python files are at the package root (flat layout), which poetry doesn't support.

## Licensing

- **imagestag**: MIT License - fully permissive
- **stagforge**: Elastic License 2.0 - no hosted service offering
