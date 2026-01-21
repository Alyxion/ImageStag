# REST API Documentation

## Overview

The Stagforge API provides programmatic access to all editor features. All endpoints are prefixed with `/api`.

**Key Concepts:**
- **Session**: A browser tab/connection with one or more open documents
- **Document**: An image document with dimensions, layers, and history
- **Layer**: A single layer within a document (raster, vector, text, or group)

## Resource Selection

All resource identifiers (session, document, layer) support flexible selection:

| Value | Meaning |
|-------|---------|
| UUID | Specific resource by ID (e.g., `86bd21b2-4c72-4c61-a7e9-47e4be52f37b`) |
| `current` | Active/selected resource |
| Integer | Index (0-based, e.g., `0` for first) |
| String | Name match (e.g., `Background`) |

**Examples:**
```
/api/sessions/current/documents/current/layers/0          # Top layer of active doc
/api/sessions/current/documents/testsample/layers/Background
/api/sessions/current/documents/0/image                   # First document's image
```

---

## URL Structure

```
/api/sessions                                              # List sessions
/api/sessions/{session}                                    # Session info

/api/sessions/{session}/documents                          # List documents
/api/sessions/{session}/documents/{doc}                    # Document info
/api/sessions/{session}/documents/{doc}/image              # Composite image
/api/sessions/{session}/documents/{doc}/export             # Export document
/api/sessions/{session}/documents/{doc}/command            # Execute command

/api/sessions/{session}/documents/{doc}/layers             # List layers
/api/sessions/{session}/documents/{doc}/layers/{layer}     # Layer info
/api/sessions/{session}/documents/{doc}/layers/{layer}/image    # Layer image
/api/sessions/{session}/documents/{doc}/layers/{layer}/effects  # Layer effects

/api/sessions/{session}/documents/{doc}/groups             # Create layer group
/api/sessions/{session}/documents/{doc}/history            # History state
/api/sessions/{session}/documents/{doc}/selection          # Selection info
/api/sessions/{session}/documents/{doc}/view               # View/zoom state
/api/sessions/{session}/documents/{doc}/clipboard          # Clipboard ops

/api/sessions/{session}/colors                             # FG/BG colors
/api/sessions/{session}/active-tool                        # Active tool
/api/sessions/{session}/config                             # UI config

/api/tools                                                 # List tools (global)
/api/filters                                               # List filters (global)
/api/effects                                               # List effect types (global)
/api/images/sources                                        # List image sources
/api/upload/{request_id}                                   # Push data (internal)
/api/upload/stats                                          # Cache statistics
```

---

## Core Endpoints

### Health Check
```
GET /api/health
```
Returns server status.

**Response:**
```json
{"status": "ok", "version": "0.1.0"}
```

---

## Session Management

### List Sessions
```
GET /api/sessions
```
Returns all active editor sessions, sorted by most recent activity first.

**Response:**
```json
{
    "sessions": [
        {
            "id": "c7d67b80-73ea-45ae-8b1f-9eb472c53019",
            "created_at": "2026-01-21T06:10:37.721461",
            "last_activity": "2026-01-21T06:10:38.232584",
            "document_count": 1,
            "active_document_id": "86bd21b2-4c72-4c61-a7e9-47e4be52f37b",
            "active_document_name": "testsample",
            "active_tool": "brush",
            "foreground_color": "#000000",
            "background_color": "#FFFFFF"
        }
    ]
}
```

### Get Session Details
```
GET /api/sessions/{session}
```
Returns full session state including all documents and their layers.

### Refresh Browser
```
POST /api/sessions/{session}/refresh
```
Refresh the browser/reload the editor.

### Reload Image Sources
```
POST /api/sessions/{session}/reload-sources
```
Reload available image sources.

---

## Document Management

### List Documents
```
GET /api/sessions/{session}/documents
```
List all documents in a session.

**Response:**
```json
{
    "documents": [
        {"id": "...", "name": "Document 1", "width": 800, "height": 600, "layer_count": 2}
    ],
    "active_document_id": "...",
    "session_id": "..."
}
```

