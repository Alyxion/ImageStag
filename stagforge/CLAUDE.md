# Stagforge Image Editor

Browser-based image editor built on ImageStag. Licensed under Elastic License 2.0.

## Quick Start

```bash
# From the repository root (/projects/ImageStag)
poetry install
poetry run python -m stagforge.main
# Opens http://localhost:8080 with hot reload
```

## Development Commands

```bash
# Run the editor
poetry run python -m stagforge.main

# Run stagforge tests
poetry run pytest tests/stagforge/

# Run a specific test
poetry run pytest tests/stagforge/test_vector_layer_bounds.py -v
```

### Poetry "Broken Virtualenv" Bug

If you see `The virtual environment found in . seems to be broken`, this is a [known Poetry bug](https://github.com/python-poetry/poetry/issues/10610) caused by the `VIRTUAL_ENV` environment variable. Fix it by unsetting the variable:

```bash
unset VIRTUAL_ENV
poetry install
```

## Architecture
- **JS-first**: Canvas/layer logic runs entirely in browser
- **Python backend**: Optional filters via FastAPI (skimage, OpenCV, PIL)
- **No local file access**: Images loaded from backend sources only
- **Modular tools**: One file per tool, registry-based extensibility
- **Raw transfer**: Uncompressed RGBA bytes for filter I/O (no Base64)
- **API-first**: ALL tools and features MUST be accessible via REST API
- **Multi-document**: Multiple documents open simultaneously, each with independent history/layers
- **High-quality rendering**: Bicubic interpolation for zoom, anti-aliased brush strokes

## Development
- NiceGUI hot-reloads on code changes (JS, CSS, Python)
- Port 8080, never needs restart (except adding packages)
- Use chrome-mcp for debugging

## Adding Tools (JS)

**IMPORTANT: All tools MUST implement `executeAction(action, params)` for API access.**

1. Create `frontend/js/tools/MyTool.js` extending Tool base class
2. Define static properties: `id`, `name`, `icon`, `shortcut`, `cursor`
3. Override mouse/keyboard handlers for interactive use
4. **Implement `executeAction(action, params)` for programmatic/API use**
5. Import and register in `canvas_editor.js`

Example tool with API support:
```javascript
import { Tool } from './Tool.js';

export class MyTool extends Tool {
    static id = 'mytool';
    static name = 'My Tool';
    static icon = 'star';
    static shortcut = 't';

    // Interactive mouse handlers
    onMouseDown(e, x, y) { /* ... */ }
    onMouseUp(e, x, y) { /* ... */ }

    // API execution - REQUIRED for all tools
    executeAction(action, params) {
        if (action === 'draw') {
            // Perform the action
            return { success: true };
        }
        return { success: false, error: 'Unknown action' };
    }
}
```

## Adding Filters (Python)
1. Create class extending `BaseFilter` in `stagforge/filters/`
2. Use `@register_filter("filter_id")` decorator
3. Implement `apply(image: np.ndarray, **params) -> np.ndarray`

## Adding Image Sources
1. Create provider class in `stagforge/images/`
2. Use `@register_provider("source_id")` decorator
3. Implement `list_images()` and `get_image(id)`

## File Structure Convention
- One class per file
- Tools in `frontend/js/tools/`
- Filters in `stagforge/filters/`
- UI components in `frontend/js/ui/`
- Core canvas logic in `frontend/js/core/`

### Core Classes (`frontend/js/core/`)
- **Document.js** - Single document with its own LayerStack, History, colors, view state
- **DocumentManager.js** - Manages multiple open documents, tab switching, close prompts
- **Layer.js** - Individual layer with canvas, opacity, blend mode
- **LayerGroup.js** - Container for organizing layers into folders (see [LAYERS.md](docs/LAYERS.md))
- **LayerStack.js** - Layer ordering, groups, active layer selection, merge/flatten
- **Renderer.js** - Composites layers to display canvas with zoom/pan
- **History.js** - Undo/redo with automatic pixel diff detection
- **Clipboard.js** - Cut/copy/paste with selection support

## API Endpoints

**Full API documentation: [docs/API.md](docs/API.md)**

### URL Structure
```
/api/sessions/{session}/documents/{doc}/image         # Composite image
/api/sessions/{session}/documents/{doc}/layers/{layer}/image  # Layer image
/api/sessions/{session}/documents/{doc}/tools/{tool}/execute  # Tool execution
/api/sessions/{session}/documents/{doc}/command       # Commands
```

Use `current` for active session/document/layer. Supports ID, name, or index.

### Image Retrieval API
Get images with format and background options:

```bash
# WebP (default, transparent)
GET /api/sessions/current/documents/current/image

# PNG with white background
GET /api/sessions/current/documents/current/image?format=png&bg=%23FFFFFF

# AVIF (best compression)
GET /api/sessions/current/documents/current/image?format=avif

# Layer with effects
GET /api/sessions/current/documents/current/layers/0/image?format=png

# Vector layer as SVG
GET /api/sessions/current/documents/current/layers/0/image?format=svg

# Vector shapes as JSON
GET /api/sessions/current/documents/current/layers/0/image?format=json
```

**Query Parameters:**
| Parameter | Default | Values |
|-----------|---------|--------|
| `format` | `webp` | `webp`, `avif`, `png`, `svg`, `json` |
| `bg` | (transparent) | Color like `%23FFFFFF` |

**Notes:**
- Layer effects (drop shadow, stroke, glow) are automatically applied
- Use `%23` to URL-encode `#` in query strings
- `svg`/`json` formats only work for vector layers

### Tool Execution API
```
POST /api/sessions/{s}/documents/{d}/tools/{tool}/execute
{"action": "draw", "params": {...}}
```

### Command API
```
POST /api/sessions/{s}/documents/{d}/command
{"command": "undo", "params": {}}
```

### Data Cache API
```
GET /api/upload/stats  # Cache statistics
```

## Binary Protocol (Filter I/O)
Request: `[4 bytes metadata length (LE)][JSON metadata][raw RGBA bytes]`
Response: `[raw RGBA bytes]` (same dimensions as input)

## Keyboard Shortcuts
- **Selection Tools**: M (selection), L (lasso), W (magic wand)
- **Drawing Tools**: V (move), B (brush), A (spray/airbrush), E (eraser)
- **Shape Tools**: L (line), R (rect), C (circle/crop), P (polygon)
- **Other Tools**: G (gradient/fill), T (text), I (eyedropper)
- **Edit**: Ctrl+Z (undo), Ctrl+Y/Ctrl+Shift+Z (redo)
- **Clipboard**: Ctrl+C (copy from layer), Ctrl+Shift+C (copy merged from all layers), Ctrl+X (cut), Ctrl+V (paste), Ctrl+Shift+V (paste in place)
- **Selection**: Ctrl+A (select all), Ctrl+D (deselect), Delete (clear selection)
- **Colors**: X (swap FG/BG), D (reset to black/white)

## Multi-Document Support

The editor supports multiple documents open simultaneously, similar to GIMP and Photoshop.

### Features
- **Document tabs**: Tab bar shows all open documents
- **Independent state**: Each document has its own layers, history, colors, and view state
- **Tab interactions**:
  - Click tab to switch documents
  - Middle-click tab to close
  - Click × button to close
  - Click + button to create new document
- **Modified indicator**: Documents with unsaved changes show a dot (•) after the name
- **Unsaved changes prompt**: Closing a modified document shows a confirmation dialog

### Document State
Each document maintains:
- LayerStack (all layers and their pixel data)
- History (independent undo/redo stack)
- Foreground/background colors
- View state (zoom level, pan position)
- Document dimensions (width × height)
- Modified flag

### Implementation
- `Document` class encapsulates all document state
- `DocumentManager` handles document lifecycle and switching
- When switching documents, the app context (layerStack, history, renderer) is updated to point to the new document's data

## Rendering Quality

The editor uses high-quality rendering techniques for professional results.

### Canvas Rendering
- **Bicubic interpolation**: `imageSmoothingQuality = 'high'` for zoom operations
- **Always smooth**: Image smoothing enabled at all zoom levels for best quality
- **Navigator preview**: High-quality scaled preview with live updates during drawing

### Brush Quality
- **Anti-aliased circles**: Brush stamps use `ctx.arc()` for proper circular shapes
- **Supersampling**: Small brushes (< 20px) rendered at 2x-4x resolution then downscaled
- **Smooth gradients**: Soft brushes use multi-stop radial gradients for natural falloff
- **Live preview**: Navigator updates every 100ms during brush strokes

## Layer Coordinate System

Layers can be positioned anywhere in the document using offset coordinates.

### Coordinate Spaces
- **Document coordinates**: Absolute position in the document (used by tools, selections)
- **Layer canvas coordinates**: Position relative to the layer's top-left corner

### Coordinate Conversion
```javascript
// Convert document coords to layer canvas coords
const localCoords = layer.docToCanvas(docX, docY);

// Convert layer canvas coords to document coords
const docCoords = layer.canvasToDoc(canvasX, canvasY);
```

### Layer Properties
- `layer.offsetX`, `layer.offsetY`: Layer position in document space
- `layer.width`, `layer.height`: Layer canvas dimensions
- Layers can be smaller than the document and positioned anywhere

### Tool Behavior with Offset Layers
- All tools receive document coordinates in mouse events
- Tools must convert to layer coordinates before drawing
- Operations outside layer bounds are clipped
- Selections are in document space, not layer space

### VectorLayer Auto-Fit

VectorLayers automatically resize their canvas to fit shape bounds:

- **Shapes stored in document coordinates** (not layer-relative)
- **Auto-fit on add/remove**: Canvas shrinks to bounding box + padding
- **Expand during editing**: Canvas grows to document size while dragging
- **Shrink on edit end**: Canvas shrinks back to fit content

This provides 97%+ memory savings for small shapes on large documents. See `docs/VECTOR_RENDERING.md` for detailed implementation notes and common pitfalls.

## Layer Effects Architecture

Layer effects (drop shadow, stroke, glow, etc.) are non-destructive visual effects applied to layers. The implementation follows a cross-platform architecture:

### Implementation Layers

1. **Rust (ImageStag)** - Core pixel manipulation in `/projects/ImageStag/rust/src/filters/`
2. **Python (ImageStag)** - OOP wrappers in `/projects/ImageStag/imagestag/layer_effects/`
3. **JavaScript (Stagforge)** - Effect classes in `frontend/js/effects/`

### Python API

```python
from imagestag.layer_effects import DropShadow, Stroke, OuterGlow

# Apply drop shadow
shadow = DropShadow(blur=5, offset_x=10, offset_y=10, color=(0, 0, 0))
result = shadow.apply(image_rgba)
# result.image = output array (may be larger than input)
# result.offset_x, result.offset_y = position shift
```

### Available Effects

| Effect | Description | Expands Canvas |
|--------|-------------|----------------|
| `DropShadow` | Shadow behind layer | Yes |
| `InnerShadow` | Shadow inside layer edges | No |
| `OuterGlow` | Glow radiating outward | Yes |
| `InnerGlow` | Glow radiating inward | No |
| `BevelEmboss` | 3D raised/sunken appearance | Outer only |
| `Stroke` | Outline around content | Outside/center only |
| `ColorOverlay` | Solid color overlay | No |

### Format Support

ALL effects MUST support these pixel formats:
- **RGB8**: uint8 (0-255), 3 channels
- **RGBA8**: uint8 (0-255), 4 channels
- **RGBf32**: float32 (0.0-1.0), 3 channels
- **RGBAf32**: float32 (0.0-1.0), 4 channels

### Adding New Effects

1. Implement Rust function in `/projects/ImageStag/rust/src/filters/lighting.rs`
2. Export from `lib.rs`
3. Create Python wrapper in `/projects/ImageStag/imagestag/layer_effects/`
4. Create JS class in `frontend/js/effects/`
5. Add parity tests
6. Rebuild Rust extension: `cd /projects/ImageStag && poetry run maturin develop --release --manifest-path rust/Cargo.toml`

### Parity Requirement

Python and JS effects MUST produce 99.9% pixel match (≤0.1% difference).

## Cross-Platform Rendering (CRITICAL)

**REQUIREMENT: Dynamic layers (text, vector) MUST render identically in JavaScript and Python.**

This is a core architectural requirement. Any feature that renders dynamic content must:
1. Produce pixel-identical output in both JS and Python
2. Be verified by automated pixel diff tests
3. Use the same algorithms (Lanczos downscaling, font rendering, etc.)

### Vector Layer Rendering via SVG

**All vector graphics MUST be representable as SVG.** See `docs/VECTOR_RENDERING.md` for full details.

- Temporary Canvas 2D rendering is acceptable during editing
- Final rasterization MUST use SVG rendering for cross-platform parity

**Reference Renderers (DO NOT CHANGE):**
- **JavaScript**: Chrome's native SVG renderer (via `<img>` element)
- **Python**: resvg (via `resvg-py` package)

These renderers are locked. Do NOT substitute with alternatives:
- No resvg-wasm, canvg, or other JS SVG libraries
- No CairoSVG, librsvg, svglib, or other Python SVG libraries

**Anti-aliasing:** Use `shape-rendering="crispEdges"` for cross-platform parity testing. Chrome and resvg have different AA algorithms causing 1-4% difference on curves/diagonals with AA enabled. With `crispEdges` (AA disabled), both produce identical output.

**Shape Types:** rect, ellipse, line, polygon, path

**Parity Requirement:** 99.9% pixel match (≤0.1% difference) between JS and Python

**Pixel Diff Algorithm:**
- A pixel is "different" if ANY RGBA channel differs by 5 or more (out of 255)
- Differences below 5 do not count as errors
- Differences >0.1% indicate a real rendering bug, NOT anti-aliasing
- **DO NOT increase the tolerance value** - fix the rendering instead

**Adding New Vector Elements:**
1. Add `toSVGElement()` to JS shape class
2. Add shape case to Python's `shape_to_svg_element()`
3. Add parity tests to `tests/test_vector_parity.py`
4. **All tests MUST pass before merge**

### Document Serialization

Documents can be fully transferred between JS and Python using JSON serialization:

```
POST /api/sessions/{id}/document/export  → Full document JSON
POST /api/sessions/{id}/document/import  ← Full document JSON
```

**Document Format:**
```json
{
  "version": "1.0",
  "id": "uuid",
  "name": "Document Name",
  "width": 800,
  "height": 600,
  "layers": [
    {
      "type": "raster",
      "id": "uuid",
      "name": "Layer 1",
      "offsetX": 0,
      "offsetY": 0,
      "opacity": 1.0,
      "blendMode": "normal",
      "visible": true,
      "imageData": "data:image/png;base64,..."
    },
    {
      "type": "text",
      "id": "uuid",
      "runs": [{"text": "Hello", "fontSize": 24, "color": "#000000"}],
      "fontSize": 24,
      "fontFamily": "Arial",
      ...
    },
    {
      "type": "vector",
      "id": "uuid",
      "shapes": [{"type": "rect", "x": 10, "y": 10, "width": 100, "height": 50, ...}],
      ...
    }
  ],
  "activeLayerIndex": 0,
  "foregroundColor": "#000000",
  "backgroundColor": "#FFFFFF"
}
```

### Python Rendering Module

The `stagforge/rendering/` module provides Python implementations that match JS rendering:

```
stagforge/rendering/
├── __init__.py          # Exports: render_text_layer, render_vector_layer, render_document, render_layer
├── text.py              # Text layer rendering with PIL + Lanczos-3 downscaling
├── vector.py            # Vector shapes via resvg (SVG rendering)
├── document.py          # Full document compositing, pixel diff utilities
└── lanczos.py           # Lanczos-3 resampling matching JS implementation
```

| Layer Type | Python Renderer | Algorithm |
|------------|-----------------|-----------|
| Text | PIL + Lanczos | 4x render + Lanczos-3 downscale |
| Vector | resvg | Convert shapes to SVG, render with resvg-py |
| Raster | Direct | Decode PNG data URL, no transformation |

### Rendering API Endpoints

Server-side rendering for parity testing:

```
POST /api/rendering/layer     # Render single layer to RGBA bytes
POST /api/rendering/document  # Render full document to RGBA bytes
POST /api/rendering/diff      # Compare two images, return diff metrics
```

### Pixel Diff Testing

All dynamic layer rendering must pass pixel diff tests:

```python
from stagforge.rendering import render_text_layer, render_vector_layer
from stagforge.rendering.document import compute_pixel_diff, images_match

# Render layer in Python
py_pixels = render_text_layer(layer_data, output_width=200, output_height=100)

# Compare with JS rendering
diff_ratio, diff_image = compute_pixel_diff(js_pixels, py_pixels)
assert images_match(js_pixels, py_pixels, tolerance=0.05)  # 95% match
```

### Rendering Parity Tests

Two test files ensure cross-platform rendering consistency:

**`tests/test_rendering_parity.py`** - Unit tests (no browser required):
- `TestLanczosResampling` - Lanczos-3 algorithm correctness
- `TestTextRendering` - Text layer output validation
- `TestVectorRendering` - Vector shapes (rect, ellipse, line, polygon)
- `TestDocumentRendering` - Layer compositing, opacity, visibility
- `TestPixelDiff` - Diff utility functions

**`tests/test_rendering_parity_integration.py`** - Browser integration tests:
- `TestTextLayerParity` - JS vs Python text rendering comparison
- `TestVectorLayerParity` - JS vs Python vector rendering comparison
- `TestDocumentParity` - Full document export/render comparison
- `TestRenderingAPI` - Server-side rendering API validation

### Adding New Dynamic Layer Types

When adding a new dynamic (non-raster) layer type:

1. Implement JS renderer in `frontend/js/core/`
2. Implement Python renderer in `stagforge/rendering/`
3. Add unit tests in `tests/test_rendering_parity.py`
4. Add integration tests in `tests/test_rendering_parity_integration.py`
5. Document the rendering algorithm in this file
6. **All tests MUST pass before the feature is considered complete**

## Testing

### Test Framework
Tests use Selenium WebDriver with a unified helper system in `tests/helpers/`:

- **EditorTestHelper**: Browser interaction, canvas events, tool selection
- **PixelHelper**: Pixel extraction, checksums, color counting
- **ToolHelper**: Tool-specific operations (brush, shapes, etc.)
- **LayerHelper**: Layer creation, manipulation, properties
- **SelectionHelper**: Selection operations, clipboard

### Running Tests
```bash
pytest tests/                                    # All tests
pytest tests/test_tools_*.py                    # Tool tests only
pytest tests/test_rendering_parity.py -v        # Python rendering unit tests (no browser)
pytest tests/test_rendering_parity_playwright.py -v  # JS/Python parity tests (uses Playwright)
pytest -k "brush"                                # Tests matching pattern
```

### Browser-Based Parity Tests (Playwright)

The `test_rendering_parity_playwright.py` tests use **Playwright** to run JavaScript in a real browser and compare output with Python rendering. Playwright bundles its own Chromium, so no external driver needed.

**Setup:**
```bash
pip install playwright pytest-playwright
playwright install chromium
```

**What these tests verify:**
- Canvas shapes (rect, ellipse, line) render identically in JS and Python
- Text rendering produces similar output
- Lanczos downscaling preserves content in both

**Note on ARM64 Linux:** PIL must be installed for ARM64. If system PIL is x86_64, install to a local path:
```bash
pip install --target=/tmp/pylibs pillow
PYTHONPATH=/tmp/pylibs:$PYTHONPATH pytest tests/test_rendering_parity_playwright.py -v
```

### Testing Principles

**CRITICAL: Always use range-based assertions for pixel counts, never just "it changed".**

#### Expected Pixel Counts

Calculate expected pixels from geometry with appropriate tolerance:

| Shape | Formula | Default Tolerance |
|-------|---------|-------------------|
| Line/stroke | length × width | ±30% |
| Rectangle | width × height | ±10% |
| Circle | π × r² | ±20% |
| Ellipse | π × a × b | ±20% |
| Outline | perimeter × stroke | ±30% |
| Diagonal line | √(Δx² + Δy²) × width | ±35% |

#### Assertion Helpers

```python
from tests.helpers import (
    approx_line_pixels,
    approx_rect_pixels,
    approx_circle_pixels,
    assert_pixel_count_in_range,
    assert_pixel_count_exact,
)

# Range assertions for drawing operations
min_px, max_px = approx_line_pixels(length=100, width=4)
assert min_px <= actual <= max_px

# Exact assertions for undo/redo
assert_pixel_count_exact(after_undo, 0, "Undo should restore empty canvas")
```

#### When to Use Each Assertion Type

**Range assertions** (most common):
- After drawing any shape or stroke
- After erasing content
- After clipboard paste

**Exact assertions**:
- Undo/redo must restore exactly to previous state
- Operations outside layer bounds must produce 0 pixels
- Layer fill must produce exact width × height pixels

#### Example Test Pattern

```python
def test_brush_horizontal_stroke(self, helpers):
    helpers.new_document(200, 200)

    brush_size = 10
    stroke_length = 100  # from (50, 100) to (150, 100)

    helpers.tools.brush_stroke(
        [(50, 100), (150, 100)],
        color='#FF0000',
        size=brush_size
    )

    red_pixels = helpers.pixels.count_pixels_with_color(
        (255, 0, 0, 255), tolerance=10
    )

    # Expected: 100 × 10 = 1000 pixels, ±30% = 700-1300
    min_expected, max_expected = approx_line_pixels(stroke_length, brush_size)

    assert min_expected <= red_pixels <= max_expected, \
        f"Expected {min_expected}-{max_expected} pixels, got {red_pixels}"
```

#### Testing Offset Layers

Always test tools with layers at different positions:

```python
def test_brush_on_offset_layer(self, helpers):
    helpers.new_document(400, 400)

    # Create layer NOT at origin
    layer_id = helpers.layers.create_offset_layer(
        offset_x=200, offset_y=200,
        width=150, height=150
    )

    # Draw in document coordinates
    helpers.tools.brush_stroke([(250, 275), (320, 275)], color='#FF0000')

    # Verify on the specific layer
    pixels = helpers.pixels.count_pixels_with_color(
        (255, 0, 0, 255), tolerance=10, layer_id=layer_id
    )

    # Calculate expected based on portion inside layer
    # ...
```

### Test Categories

- `test_tools_brush_eraser.py` - Brush/eraser with offset layers
- `test_tools_shapes.py` - Line/rect/circle with offset layers
- `test_tools_selection.py` - Selection tools with offset layers
- `test_clipboard.py` - Copy/cut/paste with offset layers
- `test_layers.py` - Layer operations
- `test_rendering_parity.py` - Python rendering unit tests (21 tests, no browser)
- `test_rendering_parity_playwright.py` - JS/Python parity tests via Playwright (7 tests)
- `test_vector_parity.py` - Vector layer JS/Python SVG rendering parity (requires Playwright)
