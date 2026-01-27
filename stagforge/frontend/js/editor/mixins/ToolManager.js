/**
 * ToolManager Mixin
 *
 * Handles tool selection, tool groups, flyout menus,
 * and cycling through tools in a group.
 *
 * Required component data:
 *   - tools: Array
 *   - toolGroups: Array
 *   - currentToolId: String
 *   - activeGroupTools: Object
 *   - activeToolFlyout: String|null
 *   - flyoutCloseTimeout: Number|null
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateToolProperties(): Updates tool property panel
 *   - updateBrushCursor(): Updates cursor for size-based tools
 */
export const ToolManagerMixin = {
    methods: {
        /**
         * Update the tool list from the app's ToolManager
         */
        updateToolList() {
            const app = this.getState();
            if (!app?.toolManager) return;
            this.tools = app.toolManager.getAll().map(t => ({
                id: t.constructor.id,
                name: t.constructor.name,
                icon: t.constructor.icon,
                shortcut: t.constructor.shortcut,
                group: t.constructor.group || null,
            }));
            this.buildToolGroups();
        },

        /**
         * Build tool groups from the flat tool list
         * Groups related tools (e.g., brush/pencil/spray) under a single flyout
         */
        buildToolGroups() {
            // Define tool groupings
            const groupDefs = [
                { id: 'select', name: 'Select', shortcut: 'v', tools: ['select'] },
                { id: 'selection', name: 'Selection', shortcut: 'm', tools: ['selection'] },
                { id: 'freeform', name: 'Freeform Selection', shortcut: 'l', tools: ['lasso'] },
                { id: 'quicksel', name: 'Quick Selection', shortcut: 'w', tools: ['magicwand'] },
                { id: 'crop', name: 'Crop', shortcut: 'c', tools: ['crop'] },
                { id: 'move', name: 'Move', shortcut: null, tools: ['move'] },
                { id: 'hand', name: 'Hand', shortcut: 'h', tools: ['hand'] },
                { id: 'brush', name: 'Brush', shortcut: 'b', tools: ['brush', 'pencil', 'spray'] },
                { id: 'stamp', name: 'Stamp', shortcut: 's', tools: ['clonestamp'] },
                { id: 'retouch', name: 'Retouch', shortcut: null, tools: ['smudge', 'blur', 'sharpen'] },
                { id: 'dodge', name: 'Dodge/Burn', shortcut: 'o', tools: ['dodge', 'burn', 'sponge'] },
                { id: 'eraser', name: 'Eraser', shortcut: 'e', tools: ['eraser'] },
                { id: 'pen', name: 'Pen', shortcut: 'p', tools: ['pen'] },
                { id: 'shapes', name: 'Shapes', shortcut: 'u', tools: ['rect', 'circle', 'polygon', 'line', 'shape'] },
                { id: 'fill', name: 'Fill', shortcut: 'g', tools: ['fill', 'gradient'] },
                { id: 'text', name: 'Text', shortcut: 't', tools: ['text'] },
                { id: 'eyedropper', name: 'Eyedropper', shortcut: 'i', tools: ['eyedropper'] },
            ];

            const toolsMap = new Map(this.tools.map(t => [t.id, t]));
            this.toolGroups = [];

            for (const def of groupDefs) {
                const groupTools = def.tools
                    .map(id => toolsMap.get(id))
                    .filter(t => t);
                if (groupTools.length > 0) {
                    this.toolGroups.push({
                        id: def.id,
                        name: def.name,
                        shortcut: def.shortcut,
                        tools: groupTools,
                    });
                    // Set default active tool for group
                    if (!this.activeGroupTools[def.id]) {
                        this.activeGroupTools[def.id] = groupTools[0].id;
                    }
                }
            }

            // Add ungrouped tools
            const groupedToolIds = new Set(groupDefs.flatMap(g => g.tools));
            const ungroupedTools = this.tools.filter(t => !groupedToolIds.has(t.id));
            for (const tool of ungroupedTools) {
                this.toolGroups.push({
                    id: `single-${tool.id}`,
                    name: tool.name,
                    shortcut: tool.shortcut,
                    tools: [tool],
                });
                this.activeGroupTools[`single-${tool.id}`] = tool.id;
            }
        },

        /**
         * Check if a tool group contains the currently active tool
         * @param {Object} group - Tool group object
         * @returns {boolean}
         */
        isToolGroupActive(group) {
            return group.tools.some(t => t.id === this.currentToolId);
        },

        /**
         * Get the active tool within a group
         * @param {Object} group - Tool group object
         * @returns {Object} Tool object
         */
        getActiveToolInGroup(group) {
            const activeId = this.activeGroupTools[group.id];
            return group.tools.find(t => t.id === activeId) || group.tools[0];
        },

        /**
         * Select the active tool from a group (main button click)
         * @param {Object} group - Tool group object
         */
        selectToolFromGroup(group) {
            // Skip if long press just fired (flyout opened instead)
            if (this._longPressFired) {
                this._longPressFired = false;
                return;
            }
            const tool = this.getActiveToolInGroup(group);
            this.selectTool(tool.id);
            this.closeToolFlyout();
            this.tabletExpandedToolGroup = null;
        },

        /**
         * Start long-press timer to open tool group flyout
         * @param {PointerEvent} event
         * @param {Object} group - Tool group object
         */
        startToolLongPress(event, group) {
            if (group.tools.length <= 1) return;
            // Capture rect immediately — event.currentTarget is null after async
            const rect = event.currentTarget.getBoundingClientRect();
            this._longPressTimer = setTimeout(() => {
                this._longPressFired = true;
                this.tabletFlyoutPos = {
                    x: rect.right + 4,
                    y: rect.top,
                };
                this.tabletExpandedToolGroup = group.id;
            }, 400);
        },

        /**
         * Cancel long-press timer
         */
        cancelToolLongPress() {
            if (this._longPressTimer) {
                clearTimeout(this._longPressTimer);
                this._longPressTimer = null;
            }
        },

        /**
         * Show the flyout menu for a tool group (on hover)
         * @param {Event} event - Mouse event
         * @param {Object} group - Tool group object
         */
        showToolFlyout(event, group) {
            if (group.tools.length <= 1) return;
            this.cancelCloseFlyout();
            // Compute fixed position from the hovered group element
            const el = event.currentTarget;
            const rect = el.getBoundingClientRect();
            this.desktopFlyoutPos = { x: rect.right + 2, y: rect.top };
            this.desktopFlyoutGroup = group;
            this.desktopFlyoutTools = group.tools;
            this.activeToolFlyout = group.id;
        },

        /**
         * Schedule closing the flyout after a delay
         */
        scheduleCloseFlyout() {
            this.flyoutCloseTimeout = setTimeout(() => {
                this.activeToolFlyout = null;
            }, 200);
        },

        /**
         * Cancel scheduled flyout close
         */
        cancelCloseFlyout() {
            if (this.flyoutCloseTimeout) {
                clearTimeout(this.flyoutCloseTimeout);
                this.flyoutCloseTimeout = null;
            }
        },

        /**
         * Immediately close the tool flyout
         */
        closeToolFlyout() {
            this.cancelCloseFlyout();
            this.activeToolFlyout = null;
        },

        /**
         * Select a specific tool from a flyout menu
         * @param {Object} group - Tool group object
         * @param {Object} tool - Tool object to select
         */
        selectToolFromFlyout(group, tool) {
            this.activeGroupTools[group.id] = tool.id;
            this.selectTool(tool.id);
            this.closeToolFlyout();
        },

        /**
         * Cycle through tools in a group (Shift+shortcut)
         * @param {string} shortcut - Keyboard shortcut
         * @returns {boolean} True if cycling occurred
         */
        cycleToolInGroup(shortcut) {
            const group = this.toolGroups.find(g => g.shortcut === shortcut);
            if (!group || group.tools.length <= 1) return false;

            const currentActiveId = this.activeGroupTools[group.id];
            const currentIndex = group.tools.findIndex(t => t.id === currentActiveId);
            const nextIndex = (currentIndex + 1) % group.tools.length;
            const nextTool = group.tools[nextIndex];

            this.activeGroupTools[group.id] = nextTool.id;
            this.selectTool(nextTool.id);
            return true;
        },

        /**
         * Select a tool by ID
         * @param {string} toolId - Tool identifier
         */
        selectTool(toolId) {
            const app = this.getState();
            if (!app?.toolManager) return;
            app.toolManager.select(toolId);
        },

        /**
         * Update a property on the current tool
         * @param {string} propId - Property identifier
         * @param {*} value - New value
         */
        updateToolProperty(propId, value) {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (!tool) return;
            const numValue = parseFloat(value);
            tool[propId] = isNaN(numValue) ? value : numValue;
            if (tool.onPropertyChanged) {
                tool.onPropertyChanged(propId, tool[propId]);
            }
            this.updateToolProperties();

            // Track brush preset changes
            if (propId === 'preset' && this.currentToolId === 'brush') {
                this.currentBrushPreset = value;
                const preset = this.toolProperties.find(p => p.id === 'preset');
                if (preset) {
                    const opt = preset.options.find(o => o.value === value);
                    this.currentBrushPresetName = opt ? opt.label : value;
                }
            }

            // Update cursor when size changes for any size-based tool
            if (propId === 'size') {
                this.updateBrushCursor();
            }
        },
    },
};

export default ToolManagerMixin;