### Create Document
```
POST /api/sessions/{session}/documents
Content-Type: application/json

{"width": 800, "height": 600, "name": "New Document"}
```

### Get Document
```
GET /api/sessions/{session}/documents/{doc}
```
Get document details including all layers.

### Update Document
```
PUT /api/sessions/{session}/documents/{doc}
Content-Type: application/json

{"name": "Renamed", "width": 1024, "height": 768}
```

### Close Document
```
DELETE /api/sessions/{session}/documents/{doc}
```

### Activate Document
```
POST /api/sessions/{session}/documents/{doc}/activate
```
Set as the active document.

### Get Composite Image
```
GET /api/sessions/{session}/documents/{doc}/image
GET /api/sessions/{session}/documents/{doc}/image?format=webp
GET /api/sessions/{session}/documents/{doc}/image?format=png&bg=%23FFFFFF
```
Returns the composite image (all visible layers merged) with layer effects applied.

**Query Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `format` | `webp` | Output format: `webp`, `avif`, `png` |
| `bg` | (none) | Background color (e.g., `%23FFFFFF` for white). Omit for transparent. |

**Note:** Use `%23` to URL-encode `#` in query strings.

**Response Headers:**
- `X-Width` - Image width in pixels
- `X-Height` - Image height in pixels
- `X-Document-Id` - The document ID
- `X-Document-Name` - The document name
- `Content-Type` - MIME type (`image/webp`, `image/avif`, `image/png`)

**Response Body:** Encoded image data in the requested format

### Export Document
```
GET /api/sessions/{session}/documents/{doc}/export
```
Export full document as JSON including all layers with their content.

### Import Document
```
POST /api/sessions/{session}/documents/{doc}/import
Content-Type: application/json

{"document": {...}}
```

### Flatten Document
```
POST /api/sessions/{session}/documents/{doc}/flatten
```
Flatten all layers into one.

---

## Layer Management

### List Layers
```
GET /api/sessions/{session}/documents/{doc}/layers
```

**Response:**
```json
{
    "layers": [
        {
            "id": "layer-id",
            "name": "Background",
            "type": "raster",
            "visible": true,
            "locked": false,
            "opacity": 1.0,
            "blend_mode": "normal",
            "width": 800,
            "height": 600,
            "offset_x": 0,
            "offset_y": 0,
            "parent_id": null
        }
    ],
    "active_layer_id": "layer-id"
}
```

**Layer Types:** `raster`, `vector`, `text`, `group`

### Create Layer
```
POST /api/sessions/{session}/documents/{doc}/layers
Content-Type: application/json

{"name": "Layer 1", "type": "raster"}
```

### Get Layer
```
GET /api/sessions/{session}/documents/{doc}/layers/{layer}
```

### Update Layer
```
PUT /api/sessions/{session}/documents/{doc}/layers/{layer}
Content-Type: application/json

{"name": "Renamed", "opacity": 0.5, "visible": false}
```

### Delete Layer
```
DELETE /api/sessions/{session}/documents/{doc}/layers/{layer}
```

### Get Layer Image/Data
```
GET /api/sessions/{session}/documents/{doc}/layers/{layer}/image
GET /api/sessions/{session}/documents/{doc}/layers/{layer}/image?format=webp
GET /api/sessions/{session}/documents/{doc}/layers/{layer}/image?format=svg
GET /api/sessions/{session}/documents/{doc}/layers/{layer}/image?format=json
```
Returns the layer's image data with effects applied, or vector data for vector layers.

**Query Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `format` | `webp` | Output format: `webp`, `avif`, `png` for raster; `svg`, `json` for vector layers |
| `bg` | (none) | Background color (e.g., `%23FFFFFF`). Omit for transparent. |

**Format Notes:**
- **Raster layers**: Use `webp`, `avif`, or `png`
- **Vector layers**: Use `svg` for SVG markup, `json` for shape data, or raster formats for rendered image
- Layer effects (drop shadow, stroke, glow, etc.) are included in the output

