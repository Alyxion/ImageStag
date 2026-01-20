# SFR File Format

## Overview

SFR (Stagforge) is a ZIP-based document format that separates JSON metadata from binary layer data. This provides:

- **Efficient storage**: Binary formats (WebP, AVIF) are more compact than Base64-encoded PNG
- **Streaming support**: Large layers can be loaded on-demand
- **Clear separation**: JSON structure is human-readable without binary noise
- **Future extensibility**: Easy to add new layer types and formats

## File Extension

`.sfr` - A standard ZIP archive with a specific internal structure.

## Archive Structure

```
document.sfr (ZIP archive)
├── content.json          # Main document structure
├── layers/
│   ├── {layer-id}.webp   # 8-bit raster layers
│   ├── {layer-id}.avif   # Float layers (future)
│   └── {layer-id}.svg    # SVG layers (future)
└── thumbnails/           # Optional thumbnails (future)
    └── preview.webp
```

## content.json Structure

```json
{
    "format": "stagforge",
    "version": 2,
    "document": {
        "_version": 1,
        "_type": "Document",
        "id": "uuid",
        "name": "My Document",
        "width": 800,
        "height": 600,
        "foregroundColor": "#000000",
        "backgroundColor": "#FFFFFF",
        "activeLayerIndex": 0,
        "viewState": {
            "zoom": 1.0,
            "panX": 0,
            "panY": 0
        },
        "layers": [
            {
                "_version": 1,
                "_type": "Layer",
                "type": "raster",
                "id": "layer-uuid",
                "name": "Background",
                "width": 800,
                "height": 600,
                "offsetX": 0,
                "offsetY": 0,
                "opacity": 1.0,
                "blendMode": "normal",
                "visible": true,
                "locked": false,
                "imageFile": "layers/layer-uuid.webp",
                "imageFormat": "webp",
                "effects": []
            },
            {
                "_version": 2,
                "_type": "VectorLayer",
                "type": "vector",
                "id": "vector-uuid",
                "name": "Shapes",
                "shapes": [
                    {
                        "type": "rect",
                        "x": 100,
                        "y": 100,
                        "width": 200,
                        "height": 150,
                        "fill": true,
                        "fillColor": "#FF0000"
                    }
                ],
                "effects": []
            },
            {
                "_version": 1,
                "_type": "TextLayer",
                "type": "text",
                "id": "text-uuid",
                "name": "Title",
                "text": "Hello World",
                "fontSize": 32,
                "fontFamily": "Arial",
                "color": "#000000",
                "x": 100,
                "y": 400,
                "effects": []
            }
        ]
    },
    "metadata": {
        "createdAt": "2025-01-19T12:00:00Z",
        "modifiedAt": "2025-01-19T12:30:00Z",
        "software": "Stagforge 1.0"
    }
}
```

## Layer Types

### Raster Layers (8-bit)

Standard image layers with pixel data stored as WebP files.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"raster"` |
| `imageFile` | string | Path to WebP file in archive |
| `imageFormat` | string | `"webp"` |

**File format**: WebP with lossless compression for quality preservation.

### Float Layers (Future)

High dynamic range layers with 32-bit float data stored as AVIF.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"float"` |
| `imageFile` | string | Path to AVIF file in archive |
| `imageFormat` | string | `"avif"` |
| `bitDepth` | number | `32` |

### Vector Layers

Vector shapes stored inline in JSON. No external file.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"vector"` |
| `shapes` | array | Shape objects (rect, ellipse, line, polygon, path) |

### SVG Layers (Future)

Full SVG content stored as external SVG files.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"svg"` |
| `svgFile` | string | Path to SVG file in archive |

### Text Layers

