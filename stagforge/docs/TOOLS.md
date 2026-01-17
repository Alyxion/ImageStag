# Tool System

## Overview

The tool system uses a registry pattern for maximum extensibility. Each tool is a separate file that self-registers.

## Base Class

All tools extend the `Tool` base class (`frontend/js/tools/Tool.js`):

```javascript
export class Tool {
    static id = 'tool';           // Unique identifier
    static name = 'Tool';         // Display name
    static icon = 'cursor';       // Icon name
    static shortcut = null;       // Keyboard shortcut
    static cursor = 'default';    // CSS cursor

    constructor(app) { this.app = app; }

    // Lifecycle
    activate() {}
    deactivate() {}

    // Input handlers
    onMouseDown(e, x, y) {}
    onMouseMove(e, x, y) {}
    onMouseUp(e, x, y) {}
    onMouseLeave(e) {}
    onKeyDown(e) {}
    onKeyUp(e) {}

    // Properties for UI
    getProperties() { return []; }

    // API execution - REQUIRED
    executeAction(action, params) {
        return { success: false, error: 'Not implemented' };
    }
}
```

## Creating a New Tool

1. Create file `frontend/js/tools/MyTool.js`:

```javascript
import { Tool } from './Tool.js';

export class MyTool extends Tool {
    static id = 'mytool';
    static name = 'My Tool';
    static icon = 'star';
    static shortcut = 'm';
    static cursor = 'crosshair';

    onMouseDown(e, x, y) {
        // Start operation
        this.app.history.saveState('My Action');
    }

    onMouseUp(e, x, y) {
        // Finish operation
        this.app.history.finishState();
        this.app.renderer.requestRender();
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 100, value: 10 }
        ];
    }

    executeAction(action, params) {
        if (action === 'draw') {
            // Programmatic execution
            return { success: true };
        }
        return { success: false, error: 'Unknown action' };
    }
}
```

2. Register in `canvas_editor.js`:

```javascript
import { MyTool } from './tools/MyTool.js';
app.toolManager.register(MyTool);
```

## Property Types

Tools can define properties shown in the ribbon:

- `range` - Slider with min/max/step
- `select` - Dropdown with options array
- `checkbox` - Boolean toggle
- `color` - Color picker
- `number` - Numeric input

## Canvas Bounds

Painting tools are prevented from starting strokes outside the document bounds. The following tools are allowed to work outside bounds:
- move
- hand
- selection
- lasso
- crop

## Available Tools

### Selection Tools
| Tool | ID | Shortcut | Description |
|------|----|----------|-------------|
| Selection | selection | M | Rectangular selection |
| Lasso | lasso | L | Freehand selection |
| Magic Wand | magicwand | W | Color-based selection |

### Drawing Tools
| Tool | ID | Shortcut | Description |
|------|----|----------|-------------|
| Brush | brush | B | Freehand painting |
| Spray | spray | A | Airbrush effect |
| Eraser | eraser | E | Erase to transparency |

### Shape Tools
| Tool | ID | Shortcut | Description |
|------|----|----------|-------------|
| Line | line | L | Straight lines |
| Rectangle | rect | R | Rectangles |
| Circle | circle | C | Circles/ellipses |
| Polygon | polygon | P | Multi-vertex shapes |

### Other Tools
| Tool | ID | Shortcut | Description |
|------|----|----------|-------------|
| Move | move | V | Move layers/selections |
| Fill | fill | G | Flood fill |
| Gradient | gradient | G | Color gradients |
| Text | text | T | Text layers |
| Eyedropper | eyedropper | I | Color sampling |
| Crop | crop | C | Crop document |
| Hand | hand | H | Pan viewport |
| Pen | pen | P | Bezier paths |

## API Execution

All tools must implement `executeAction(action, params)` for programmatic use:

```javascript
// Example: Brush stroke via API
POST /api/sessions/{id}/tools/brush/execute
{
    "action": "stroke",
    "params": {
        "points": [[100, 100], [150, 120], [200, 100]],
        "color": "#ff0000",
        "size": 20
    }
}
```
