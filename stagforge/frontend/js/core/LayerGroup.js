/**
 * LayerGroup - Container for organizing layers into folders.
 *
 * Groups are non-renderable containers that:
 * - Organize layers hierarchically using flat array with parentId references
 * - Affect visibility and opacity of child layers
 * - Can be expanded/collapsed in the UI
 * - Do not have a canvas (not drawable)
 */

export class LayerGroup {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {string} [options.id] - Unique identifier
     * @param {string} [options.name] - Display name
     * @param {string} [options.parentId] - Parent group ID (null for root)
     * @param {number} [options.opacity] - Opacity 0.0-1.0
     * @param {string} [options.blendMode] - Blend mode (passthrough or specific)
     * @param {boolean} [options.visible] - Visibility
     * @param {boolean} [options.locked] - Lock state
     * @param {boolean} [options.expanded] - Expanded state in UI
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.name = options.name || 'Group';
        this.type = 'group';

        // Parent group ID (null = root level)
        this.parentId = options.parentId || null;

        // Group properties
        this.opacity = options.opacity ?? 1.0;
        this.blendMode = options.blendMode || 'passthrough';  // 'passthrough' lets children blend individually
        this.visible = options.visible ?? true;
        this.locked = options.locked ?? false;

        // UI state - whether group is expanded (showing children)
        this.expanded = options.expanded ?? true;

        // Groups don't have effects (children have their own)
        this.effects = [];
    }

    /**
     * Check if this is a group.
     * @returns {boolean}
     */
    isGroup() {
        return true;
    }

    /**
     * Check if this is a vector layer.
     * @returns {boolean}
     */
    isVector() {
        return false;
    }

    /**
     * Get bounds - groups have no bounds of their own.
     * @returns {null}
     */
    getBounds() {
        return null;
    }

    /**
     * Get content bounds - groups have no content.
     * @returns {null}
     */
    getContentBounds() {
        return null;
    }

    /**
     * Groups cannot be rendered directly.
     */
    render() {
        // No-op - groups don't render
    }

    /**
     * Rotate the layer group. Groups have no content to rotate,
     * but this method exists for API consistency.
     * Child layers are rotated individually by Document.rotateCanvas().
     *
     * @param {number} degrees - Rotation angle (90, 180, or 270)
     * @param {number} oldDocWidth - Document width before rotation
     * @param {number} oldDocHeight - Document height before rotation
     * @param {number} newDocWidth - Document width after rotation
     * @param {number} newDocHeight - Document height after rotation
     * @returns {Promise<void>}
     */
    async rotateCanvas(degrees, oldDocWidth, oldDocHeight, newDocWidth, newDocHeight) {
        // No-op - groups have no canvas to rotate
    }

    /**
     * Mirror the layer group. Groups have no content to mirror,
     * but this method exists for API consistency.
     * Child layers are mirrored individually by Document.mirrorCanvas().
     *
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @param {number} docWidth - Document width
     * @param {number} docHeight - Document height
     * @returns {Promise<void>}
     */
    async mirrorContent(direction, docWidth, docHeight) {
        // No-op - groups have no canvas to mirror
    }

    /**
     * Clone this group (without children - they clone separately).
     * @returns {LayerGroup}
     */
    clone() {
        return new LayerGroup({
            name: `${this.name} (copy)`,
            parentId: this.parentId,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            expanded: this.expanded
        });
    }

    /**
     * Serialize for history/save.
     * @returns {Object}
     */
    serialize() {
        return {
            _version: LayerGroup.VERSION,
            _type: 'LayerGroup',
            type: 'group',
            id: this.id,
            name: this.name,
            parentId: this.parentId,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            expanded: this.expanded
        };
    }

    /**
     * Migrate serialized data from older versions.
     * @param {Object} data - Serialized group data
     * @returns {Object} - Migrated data at current version
     */
    static migrate(data) {
        // Handle pre-versioned data
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Initial version
        if (data._version < 1) {
            data.parentId = data.parentId ?? null;
            data.expanded = data.expanded ?? true;
            data.blendMode = data.blendMode || 'passthrough';
            data._version = 1;
        }

        // Future migrations:
        // if (data._version < 2) { ... data._version = 2; }

        return data;
    }

    /**
     * Restore from serialized data.
     * @param {Object} data
     * @returns {LayerGroup}
     */
    static deserialize(data) {
        // Migrate to current version
        data = LayerGroup.migrate(data);

        return new LayerGroup({
            id: data.id,
            name: data.name,
            parentId: data.parentId,
            opacity: data.opacity,
            blendMode: data.blendMode,
            visible: data.visible,
            locked: data.locked,
            expanded: data.expanded
        });
    }

    /**
     * Check if this is a text layer.
     * @returns {boolean}
     */
    isText() {
        return false;
    }

    /**
     * Check if this is an SVG layer.
     * @returns {boolean}
     */
    isSVG() {
        return false;
    }
}

// Register LayerGroup with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('group', LayerGroup, ['LayerGroup']);
