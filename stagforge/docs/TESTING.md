# Testing Guide

## Overview

Stagforge uses Playwright-based testing with a custom `Screen` fixture that mimics NiceGUI's testing API. Tests run against the live editor in a headless Chromium browser.

## Running Tests

```bash
# Run all stagforge tests
poetry run pytest tests/stagforge/

# Run specific test file
poetry run pytest tests/stagforge/test_vector_layer_bounds.py -v

# Run tests matching pattern
poetry run pytest -k "vector" -v

# Run SFR serialization tests (browser-based)
poetry run pytest tests/stagforge/test_sfr_browser_integration.py -v
```

**Note:** For browser integration tests, the dev server must be running at `localhost:8080`:
```bash
poetry run python -m stagforge.main
```

## Screen Fixture

The `screen` fixture provides a NiceGUI Screen-like API using Playwright:

```python
def test_example(screen):
    # Navigate to the editor
    screen.open('/')
    screen.wait_for_editor()

    # Assert content
    screen.should_contain('Canvas')
    screen.should_not_contain('Error')

    # Wait
    screen.wait(0.5)

    # Interact with elements
    screen.click('.some-button')
    screen.type('input[name="width"]', '800')

    # Execute JavaScript
    result = screen.page.evaluate("() => window.__stagforge_app__.layerStack.layers.length")
```

### Screen API Reference

| Method | Description |
|--------|-------------|
| `open(path)` | Navigate to a path (e.g., `'/'`) |
| `wait_for_editor()` | Wait for CanvasEditor to fully initialize |
| `should_contain(text)` | Assert page contains text |
| `should_not_contain(text)` | Assert page does not contain text |
| `wait(seconds)` | Wait for duration |
| `click(selector)` | Click element |
| `type(selector, text)` | Type into input |
| `find(selector)` | Find single element |
| `find_all(selector)` | Find all matching elements |
| `execute_script(js)` | Execute JavaScript (returns result) |
| `page` | Direct access to Playwright Page object |

## Accessing the Editor

The CanvasEditor Vue component exposes state via `window.__stagforge_app__`:

```javascript
// In page.evaluate():
const app = window.__stagforge_app__;

// Access document manager
app.documentManager.getActiveDocument()  // Current document (use method, not getter)
app.documentManager.documents            // All open documents

// Access layer stack
app.layerStack.layers        // Array of layers
app.layerStack.width         // Document width
app.layerStack.height        // Document height

// Access tools
app.toolManager.currentTool  // Current tool instance
app.toolManager.select('brush')  // Select a tool

// Access history
app.history.undo()
app.history.redo()

// Access renderer
app.renderer.zoom            // Current zoom level
app.renderer.requestRender() // Force re-render

// Access file manager
app.fileManager.save()              // Save to current file
app.fileManager.saveAs()            // Save with file picker
app.fileManager.serializeDocument() // Get SFR JSON (async)
```

### Important: Document Access

Always use `getActiveDocument()` method, not `activeDocument` getter:

```javascript
// CORRECT:
const doc = app.documentManager.getActiveDocument();

// INCORRECT (returns null):
const doc = app.documentManager.activeDocument;
```

## Window-Exposed Classes

These classes are exposed on `window` for testing:

| Global | Description |
|--------|-------------|
| `window.__stagforge_app__` | Main application instance |
| `window.VectorLayer` | VectorLayer class for creating vector layers |
| `window.TextLayer` | TextLayer class for creating text layers |
| `window.createVectorShape` | Factory function for vector shapes |
| `window.LayerEffects` | Layer effects module with `effectRegistry` |
| `window.sessionId` | Current session ID |

## Creating Vector Shapes

Use `window.createVectorShape()` to create shapes programmatically:

