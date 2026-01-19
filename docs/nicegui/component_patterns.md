# NiceGUI Component Patterns

Detailed patterns for building custom NiceGUI components.

## Element Class Structure

```python
from pathlib import Path
from dataclasses import dataclass
from nicegui import app
from nicegui.element import Element
from nicegui.events import GenericEventArguments, handle_event

# Register static files (CSS, additional JS)
_COMPONENT_DIR = Path(__file__).parent

class MyComponent(Element, component="my_component.js"):
    """Custom NiceGUI component.

    The component= parameter specifies the Vue.js file path relative to
    this Python file.
    """

    def __init__(self, width: int = 100, height: int = 100) -> None:
        super().__init__()

        # Set props passed to Vue component
        self._props["width"] = width
        self._props["height"] = height

        # Register event handlers
        self.on("custom-event", self._handle_custom_event)

    def _handle_custom_event(self, e) -> None:
        # e.args contains data from JavaScript
        pass
```

## Props (Python to JavaScript)

Props are the primary way to pass data from Python to the Vue component.

### Setting Props

```python
def __init__(self) -> None:
    super().__init__()
    # Initial props
    self._props["count"] = 0
    self._props["config"] = {"theme": "dark"}

def update_count(self, value: int) -> None:
    self._props["count"] = value
    self.update()  # Trigger Vue re-render
```

### Receiving Props in Vue

```javascript
export default {
    props: {
        count: { type: Number, default: 0 },
        config: { type: Object, default: () => ({}) }
    },
    // Access via this.count, this.config
};
```

### Dynamic Props

Props prefixed with `:` are evaluated as JavaScript expressions:

```python
self._props[":items"] = "['a', 'b', 'c']"  # JS array literal
```

## Events (JavaScript to Python)

Events are the primary way for the Vue component to communicate back to Python.

### Emitting Events

```javascript
methods: {
    onClick() {
        this.$emit('item-clicked', {
            id: this.selectedId,
            value: this.currentValue
        });
    }
}
```

### Handling Events in Python

```python
def __init__(self) -> None:
    super().__init__()
    self.on("item-clicked", self._on_item_clicked)

def _on_item_clicked(self, e) -> None:
    item_id = e.args["id"]
    value = e.args["value"]
```

### Event Argument Dataclasses

For type-safe event handling:

```python
from dataclasses import dataclass
from nicegui.events import GenericEventArguments

@dataclass
class ItemClickedEventArgs(GenericEventArguments):
    id: str = ""
    value: int = 0

def _on_item_clicked(self, e) -> None:
    args = ItemClickedEventArgs(
        sender=self,
        client=self.client,
        id=e.args.get("id", ""),
        value=e.args.get("value", 0),
    )
    if self._click_handler:
        handle_event(self._click_handler, args)
```

### Event Decorators

Provide a fluent API for registering handlers:

```python
class MyComponent(Element, component="my_component.js"):
    def __init__(self) -> None:
        super().__init__()
        self._click_handler = None
        self.on("item-clicked", self._on_item_clicked)

    def on_click(self, handler: Callable) -> "MyComponent":
        """Register click handler."""
        self._click_handler = handler
        return self

# Usage:
@component.on_click
def handle_click(e):
    print(e.id, e.value)
```

## Methods (Python to JavaScript)

Use `run_method()` to call Vue component methods from Python.

### Fire-and-Forget

```python
def start(self) -> None:
    self.run_method("start")

def set_config(self, config: dict) -> None:
    self.run_method("setConfig", config)
```

### Async with Return Value

```python
async def get_state(self) -> dict:
    return await self.run_method("getState")

async def calculate(self, x: int, y: int) -> int:
    return await self.run_method("calculate", x, y)
```

### Vue Method Implementation

```javascript
methods: {
    start() {
        this.isRunning = true;
    },
    setConfig(config) {
        Object.assign(this.config, config);
    },
    getState() {
        return { running: this.isRunning, count: this.count };
    },
    calculate(x, y) {
        return x + y;
    }
}
```

## Vue Component Template

```javascript
export default {
    template: `
        <div class="my-component" :style="containerStyle">
            <canvas ref="canvas" :width="width" :height="height"></canvas>
            <div v-if="showOverlay" class="overlay">{{ message }}</div>
        </div>
    `,

    props: {
        width: { type: Number, default: 100 },
        height: { type: Number, default: 100 },
        showOverlay: { type: Boolean, default: false },
    },

    data() {
        return {
            message: '',
            isInitialized: false,
        };
    },

    computed: {
        containerStyle() {
            return {
                width: `${this.width}px`,
                height: `${this.height}px`,
            };
        },
    },

    async mounted() {
        // Initialize after DOM is ready
        await this.initialize();
        this.isInitialized = true;
    },

    unmounted() {
        // Cleanup resources
        this.cleanup();
    },

    methods: {
        async initialize() {
            // Setup code
        },
        cleanup() {
            // Teardown code
        },
    },

    watch: {
        // React to prop changes
        width(newVal, oldVal) {
            this.onResize();
        },
    },
};
```

## Static Files

### CSS Registration

```python
from pathlib import Path
from nicegui import app

_COMPONENT_DIR = Path(__file__).parent
_CSS_REGISTERED = False

class MyComponent(Element, component="my_component.js"):
    def __init__(self) -> None:
        super().__init__()

        # Register CSS once
        global _CSS_REGISTERED
        if not _CSS_REGISTERED:
            app.add_static_files("/my-component", _COMPONENT_DIR)
            _CSS_REGISTERED = True

        # Add CSS to page
        self.client.add_head_html(
            '<link rel="stylesheet" href="/my-component/my_component.css">'
        )
```

### Inline Styles

For simple components, use inline styles in the template:

```javascript
template: `<div :style="{ width: width + 'px', height: height + 'px' }">...</div>`
```

## Module Exports

```python
# __init__.py
from .my_component import MyComponent
from .events import ItemClickedEventArgs

__all__ = ["MyComponent", "ItemClickedEventArgs"]
```

## Best Practices

1. **Clean up in unmounted()** - Remove timers, event listeners, close connections
2. **Use props for data flow** - Avoid direct DOM manipulation
3. **Emit events for actions** - Let Python handle business logic
4. **Define prop types** - Add validation in Vue props
5. **Batch updates** - Call `self.update()` once after multiple prop changes
6. **Handle errors** - Emit error events for JavaScript exceptions

## Common Patterns

### Bidirectional Binding

```python
class Input(Element, component="input.js"):
    def __init__(self, value: str = "") -> None:
        super().__init__()
        self._props["value"] = value
        self.on("input", lambda e: setattr(self, "_value", e.args["value"]))

    @property
    def value(self) -> str:
        return self._props.get("value", "")

    @value.setter
    def value(self, v: str) -> None:
        self._props["value"] = v
        self.update()
```

### Lazy Initialization

```python
def __init__(self) -> None:
    super().__init__()
    self._initialized = False
    self.on("mounted", self._on_mounted)

async def _on_mounted(self, e) -> None:
    if not self._initialized:
        await self._initialize()
        self._initialized = True
```

### Resource Cleanup

```python
def __init__(self) -> None:
    super().__init__()
    self._cleanup_handlers = []

def add_cleanup(self, handler: Callable) -> None:
    self._cleanup_handlers.append(handler)

def __del__(self) -> None:
    for handler in self._cleanup_handlers:
        handler()
```
