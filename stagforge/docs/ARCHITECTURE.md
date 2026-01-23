# Stagforge Architecture

## Overview

Stagforge is a browser-based image editor with a JavaScript-first architecture. The Python backend (NiceGUI + FastAPI) provides:
- REST API for automation and testing
- WebSocket Bridge for bidirectional communication
- Python filters and image processing
- Server-side rendering for cross-platform parity

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

### 8. Cross-Platform Parity
Dynamic layers (text, vector) must render identically in JavaScript and Python. See [VECTOR_RENDERING.md](VECTOR_RENDERING.md).

## Directory Structure

```
stagforge/
├── main.py                    # NiceGUI entry point
├── stagforge/
│   ├── app.py                 # FastAPI app factory
│   ├── canvas_editor.js       # Vue component
│   ├── canvas_editor.py       # Python editor bindings
│   ├── api/                   # REST API endpoints
│   │   ├── router.py          # Main API router
│   │   ├── documents.py       # Document endpoints
│   │   ├── layers.py          # Layer endpoints
│   │   ├── tools.py           # Tool execution
│   │   ├── upload.py          # Push-based data transfer
│   │   └── data_cache.py      # Image data caching
│   ├── bridge/                # WebSocket communication
│   │   ├── editor_bridge.py   # Thread-safe Python bridge
│   │   ├── session.py         # Session management
│   │   └── exceptions.py      # Bridge errors
│   ├── filters/               # Python image filters
│   ├── images/                # Image source providers
│   ├── rendering/             # Python rendering (text, vector)
│   └── sessions/              # Session management
├── frontend/
│   ├── js/
│   │   ├── core/              # Core classes
│   │   ├── tools/             # Tool implementations
│   │   ├── ui/                # UI components
│   │   ├── effects/           # Layer effects
│   │   ├── bridge/            # WebSocket client
│   │   └── editor/mixins/     # Editor mixins
│   └── css/
│       └── main.css           # Styles
└── docs/                      # Documentation
```

## Communication Architecture

### WebSocket Bridge

The WebSocket Bridge enables real-time bidirectional communication:

```
Python (EditorBridge)  ←→  WebSocket  ←→  JavaScript (EditorBridgeClient)
```

**Key Features:**
- Thread-safe synchronous API for Python
- Automatic reconnection on disconnect
- Heartbeat-based connection health monitoring
- Command/response correlation with timeouts

See [WEBSOCKET_BRIDGE.md](WEBSOCKET_BRIDGE.md) for details.

### REST API

Full REST API for programmatic access to all editor features:

```
/api/sessions/{session}/documents/{doc}/...
```

See [API.md](API.md) for complete reference.

### Push-Based Data Transfer

Large images are transferred using a push mechanism to avoid WebSocket payload limits:

1. Client requests image via REST API
2. Backend generates unique request ID
3. Browser JS renders and POSTs data to `/api/upload/{request_id}`
4. Backend returns data to waiting client

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

### WebSocket Communication
```
Python bridge.call() → WebSocket → JS handler executes
                                         ↓
Python receives result ← WebSocket ← JS sends response
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

### UI (`stagforge/canvas_editor.js`)
- Vue component providing the editor shell
- Menu system, panels, dialogs
- Event handling and state management

### Bridge (`stagforge/bridge/`)
- **EditorBridge** - Thread-safe Python WebSocket client
- **BridgeSession** - Session state management
- **EditorBridgeClient** (JS) - Browser WebSocket client

### Editor Mixins (`frontend/js/editor/mixins/`)
Modular Vue mixins extracted from the main editor:
- **BridgeManager** - WebSocket bridge lifecycle
- **FileManager** - File operations
- **MenuManager** - Menu system
- **LayerOperations** - Layer management
- **ViewManager** - Zoom/pan controls
- **SessionAPIManager** - API communication
- **DocumentUIManager** - Document UI state

## Memory Management

### History System
- Automatic pixel diff detection (only stores changed regions)
- Memory limits with automatic eviction
- Efficient patch-based undo/redo

### Layer System
- Lazy canvas creation
- Automatic bounds expansion
- Image caching for auto-save optimization
- Dispose methods for cleanup

### Data Cache
- Automatic garbage collection
- Max total storage: 500 MB
- Entry timeout: 5 minutes
- Cleanup interval: 60 seconds

## Event System

Uses a publish/subscribe EventBus for decoupled communication:
- `tool:changed` - Tool selection
- `layer:*` - Layer operations
- `history:changed` - Undo/redo state
- `document:*` - Document management
- `clipboard:*` - Clipboard operations

## Testing Architecture

Two testing frameworks are available:

### Playwright Async (`helpers_pw/`)
Comprehensive async test helpers for UI automation:
- `EditorTestHelper` - Browser/canvas interaction
- `PixelHelper` - Pixel extraction and verification
- `ToolHelper` - Tool-specific operations
- `LayerHelper` - Layer management
- `SelectionHelper` - Selection and clipboard

### Playwright Sync (`screen` fixture)
Simpler synchronous API for basic tests.

See [TESTING.md](TESTING.md) for details.

## Deployment

### Development Mode
```bash
poetry run python -m stagforge.main
```
- Hot reload on code changes
- Port 8080
- Debug logging enabled

### Production
- Set `NICEGUI_STORAGE_SECRET` environment variable
- Use reverse proxy (nginx) for TLS termination
- Configure session persistence if needed