```python
result = screen.page.evaluate("""
    () => {
        const app = window.__stagforge_app__;
        const VectorLayer = window.VectorLayer;

        // Create vector layer
        const layer = new VectorLayer({
            name: 'My Vector Layer',
            width: app.layerStack.width,
            height: app.layerStack.height
        });

        // Set document dimensions for proper offset handling
        layer._docWidth = app.layerStack.width;
        layer._docHeight = app.layerStack.height;

        // Create a shape (type must be in the object)
        const circle = window.createVectorShape({
            type: 'ellipse',
            cx: 100, cy: 100,
            rx: 50, ry: 50,
            fill: true,
            fillColor: '#FF0000',
            stroke: true,
            strokeColor: '#000000',
            strokeWidth: 2,
            opacity: 1.0
        });

        layer.addShape(circle);
        app.layerStack.addLayer(layer);

        // Get bounds
        const bounds = layer.getShapesBounds();
        return { layerId: layer.id, bounds };
    }
""")
```

### Available Shape Types

| Type | Required Properties |
|------|---------------------|
| `rect` | `x`, `y`, `width`, `height` |
| `ellipse` | `cx`, `cy`, `rx`, `ry` |
| `line` | `x1`, `y1`, `x2`, `y2` |
| `polygon` | `points` (array of `[x, y]`) |
| `path` | `points` (array of point objects with handles) |

### Common Shape Properties

All shapes support:
- `fill` (boolean) - Whether to fill
- `fillColor` (string) - Fill color hex
- `stroke` (boolean) - Whether to stroke
- `strokeColor` (string) - Stroke color hex
- `strokeWidth` (number) - Stroke width in pixels
- `opacity` (number) - 0.0 to 1.0

## Adding Layer Effects

Use `window.LayerEffects.effectRegistry` to access effect classes:

```python
result = screen.page.evaluate("""
    () => {
        const app = window.__stagforge_app__;
        const LayerEffects = window.LayerEffects;

        // Get a layer
        const layer = app.layerStack.layers[0];

        // Create an effect from the registry
        const DropShadow = LayerEffects.effectRegistry['dropShadow'];
        const shadow = new DropShadow({
            offsetX: 10,
            offsetY: 10,
            blur: 15,
            color: '#000000',
            opacity: 0.5
        });

        // Add effect to layer
        layer.addEffect(shadow);

        // Request re-render
        app.renderer.requestRender();

        return { effectCount: layer.effects.length };
    }
""")
```

### Available Effect Types

| Effect Type | Key Properties |
|-------------|----------------|
| `dropShadow` | `offsetX`, `offsetY`, `blur`, `color`, `opacity` |
| `innerShadow` | `offsetX`, `offsetY`, `blur`, `color`, `opacity` |
| `outerGlow` | `blur`, `color`, `opacity`, `spread` |
| `innerGlow` | `blur`, `color`, `opacity`, `source` |
| `bevelEmboss` | `style`, `depth`, `size`, `angle`, `altitude` |
| `stroke` | `size`, `position`, `color`, `opacity` |
| `colorOverlay` | `color`, `opacity` |

## Testing Async Operations

For async operations (serialization, deserialization), use `async () => {}`:

```python
result = screen.page.evaluate("""
    async () => {
        const app = window.__stagforge_app__;

        // Document.serialize() is async
        const doc = app.documentManager.getActiveDocument();
        const serialized = await doc.serialize();

        // FileManager.serializeDocument() is async
        const sfrData = await app.fileManager.serializeDocument();

        return { layers: serialized.layers.length };
    }
""")
```

## Test Categories

| File | Purpose |
|------|---------|
| `test_sfr_browser_integration.py` | SFR file format browser tests |
| `test_sfr_serialization.py` | Unit tests for serialization |
| `test_sfr_effects_roundtrip.py` | Effects serialization tests |
| `test_vector_layer_bounds.py` | Vector layer bounding box tests |
| `test_vector_parity.py` | JS/Python SVG rendering parity |
| `test_rendering_parity.py` | Python rendering unit tests |
| `test_tools_*.py` | Tool-specific tests |
| `test_layers.py` | Layer operations |
| `test_clipboard.py` | Copy/cut/paste |

## Writing New Tests

