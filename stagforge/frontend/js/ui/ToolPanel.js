/**
 * ToolPanel - Tool selection and properties panel.
 */
export class ToolPanel {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.container = document.getElementById('tool-panel');
        this.render();
        this.bindEvents();
    }

    render() {
        const tools = this.app.toolManager.getAll();
        const currentId = this.app.toolManager.currentTool?.constructor.id;

        // Tool buttons
        const toolButtons = tools.map(tool => {
            const ToolClass = tool.constructor;
            const isActive = ToolClass.id === currentId;
            const shortcut = ToolClass.shortcut ? ` (${ToolClass.shortcut.toUpperCase()})` : '';
            return `
                <button class="tool-button ${isActive ? 'active' : ''}"
                        data-tool="${ToolClass.id}"
                        title="${ToolClass.name}${shortcut}">
                    ${this.getToolIcon(ToolClass.icon)}
                </button>
            `;
        }).join('');

        // Only render tool buttons section if not already rendered
        let toolSection = this.container.querySelector('.tool-buttons-section');
        if (!toolSection) {
            toolSection = document.createElement('div');
            toolSection.className = 'tool-buttons-section';
            this.container.insertBefore(toolSection, this.container.firstChild);
        }
        toolSection.innerHTML = toolButtons;
    }

    getToolIcon(iconName) {
        // Simple text-based icons
        const icons = {
            'brush': '🖌',
            'eraser': '◻',
            'square': '▢',
            'fill': '🪣',
            'eyedropper': '💧',
            'move': '✥',
            'cursor': '➤'
        };
        return icons[iconName] || iconName.charAt(0).toUpperCase();
    }

    bindEvents() {
        // Tool button clicks
        this.container.addEventListener('click', (e) => {
            const btn = e.target.closest('.tool-button');
            if (btn) {
                const toolId = btn.dataset.tool;
                this.app.toolManager.select(toolId);
            }
        });

        // Listen for tool changes
        this.app.eventBus.on('tool:changed', () => this.update());
    }

    update() {
        this.render();
    }
}
