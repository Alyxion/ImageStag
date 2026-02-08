# Versioning System

Stagforge uses per-element versioning to support incremental migration of serialized data. This allows parameters to change over time without invalidating entire documents.

## Overview

Every serializable element (layers, effects, filters) has a `version` or `VERSION` field that tracks its serialization format version. When deserializing data, the version is checked and migration logic is applied if needed.

## Benefits

- **Incremental migration**: Fix parameter changes without invalidating entire files
- **Per-class versioning**: Each element type migrates independently
- **Backwards compatibility**: Old documents load correctly with new code
- **Forward planning**: Easy to add migrations for future changes

## JavaScript Elements

JavaScript classes use uppercase `VERSION` (static property):

### Core Classes

| Class | File | Current Version | Notes |
|-------|------|-----------------|-------|
| Document | `core/Document.js` | 1 | |
| Layer | `core/Layer.js` | 1 | |
| TextLayer | `core/TextLayer.js` | 1 | |
| StaticSVGLayer | `core/StaticSVGLayer.js` | 1 | Replaced VectorLayer |
| LayerEffect | `effects/LayerEffect.js` | 1 | |

### Effect Classes

| Class | File | Current Version |
|-------|------|-----------------|
| DropShadowEffect | `effects/DropShadowEffect.js` | 1 |
| InnerShadowEffect | `effects/InnerShadowEffect.js` | 1 |
| OuterGlowEffect | `effects/OuterGlowEffect.js` | 1 |
| InnerGlowEffect | `effects/InnerGlowEffect.js` | 1 |
| BevelEmbossEffect | `effects/BevelEmbossEffect.js` | 1 |
| StrokeEffect | `effects/StrokeEffect.js` | 1 |
| ColorOverlayEffect | `effects/ColorOverlayEffect.js` | 1 |

### Serialization Format

```javascript
// Every serialized object includes:
{
    "_version": 1,
    "_type": "Layer",
    // ... rest of data
}
```

### Migration Pattern (JavaScript)

```javascript
class Layer {
    static VERSION = 1;

    serialize() {
        return {
            _version: Layer.VERSION,
            _type: 'Layer',
            // ... fields
        };
    }

    static migrate(data) {
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Add default offsetX/offsetY
        if (data._version < 1) {
            data.offsetX = data.offsetX ?? 0;
            data.offsetY = data.offsetY ?? 0;
            data._version = 1;
        }

        // Future: v1 -> v2
        // if (data._version < 2) { ... data._version = 2; }

        return data;
    }

    static async deserialize(data) {
        data = Layer.migrate(data);
        // ... create instance from migrated data
    }
}
```

## Python Elements

Python classes use lowercase `version` (class attribute):

### Filter Base

```python
class BaseFilter(ABC):
    name: str = "Base Filter"
    description: str = "Description"
    category: str = "uncategorized"
    version: int = 1  # Serialization version
```

### Filter Categories

| Category | Filters |
|----------|---------|
| blur | GaussianBlur, BoxBlur, MedianBlur, BilateralBlur, MotionBlur |
| sharpen | UnsharpMask |
| edge | Sobel, Canny, Laplacian, Prewitt, Scharr, FindContours |
| color | Grayscale, Invert, BrightnessContrast, Sepia, HueSaturation, ColorBalance, Gamma, AutoContrast, EqualizeHistogram, ChannelMixer, Vibrance, Temperature |
| noise | AddNoise, Denoise, DenoiseTv, DenoiseWavelet, DenoiseBilateral, RemoveHotPixels |
| threshold | BinaryThreshold, OtsuThreshold, AdaptiveThreshold, ColorThreshold, Posterize |
| morphology | Erode, Dilate, Open, Close, MorphologyGradient, TopHat, BlackHat |
| artistic | Emboss, OilPainting, PencilSketch, Cartoon, Stylization, DetailEnhance, EdgePreserving, Pixelate, Vignette |

All filters are currently at version 1.

## Adding Migrations

### When to Bump Version

Bump the version when:
- Adding a required parameter (provide default in migration)
- Renaming a parameter
- Changing parameter type or range
- Restructuring serialized data

### Migration Example

```javascript
// Example: Adding 'quality' parameter in v2
static migrate(data) {
    if (data._version === undefined) data._version = 0;

    if (data._version < 1) {
        data.offsetX = data.offsetX ?? 0;
        data._version = 1;
    }

    if (data._version < 2) {
        data.quality = data.quality ?? 'high';  // New param with default
        data._version = 2;
    }

    return data;
}
```

### Testing Migrations

1. Save a document with the current version
2. Modify the class to add migration logic
3. Bump VERSION
4. Reload the document - it should migrate automatically

## Integration with Auto-Save

The auto-save system (see [AUTO_SAVE.md](./AUTO_SAVE.md)) stores documents with version information. When documents are restored:

1. Document is deserialized
2. `Document.migrate()` is called
3. Each layer's `migrate()` is called
4. Each effect's `migrate()` is called

This ensures old auto-saved documents load correctly even after code updates.

## Best Practices

1. **Never break backwards compatibility** - always add migrations
2. **Use sensible defaults** - migrated values should work reasonably
3. **Test migrations** - save before, update code, load after
4. **Document changes** - note what changed in each version
5. **Increment, don't skip** - go from v1 to v2 to v3, never skip
