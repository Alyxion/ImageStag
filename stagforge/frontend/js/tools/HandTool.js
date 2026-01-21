/**
 * HandTool - Pan/navigate the canvas view
 */
import { Tool } from './Tool.js';

export class HandTool extends Tool {
    static id = 'hand';
    static name = 'Hand';
    static icon = 'hand';
    static iconEntity = '&#9995;';  // Hand
    static group = 'hand';
    static groupShortcut = 'h';
    static priority = 10;
    static cursor = 'grab';

    constructor(app) {
        super(app);
        this.isPanning = false;
        this.lastX = 0;
        this.lastY = 0;
    }

    activate() {
        super.activate();
        this.app.displayCanvas.style.cursor = 'grab';
    }

    onMouseDown(e, x, y) {
        this.isPanning = true;
        this.lastX = e.clientX;
        this.lastY = e.clientY;
        this.app.displayCanvas.style.cursor = 'grabbing';
    }

    onMouseMove(e, x, y) {
        if (!this.isPanning) return;

        const dx = e.clientX - this.lastX;
        const dy = e.clientY - this.lastY;

        this.app.renderer.pan(dx, dy);

        this.lastX = e.clientX;
        this.lastY = e.clientY;

        // Emit event for navigator update
        this.app.eventBus.emit('viewport:changed');
    }

    onMouseUp(e, x, y) {
        this.isPanning = false;
        this.app.displayCanvas.style.cursor = 'grab';
    }

    onMouseLeave(e) {
        this.isPanning = false;
        this.app.displayCanvas.style.cursor = 'grab';
    }

    /**
     * Execute action via API
     */
    executeAction(action, params = {}) {
        if (action === 'pan') {
            const { dx = 0, dy = 0 } = params;
            this.app.renderer.pan(dx, dy);
            this.app.eventBus.emit('viewport:changed');
            return { success: true };
        }
        if (action === 'center') {
            this.app.renderer.centerCanvas();
            this.app.eventBus.emit('viewport:changed');
            return { success: true };
        }
        if (action === 'fit') {
            this.app.renderer.fitToViewport();
            this.app.eventBus.emit('viewport:changed');
            return { success: true };
        }
        return { success: false, error: 'Unknown action: ' + action };
    }

    getProperties() {
        return [];
    }
}
