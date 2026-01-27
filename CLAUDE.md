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