**Response Headers:**
- `X-Width`, `X-Height` - Dimensions
- `X-Layer-Id` - Layer ID
- `X-Layer-Name` - Layer name
- `X-Layer-Type` - Layer type (`raster`, `vector`, `text`, `group`)
- `X-Data-Type` - Data type (`image`, `svg`, `vector-json`)
- `Content-Type` - MIME type

### Duplicate Layer
```
POST /api/sessions/{session}/documents/{doc}/layers/{layer}/duplicate
```

### Move Layer
```
POST /api/sessions/{session}/documents/{doc}/layers/{layer}/move
Content-Type: application/json

{"to_index": 0}
```

### Merge Down
```
POST /api/sessions/{session}/documents/{doc}/layers/{layer}/merge-down
```

---

## Layer Groups

### Create Group
```
POST /api/sessions/{session}/documents/{doc}/groups
Content-Type: application/json

{"name": "Group 1"}
```

### Create Group from Layers
```
POST /api/sessions/{session}/documents/{doc}/groups/from-layers
Content-Type: application/json

{"layer_ids": ["layer-1", "layer-2"], "name": "Group 1"}
```

### Delete/Ungroup
```
DELETE /api/sessions/{session}/documents/{doc}/groups/{group}
```
Children are moved out of the group, not deleted.

### Move Layer to Group
```
POST /api/sessions/{session}/documents/{doc}/layers/{layer}/move-to-group
Content-Type: application/json

{"group_id": "group-id"}
```

### Remove from Group
```
POST /api/sessions/{session}/documents/{doc}/layers/{layer}/remove-from-group
```

---

## Layer Effects

### List Effects
```
GET /api/sessions/{session}/documents/{doc}/layers/{layer}/effects
```

### Add Effect
```
POST /api/sessions/{session}/documents/{doc}/layers/{layer}/effects
Content-Type: application/json

{
    "effect_type": "dropShadow",
    "params": {
        "offsetX": 5,
        "offsetY": 5,
        "blur": 10,
        "color": "#000000"
    }
}
```

**Effect Types:**

| Type | Parameters |
|------|------------|
| `dropShadow` | `offsetX, offsetY, blur, spread, color, colorOpacity` |
| `innerShadow` | `offsetX, offsetY, blur, choke, color, colorOpacity` |
| `outerGlow` | `blur, spread, color, colorOpacity` |
| `innerGlow` | `blur, choke, color, colorOpacity, source` |
| `bevelEmboss` | `style, depth, direction, size, soften, angle, altitude` |
| `stroke` | `size, position, color, colorOpacity` |
| `colorOverlay` | `color` |

All effects also accept: `enabled`, `blendMode`, `opacity`

### Update Effect
```
PUT /api/sessions/{session}/documents/{doc}/layers/{layer}/effects/{effect_id}
Content-Type: application/json

{"params": {"blur": 15}}
```

### Remove Effect
```
DELETE /api/sessions/{session}/documents/{doc}/layers/{layer}/effects/{effect_id}
```

---

## Selection

### Get Selection
```
GET /api/sessions/{session}/documents/{doc}/selection
```

### Set Selection
```
PUT /api/sessions/{session}/documents/{doc}/selection
Content-Type: application/json

{"x": 10, "y": 10, "width": 100, "height": 100}
```

### Clear Selection
```
DELETE /api/sessions/{session}/documents/{doc}/selection
```

### Select All
```
POST /api/sessions/{session}/documents/{doc}/selection/all
```

### Invert Selection
```
POST /api/sessions/{session}/documents/{doc}/selection/invert
```

---

## History

### Get History State
```
GET /api/sessions/{session}/documents/{doc}/history
```

**Response:**
```json
{
    "history": {
        "can_undo": true,
        "can_redo": false,
        "undo_count": 5,
        "redo_count": 0
    }
}
```

### Undo
```
POST /api/sessions/{session}/documents/{doc}/history/undo
```

### Redo
```
POST /api/sessions/{session}/documents/{doc}/history/redo
```

