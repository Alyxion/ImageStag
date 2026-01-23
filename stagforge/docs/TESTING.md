# Testing Guide

## Overview

Stagforge has two testing frameworks:

1. **Playwright (Async)** - New framework with `helpers_pw/` module for comprehensive UI testing
2. **Playwright (Sync)** - Legacy `screen` fixture for simpler tests

Both frameworks run against the live editor in a headless Chromium browser.

## Running Tests

```bash
# Run all stagforge tests
poetry run pytest tests/stagforge/

# Run Playwright async tests only
poetry run pytest tests/stagforge/test_*_pw.py -v

# Run specific test file
poetry run pytest tests/stagforge/test_clipboard_pw.py -v

# Run tests matching pattern
poetry run pytest -k "brush" -v

# Run without auto-starting server (use existing server)
STAGFORGE_TEST_SERVER=0 poetry run pytest tests/stagforge/test_*_pw.py -v
```

**Note:** For browser integration tests, either let the test fixture start the server automatically, or run it manually at `localhost:8080`:
```bash
poetry run python -m stagforge.main
```

---

## Playwright Async Framework (`helpers_pw/`)

The new async Playwright framework provides comprehensive test helpers for UI automation.

### Test File Naming

Playwright async tests use the `_pw.py` suffix:
- `test_clipboard_pw.py`
- `test_layers_pw.py`
- `test_tools_brush_eraser_pw.py`
- etc.

### Helper Modules

```
tests/stagforge/helpers_pw/
├── __init__.py      # TestHelpers class combining all helpers
├── editor.py        # EditorTestHelper - Browser interaction, canvas events
├── pixels.py        # PixelHelper - Pixel extraction, checksums, counting
├── tools.py         # ToolHelper - Tool-specific operations
├── layers.py        # LayerHelper - Layer creation, manipulation
├── selection.py     # SelectionHelper - Selection and clipboard
└── assertions.py    # Pixel counting assertion utilities
```

### Basic Test Pattern

```python
import pytest
from .helpers_pw import TestHelpers

pytestmark = pytest.mark.asyncio

class TestMyFeature:
    async def test_example(self, helpers: TestHelpers):
        # Create a new document
        await helpers.new_document(200, 200)

        # Draw something
        await helpers.tools.brush_stroke(
            [(50, 50), (150, 150)],
            color='#FF0000',
            size=10
        )

        # Verify pixels
        red_pixels = await helpers.pixels.count_pixels_with_color(
            (255, 0, 0, 255), tolerance=10
        )
        assert red_pixels > 0

        # Test undo
        await helpers.undo()
        after_undo = await helpers.pixels.count_non_transparent_pixels()
        assert after_undo == 0
```

### Fixtures

The `conftest_pw.py` provides these fixtures:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `browser` | session | Chromium browser instance |
| `context` | function | Fresh browser context per test |
| `page` | function | Fresh page per test |
| `helpers` | function | TestHelpers with editor navigation |
| `server_process` | session | Auto-starts server (set `STAGFORGE_TEST_SERVER=0` to skip) |

### TestHelpers API

```python
class TestHelpers:
    editor: EditorTestHelper    # Browser/canvas interaction
    pixels: PixelHelper         # Pixel extraction and verification
    tools: ToolHelper           # Tool operations
    layers: LayerHelper         # Layer management
    selection: SelectionHelper  # Selection and clipboard

    # Convenience methods
    async def new_document(width, height)
    async def undo()
    async def redo()
```

### EditorTestHelper Methods

| Method | Description |
|--------|-------------|
| `navigate_to_editor()` | Navigate and wait for editor initialization |
| `execute_js(script)` | Execute JavaScript in the browser |
| `doc_to_screen(doc_x, doc_y)` | Convert document to screen coordinates |
| `click_at_doc(x, y)` | Click at document coordinates |
| `drag_at_doc(x1, y1, x2, y2)` | Drag in document coordinates |
| `draw_stroke(points)` | Draw a stroke through points |
| `select_tool(tool_id)` | Select a tool |
| `set_foreground_color(hex)` | Set foreground color |
| `press_key(key, ctrl, shift, alt)` | Press keyboard key |
| `new_document(w, h)` | Create new document |
| `get_layer_info(layer_id)` | Get layer info dict |

