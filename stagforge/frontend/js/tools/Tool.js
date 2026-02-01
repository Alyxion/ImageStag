/**
 * Tool - Abstract base class for all drawing tools.
 * Each tool should be in its own file and extend this class.
 *
 * Tools are self-describing and auto-discovered. Define these static properties:
 *   - id: Unique tool identifier (required)
 *   - name: Display name (required)
 *   - icon: Icon identifier for fallback (optional)
 *   - iconEntity: HTML entity for icon display (required for UI)
 *   - shortcut: Keyboard shortcut key, e.g., 'b' (optional)
 *   - group: Group name for toolbar organization (required)
 *   - groupShortcut: Shortcut to activate group's first tool (optional)
 *   - priority: Sort order within group, lower = higher in list (default 100)
 *   - cursor: CSS cursor style (default 'default')
 *   - limitedMode: Include in limited/simple mode? (default false)
 */
export class Tool {
    // Static properties - override in subclasses
    static id = 'tool';
    static name = 'Tool';
    static icon = 'cursor';
    static iconEntity = '&#9679;';  // Default circle
    static shortcut = null;         // Tool-specific shortcut
    static group = 'misc';          // Group name for toolbar
    static groupShortcut = null;    // Shortcut for the group
    static priority = 100;          // Sort order (lower = higher)
    static cursor = 'default';
    static limitedMode = false;     // Available in limited mode?

    /**
     * Layer types this tool can operate on.
     * Override in subclasses to specify compatible layer types.
     * @type {{raster?: boolean, text?: boolean, svg?: boolean, group?: boolean}}
     */
    static layerTypes = { raster: true, text: true, svg: true, group: false };

    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.active = false;
    }

    /**
     * Called when tool is selected.
     */
    activate() {
        this.active = true;
        this.app.displayCanvas.style.cursor = this.constructor.cursor;
    }

    /**
     * Called when tool is deselected.
     */
    deactivate() {
        this.active = false;
    }

    /**
     * Handle mouse down event.
     * @param {MouseEvent} e - Mouse event
     * @param {number} x - Canvas X coordinate
     * @param {number} y - Canvas Y coordinate
     */
    onMouseDown(e, x, y) {}

    /**
     * Handle mouse move event.
     * @param {MouseEvent} e - Mouse event
     * @param {number} x - Canvas X coordinate
     * @param {number} y - Canvas Y coordinate
     */
    onMouseMove(e, x, y) {}

    /**
     * Handle mouse up event.
     * @param {MouseEvent} e - Mouse event
     * @param {number} x - Canvas X coordinate
     * @param {number} y - Canvas Y coordinate
     */
    onMouseUp(e, x, y) {}

    /**
     * Handle mouse leave event.
     * @param {MouseEvent} e - Mouse event
     */
    onMouseLeave(e) {}

    /**
     * Handle key down event.
     * @param {KeyboardEvent} e - Keyboard event
     */
    onKeyDown(e) {}

    /**
     * Handle key up event.
     * @param {KeyboardEvent} e - Keyboard event
     */
    onKeyUp(e) {}

    /**
     * Get tool properties for the properties panel.
     * @returns {Array<Object>} Property definitions
     */
    getProperties() {
        return [];
    }

    /**
     * Set a property value.
     * @param {string} id - Property ID
     * @param {*} value - New value
     */
    setProperty(id, value) {
        if (this[id] !== undefined) {
            this[id] = value;
            this.onPropertyChanged(id, value);
        }
    }

    /**
     * Called when a property changes.
     * Override to handle property changes.
     * @param {string} id - Property ID
     * @param {*} value - New value
     */
    onPropertyChanged(id, value) {}

    /**
     * Get contextual hint for the tool.
     * Override to provide tool-specific hints based on current state.
     * @returns {string|null} Hint text or null if no hint
     */
    getHint() {
        return null;
    }

    /**
     * Check if this tool can operate on the given layer.
     * Uses the static layerTypes property to determine compatibility.
     *
     * @param {Object} layer - The layer to check
     * @returns {boolean} True if the tool can operate on this layer type
     */
    canOperateOn(layer) {
        if (!layer) return false;

        const types = this.constructor.layerTypes;

        // Determine the layer type
        if (layer.isGroup?.()) {
            return types.group ?? false;
        }
        if (layer.isSVG?.()) {
            return types.svg ?? types.raster ?? false;
        }
        if (layer.isText?.()) {
            return types.text ?? types.raster ?? false;
        }

        // Default to raster
        return types.raster ?? false;
    }

    /**
     * Get a message explaining why this tool cannot operate on the given layer.
     *
     * @param {Object} layer - The layer that is incompatible
     * @returns {string} User-friendly message
     */
    getIncompatibilityMessage(layer) {
        if (!layer) {
            return `${this.constructor.name} requires a layer`;
        }

        let layerType = 'raster';
        if (layer.isGroup?.()) layerType = 'group';
        else if (layer.isSVG?.()) layerType = 'svg';
        else if (layer.isText?.()) layerType = 'text';

        return `${this.constructor.name} cannot operate on ${layerType} layers`;
    }
}