### Clear History
```
DELETE /api/sessions/{session}/documents/{doc}/history
```

---

## Clipboard

### Get Clipboard Info
```
GET /api/sessions/{session}/documents/{doc}/clipboard
```

### Copy
```
POST /api/sessions/{session}/documents/{doc}/clipboard/copy
```

### Copy Merged
```
POST /api/sessions/{session}/documents/{doc}/clipboard/copy-merged
```

### Cut
```
POST /api/sessions/{session}/documents/{doc}/clipboard/cut
```

### Paste
```
POST /api/sessions/{session}/documents/{doc}/clipboard/paste
```

### Paste in Place
```
POST /api/sessions/{session}/documents/{doc}/clipboard/paste-in-place
```

---

## View/Zoom

### Get View State
```
GET /api/sessions/{session}/documents/{doc}/view
```

### Set View
```
PUT /api/sessions/{session}/documents/{doc}/view
Content-Type: application/json

{"zoom": 2.0, "pan_x": 100, "pan_y": 50}
```

### Fit to Window
```
POST /api/sessions/{session}/documents/{doc}/view/fit
```

### Zoom to 100%
```
POST /api/sessions/{session}/documents/{doc}/view/actual
```

---

## Tool Execution

### Execute Tool Action
```
POST /api/sessions/{session}/documents/{doc}/tools/{tool_id}/execute
Content-Type: application/json

{
    "action": "stroke",
    "params": {
        "points": [[100, 100], [200, 100]],
        "color": "#FF0000",
        "size": 10
    }
}
```

**Available Tools and Actions:**

| Tool | Action | Parameters |
|------|--------|------------|
| **selection** | `select` | `{x, y, width, height}` |
| | `select_all` | - |
| | `clear` | - |
| | `get` | - |
| **lasso** | `select` | `{points: [[x,y], ...]}` |
| | `clear` | - |
| **magicwand** | `select` | `{x, y, tolerance, contiguous}` |
| **brush** | `stroke` | `{points: [[x,y],...], color, size, hardness, opacity, flow}` |
| | `dot` | `{x, y, size, color}` |
| **spray** | `spray` | `{x, y, size, density, color, count}` |
| | `stroke` | `{points: [[x,y],...], ...}` |
| **eraser** | `stroke` | `{points: [[x,y],...], size}` |
| **line** | `draw` | `{start: [x,y], end: [x,y], color, width}` |
| **rect** | `draw` | `{x, y, width, height}` or `{start, end}` |
| **circle** | `draw` | `{center: [x,y], radius}` or `{start, end}` |
| **polygon** | `draw` | `{points: [[x,y],...], color, fill, stroke, strokeWidth}` |
| **fill** | `fill` | `{point: [x,y], color, tolerance}` |
| **gradient** | `draw` | `{x1, y1, x2, y2, type, startColor, endColor}` |
| **text** | `draw` | `{text, x, y, fontSize, fontFamily, color}` |
| **crop** | `crop` | `{x, y, width, height}` |

---

## Command Execution

### Execute Command
```
POST /api/sessions/{session}/documents/{doc}/command
Content-Type: application/json

{"command": "undo", "params": {}}
```

**Available Commands:**

| Category | Command | Parameters |
|----------|---------|------------|
| **Edit** | `undo` | - |
| | `redo` | - |
| **Clipboard** | `copy` | - |
| | `copy_merged` | - |
| | `cut` | - |
| | `paste` | - |
| | `paste_in_place` | - |
| **Selection** | `select_all` | - |
| | `deselect` | - |
| | `delete_selection` | - |
| **Layers** | `new_layer` | - |
| | `delete_layer` | - |
| | `duplicate_layer` | - |
| | `merge_down` | - |
| | `flatten` | - |
| **Colors** | `set_foreground_color` | `{color: "#rrggbb"}` |
| | `set_background_color` | `{color: "#rrggbb"}` |
| **Other** | `select_tool` | `{tool_id: "brush"}` |
| | `apply_filter` | `{filter_id, params: {...}}` |
| | `new_document` | `{width, height}` |

