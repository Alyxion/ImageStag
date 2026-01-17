/**
 * CircleTool - Draw circles and ellipses.
 *
 * By default creates vector shapes on vector layers.
 * Hold Alt to force raster mode on the current layer.
 */
import { Tool } from './Tool.js';
import { VectorLayer } from '../core/VectorLayer.js';
import { EllipseShape } from '../core/shapes/EllipseShape.js';

export class CircleTool extends Tool {
    static id = 'circle';
    static name = 'Circle';
    static icon = 'circle';
    static shortcut = 'c';
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

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Alt key forces raster mode
        this.forceRaster = e.altKey;

        this.isDrawing = true;
        this.startX = x;
        this.startY = y;

        this.previewCanvas.width = layer.width;
        this.previewCanvas.height = layer.height;
    }

    onMouseMove(e, x, y) {
        if (!this.isDrawing) return;

        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        this.drawEllipse(this.previewCtx, this.startX, this.startY, x, y, e.shiftKey);
        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    onMouseUp(e, x, y) {
        if (!this.isDrawing) return;

        // Use vector mode unless Alt is held or vectorMode is disabled
        const useVector = this.vectorMode && !this.forceRaster;

        if (useVector) {
            this.createVectorShape(x, y, e.shiftKey);
        } else {
            // Raster mode - draw directly to layer
            const layer = this.app.layerStack.getActiveLayer();
            if (layer && !layer.locked) {
                this.app.history.saveState('Circle');

                // Convert document coordinates to layer canvas coordinates
                let canvasStartX = this.startX, canvasStartY = this.startY;
                let canvasEndX = x, canvasEndY = y;
                if (layer.docToCanvas) {
                    const start = layer.docToCanvas(this.startX, this.startY);
                    const end = layer.docToCanvas(x, y);
                    canvasStartX = start.x;
                    canvasStartY = start.y;
                    canvasEndX = end.x;
                    canvasEndY = end.y;
                }

                this.drawEllipse(layer.ctx, canvasStartX, canvasStartY, canvasEndX, canvasEndY, e.shiftKey);
                this.app.history.finishState();
            }
        }

        this.isDrawing = false;
        this.forceRaster = false;
        this.app.renderer.clearPreviewLayer();
        this.app.renderer.requestRender();
    }

    createVectorShape(x, y, constrain) {
        let width = x - this.startX;
        let height = y - this.startY;

        // Constrain to circle if shift held
        if (constrain) {
            const size = Math.max(Math.abs(width), Math.abs(height));
            width = Math.sign(width) * size || size;
            height = Math.sign(height) * size || size;
        }

        // Calculate center and radii
        const cx = this.startX + width / 2;
        const cy = this.startY + height / 2;
        const rx = Math.abs(width / 2);
        const ry = Math.abs(height / 2);

        // Skip if too small
        if (rx < 1 && ry < 1) return;

        const layer = this.getOrCreateVectorLayer();
        if (layer.locked) return;

        this.app.history.saveState('Circle');

        const shape = new EllipseShape({
            cx: cx,
            cy: cy,
            rx: rx,
            ry: ry,
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

    drawEllipse(ctx, x1, y1, x2, y2, constrain = false, options = {}) {
        let width = x2 - x1;
        let height = y2 - y1;

        // Constrain to circle if shift held
        if (constrain) {
            const size = Math.max(Math.abs(width), Math.abs(height));
            width = Math.sign(width) * size || size;
            height = Math.sign(height) * size || size;
        }

        const centerX = x1 + width / 2;
        const centerY = y1 + height / 2;
        const radiusX = Math.abs(width / 2);
        const radiusY = Math.abs(height / 2);

        if (radiusX <= 0 || radiusY <= 0) return;

        const fillColor = options.fillColor || this.fillColor || this.app.foregroundColor || '#000000';
        const strokeColor = options.strokeColor || this.strokeColor || this.app.backgroundColor || '#FFFFFF';
        const doFill = options.fill !== undefined ? options.fill : this.fill;
        const doStroke = options.stroke !== undefined ? options.stroke : this.stroke;
        const strokeW = options.strokeWidth || this.strokeWidth;

        ctx.beginPath();
        ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);

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

    drawCircle(ctx, centerX, centerY, radius, options = {}) {
        if (radius <= 0) return;

        const fillColor = options.fillColor || this.fillColor || this.app.foregroundColor || '#000000';
        const strokeColor = options.strokeColor || this.strokeColor || this.app.backgroundColor || '#FFFFFF';
        const doFill = options.fill !== undefined ? options.fill : this.fill;
        const doStroke = options.stroke !== undefined ? options.stroke : this.stroke;
        const strokeW = options.strokeWidth || this.strokeWidth;

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);

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
            this.app.history.saveState('Circle');

            const options = {
                fillColor: params.fillColor || params.color,
                strokeColor: params.strokeColor,
                fill: params.fill !== undefined ? params.fill : true,
                stroke: params.stroke !== undefined ? params.stroke : false,
                strokeWidth: params.strokeWidth,
            };

            // Support multiple input formats
            if (params.center && params.radius !== undefined) {
                // Circle by center + radius - convert to layer coordinates
                let cx = params.center[0], cy = params.center[1];
                if (layer.docToCanvas) {
                    const c = layer.docToCanvas(cx, cy);
                    cx = c.x;
                    cy = c.y;
                }
                this.drawCircle(layer.ctx, cx, cy, params.radius, options);
            } else if (params.x !== undefined && params.y !== undefined && params.radius !== undefined) {
                // Circle by x, y, radius - convert to layer coordinates
                let cx = params.x, cy = params.y;
                if (layer.docToCanvas) {
                    const c = layer.docToCanvas(cx, cy);
                    cx = c.x;
                    cy = c.y;
                }
                this.drawCircle(layer.ctx, cx, cy, params.radius, options);
            } else if (params.start && params.end) {
                // Ellipse by bounding box - convert to layer coordinates
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
                this.drawEllipse(layer.ctx, x1, y1, x2, y2, false, options);
            } else {
                return { success: false, error: 'Need center/radius or x/y/radius or start/end' };
            }

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
