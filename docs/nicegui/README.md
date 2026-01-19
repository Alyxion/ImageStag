# NiceGUI Component Development

This guide covers patterns for building custom NiceGUI components in ImageStag.

## Overview

NiceGUI custom components extend the `Element` base class and pair with a Vue.js
frontend component. Communication flows bidirectionally:

- **Python → JavaScript**: Props via `self._props` and methods via `self.run_method()`
- **JavaScript → Python**: Events via `this.$emit()`

## Quick Start

```python
from nicegui.element import Element

class MyComponent(Element, component="my_component.js"):
    def __init__(self, value: int = 0) -> None:
        super().__init__()
        self._props["value"] = value
        self.on("change", self._on_change)
    
    def _on_change(self, e) -> None:
        print(f"Value changed: {e.args['value']}")
```

```javascript
// my_component.js
export default {
    template: `<div @click="increment">{{ value }}</div>`,
    props: { value: Number },
    methods: {
        increment() {
            this.$emit('change', { value: this.value + 1 });
        }
    }
};
```

## Documentation

- [Component Patterns](./component_patterns.md) - Element, props, events, methods

## Component Directory Structure

```
imagestag/components/my_component/
├── __init__.py           # Public exports
├── my_component.py       # Python Element class
├── my_component.js       # Vue.js component
└── my_component.css      # Optional styles
```

## Key Patterns

| Pattern | Python | JavaScript |
|---------|--------|------------|
| Set prop | `self._props["key"] = value` | Access via `this.key` |
| Update UI | `self.update()` | Automatic on prop change |
| Emit event | `self.on("name", handler)` | `this.$emit("name", data)` |
| Call method | `self.run_method("name", arg)` | Define in `methods: {}` |
| Async call | `await self.run_method("name")` | Return value from method |

## See Also

- [NiceGUI Documentation](https://nicegui.io/documentation)
- [Vue.js Guide](https://vuejs.org/guide/)