---

## Colors

### Get Colors
```
GET /api/sessions/{session}/colors
```

**Response:**
```json
{
    "foreground": "#000000",
    "background": "#FFFFFF",
    "recent_colors": ["#FF0000", "#00FF00"]
}
```

### Set Foreground Color
```
PUT /api/sessions/{session}/colors/foreground
Content-Type: application/json

{"color": "#FF0000"}
```

### Set Background Color
```
PUT /api/sessions/{session}/colors/background
Content-Type: application/json

{"color": "#FFFFFF"}
```

### Swap Colors
```
POST /api/sessions/{session}/colors/swap
```

### Reset Colors
```
POST /api/sessions/{session}/colors/reset
```
Reset to black/white.

---

## Active Tool

### Get Active Tool
```
GET /api/sessions/{session}/active-tool
```

**Response:**
```json
{
    "tool_id": "brush",
    "tool_properties": {
        "preset": "hard-round-md",
        "size": 20,
        "hardness": 100
    }
}
```

### Set Active Tool
```
PUT /api/sessions/{session}/active-tool
Content-Type: application/json

{"tool_id": "eraser"}
```

---

## Configuration

### Get Config
```
GET /api/sessions/{session}/config
GET /api/sessions/{session}/config?path=rendering.vectorSupersampleLevel
```
Get UIConfig settings. Omit `path` for full config.

### Set Config
```
PUT /api/sessions/{session}/config
Content-Type: application/json

{
    "path": "rendering.vectorSupersampleLevel",
    "value": 4
}
```

**Config Paths:**

| Path | Type | Description |
|------|------|-------------|
| `rendering.vectorSVGRendering` | boolean | Use SVG rendering for vectors |
| `rendering.vectorSupersampleLevel` | 1-4 | Supersampling level |
| `rendering.vectorAntialiasing` | boolean | Use anti-aliasing |
| `mode` | string | 'desktop', 'tablet', or 'limited' |

---

## Global Endpoints

### List Tools
```
GET /api/tools
GET /api/tools/{tool_id}
```
List available tools with their actions and parameters.

### List Filters
```
GET /api/filters
GET /api/filters/{filter_id}
```
List available filters with parameter schemas.

### Apply Filter (Binary)
```
POST /api/filters/{filter_id}
Content-Type: application/octet-stream
```
Apply filter using binary protocol.

### List Effect Types
```
GET /api/effects
GET /api/effects/{effect_type}
```
List available layer effect types with parameters.

### List Image Sources
```
GET /api/images/sources
```

### Get Sample Image
```
GET /api/images/{source}/{id}
```
Get sample image as raw RGBA.

### Data Cache Stats
```
GET /api/upload/stats
```
Get data cache statistics for monitoring.

**Response:**
```json
{
    "total_bytes": 1234567,
    "max_bytes": 524288000,
    "entry_count": 3,
    "pending_count": 1,
    "usage_percent": 0.24
}
```

---

## Data Transfer Architecture

The API uses a **push-based data transfer** mechanism to avoid WebSocket payload limits when fetching large images.

### How It Works

1. **Client requests image** via `GET /api/.../image`
2. **Backend generates unique request ID** and tells browser JS to push data
3. **Browser renders image** (with effects) and POSTs to `/api/upload/{request_id}`
4. **Backend receives data** and returns it to the waiting client

This allows transferring multi-megabyte images without hitting browser WebSocket limits.

### Upload Endpoint (Internal)
```
POST /api/upload/{request_id}
Content-Type: image/webp
X-Width: 800
X-Height: 600
X-Document-Id: doc-uuid
X-Document-Name: My Document
X-Layer-Id: layer-uuid (optional)
X-Layer-Name: Layer 1 (optional)
X-Layer-Type: raster (optional)
X-Data-Type: image

[binary data]
```
This endpoint is used internally by the browser. External clients should use the `/image` endpoints.

### Cache Configuration

