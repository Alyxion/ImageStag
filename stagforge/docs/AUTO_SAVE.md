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
2. Serializes all open documents to SFR ZIP format (same as .sfr files)
3. Uses cached WebP blobs for unchanged layers (fast saves)
4. Saves to OPFS under a unique tab ID
5. Updates the manifest file

### Automatic Restoration

On page load/refresh:
1. Checks for saved documents in OPFS for this tab
2. If found, restores all documents with their layers and history position
3. If not found, creates a new "Untitled" document

## Storage Structure

```
stagforge_autosave/           # OPFS root
└── {tab-id}/                 # Unique per browser tab
    ├── manifest.json         # List of saved documents with history tracking
    ├── doc_{uuid}.sfr        # SFR ZIP file (same format as .sfr files)
    └── _session.json         # Session close timestamp
```

### Document Format

Documents are stored as SFR ZIP files (identical format to saved .sfr files):
```
doc_{uuid}.sfr (ZIP archive)
├── content.json              # Document structure
└── layers/
    └── {layer-id}.webp       # Raster layer images
```

See [SFR_FILE_FORMAT.md](./SFR_FILE_FORMAT.md) for full format specification.

### Manifest Format

The manifest tracks all documents and their history state:
```json
{
    "tabId": "uuid",
    "savedAt": 1705689600000,
    "documents": [
        {
            "id": "uuid",
            "name": "My Drawing",
            "savedAt": 1705689600000,
            "historyIndex": 5
        }
    ]
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

## Status Indicators

The editor provides multiple visual indicators for document state and auto-save status.

### Document Tab Modified Indicator

When a document has unsaved changes, the tab displays:

- **Yellow dot (●)** after the document name with a subtle pulse animation
- **Highlighted background** with a warning-colored tint

CSS classes:
```css
.document-tab.modified {
    background-color: rgba(255, 165, 0, 0.12);
}
.document-tab.modified .document-tab-name::after {
    content: ' ●';
    color: var(--warning);
    animation: modified-pulse 2s ease-in-out infinite;
}
```

### Auto-Save Status Bar

The status bar shows real-time auto-save state with icons and animations:

| State | Icon | Visual | Meaning |
|-------|------|--------|---------|
| Saving | ↻ (spinner) | Blue pulse animation | Currently writing to OPFS |
| Just Saved | ✓ | Green flash animation | Save completed (shows for 3 seconds) |
| Saved | ✓ | Green background | Last save time displayed |
| (no indicator) | — | Default | No unsaved changes |

CSS classes:
```css
.status-autosave.saving {
    animation: autosave-pulse 1.5s ease-in-out infinite;
}
.status-autosave.saved {
    background-color: rgba(40, 167, 69, 0.15);
}
.status-autosave.just-saved {
    animation: autosave-flash 0.5s ease-out;
}
```

### Events

The auto-save system triggers events that update the UI:

| Event | Trigger | UI Update |
|-------|---------|-----------|
| `document:modified` | Any document change | Tab shows modified indicator |
| `autosave:start` | Auto-save begins | Status shows "Saving..." with spinner |
| `autosave:complete` | Auto-save finishes | Status shows "✓ Saved" with flash |

### Implementation Details

The `justSaved` flag is used to show the flash animation:
```javascript
// In canvas_editor.js
this.justSaved = true;
setTimeout(() => {
    this.justSaved = false;
}, 3000);  // Flash visible for 3 seconds
```

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
