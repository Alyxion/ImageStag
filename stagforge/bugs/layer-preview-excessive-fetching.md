# Layer Preview Images Fetched Excessively

**Status: IMPLEMENTED** - Change tracking infrastructure added, client-side optimization pending.

## Implementation Complete

- `changeCounter` and `lastChangeTimestamp` added to Layer (JS + Python)
- `changeCounter` and `lastChangeTimestamp` added to Document (JS + Python)
- API endpoint `GET /api/sessions/{session}/documents/{doc}/changes` created
- `markChanged()` method added to BaseLayer, called automatically on `invalidateImageCache()`

---

## Description

In the API browse page, layer preview images are always fetched regardless of whether the layer content has changed. With dozens of layers, this creates unnecessary network traffic and performance overhead.

## Steps to Reproduce

1. Open a document with many layers (10+)
2. Open the API browse page or layer panel
3. Observe network requests - all layer previews are fetched repeatedly
4. Make no changes to any layer
5. Previews continue to be re-fetched on each poll/refresh cycle

## Expected Behavior

Layer previews should only be fetched when the layer content has actually changed. The client should be able to check if a layer has been modified before requesting its preview image.

## Proposed Solution

### 1. Add Change Tracking to Layer Attributes

Add to both Python (`stagforge/layers/`) and JavaScript (`stagforge/frontend/js/core/Layer.js`):

```javascript
// Layer attributes
{
    changeCounter: 0,        // Increments on every modification
    lastChangeTimestamp: 0,  // Unix timestamp of last change
}
```

```python
# Python layer model
class BaseLayer:
    change_counter: int = 0
    last_change_timestamp: float = 0.0
```

### 2. Add Change Tracking to Document Attributes

Add to both Python (`stagforge/layers/document.py`) and JavaScript (`stagforge/frontend/js/core/Document.js`):

```javascript
// Document attributes
{
    changeCounter: 0,        // Increments on any document change
    lastChangeTimestamp: 0,  // Unix timestamp of last change
}
```

### 3. Create Central Metadata API Endpoint

Add a lightweight endpoint polled ~1/second that returns change metadata only:

```
GET /api/sessions/{session}/documents/{doc}/changes
```

Response:
```json
{
    "document": {
        "changeCounter": 42,
        "lastChangeTimestamp": 1707123456789
    },
    "layers": {
        "layer-id-1": { "changeCounter": 5, "lastChangeTimestamp": 1707123456000 },
        "layer-id-2": { "changeCounter": 12, "lastChangeTimestamp": 1707123456500 }
    }
}
```

### 4. Client-Side Caching Logic

The client should:
1. Poll the `/changes` endpoint periodically (~1s)
2. Compare `changeCounter` with locally cached values
3. Only fetch layer preview images when `changeCounter` has increased
4. Cache preview images with their corresponding `changeCounter`

## Affected Files

- `stagforge/frontend/js/core/Layer.js` - Add change tracking
- `stagforge/frontend/js/core/Document.js` - Add change tracking
- `stagforge/layers/base.py` - Add change tracking to Python models
- `stagforge/layers/document.py` - Add document-level change tracking
- `stagforge/api/documents.py` - Add `/changes` endpoint
- API browse page components - Implement smart fetching

## Priority

Medium - Performance optimization, becomes critical with large documents.
