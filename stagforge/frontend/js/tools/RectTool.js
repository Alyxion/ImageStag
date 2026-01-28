/**
 * RectTool - Draw rectangles and squares.
 *
 * By default creates vector shapes on vector layers.
 * Hold Alt to force raster mode on the current layer.
 */
import { Tool } from './Tool.js';
import { VectorLayer } from '../core/VectorLayer.js';
import { RectShape } from '../core/shapes/RectShape.js';

export class RectTool extends Tool {
    static id = 'rect';
    static name = 'Rectangle';
    static icon = 'rect';
    static iconEntity = '&#9634;';  // Square
    static group = 'shapes';
    static groupShortcut = 'u';
    static priority = 10;  // First in shapes
    static cursor = 'crosshair';

    constructor(app) {
        super(app);
        this.fill = true;
        this.stroke = true;
        this.strokeWidth = 2;
        this.fillColor = null;   // null = use app.foregroundColor
        this.strokeColor = null; // null = use app.backgroundColor
        this.vectorMode = true;  // Create vector shapes by default
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.forceRaster = false;

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
        this.drawRect(this.previewCtx, this.startX, this.startY, x, y, e.shiftKey);
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
                this.app.history.saveState('Rectangle');
                // x, y are already in layer-local coordinates (pre-transformed by app.js)
                this.drawRect(layer.ctx, this.startX, this.startY, x, y, e.shiftKey);
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
        let width = x - this.startDocX;
        let height = y - this.startDocY;

        // Constrain to square if shift held
        if (constrain) {
            const size = Math.max(Math.abs(width), Math.abs(height));
            width = Math.sign(width) * size || size;
            height = Math.sign(height) * size || size;
        }

        // Normalize negative dimensions
        let rectX = this.startDocX;
        let rectY = this.startDocY;
        if (width < 0) {
            rectX += width;
            width = -width;
        }
        if (height < 0) {
            rectY += height;
            height = -height;
        }

        // Skip if too small
        if (width < 2 && height < 2) return;

        const layer = this.getOrCreateVectorLayer();
        if (layer.locked) return;

        this.app.history.saveState('Rectangle');

        const shape = new RectShape({
            x: rectX,
            y: rectY,
            width: width,
            height: height,
            fillColor: this.fillColor || this.app.foregroundColor || '#000000',
            strokeColor: this.strokeColor || this.app.backgroundColor || '#FFFFFF',
            fill: this.fill,
            stroke: this.stroke,
            strokeWidth: this.strokeWidth
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

    drawRect(ctx, x1, y1, x2, y2, constrain = false, options = {}) {
        let width = x2 - x1;
        let height = y2 - y1;

        // Constrain to square if shift held
        if (constrain) {
            const size = Math.max(Math.abs(width), Math.abs(height));
            width = Math.sign(width) * size || size;
            height = Math.sign(height) * size || size;
        }

        const fillColor = options.fillColor || this.fillColor || this.app.foregroundColor || '#000000';
        const strokeColor = options.strokeColor || this.strokeColor || this.app.backgroundColor || '#FFFFFF';
        const doFill = options.fill !== undefined ? options.fill : this.fill;
        const doStroke = options.stroke !== undefined ? options.stroke : this.stroke;
        const strokeW = options.strokeWidth || this.strokeWidth;

        ctx.beginPath();
        ctx.rect(x1, y1, width, height);

        if (doFill) {
            ctx.fillStyle = fillColor;
            ctx.fill();
        }

        if (doStroke) {
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = strokeW;
            ctx.stroke();
        }
    }

    // API execution method
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return { success: false, error: 'No active layer' };

        if (action === 'draw') {
            // Support both start/end and x/y/width/height formats
            let x1, y1, x2, y2;
            if (params.start && params.end) {
                x1 = params.start[0];
                y1 = params.start[1];
                x2 = params.end[0];
                y2 = params.end[1];
            } else if (params.x !== undefined && params.y !== undefined && params.width !== undefined && params.height !== undefined) {
                x1 = params.x;
                y1 = params.y;
                x2 = params.x + params.width;
                y2 = params.y + params.height;
            } else {
                return { success: false, error: 'Need start/end or x/y/width/height' };
            }

            // Convert document coordinates to layer canvas coordinates
            if (layer.docToCanvas) {
                const start = layer.docToCanvas(x1, y1);
                const end = layer.docToCanvas(x2, y2);
                x1 = start.x;
                y1 = start.y;
                x2 = end.x;
                y2 = end.y;
            }

            this.app.history.saveState('Rectangle');
            this.drawRect(layer.ctx, x1, y1, x2, y2, false, {
                fillColor: params.fillColor || params.color,
                strokeColor: params.strokeColor,
                fill: params.fill !== undefined ? params.fill : true,
                stroke: params.stroke !== undefined ? params.stroke : false,
                strokeWidth: params.strokeWidth,
            });

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }
        return { success: false, error: 'Invalid action' };
    }

    getProperties() {
        return [
            { id: 'fill', name: 'Fill', type: 'checkbox', value: this.fill },
            { id: 'fillColor', name: 'Fill Color', type: 'color', value: this.fillColor || this.app.foregroundColor },
            { id: 'stroke', name: 'Stroke', type: 'checkbox', value: this.stroke },
            { id: 'strokeColor', name: 'Stroke Color', type: 'color', value: this.strokeColor || this.app.backgroundColor },
            { id: 'strokeWidth', name: 'Width', type: 'range', min: 1, max: 50, step: 1, value: this.strokeWidth }
        ];
    }

    onPropertyChanged(id, value) {
        if (id === 'fill' || id === 'stroke') {
            this[id] = value;
        } else if (id === 'fillColor') {
            this.fillColor = value;
        } else if (id === 'strokeColor') {
            this.strokeColor = value;
        } else if (id === 'strokeWidth') {
            this.strokeWidth = value;
        }
    }
}
