# CRITICAL: Multiple Documents Lost on Reload

## Status: FIXED

## Problem
When multiple documents were open and the page was reloaded, only the most recently modified document survived.

## Root Cause
In `AutoSave.js`, restored documents were given NEW random IDs, but ZIP files kept OLD IDs. The orphan cleanup then deleted the old ZIP files, losing unchanged documents.

## Fix Applied
Removed the line that generated new random IDs on restore. Documents now keep their original IDs from the serialized data:

```javascript
// Before (broken):
const doc = await Document.deserialize(docData, this.app.eventBus);
doc.id = crypto.randomUUID();  // REMOVED

// After (fixed):
const doc = await Document.deserialize(docData, this.app.eventBus);
// Keeps original ID for stable auto-save
```

## Files Modified
- `stagforge/frontend/js/core/AutoSave.js`
