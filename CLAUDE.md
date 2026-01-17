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
│   ├── filters/         # Image filters
│   ├── layer_effects/   # Effect classes
│   ├── components/      # UI components
│   └── streams/         # Video/camera streams
├── stagforge/           # Image editor (ELv2)
│   ├── api/             # REST API
│   ├── frontend/        # JS/CSS frontend
│   ├── rendering/       # Python rendering
│   └── CLAUDE.md        # Stagforge dev guide
├── rust/                # Rust extensions
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
