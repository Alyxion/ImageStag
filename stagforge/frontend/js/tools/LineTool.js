/**
 * LineTool - Draw straight lines.
 *
 * By default creates vector shapes on vector layers.
 * Hold Alt to force raster mode on the current layer.
 */
import { Tool } from './Tool.js';
import { VectorLayer } from '../core/VectorLayer.js';
import { LineShape } from '../core/shapes/LineShape.js';

export class LineTool extends Tool {
    static id = 'line';
    static name = 'Line';
    static icon = 'line';
    static iconEntity = '&#9585;';  // Diagonal line
    static group = 'shapes';
    static priority = 50;  // Last in shapes group
    static cursor = 'crosshair';

    constructor(app) {
        super(app);
        this.lineWidth = 2;
        this.strokeColor = null; // null = use app.foregroundColor
        this.vectorMode = true;  // Create vector shapes by default
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.forceRaster = false;

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');
    }

    /**
     * Get or create a vector layer for the shape.
     */
    getOrCreateVectorLayer() {
        let layer = this.app.layerStack.getActiveLayer();

        // If not a vector layer, create one
        if (!layer || !layer.isVector || !layer.isVector()) {
            layer = new VectorLayer({
                width: this.app.width,
                height: this.app.height,
                name: 'Shape Layer'
            });
            this.app.layerStack.addLayer(layer);
            this.app.layerStack.setActiveLayerById(layer.id);
            this.app.eventBus.emit('layers:changed');
        }

        return layer;
    }

    onMouseDown(e, x, y, coords) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Alt key forces raster mode
        this.forceRaster = e.altKey;

        this.isDrawing = true;
        // Store both layer-local (for raster) and document coords (for vector)
        this.startX = x;  // layer-local
        this.startY = y;
        this.startDocX = coords?.docX ?? x;  // document coords for vector shapes
        this.startDocY = coords?.docY ?? y;

        this.previewCanvas.width = layer.width;
        this.previewCanvas.height = layer.height;
    }

    onMouseMove(e, x, y) {
        if (!this.isDrawing) return;

        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        this.drawLine(this.previewCtx, this.startX, this.startY, x, y, e.shiftKey);
        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    onMouseUp(e, x, y, coords) {
        if (!this.isDrawing) return;

        // Use vector mode unless Alt is held or vectorMode is disabled
        const useVector = this.vectorMode && !this.forceRaster;

        if (useVector) {
            // Vector shapes use document coordinates
            const docX = coords?.docX ?? x;
            const docY = coords?.docY ?? y;
            this.createVectorShape(docX, docY, e.shiftKey);
        } else {
            // Raster mode - draw directly to layer using layer-local coordinates
            const layer = this.app.layerStack.getActiveLayer();
            if (layer && !layer.locked) {
                this.app.history.saveState('Line');
                // x, y are already in layer-local coordinates (pre-transformed by app.js)
                this.drawLine(layer.ctx, this.startX, this.startY, x, y, e.shiftKey);
                this.app.history.finishState();
            }
        }

        this.isDrawing = false;
        this.forceRaster = false;
        this.app.renderer.clearPreviewLayer();
        this.app.renderer.requestRender();
    }

    createVectorShape(x, y, constrain) {
        // x, y are document coordinates (passed from onMouseUp)
        // startDocX/startDocY are also document coordinates
        let x2 = x, y2 = y;

        if (constrain) {
            // Snap to 45-degree angles
            const dx = x - this.startDocX;
            const dy = y - this.startDocY;
            const angle = Math.atan2(dy, dx);
            const snapAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
            const dist = Math.sqrt(dx * dx + dy * dy);
            x2 = this.startDocX + Math.cos(snapAngle) * dist;
            y2 = this.startDocY + Math.sin(snapAngle) * dist;
        }

        // Skip if too small
        const dist = Math.sqrt((x2 - this.startDocX) ** 2 + (y2 - this.startDocY) ** 2);
        if (dist < 2) return;

        const layer = this.getOrCreateVectorLayer();
        if (layer.locked) return;

        this.app.history.saveState('Line');

        const shape = new LineShape({
            x1: this.startDocX,
            y1: this.startDocY,
            x2: x2,
            y2: y2,
            strokeColor: this.strokeColor || this.app.foregroundColor || '#000000',
            strokeWidth: this.lineWidth
        });

        layer.addShape(shape);
        layer.selectShape(shape.id);

        this.app.history.finishState();

        // Auto-switch to vector-edit tool
        this.app.toolManager.select('select');
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.forceRaster = false;
            this.app.renderer.clearPreviewLayer();
        }
    }

    drawLine(ctx, x1, y1, x2, y2, constrain = false) {
        ctx.beginPath();
        ctx.moveTo(x1, y1);

        if (constrain) {
            // Snap to 45-degree angles
            const dx = x2 - x1;
            const dy = y2 - y1;
            const angle = Math.atan2(dy, dx);
            const snapAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
            const dist = Math.sqrt(dx * dx + dy * dy);
            ctx.lineTo(x1 + Math.cos(snapAngle) * dist, y1 + Math.sin(snapAngle) * dist);
        } else {
            ctx.lineTo(x2, y2);
        }

        ctx.strokeStyle = this.app.foregroundColor || '#000000';
        ctx.lineWidth = this.lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();
    }

    // API execution method
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return { success: false, error: 'No active layer' };

        if (action === 'draw' && params.start && params.end) {
            this.app.history.saveState('Line');

            // Override color if provided
            const origColor = this.app.foregroundColor;
            if (params.color) this.app.foregroundColor = params.color;
            if (params.width) this.lineWidth = params.width;

            // Convert document coordinates to layer canvas coordinates
            let x1 = params.start[0], y1 = params.start[1];
            let x2 = params.end[0], y2 = params.end[1];
            if (layer.docToCanvas) {
                const start = layer.docToCanvas(x1, y1);
                const end = layer.docToCanvas(x2, y2);
                x1 = start.x;
                y1 = start.y;
                x2 = end.x;
                y2 = end.y;
            }

            this.drawLine(layer.ctx, x1, y1, x2, y2);

            if (params.color) this.app.foregroundColor = origColor;

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }
        return { success: false, error: 'Invalid action or params' };
    }

    getProperties() {
        return [
            { id: 'strokeColor', name: 'Color', type: 'color', value: this.strokeColor || this.app.foregroundColor },
            { id: 'lineWidth', name: 'Width', type: 'range', min: 1, max: 50, step: 1, value: this.lineWidth }
        ];
    }

    onPropertyChanged(id, value) {
        if (id === 'strokeColor') {
            this.strokeColor = value;
        } else if (id === 'lineWidth') {
            this.lineWidth = Number(value);
        }
    }
}
