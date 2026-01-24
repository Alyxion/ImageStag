# NiceGUI Integration Guide

This document covers how to embed Stagforge in NiceGUI applications and important architectural considerations.

## Overview

Stagforge can be embedded in NiceGUI applications using the `StagforgeEditor` component, which renders the editor in an iframe. This allows NiceGUI apps to provide image editing capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NiceGUI App                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Python (NiceGUI)                     │  │
│  │  - UI controls (buttons, dialogs)                 │  │
│  │  - StagforgeEditor component                      │  │
│  │  - API calls to Stagforge                         │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│                    HTTP/REST API                        │
│                         │                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │           Stagforge API (FastAPI)                 │  │
│  │  - Mounted at /api                                │  │
│  │  - WebSocket bridge for JS communication          │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│                    WebSocket                            │
│                         │                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Stagforge Editor (iframe)                 │  │
│  │  - JavaScript canvas editor                       │  │
│  │  - Receives commands via WebSocket                │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Critical: Avoiding Deadlocks

### The Problem

NiceGUI runs on a single-threaded async event loop (uvicorn/uvloop). When making HTTP requests from Python back to the same server, you can cause deadlocks:

```python
# WRONG - This will deadlock!
def on_button_click():
    # Synchronous HTTP request blocks the event loop
    response = requests.post("http://localhost:8080/api/...")
    # Server can't process request because event loop is blocked
```

### Solution 1: Use ThreadPoolExecutor

Run blocking HTTP requests in a thread pool:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

async def on_button_click():
    loop = asyncio.get_event_loop()
    # Request runs in separate thread, event loop stays free
    result = await loop.run_in_executor(executor, blocking_http_call)
```

### Solution 2: Use Fire-and-Forget Commands

For commands that don't need a response, use `editor_bridge.fire()` instead of `editor_bridge.call()`:

```python
# editor_bridge.call() - BLOCKS with threading.Event.wait()
result = editor_bridge.call(session_id, "executeCommand", params)  # Deadlock!

# editor_bridge.fire() - Non-blocking, fire-and-forget
editor_bridge.fire(session_id, "executeCommand", params)  # Safe!
```

The `call()` method uses `threading.Event.wait()` which blocks the thread that also needs to process the WebSocket response - causing a deadlock.

### Solution 3: Client-Side API Calls

Have JavaScript in the iframe call the API directly instead of Python:

```javascript
// In iframe JavaScript
fetch('/api/sessions/current/documents/current/layers/import', {
    method: 'POST',
    body: JSON.stringify(data)
});
```

## API Endpoints for NiceGUI Integration

### Layer Import (Fire-and-Forget)

```
POST /api/sessions/{session_id}/documents/{doc}/layers/import
```

This endpoint uses fire-and-forget to avoid deadlocks. It returns immediately after sending the command to JavaScript.

### Image Retrieval

```
GET /api/sessions/{session_id}/documents/{doc}/image?format=png
```

Safe to call from NiceGUI - just reads data, no WebSocket round-trip needed.

## StagforgeEditor Component

### Basic Usage

```python
from stagforge.nicegui import StagforgeEditor
from skimage import data

editor = StagforgeEditor(
    width=800,
    height=600,
    isolated=True,
    initial_image=data.astronaut(),
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | int | 800 | Editor width in pixels |
| `height` | int | 600 | Editor height in pixels |
| `isolated` | bool | False | Disable auto-save/restore |
| `initial_image` | bytes/ndarray | None | Image to load after init |
| `server_url` | str | "" | Base URL (default: localhost:8080) |
| `doc_width` | int | 800 | Document canvas width |
| `doc_height` | int | 600 | Document canvas height |

### Isolated Mode

When `isolated=True`:
- Auto-save is disabled (no localStorage persistence)
- Each session starts with a fresh document
- Ideal for embedded use where you control the image lifecycle

### Methods

```python
# Load the initial image (call after editor is ready)
success = editor.load_initial_image()

# Get merged image from all layers
img_bytes = await editor.get_merged_image('png')

# Get specific layer image
layer_bytes = await editor.get_layer_image(layer_id, 'png')

# Export/import document JSON
doc_data = await editor.get_document_json()
await editor.load_document_json(doc_data)
```

## Example: Minimal NiceGUI App

```python
from nicegui import app, ui
from stagforge.app import create_api_app
from stagforge.nicegui import StagforgeEditor

# Mount Stagforge API
app.mount("/api", create_api_app())

@ui.page('/')
def main():
    editor = StagforgeEditor(
        width=800,
        height=600,
        isolated=True,
    )

ui.run(port=8080)
```

## Troubleshooting

### "Read timed out" after 30 seconds

**Cause:** Deadlock from synchronous HTTP request blocking the event loop.

**Fix:** Use `run_in_executor()` for blocking calls or switch to fire-and-forget.

### Editor shows but doesn't respond to commands

**Cause:** WebSocket not connected or session mismatch.

**Fix:** Check browser console for WebSocket errors. Ensure session_id matches.

### "Session not found" errors

**Cause:** Session auto-registration happens on first WebSocket connection.

**Fix:** Wait for editor to fully load before calling APIs.