### PixelHelper Methods

| Method | Description |
|--------|-------------|
| `get_layer_image_data(layer_id)` | Get layer as numpy array |
| `get_composite_image_data()` | Get composited image |
| `get_pixel(x, y)` | Get (R, G, B, A) at coordinates |
| `compute_checksum(layer_id)` | MD5 checksum for comparison |
| `count_pixels_with_color(rgba, tolerance)` | Count matching pixels |
| `count_non_transparent_pixels()` | Count non-transparent pixels |
| `get_average_brightness()` | Get average luminance |
| `get_bounding_box_of_content()` | Find content bounds |

### ToolHelper Methods

| Method | Description |
|--------|-------------|
| `brush_stroke(points, color, size)` | Draw brush stroke |
| `brush_dot(x, y, color, size)` | Single brush dot |
| `eraser_stroke(points, size)` | Erase along path |
| `draw_line(x1, y1, x2, y2, color, width)` | Draw line |
| `draw_filled_rect(x, y, w, h, color)` | Draw filled rectangle |
| `draw_filled_circle(cx, cy, r, color)` | Draw filled circle |
| `pencil_stroke(points, color, size)` | Aliased pencil stroke |
| `smudge_stroke(points, size, strength)` | Smudge tool |
| `blur_stroke(points, size, strength)` | Blur tool |
| `dodge_stroke(points, size, exposure)` | Lighten areas |
| `burn_stroke(points, size, exposure)` | Darken areas |
| `clone_stamp_set_source(x, y)` | Set clone source |
| `clone_stamp_stroke(points, size)` | Paint with clone stamp |

### LayerHelper Methods

| Method | Description |
|--------|-------------|
| `create_layer(name, width, height)` | Create new layer |
| `create_offset_layer(offset_x, offset_y, width, height)` | Create positioned layer |
| `create_filled_layer(color, width, height, offset_x, offset_y)` | Create pre-filled layer |
| `delete_layer(layer_id)` | Delete layer |
| `duplicate_layer(layer_id)` | Duplicate layer |
| `fill_layer_with_color(color, layer_id)` | Fill layer with color |
| `set_layer_offset(x, y, layer_id)` | Set layer position |
| `set_layer_opacity(opacity, layer_id)` | Set layer opacity |
| `merge_down(layer_id)` | Merge layer down |
| `flatten_all()` | Flatten all layers |

### SelectionHelper Methods

| Method | Description |
|--------|-------------|
| `select_rect(x, y, w, h)` | Select via mouse drag |
| `select_rect_api(x, y, w, h)` | Select via API (precise) |
| `select_all()` | Select entire document |
| `clear_selection()` | Clear selection |
| `has_selection()` | Check if selection exists |
| `get_selection_bounds()` | Get (x, y, w, h) tuple |
| `copy()` / `cut()` / `paste()` | Clipboard operations |
| `delete_selection_content()` | Delete selection area |
| `select_by_color(x, y, tolerance)` | Magic wand select |

---

## Pixel Assertion Helpers

Use range-based assertions for pixel counts to account for antialiasing:

```python
from .helpers_pw import approx_line_pixels, approx_rect_pixels, approx_circle_pixels

# Line assertion
min_px, max_px = approx_line_pixels(length=100, width=10, tolerance=0.30)
assert min_px <= actual <= max_px

# Rectangle assertion
min_px, max_px = approx_rect_pixels(width=50, height=50, tolerance=0.10)
assert min_px <= actual <= max_px

# Circle assertion
min_px, max_px = approx_circle_pixels(radius=25, tolerance=0.20)
assert min_px <= actual <= max_px
```