Text content stored inline in JSON for editability.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"text"` |
| `text` | string | Text content |
| `fontSize` | number | Font size in pixels |
| `fontFamily` | string | Font family name |
| `color` | string | Text color (hex) |
| `x`, `y` | number | Position in document |

### Layer Groups

Container layers for organizing other layers into folders. No external file.

| Field | Type | Description |
|-------|------|-------------|
| `_type` | string | `"LayerGroup"` |
| `type` | string | `"group"` |
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `parentId` | string\|null | Parent group ID (null = root) |
| `opacity` | number | Group opacity (0.0-1.0) |
| `blendMode` | string | Blend mode (default: `"passthrough"`) |
| `visible` | boolean | Group visibility |
| `locked` | boolean | Group lock state |
| `expanded` | boolean | UI collapsed/expanded state |

**Example**:
```json
{
    "_version": 1,
    "_type": "LayerGroup",
    "type": "group",
    "id": "group-uuid",
    "name": "Effects",
    "parentId": null,
    "opacity": 1.0,
    "blendMode": "passthrough",
    "visible": true,
    "locked": false,
    "expanded": true
}
```

**Note**: Layer groups have no image data. Child layers reference the group via their `parentId` field.

### Layer Hierarchy (parentId)

All layers (raster, vector, text, groups) can have a `parentId` field:

| Value | Meaning |
|-------|---------|
| `null` | Root-level layer (no parent) |
| `"group-uuid"` | Child of the specified group |

Example document with groups:
```json
"layers": [
    { "type": "group", "id": "grp1", "name": "Background", "parentId": null },
    { "type": "raster", "id": "bg", "name": "Sky", "parentId": "grp1" },
    { "type": "raster", "id": "fg", "name": "Trees", "parentId": "grp1" },
    { "type": "group", "id": "grp2", "name": "Characters", "parentId": null },
    { "type": "raster", "id": "char1", "name": "Player", "parentId": "grp2" }
]
```

## Image Formats

### WebP (8-bit raster)

- **Compression**: Lossless
- **Color space**: sRGB
- **Alpha**: Supported
- **Quality**: 100 (lossless mode)

WebP is chosen for 8-bit layers because:
- Smaller than PNG (typically 20-30% reduction)
- Browser-native support
- Lossless mode preserves pixel-perfect quality

### AVIF (Float layers - Future)

- **Compression**: Lossless
- **Bit depth**: 10-12 bits per channel
- **HDR**: Supported
- **Alpha**: Supported

AVIF is chosen for float layers because:
- Supports high bit depth
- Excellent compression for HDR content
- Growing browser support

## Version History

| Version | Changes |
|---------|---------|
| 2 | Current: ZIP-based format with separate binary files |

## Implementation Notes

### Browser Support

The implementation uses:
- **JSZip**: Static library at `frontend/js/lib/jszip.min.js` for ZIP creation/extraction
- **Canvas API**: For WebP encoding via `canvas.toBlob('image/webp')`
- **Blob API**: For efficient binary handling

JSZip is loaded via script tag in `main.py` before the editor initializes.

### Saving Process

1. Serialize document to JSON (without image data)
2. For each raster layer:
   - Check if cached WebP blob exists (skip encoding if unchanged)
   - If no cache: Convert canvas to WebP blob and cache it
   - Add cached blob to ZIP as `layers/{layer-id}.webp`
   - Set `imageFile` reference in JSON
3. Add `content.json` to ZIP
4. Generate ZIP blob with STORE compression (no compression)

**Why STORE compression?** WebP images are already compressed. Applying DEFLATE compression would:
- Waste CPU cycles
- Potentially increase file size (compressed data doesn't compress well)
- Slow down save operations

### WebP Caching

Layers cache their WebP blob after first encoding. This cache is invalidated when:
- `setImageData()` is called (filter results)
- `clear()` is called
- `fill()` is called
- `expandToInclude()` resizes the canvas
- `trimToContent()` resizes the canvas
- Any tool modifies the layer (via `invalidateImageCache()`)

Benefits:
- Unchanged layers save instantly (no re-encoding)
- AutoSave and manual save both benefit from the cache
- Memory overhead is minimal (WebP is compact)

### Loading Process

1. Extract ZIP archive
2. Parse `content.json`
3. For each layer with `imageFile`:
   - Extract the referenced file
   - Load as Image/Blob
   - Draw to layer canvas
4. Vector/text layers: Restore from inline JSON

### Error Handling

| Error | Handling |
|-------|----------|
| Missing `content.json` | Invalid file error |
| Missing layer file | Skip layer, log warning |
| Corrupt image | Skip layer, log warning |
| Unsupported format | Fallback to raw if possible |

## Typical File Sizes

| Content | Approximate Size |
|---------|------------------|
| 800x600 white canvas | ~0.5 KB |
| 800x600 photo | ~200 KB |
| 4K document with layers | ~4 MB |

WebP lossless compression provides significant savings compared to uncompressed or PNG formats.

## AutoSave Integration

AutoSave uses the same SFR ZIP format for OPFS (Origin Private File System) storage:

- **Consistent format**: Both `.sfr` files and autosaved documents use identical ZIP structure
- **Shared code**: `serializeDocumentToZip()` and `parseDocumentZip()` are used by both
- **Cached WebP**: AutoSave benefits from the same WebP caching as manual save
- **File extension**: AutoSave files are named `doc_{id}.sfr` in OPFS

This ensures:
1. Documents can be recovered from autosave with full fidelity
2. No format conversion is needed between autosave and file save
3. Both save paths benefit from caching optimizations

## Security Considerations

- ZIP bomb protection: Limit decompressed size
- Path traversal: Validate all file paths within archive
- Content validation: Verify image formats before loading
