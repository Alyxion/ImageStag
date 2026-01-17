# Slopstag Architecture

## Overview

Slopstag is a browser-based image editor with a JavaScript-first architecture. The Python backend (NiceGUI + FastAPI) serves as an optional filter processing engine.

## Core Principles

### 1. JavaScript-First
All canvas operations, layer management, and UI run entirely in the browser using vanilla JavaScript. No framework dependencies for core functionality.

### 2. No Local File Access
Images are loaded from backend sources only (skimage samples, uploaded files). This ensures security and cross-platform compatibility.

### 3. Modular Design
- One class per file
- Registry-based auto-discovery for tools and filters
- Clear separation of concerns

### 4. API-First
All tools and features must be accessible via REST API for automation and testing.

### 5. Raw Transfer
Uncompressed RGBA bytes for filter I/O (no Base64 encoding). Binary protocol for efficiency.

### 6. Multi-Document Support
Multiple documents open simultaneously, each with independent:
- LayerStack
- History (undo/redo)
- Colors (foreground/background)
- View state (zoom, pan)

### 7. High-Quality Rendering
- Bicubic interpolation for zoom
- Anti-aliased brush strokes with supersampling
- Live navigator preview updates

## Directory Structure

```
slopstag/
├── main.py                 # NiceGUI entry point
├── slopstag/               # Python package
│   ├── app.py              # FastAPI app factory
│   ├── canvas_editor.js    # Vue component (to be split)
│   ├── api/                # REST API endpoints
│   ├── filters/            # Python image filters
│   └── images/             # Image source providers
├── frontend/               # Static JS/CSS
│   ├── js/
│   │   ├── core/           # Core classes (Layer, History, etc.)
│   │   ├── tools/          # Tool implementations
│   │   ├── ui/             # UI components
│   │   └── plugins/        # Backend connector
│   └── css/
│       └── main.css        # Styles (to be split)
└── docs/                   # Documentation
```

## Data Flow

### Drawing Operations
```
User Input → Tool Handler → Layer Canvas → Renderer → Display
                ↓
           History System (auto-diff)
```

### Filter Operations
```
UI → PluginManager → BackendConnector → FastAPI
                                            ↓
                                    Python Filter
                                            ↓
Layer ← Raw RGBA ← Response ← BackendConnector
```

### Document Switching
```
Tab Click → DocumentManager.setActiveDocument()
                    ↓
            Save current view state
                    ↓
            Update app context (layerStack, history)
                    ↓
            Update renderer references
                    ↓
            Restore target view state
```

## Key Classes

### Core (`frontend/js/core/`)
- **Document** - Single document with LayerStack, History, colors, view state
- **DocumentManager** - Manages multiple documents, tab switching
- **Layer** - Individual layer with canvas, opacity, blend mode
- **LayerStack** - Layer ordering, active selection, merge/flatten
- **Renderer** - Composites layers to display with zoom/pan
- **History** - Undo/redo with automatic pixel diff detection
- **Clipboard** - Cut/copy/paste with selection and merge support

### Tools (`frontend/js/tools/`)
- **Tool** - Abstract base class
- **ToolManager** - Registry and tool switching
- Individual tools: Brush, Eraser, Selection, Move, etc.

### UI (`slopstag/canvas_editor.js`)
- Vue component providing the editor shell
- Menu system, panels, dialogs
- Event handling and state management

## Memory Management

### History System
- Automatic pixel diff detection (only stores changed regions)
- Memory limits with automatic eviction
- Efficient patch-based undo/redo

### Layer System
- Lazy canvas creation
- Automatic bounds expansion
- Dispose methods for cleanup

## Event System

Uses a publish/subscribe EventBus for decoupled communication:
- `tool:changed` - Tool selection
- `layer:*` - Layer operations
- `history:changed` - Undo/redo state
- `document:*` - Document management
- `clipboard:*` - Clipboard operations
