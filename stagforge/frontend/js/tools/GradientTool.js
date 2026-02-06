/**
 * GradientTool - Draw linear or radial gradients.
 */
import { Tool } from './Tool.js';
import { applySelectionMask } from '../utils/SelectionMask.js';

export class GradientTool extends Tool {
    static id = 'gradient';
    static name = 'Gradient';
    static icon = 'gradient';
    static iconEntity = '&#9698;';  // Gradient triangle
    static group = 'fill';
    static priority = 20;  // After fill in same group
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

        // Don't allow gradient on vector/SVG layers
        if (layer.isVector?.() || layer.isSVG?.()) return;

        this.isDrawing = true;
        this.startX = x;
        this.startY = y;

        // Get document dimensions for gradient canvas
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;

        // Set up preview canvas at document size (gradient fills whole area)
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;

        // Pause selection animation so it doesn't overwrite our preview
        this.app.selectionManager?.stopAnimation();
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

        // Get document dimensions
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;

        // Save state for undo - history auto-detects changed region
        this.app.history.saveState('Gradient');

        // Draw gradient to temp canvas first
        this.drawGradient(this.previewCtx, this.startX, this.startY, x, y);

        // Expand layer to document bounds (gradient fills whole document)
        layer.expandToInclude(0, 0, docWidth, docHeight);

        // Composite onto layer at layer's offset position
        const offsetX = layer.offsetX || 0;
        const offsetY = layer.offsetY || 0;
        layer.ctx.drawImage(this.previewCanvas, -offsetX, -offsetY);
        layer.invalidateImageCache();

        // Finish history capture
        this.app.history.finishState();

        this.isDrawing = false;
        this.app.renderer.clearPreviewLayer();
        this.app.renderer.requestRender();

        // Resume selection animation if there's a selection
        if (this.app.selectionManager?.hasSelection) {
            this.app.selectionManager.startAnimation();
        }
    }

    onMouseLeave(e) {
        // Keep drawing state - user might return
    }

    drawGradientPreview(endX, endY) {
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        this.drawGradient(this.previewCtx, this.startX, this.startY, endX, endY);
        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    drawGradient(ctx, x1, y1, x2, y2, isPreview = false) {
        const fgColor = this.app.foregroundColor || '#000000';
        const bgColor = this.app.backgroundColor || '#FFFFFF';
        const canvas = ctx.canvas;

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

        // Draw gradient to full canvas
        ctx.globalAlpha = this.opacity / 100;
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.globalAlpha = 1.0;

        // Apply selection mask using alpha blending (supports soft edges)
        const selectionManager = this.app.selectionManager;
        if (selectionManager?.hasSelection) {
            // Get layer offset for coordinate conversion
            const layer = this.app.layerStack?.getActiveLayer();
            const offsetX = layer?.offsetX || 0;
            const offsetY = layer?.offsetY || 0;

            applySelectionMask(canvas, selectionManager, offsetX, offsetY);
        }
    }

    deactivate() {
        super.deactivate();
        this.isDrawing = false;
        this.app.renderer.clearPreviewLayer();

        // Resume selection animation if there's a selection
        if (this.app.selectionManager?.hasSelection) {
            this.app.selectionManager.startAnimation();
        }
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
            layer.invalidateImageCache();
            this.app.history.finishState();

            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
