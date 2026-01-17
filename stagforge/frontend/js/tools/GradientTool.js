/**
 * GradientTool - Draw linear or radial gradients.
 */
import { Tool } from './Tool.js';

export class GradientTool extends Tool {
    static id = 'gradient';
    static name = 'Gradient';
    static icon = 'gradient';
    static shortcut = 'g';
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // Gradient properties
        this.gradientType = 'linear'; // 'linear' or 'radial'
        this.opacity = 100;

        // State
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isDrawing = true;
        this.startX = x;
        this.startY = y;

        // Set up preview canvas
        this.previewCanvas.width = layer.width;
        this.previewCanvas.height = layer.height;
    }

    onMouseMove(e, x, y) {
        if (!this.isDrawing) return;

        // Show preview
        this.drawGradientPreview(x, y);
    }

    onMouseUp(e, x, y) {
        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            this.isDrawing = false;
            this.app.renderer.clearPreviewLayer();
            return;
        }

        // Save state for undo - history auto-detects changed region
        this.app.history.saveState('Gradient');

        // Draw final gradient
        this.drawGradient(layer.ctx, this.startX, this.startY, x, y);

        // Finish history capture
        this.app.history.finishState();

        this.isDrawing = false;
        this.app.renderer.clearPreviewLayer();
        this.app.renderer.requestRender();
    }

    onMouseLeave(e) {
        // Keep drawing state - user might return
    }

    drawGradientPreview(endX, endY) {
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        this.drawGradient(this.previewCtx, this.startX, this.startY, endX, endY);
        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    drawGradient(ctx, x1, y1, x2, y2) {
        const fgColor = this.app.foregroundColor || '#000000';
        const bgColor = this.app.backgroundColor || '#FFFFFF';

        let gradient;

        if (this.gradientType === 'radial') {
            // Radial gradient from center
            const radius = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
            gradient = ctx.createRadialGradient(x1, y1, 0, x1, y1, radius);
        } else {
            // Linear gradient
            gradient = ctx.createLinearGradient(x1, y1, x2, y2);
        }

        gradient.addColorStop(0, fgColor);
        gradient.addColorStop(1, bgColor);

        ctx.globalAlpha = this.opacity / 100;
        ctx.fillStyle = gradient;

        // Check for active selection and constrain gradient to selection bounds
        const selectionTool = this.app.toolManager?.tools.get('selection');
        const selection = selectionTool?.getSelection();

        if (selection && selection.width > 0 && selection.height > 0) {
            // Draw gradient only within selection
            ctx.save();
            ctx.beginPath();
            ctx.rect(selection.x, selection.y, selection.width, selection.height);
            ctx.clip();
            ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.restore();
        } else {
            ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        }

        ctx.globalAlpha = 1.0;
    }

    deactivate() {
        super.deactivate();
        this.isDrawing = false;
        this.app.renderer.clearPreviewLayer();
    }

    getProperties() {
        return [
            { id: 'gradientType', name: 'Type', type: 'select', options: ['linear', 'radial'], value: this.gradientType },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 1, max: 100, step: 1, value: this.opacity }
        ];
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'draw' || action === 'fill') {
            const x1 = params.x1 !== undefined ? params.x1 : (params.start ? params.start[0] : 0);
            const y1 = params.y1 !== undefined ? params.y1 : (params.start ? params.start[1] : 0);
            const x2 = params.x2 !== undefined ? params.x2 : (params.end ? params.end[0] : layer.width);
            const y2 = params.y2 !== undefined ? params.y2 : (params.end ? params.end[1] : layer.height);

            if (params.type) this.gradientType = params.type;
            if (params.opacity !== undefined) this.opacity = params.opacity;
            if (params.startColor) this.app.foregroundColor = params.startColor;
            if (params.endColor) this.app.backgroundColor = params.endColor;

            this.app.history.saveState('Gradient');
            this.drawGradient(layer.ctx, x1, y1, x2, y2);
            this.app.history.finishState();
            this.app.renderer.requestRender();

            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