The data cache has automatic garbage collection:
- **Max total storage**: 500 MB
- **Entry timeout**: 5 minutes
- **Cleanup interval**: 60 seconds

Old entries are evicted when storage limit is reached.

---

## Binary Protocol

For filter I/O, raw RGBA bytes are used for efficiency.

### Request Format
```
[4 bytes: metadata length (little-endian)]
[JSON metadata]
[raw RGBA bytes]
```

### Metadata Schema
```json
{
    "width": 800,
    "height": 600,
    "params": {
        "sigma": 2.0
    }
}
```

### Response Format
```
[raw RGBA bytes]
```
Same dimensions as input unless filter transforms size.

---

## Error Handling

Errors return JSON with error details:
```json
{
    "detail": "Error message"
}
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (invalid params)
- `404` - Resource not found (session, document, layer)
- `500` - Server error

---

## Quick Reference

| Operation | Endpoint |
|-----------|----------|
| List sessions | `GET /api/sessions` |
| Get session | `GET /api/sessions/current` |
| List documents | `GET /api/sessions/current/documents` |
| Create document | `POST /api/sessions/current/documents` |
| Get image (WebP) | `GET /api/sessions/current/documents/current/image` |
| Get image (PNG) | `GET /api/sessions/current/documents/current/image?format=png` |
| Get image (AVIF) | `GET /api/sessions/current/documents/current/image?format=avif` |
| Get image (with bg) | `GET /api/sessions/current/documents/current/image?bg=%23FFFFFF` |
| Get layer image | `GET /api/sessions/current/documents/current/layers/0/image` |
| Get layer SVG | `GET /api/sessions/current/documents/current/layers/0/image?format=svg` |
| List layers | `GET /api/sessions/current/documents/current/layers` |
| Get layer | `GET /api/sessions/current/documents/current/layers/0` |
| Execute tool | `POST /api/sessions/current/documents/current/tools/brush/execute` |
| Execute command | `POST /api/sessions/current/documents/current/command` |
| Undo | `POST /api/sessions/current/documents/current/history/undo` |
| Export document | `GET /api/sessions/current/documents/current/export` |
| List tools | `GET /api/tools` |
| List filters | `GET /api/filters` |
| List effects | `GET /api/effects` |

---

## Examples

### Draw a red line
```bash
curl -X POST "http://localhost:8080/api/sessions/current/documents/current/tools/line/execute" \
  -H "Content-Type: application/json" \
  -d '{"action": "draw", "params": {"start": [10, 10], "end": [100, 100], "color": "#FF0000", "width": 3}}'
```

### Add drop shadow to layer
```bash
curl -X POST "http://localhost:8080/api/sessions/current/documents/current/layers/0/effects" \
  -H "Content-Type: application/json" \
  -d '{"effect_type": "dropShadow", "params": {"offsetX": 5, "offsetY": 5, "blur": 10, "color": "#000000"}}'
```

### Get composite image (WebP, transparent)
```bash
curl "http://localhost:8080/api/sessions/current/documents/current/image" -o image.webp
```

### Get composite image (PNG with white background)
```bash
curl "http://localhost:8080/api/sessions/current/documents/current/image?format=png&bg=%23FFFFFF" -o image.png
```

### Get composite image (AVIF, best compression)
```bash
curl "http://localhost:8080/api/sessions/current/documents/current/image?format=avif" -o image.avif
```

### Get layer as PNG (with effects)
```bash
curl "http://localhost:8080/api/sessions/current/documents/current/layers/0/image?format=png" -o layer.png
```

### Get vector layer as SVG
```bash
curl "http://localhost:8080/api/sessions/current/documents/current/layers/1/image?format=svg" -o shapes.svg
```

### Get vector layer shapes as JSON
```bash
curl "http://localhost:8080/api/sessions/current/documents/current/layers/1/image?format=json" -o shapes.json
```

### Create new document
```bash
curl -X POST "http://localhost:8080/api/sessions/current/documents" \
  -H "Content-Type: application/json" \
  -d '{"width": 1920, "height": 1080, "name": "My Artwork"}'
```
