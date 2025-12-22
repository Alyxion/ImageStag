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

# Add a new dependency
poetry add <package>
```

## Architecture

- **Package Manager**: Poetry
- **Python Version**: 3.12+
- **Main Package**: `imagestag/`
- **Tests**: `tests/`

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