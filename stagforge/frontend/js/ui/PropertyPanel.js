/**
 * PropertyPanel - Tool properties panel.
 */
export class PropertyPanel {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.container = document.getElementById('property-panel');
        this.render();
        this.bindEvents();
    }

    render() {
        const tool = this.app.toolManager.currentTool;
        const properties = tool ? tool.getProperties() : [];

        if (properties.length === 0) {
            this.container.innerHTML = `
                <div class="panel-header">Properties</div>
                <div class="panel-empty">No properties</div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="panel-header">Properties</div>
            <div class="property-list">
                ${properties.map(prop => this.renderProperty(prop)).join('')}
            </div>
        `;
    }

    renderProperty(prop) {
        switch (prop.type) {
            case 'range':
                return `
                    <div class="property-row">
                        <label>${prop.name}</label>
                        <input type="range" class="property-input"
                               data-prop="${prop.id}"
                               min="${prop.min}" max="${prop.max}"
                               step="${prop.step || 1}"
                               value="${prop.value}">
                        <span class="property-value" id="prop-value-${prop.id}">${prop.value}</span>
                    </div>
                `;

            case 'select':
                return `
                    <div class="property-row">
                        <label>${prop.name}</label>
                        <select class="property-input" data-prop="${prop.id}">
                            ${prop.options.map(opt => `
                                <option value="${opt.value}" ${opt.value === prop.value ? 'selected' : ''}>
                                    ${opt.label}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                `;

            case 'checkbox':
                return `
                    <div class="property-row">
                        <label>
                            <input type="checkbox" class="property-input"
                                   data-prop="${prop.id}"
                                   ${prop.value ? 'checked' : ''}>
                            ${prop.name}
                        </label>
                    </div>
                `;

            case 'color':
                return `
                    <div class="property-row">
                        <label>${prop.name}</label>
                        <input type="color" class="property-input"
                               data-prop="${prop.id}"
                               value="${prop.value}">
                    </div>
                `;

            case 'number':
                return `
                    <div class="property-row">
                        <label>${prop.name}</label>
                        <input type="number" class="property-input"
                               data-prop="${prop.id}"
                               min="${prop.min}" max="${prop.max}"
                               step="${prop.step || 1}"
                               value="${prop.value}">
                    </div>
                `;

            default:
                return '';
        }
    }

    bindEvents() {
        // Property changes
        this.container.addEventListener('input', (e) => {
            const input = e.target;
            if (!input.classList.contains('property-input')) return;

            const propId = input.dataset.prop;
            let value;

            if (input.type === 'checkbox') {
                value = input.checked;
            } else if (input.type === 'range' || input.type === 'number') {
                value = parseFloat(input.value);
                // Update value display
                const valueSpan = document.getElementById(`prop-value-${propId}`);
                if (valueSpan) valueSpan.textContent = value;
            } else {
                value = input.value;
            }

            this.app.toolManager.setCurrentProperty(propId, value);
        });

        // Listen for tool changes
        this.app.eventBus.on('tool:changed', () => this.render());
        this.app.eventBus.on('tool:property-changed', () => this.render());
    }

    update() {
        this.render();
    }
}
