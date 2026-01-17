/**
 * MoveTool - Move layer contents by adjusting layer offset.
 *
 * Uses offset-based movement so pixels are never lost when
 * moving layers outside the document bounds.
 */
import { Tool } from './Tool.js';

export class MoveTool extends Tool {
    static id = 'move';
    static name = 'Move';
    static icon = 'move';
    static shortcut = null;  // Removed - 'v' is now used by Select tool
    static cursor = 'move';

    constructor(app) {
        super(app);

        // State
        this.isMoving = false;
        this.startX = 0;
        this.startY = 0;
        this.initialOffsetX = 0;
        this.initialOffsetY = 0;
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isMoving = true;
        this.startX = x;
        this.startY = y;

        // Save initial layer offset for relative movement
        this.initialOffsetX = layer.offsetX ?? 0;
        this.initialOffsetY = layer.offsetY ?? 0;

        // Use structural change tracking for offset-based movement
        this.app.history.beginCapture('Move Layer', []);
        this.app.history.beginStructuralChange();
    }

    onMouseMove(e, x, y) {
        if (!this.isMoving) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Calculate total movement from start position
        const dx = Math.round(x - this.startX);
        const dy = Math.round(y - this.startY);

        // Update layer offset (doesn't touch pixel data)
        layer.offsetX = this.initialOffsetX + dx;
        layer.offsetY = this.initialOffsetY + dy;

        this.app.renderer.requestRender();
    }

    onMouseUp(e, x, y) {
        if (this.isMoving) {
            this.isMoving = false;
            // Commit structural change (includes offset changes)
            this.app.history.commitCapture();
        }
    }

    onMouseLeave(e) {
        // Keep state on mouse leave to allow continued dragging
    }

    getProperties() {
        return [];
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'move' && params.dx !== undefined && params.dy !== undefined) {
            this.app.history.beginCapture('Move Layer', []);
            this.app.history.beginStructuralChange();

            layer.offsetX = (layer.offsetX ?? 0) + params.dx;
            layer.offsetY = (layer.offsetY ?? 0) + params.dy;

            this.app.history.commitCapture();
            this.app.renderer.requestRender();
            return { success: true };
        }

        if (action === 'set_position' && params.x !== undefined && params.y !== undefined) {
            this.app.history.beginCapture('Move Layer', []);
            this.app.history.beginStructuralChange();

            layer.offsetX = params.x;
            layer.offsetY = params.y;

            this.app.history.commitCapture();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}. Use 'move' with dx/dy or 'set_position' with x/y.` };
    }
}
