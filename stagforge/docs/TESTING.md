# Testing Guide

## Overview

Slopstag uses Playwright-based testing with a custom `Screen` fixture that mimics NiceGUI's testing API. Tests run against the live editor in a headless Chromium browser.

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_vector_layer_bounds.py -v

# Run tests matching pattern
poetry run pytest -k "vector" -v
```

**Note:** The server must be running at `localhost:8080` for integration tests.

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
    result = screen.page.evaluate("() => window.__slopstag_app__.layerStack.layers.length")
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

The CanvasEditor Vue component exposes state via `window.__slopstag_app__`:

```javascript
// In page.evaluate():
const app = window.__slopstag_app__;

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
```

## Creating Vector Shapes

Use `window.createVectorShape()` to create shapes programmatically:

```python
result = screen.page.evaluate("""
    () => {
        const app = window.__slopstag_app__;
        const VectorLayer = window.VectorLayer;

        // Create vector layer
        const layer = new VectorLayer({
            name: 'My Vector Layer',
            width: app.layerStack.width,
            height: app.layerStack.height
        });

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

## Test Categories

| File | Purpose |
|------|---------|
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
4. Access app state via `window.__slopstag_app__`
5. Create shapes via `window.createVectorShape({type: '...', ...})`

Example test:

```python
def test_new_feature(screen):
    screen.open('/')
    screen.wait_for_editor()

    result = screen.page.evaluate("""
        () => {
            const app = window.__slopstag_app__;
            // ... test logic ...
            return { success: true, data: ... };
        }
    """)

    assert result['success']
    assert result['data'] == expected_value
```
