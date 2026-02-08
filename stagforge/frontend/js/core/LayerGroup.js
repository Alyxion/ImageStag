/**
 * LayerGroup - Container for organizing layers into folders.
 *
 * Groups are non-renderable containers that:
 * - Organize layers hierarchically using flat array with parentId references
 * - Affect visibility and opacity of child layers
 * - Can be expanded/collapsed in the UI
 * - Do not have a canvas (not drawable)
 *
 * Extends BaseLayer for consistent interface across all layer types.
 */
import { BaseLayer } from './BaseLayer.js';
import { Frame } from './Frame.js';

export class LayerGroup extends BaseLayer {
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
        super({
            ...options,
            name: options.name || 'Group',
            type: 'group',
            // Groups don't have dimensions
            width: 0,
            height: 0,
            offsetX: 0,
            offsetY: 0
        });

        // Override blend mode default for groups
        this.blendMode = options.blendMode || 'passthrough';  // 'passthrough' lets children blend individually

        // UI state - whether group is expanded (showing children)
        this.expanded = options.expanded ?? true;

        // Groups don't have effects (children have their own)
        this.effects = [];
    }

    // ==================== Type Checks ====================

    /**
     * Check if this is a group.
     * @returns {boolean}
     */
    isGroup() {
        return true;
    }

    // ==================== Frames (Disabled) ====================

    /** Groups always have exactly 1 frame. */
    addFrame() { return -1; }
    removeFrame() { return false; }
    duplicateFrame() { return -1; }

    // ==================== Bounds ====================

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
     * Get document bounds - groups have no bounds.
     * @returns {null}
     */
    getDocumentBounds() {
        return null;
    }

    /**
     * Get visual bounds - groups have no bounds.
     * @returns {null}
     */
    getVisualBounds() {
        return null;
    }

    // ==================== Rendering (No-ops) ====================

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
     * Rasterize to document - groups have nothing to rasterize.
     * @returns {{canvas: null, bounds: null}}
     */
    rasterizeToDocument(clipBounds = null) {
        return { canvas: null, bounds: null, ctx: null };
    }

    /**
     * Render thumbnail - groups have nothing to render.
     * @returns {{canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D}}
     */
    renderThumbnail(maxWidth, maxHeight, docSize = null) {
        const canvas = document.createElement('canvas');
        canvas.width = maxWidth;
        canvas.height = maxHeight;
        return { canvas, ctx: canvas.getContext('2d') };
    }

    // ==================== SVG Export ====================

    /**
     * Convert this layer group to an SVG element for document export.
     * Creates a <g> with sf:type="group" that can contain child layer elements.
     *
     * @param {Document} xmlDoc - XML document for creating elements
     * @param {Element[]} [childElements] - Child layer elements to nest inside
     * @returns {Promise<Element>} SVG group element
     */
    async toSVGElement(xmlDoc, childElements = []) {
        const {
            STAGFORGE_NAMESPACE,
            STAGFORGE_PREFIX,
            createLayerGroup,
            createPropertiesElement
        } = await import('./svgExportUtils.js');

        // Create layer group with sf:type and sf:name
        const g = createLayerGroup(xmlDoc, this.id, 'group', this.name);

        // Add sf:properties element with group properties
        const properties = {
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
        const propsEl = createPropertiesElement(xmlDoc, properties);
        g.appendChild(propsEl);

        // Append child layer elements
        for (const child of childElements) {
            g.appendChild(child);
        }

        return g;
    }

    // ==================== Clone ====================

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

    // ==================== Serialization ====================

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
}

// Register LayerGroup with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('group', LayerGroup, ['LayerGroup']);
