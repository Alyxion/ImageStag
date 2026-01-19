# Auto-Save Feature

Stagforge automatically saves your documents to browser storage, protecting against data loss from browser crashes, accidental tab closures, or page refreshes.

## How It Works

### Automatic Saving

- **Check interval**: Every 5 seconds
- **Change detection**: Compares history index to detect modifications
- **Storage**: Browser's Origin Private File System (OPFS)
- **Scope**: Per-browser-tab isolation

When you make changes (draw, add layers, etc.), the auto-save system:
1. Detects the history index has changed
2. Serializes all open documents (layers as PNG data URLs)
3. Saves to OPFS under a unique tab ID
4. Updates the manifest file

### Automatic Restoration

On page load/refresh:
1. Checks for saved documents in OPFS for this tab
2. If found, restores all documents with their layers and history position
3. If not found, creates a new "Untitled" document

## Storage Structure

```
stagforge_autosave/           # OPFS root
└── {tab-id}/                 # Unique per browser tab
    ├── manifest.json         # List of saved documents
    ├── doc_{uuid}.json       # Full document data (layers, state)
    └── _session.json         # Session close timestamp
```

### Document Format

Each document is serialized as JSON:
```json
{
    "_version": 1,
    "_historyIndex": 5,
    "_savedAt": 1705689600000,
    "id": "uuid",
    "name": "My Drawing",
    "width": 800,
    "height": 600,
    "layers": [
        {
            "_version": 1,
            "id": "layer-uuid",
            "name": "Layer 1",
            "imageData": "data:image/png;base64,...",
            "opacity": 1.0,
            "blendMode": "normal",
            "visible": true
        }
    ],
    "activeLayerIndex": 0,
    "foregroundColor": "#000000",
    "backgroundColor": "#FFFFFF",
    "viewState": { "zoom": 1.0, "panX": 0, "panY": 0 }
}
```

## Session Cleanup

Closed tabs are automatically cleaned up to prevent storage bloat.

### How It Works

**When a tab closes:**
1. `beforeunload` event fires
2. Writes `_session.json` with close timestamp
3. Records 30-minute timeout period

**When any tab opens:**
1. Scans all tab directories in OPFS
2. Checks each `_session.json` for expiration
3. If `now > closedAt + timeout`, deletes that tab's data

### Timeout Behavior

| Scenario | Result |
|----------|--------|
| Tab closed, reopened within 30 min | Documents restored |
| Tab closed, reopened after 30 min | Data deleted, fresh start |
| Tab crashed (no `_session.json`) | Data preserved indefinitely |
| Browser closed entirely | Same as tab close |

### Configuration

Default timeout is 30 minutes. To change:
```javascript
app.autoSave = new AutoSave(app, {
    interval: 5000,          // Check every 5 seconds
    sessionTimeout: 3600000  // 1 hour timeout
});
```

## Status Indicator

The editor shows auto-save status in the status bar:

| Status | Meaning |
|--------|---------|
| "Saving..." | Currently writing to OPFS |
| "Saved 2:30 PM" | Last successful save time |
| (no indicator) | No unsaved changes |

## Versioning

Each serializable element (Document, Layer, TextLayer, VectorLayer, LayerEffect) includes a version number:

```json
{
    "_version": 1,
    "_type": "Layer",
    ...
}
```

This enables incremental migration when the format changes:
- Old documents are automatically upgraded on load
- Each class handles its own migration independently
- No need to invalidate entire files for minor changes

## Troubleshooting

### Documents Not Restoring

1. **Different browser tab**: Each tab has isolated storage
2. **Timeout expired**: Data cleaned up after 30 minutes
3. **OPFS not available**: Requires HTTPS or localhost

### Storage Full

OPFS is subject to browser quota. Large documents with many layers may fill storage.

To clear auto-save data:
```javascript
app.autoSave.clear();  // Clears current tab's data
```

### Debugging

Check browser DevTools → Application → Storage → Origin Private File System:
- `stagforge_autosave/` directory contains all saved data
- Each subdirectory is a tab's storage

Console logs show auto-save activity:
```
[AutoSave] Initialized with tabId: abc123
[AutoSave] Saved 2 document(s)
[AutoSave] Restored 2 document(s) from auto-save
[AutoSave] Cleaned up stale session: xyz789
```

## Browser Support

OPFS requires:
- Chrome 86+
- Firefox 111+
- Safari 15.2+
- Secure context (HTTPS or localhost)

## Privacy

- All data stays in your browser
- Nothing is sent to servers
- Data is origin-scoped (only accessible from same domain)
- Not visible in user's file system