### Expected Pixel Calculations

| Shape | Formula | Default Tolerance |
|-------|---------|-------------------|
| Line/stroke | length × width | ±30% |
| Rectangle | width × height | ±10% |
| Circle | π × r² | ±20% |
| Ellipse | π × a × b | ±20% |
| Outline | perimeter × stroke | ±30% |
| Diagonal | √(Δx² + Δy²) × width | ±35% |

### When to Use Each Assertion Type

**Range assertions** (most common):
- After drawing any shape or stroke
- After erasing content
- After clipboard paste

**Exact assertions**:
- Undo/redo must restore exactly to previous state
- Operations outside layer bounds must produce 0 pixels
- Layer fill must produce exact width × height pixels

---

## Testing Offset Layers

Always test tools with layers at different positions:

```python
async def test_brush_on_offset_layer(self, helpers: TestHelpers):
    await helpers.new_document(400, 400)

    # Create layer NOT at origin
    layer_id = await helpers.layers.create_offset_layer(
        offset_x=200, offset_y=200,
        width=150, height=150
    )

    # Draw in document coordinates (tools always use doc coords)
    await helpers.tools.brush_stroke(
        [(250, 275), (320, 275)],
        color='#FF0000',
        size=10
    )

    # Verify on the specific layer
    pixels = await helpers.pixels.count_pixels_with_color(
        (255, 0, 0, 255), tolerance=10, layer_id=layer_id
    )

    # Calculate expected based on portion inside layer bounds
    min_expected, max_expected = approx_line_pixels(70, 10, tolerance=0.35)
    assert min_expected <= pixels <= max_expected
```

---

## Legacy Screen Fixture (Sync API)

The `screen` fixture provides a simpler NiceGUI Screen-like API for basic tests:

```python
def test_example(screen):
    # Navigate to the editor
    screen.open('/')
    screen.wait_for_editor()

    # Execute JavaScript
    result = screen.page.evaluate("""
        () => window.__stagforge_app__.layerStack.layers.length
    """)

    # Assert content
    screen.should_contain('Canvas')
```

### Screen API Reference

| Method | Description |
|--------|-------------|
| `open(path)` | Navigate to a path |
| `wait_for_editor()` | Wait for editor initialization |
| `should_contain(text)` | Assert page contains text |
| `wait(seconds)` | Wait for duration |
| `click(selector)` | Click element |
| `page` | Direct Playwright Page access |

---

## Accessing Editor State

The editor exposes state via `window.__stagforge_app__`:

```javascript
const app = window.__stagforge_app__;

// Document Manager
app.documentManager.getActiveDocument()  // Current document
app.documentManager.documents            // All documents

// Layer Stack
app.layerStack.layers        // Array of layers
app.layerStack.width         // Document width

// Tools
app.toolManager.currentTool  // Current tool
app.toolManager.select('brush')

// History
app.history.undo()
app.history.redo()
```

### Window-Exposed Classes

| Global | Description |
|--------|-------------|
| `window.__stagforge_app__` | Main application instance |
| `window.VectorLayer` | VectorLayer class |
| `window.TextLayer` | TextLayer class |
| `window.createVectorShape` | Shape factory function |
| `window.LayerEffects` | Effects module |
| `window.sessionId` | Current session ID |

---

## Test Categories

### Playwright Async Tests (`*_pw.py`)

| File | Purpose |
|------|---------|
| `test_clipboard_pw.py` | Copy/cut/paste with offset layers |
| `test_layers_pw.py` | Layer operations |
| `test_tools_brush_eraser_pw.py` | Brush/eraser with offset layers |
| `test_tools_shapes_pw.py` | Line/rect/circle with offset layers |
| `test_tools_painting_pw.py` | Pencil, smudge, blur, dodge, burn, etc. |
| `test_tools_selection_pw.py` | Selection tools with offset layers |
| `test_ui_brush_preset_pw.py` | Brush preset menu UI |

