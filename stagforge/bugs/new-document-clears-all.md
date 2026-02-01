# CRITICAL: New Document Clears All Existing Documents

## Status: FIXED

## Problem
When creating a new document (File > New), ALL existing documents were closed and auto-save data was cleared.

## Root Cause
`DocumentUIManager.js` `newDocument()` function was clearing all auto-save data and removing all existing documents before creating a new one.

## Fix Applied
Simplified `newDocument()` to just call `createDocument()` without clearing anything:

```javascript
async newDocument(width, height) {
    const app = this.getState();
    if (!app?.documentManager) return;

    app.documentManager.createDocument({
        width: width,
        height: height,
        activate: true
    });

    this.updateLayerList();
    this.fitToWindow();
    this.emitStateUpdate();
}
```

## Files Modified
- `stagforge/frontend/js/editor/mixins/DocumentUIManager.js`