1. Use the `screen` fixture for browser tests
2. Always call `screen.wait_for_editor()` after `screen.open('/')`
3. Use `screen.page.evaluate()` for JavaScript execution
4. Access app state via `window.__stagforge_app__`
5. Use `getActiveDocument()` method for document access
6. Create shapes via `window.createVectorShape({type: '...', ...})`
7. Use `async () => {}` for tests involving serialization

### Example: Testing Layer Effects Round-Trip

```python
def test_effects_survive_serialization(screen):
    """Effects should survive serialize/deserialize round-trip."""
    screen.open('/')
    screen.wait_for_editor()

    result = screen.page.evaluate("""
        async () => {
            const app = window.__stagforge_app__;
            const LayerEffects = window.LayerEffects;

            // Get layer and add effect
            const layer = app.layerStack.layers[0];
            const DropShadow = LayerEffects.effectRegistry['dropShadow'];
            layer.addEffect(new DropShadow({ blur: 10, offsetX: 5 }));

            // Serialize
            const serialized = layer.serialize();

            // Deserialize
            const Layer = layer.constructor;
            const restored = await Layer.deserialize(serialized);

            return {
                originalEffects: serialized.effects.length,
                restoredEffects: restored.effects?.length || 0,
                effectType: restored.effects?.[0]?.type
            };
        }
    """)

    assert result['originalEffects'] == 1
    assert result['restoredEffects'] == 1
    assert result['effectType'] == 'dropShadow'
```

### Example: Testing Document Modification

```python
def test_document_marked_modified_on_change(screen):
    """Document should be marked modified when layers change."""
    screen.open('/')
    screen.wait_for_editor()

    result = screen.page.evaluate("""
        () => {
            const app = window.__stagforge_app__;
            const doc = app.documentManager.getActiveDocument();

            // Clear modified flag
            doc.modified = false;
            const before = doc.modified;

            // Make a change
            doc.markModified();
            const after = doc.modified;

            return { before, after };
        }
    """)

    assert result['before'] is False
    assert result['after'] is True
```

## Custom Screen Fixture for Dev Server

If using the dev server on port 8080 (instead of test server on 8081), create a custom fixture:

```python
from playwright.sync_api import sync_playwright

class DevScreen:
    """Screen fixture for dev server at port 8080."""

    def __init__(self, page, base_url="http://127.0.0.1:8080"):
        self.page = page
        self.base_url = base_url

    def open(self, path="/"):
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        self.page.goto(url, timeout=30000)

    def wait_for_editor(self, timeout=30.0):
        self.page.wait_for_selector('.editor-root', timeout=timeout * 1000)
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.layerStack?.layers?.length > 0",
            timeout=timeout * 1000
        )
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.documentManager?.getActiveDocument?.() != null",
            timeout=timeout * 1000
        )

    def wait(self, seconds):
        self.page.wait_for_timeout(seconds * 1000)


@pytest.fixture(scope="module")
def dev_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def screen(dev_browser):
    page = dev_browser.new_page()
    s = DevScreen(page)
    yield s
    page.close()
```

## Debugging Test Failures

### Check Browser Console

```python
def test_with_console_check(screen):
    screen.open('/')
    screen.wait_for_editor()

    # Get console logs
    logs = screen.page.evaluate("() => window.getConsoleLogs()")
    print("Console logs:", logs)
```

### Take Screenshot

```python
def test_with_screenshot(screen):
    screen.open('/')
    screen.wait_for_editor()

    # Take screenshot on failure
    try:
        # ... test code ...
    except AssertionError:
        screen.page.screenshot(path="test_failure.png")
        raise
```

### Inspect App State

```python
def test_debug_app_state(screen):
    screen.open('/')
    screen.wait_for_editor()

    state = screen.page.evaluate("""
        () => {
            const app = window.__stagforge_app__;
            return {
                hasApp: !!app,
                hasDocManager: !!app?.documentManager,
                docCount: app?.documentManager?.documents?.length,
                hasFileManager: !!app?.fileManager,
                layerCount: app?.layerStack?.layers?.length,
            };
        }
    """)
    print("App state:", state)
```
