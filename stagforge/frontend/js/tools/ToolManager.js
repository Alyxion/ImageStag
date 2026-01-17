/**
 * ToolManager - Registry and controller for drawing tools.
 */
export class ToolManager {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.tools = new Map();
        this.currentTool = null;
        this.shortcutMap = new Map();
    }

    /**
     * Register a tool class.
     * @param {typeof Tool} ToolClass - Tool class to register
     */
    register(ToolClass) {
        const tool = new ToolClass(this.app);
        this.tools.set(ToolClass.id, tool);

        // Register shortcut if defined
        if (ToolClass.shortcut) {
            this.shortcutMap.set(ToolClass.shortcut.toLowerCase(), ToolClass.id);
        }
    }

    /**
     * Select a tool by ID.
     * @param {string} toolId - Tool ID to select
     */
    select(toolId) {
        if (!this.tools.has(toolId)) {
            console.warn(`Tool not found: ${toolId}`);
            return;
        }

        // Deactivate current tool
        if (this.currentTool) {
            this.currentTool.deactivate();
        }

        // Activate new tool
        this.currentTool = this.tools.get(toolId);
        this.currentTool.activate();

        this.app.eventBus.emit('tool:changed', {
            tool: this.currentTool,
            id: toolId
        });
    }

    /**
     * Get current tool.
     * @returns {Tool|null}
     */
    getCurrent() {
        return this.currentTool;
    }

    /**
     * Get all registered tools.
     * @returns {Array<Tool>}
     */
    getAll() {
        return Array.from(this.tools.values());
    }

    /**
     * Get tool by ID.
     * @param {string} id
     * @returns {Tool|undefined}
     */
    get(id) {
        return this.tools.get(id);
    }

    /**
     * Handle keyboard shortcut.
     * @param {string} key - Key pressed
     * @returns {boolean} True if handled
     */
    handleShortcut(key) {
        const toolId = this.shortcutMap.get(key.toLowerCase());
        if (toolId) {
            this.select(toolId);
            return true;
        }
        return false;
    }

    /**
     * Get properties of current tool.
     * @returns {Array<Object>}
     */
    getCurrentProperties() {
        return this.currentTool ? this.currentTool.getProperties() : [];
    }

    /**
     * Set property on current tool.
     * @param {string} id
     * @param {*} value
     */
    setCurrentProperty(id, value) {
        if (this.currentTool) {
            this.currentTool.setProperty(id, value);
            this.app.eventBus.emit('tool:property-changed', { id, value });
        }
    }
}
