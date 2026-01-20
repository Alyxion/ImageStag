# Layer Groups

Stagforge supports organizing layers into folders (groups) for better document management. Groups can be nested, affect child visibility/opacity, and are fully serializable.

## Architecture

Layer groups use a **flat array with `parentId` references** instead of a nested tree structure:

```
Visual Stack:          Flat Array with parentId:
Group A                [Layer1, GroupA, Layer2, Layer3, GroupB, Layer4]
  Layer 2              parentId: null, null, A, A, null, B
  Layer 3
Group B
  Layer 4
Layer 1
```

**Advantages:**
- Minimal code changes - existing `layers[]` and `activeLayerIndex` work unchanged
- Backward compatible - old documents without `parentId` load normally
- Simpler serialization - no nested structure to flatten/unflatten
- Consistent with Photoshop/GIMP internal representations

## LayerGroup Class

`LayerGroup` is a container class with no canvas - it doesn't render anything directly.

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `id` | string | UUID | Unique identifier |
| `name` | string | 'Group' | Display name |
| `type` | string | 'group' | Layer type identifier |
| `parentId` | string\|null | null | Parent group ID (null = root) |
| `opacity` | number | 1.0 | Group opacity (0.0-1.0) |
| `blendMode` | string | 'passthrough' | Blend mode |
| `visible` | boolean | true | Group visibility |
| `locked` | boolean | false | Group lock state |
| `expanded` | boolean | true | UI collapsed/expanded state |

### Methods

- `isGroup()` - Returns `true`
- `isVector()` - Returns `false`
- `serialize()` - Export to JSON
- `deserialize(data)` - Restore from JSON
- `clone()` - Create a deep copy

## Passthrough Blend Mode

Groups default to `passthrough` blend mode, which means:
- Child layers blend **individually** with layers below the group
- Group opacity is **ignored** (children use their own opacity)
- Behaves as if the group doesn't exist visually

Non-passthrough blend modes (e.g., `multiply`, `screen`):
- Children are composited within the group first
- Group opacity **multiplies** with child opacity
- Group blends as a unit with layers below

## LayerStack Methods

### Helper Methods

```javascript
// Get direct children of a group
const children = layerStack.getChildren(groupId);

// Get all descendants (recursive)
const descendants = layerStack.getDescendants(groupId);

// Get parent group (or null for root layers)
const parent = layerStack.getParentGroup(layer);

// Check effective visibility (considers parent chain)
const visible = layerStack.isEffectivelyVisible(layer);

// Get effective opacity (multiplied through parent chain)
const opacity = layerStack.getEffectiveOpacity(layer);

// Check if effectively locked (considers parent chain)
const locked = layerStack.isEffectivelyLocked(layer);
```

### Group Operations

```javascript
// Create an empty group
const group = layerStack.createGroup({ name: 'My Group' });

// Create a group from selected layers
const group = layerStack.createGroupFromLayers(
    [layer1.id, layer2.id],
    'Group Name'
);

// Dissolve a group (children move to parent level)
layerStack.ungroupLayers(groupId);

// Move a layer into a group
layerStack.moveLayerToGroup(layerId, groupId);

// Remove layer from its group (move to root)
layerStack.removeLayerFromGroup(layerId);

// Delete a group
layerStack.deleteGroup(groupId, false);  // Keep children
layerStack.deleteGroup(groupId, true);   // Delete children too
```

### Layer Reordering

```javascript
// Move layer up/down in z-order
layerStack.moveLayerUp(index);
layerStack.moveLayerDown(index);

// Move to top/bottom
layerStack.moveLayerToTop(index);
layerStack.moveLayerToBottom(index);

// Move to specific index
layerStack.moveLayerToIndex(fromIndex, toIndex);
```

### Property Toggles

```javascript
// Toggle visibility
layerStack.toggleLayerVisibility(layerId);

// Set opacity
layerStack.setLayerOpacity(layerId, 0.75);

// Set blend mode
layerStack.setLayerBlendMode(layerId, 'multiply');

// Toggle lock
layerStack.toggleLayerLock(layerId);

// Toggle group expanded state
layerStack.toggleGroupExpanded(groupId);

// Rename layer or group
layerStack.renameLayer(layerId, 'New Name');
```

## Events

| Event | Data | Description |
|-------|------|-------------|
| `layer:group-created` | `{ group, index }` | Group was created |
| `layer:group-deleted` | `{ groupId, deleteChildren }` | Group was deleted |
| `layer:grouped` | `{ group, layerIds }` | Layers were grouped |
| `layer:ungrouped` | `{ groupId, children }` | Group was dissolved |
| `layer:moved-to-group` | `{ layerId, groupId }` | Layer moved into group |
| `layer:visibility-changed` | `{ layerId, visible }` | Visibility toggled |
| `layer:reordered` | `{ fromIndex, toIndex }` | Layer position changed |

## Serialization

Groups serialize with type markers for proper deserialization:

```json
{
    "_version": 1,
    "_type": "LayerGroup",
    "type": "group",
    "id": "uuid",
    "name": "Group Name",
    "parentId": null,
    "opacity": 1.0,
    "blendMode": "passthrough",
    "visible": true,
    "locked": false,
    "expanded": true
}
```

Regular layers include a `parentId` field:

```json
{
    "_version": 1,
    "_type": "Layer",
    "type": "raster",
    "id": "uuid",
    "name": "Layer Name",
    "parentId": "group-uuid",
    ...
}
```

## Rendering

Groups are skipped during rendering since they have no canvas. The renderer:

1. Skips layers where `layer.isGroup()` returns `true`
2. Uses `isEffectivelyVisible(layer)` instead of `layer.visible`
3. Uses `getEffectiveOpacity(layer)` instead of `layer.opacity`

```javascript
for (const layer of layerStack.layers) {
    if (layer.isGroup && layer.isGroup()) continue;
    if (!layerStack.isEffectivelyVisible(layer)) continue;
    const opacity = layerStack.getEffectiveOpacity(layer);
    // ... render layer with effective opacity
}
```

## History Integration

All group operations are tracked in history and can be undone/redone:

- Creating groups
- Deleting groups
- Moving layers in/out of groups
- Toggling visibility/lock
- Changing opacity/blend mode
- Reordering layers

The history system stores `parentId`, `type`, and `expanded` state for proper restoration.

## Keyboard Shortcuts (Planned)

| Shortcut | Action |
|----------|--------|
| Ctrl+G | Create group from selected layers |
| Ctrl+Shift+G | Ungroup selected group |
| Ctrl+] | Move layer up |
| Ctrl+[ | Move layer down |
| Ctrl+Shift+] | Move layer to top |
| Ctrl+Shift+[ | Move layer to bottom |

## Backward Compatibility

Documents without layer groups load normally:
- Layers without `parentId` default to `null` (root level)
- Old serialization format is auto-migrated
- No groups = flat layer list (same as before)
