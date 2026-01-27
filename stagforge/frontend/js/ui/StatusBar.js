/**
 * StatusBar - Bottom status bar with coordinates and info.
 */
export class StatusBar {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.container = document.getElementById('status-bar');
        this.render();
    }

    render() {
        this.container.innerHTML = `
            <span class="status-coords" id="status-coords">X: 0 Y: 0</span>
            <span class="status-separator">|</span>
            <span class="status-size" id="status-size">800 x 600</span>
            <span class="status-separator">|</span>
            <span class="status-tool" id="status-tool">Brush</span>
            <span class="status-separator">|</span>
            <span class="status-message" id="status-message">Ready</span>
            <span class="status-right">
                <span class="status-backend" id="status-backend">Connecting...</span>
            </span>
        `;

        this.updateSize();
        this.updateTool();
        this.bindEvents();

        // Set initial backend status based on mode
        const backendMode = this.app.backendMode || 'on';
        if (backendMode === 'off') {
            this.setBackendLabel('Backend: Disabled', 'disabled');
        } else if (backendMode === 'offline') {
            this.setBackendLabel('Backend: Offline', 'disconnected');
        }
    }

    bindEvents() {
        this.app.eventBus.on('tool:changed', ({ tool }) => {
            this.updateTool();
        });

        this.app.eventBus.on('backend:connected', () => {
            this.setBackendStatus(true);
        });

        this.app.eventBus.on('backend:disconnected', (detail) => {
            const mode = detail?.mode;
            if (mode === 'off') {
                this.setBackendLabel('Backend: Disabled', 'disabled');
            } else if (mode === 'offline') {
                this.setBackendLabel('Backend: Offline', 'disconnected');
            } else {
                this.setBackendStatus(false);
            }
        });
    }

    /**
     * Update coordinate display.
     * @param {number} x
     * @param {number} y
     */
    setCoordinates(x, y) {
        const el = document.getElementById('status-coords');
        if (el) el.textContent = `X: ${x} Y: ${y}`;
    }

    /**
     * Update canvas size display.
     */
    updateSize() {
        const el = document.getElementById('status-size');
        if (el) {
            const { width, height } = this.app.layerStack;
            el.textContent = `${width} x ${height}`;
        }
    }

    /**
     * Update current tool display.
     */
    updateTool() {
        const el = document.getElementById('status-tool');
        if (el && this.app.toolManager.currentTool) {
            el.textContent = this.app.toolManager.currentTool.constructor.name;
        }
    }

    /**
     * Set status message.
     * @param {string} message
     */
    setStatus(message) {
        const el = document.getElementById('status-message');
        if (el) el.textContent = message;
    }

    /**
     * Set backend connection status.
     * @param {boolean} connected
     */
    setBackendStatus(connected) {
        const el = document.getElementById('status-backend');
        if (el) {
            el.textContent = connected ? 'Backend: Connected' : 'Backend: Offline';
            el.className = `status-backend ${connected ? 'connected' : 'disconnected'}`;
        }
    }

    /**
     * Set backend label with custom text and CSS class.
     * @param {string} text
     * @param {string} cssClass
     */
    setBackendLabel(text, cssClass) {
        const el = document.getElementById('status-backend');
        if (el) {
            el.textContent = text;
            el.className = `status-backend ${cssClass}`;
        }
    }
}