### Other Tests

| File | Purpose |
|------|---------|
| `test_rendering_parity.py` | Python rendering unit tests (no browser) |
| `test_vector_parity.py` | JS/Python SVG rendering parity |
| `test_sfr_browser_integration.py` | SFR file format browser tests |
| `test_layer_effects.py` | Layer effects via Playwright sync |
| `test_api.py` | REST API tests |

---

## Debugging Test Failures

### Take Screenshot

```python
async def test_with_screenshot(self, helpers: TestHelpers):
    await helpers.new_document(200, 200)

    try:
        # Test code
        await helpers.tools.brush_stroke([(50, 50), (150, 150)])
        assert False  # Force failure
    except AssertionError:
        await helpers.editor.page.screenshot(path="test_failure.png")
        raise
```

### Inspect App State

```python
async def test_debug_state(self, helpers: TestHelpers):
    await helpers.new_document(200, 200)

    state = await helpers.editor.execute_js("""
        (() => {
            const app = window.__stagforge_app__;
            return {
                hasApp: !!app,
                layerCount: app?.layerStack?.layers?.length,
                currentTool: app?.toolManager?.currentTool?.id
            };
        })()
    """)
    print("App state:", state)
```

### Check Console Errors

```python
async def test_with_console(self, helpers: TestHelpers):
    # Capture console messages
    logs = []
    helpers.editor.page.on("console", lambda msg: logs.append(msg.text))

    await helpers.new_document(200, 200)
    await helpers.tools.brush_stroke([(50, 50), (150, 150)])

    # Check for errors
    errors = [l for l in logs if "error" in l.lower()]
    assert len(errors) == 0, f"Console errors: {errors}"
```

---

## Writing New Tests

### Checklist

1. Use `helpers_pw` fixture for new async tests
2. Use `async def` methods with `await` calls
3. Add `pytestmark = pytest.mark.asyncio` at module level
4. Use range-based assertions for pixel counts
5. Test with offset layers, not just origin-positioned layers
6. Verify undo/redo restores exact state
7. Clean up resources (layers created during test)

### Example: Complete Test Class

```python
import pytest
from .helpers_pw import TestHelpers, approx_line_pixels

pytestmark = pytest.mark.asyncio

class TestMyTool:
    async def test_tool_draws_expected_pixels(self, helpers: TestHelpers):
        """Test tool produces expected pixel count."""
        await helpers.new_document(200, 200)

        await helpers.tools.my_tool_stroke(
            [(50, 100), (150, 100)],
            color='#FF0000',
            size=10
        )

        red_pixels = await helpers.pixels.count_pixels_with_color(
            (255, 0, 0, 255), tolerance=10
        )

        min_expected, max_expected = approx_line_pixels(100, 10)
        assert min_expected <= red_pixels <= max_expected

    async def test_tool_on_offset_layer(self, helpers: TestHelpers):
        """Test tool works correctly on offset layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=200, offset_y=200,
            width=150, height=150
        )

        await helpers.tools.my_tool_stroke(
            [(250, 275), (320, 275)],
            color='#00FF00',
            size=10
        )

        pixels = await helpers.pixels.count_pixels_with_color(
            (0, 255, 0, 255), tolerance=10, layer_id=layer_id
        )

        assert pixels > 0

    async def test_undo_restores_exact_state(self, helpers: TestHelpers):
        """Test undo restores exact pixel count."""
        await helpers.new_document(200, 200)

        initial = await helpers.pixels.count_non_transparent_pixels()

        await helpers.tools.my_tool_stroke([(50, 50), (150, 150)])
        after_draw = await helpers.pixels.count_non_transparent_pixels()
        assert after_draw > initial

        await helpers.undo()
        after_undo = await helpers.pixels.count_non_transparent_pixels()

        assert after_undo == initial, \
            f"Undo should restore exact state: {initial} vs {after_undo}"
```
