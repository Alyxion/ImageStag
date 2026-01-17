/**
 * PenTool - Create bezier paths.
 *
 * Features:
 * - Click to add corner points
 * - Click-drag to create smooth points with bezier handles
 * - Enter to finish open path
 * - Ctrl/Cmd+Enter to close path
 * - Escape to cancel current path
 * - Backspace to remove last point
 * - Click on first point to close path
 */
import { Tool } from './Tool.js';
import { VectorLayer } from '../core/VectorLayer.js';
import { PathShape, PathPoint } from '../core/shapes/PathShape.js';

export class PenTool extends Tool {
    static id = 'pen';
    static name = 'Pen';
    static icon = 'pen';
    static shortcut = 'p';
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // Current path being drawn
        this.currentPath = null;
        this.isDrawing = false;

        // Handle dragging state
        this.isDraggingHandle = false;
        this.currentPoint = null;

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');

        // Settings
        this.fillColor = null;   // null = use app.foregroundColor
        this.strokeColor = null; // null = use app.backgroundColor
        this.strokeWidth = 2;
        this.fill = false;       // Paths typically don't fill by default
        this.stroke = true;
    }

    /**
     * Get or create a vector layer for the path.
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

    activate() {
        super.activate();
        this.setupPreviewCanvas();
    }

    deactivate() {
        super.deactivate();
        if (this.isDrawing) {
            this.cancelPath();
        }
    }

    setupPreviewCanvas() {
        this.previewCanvas.width = this.app.width;
        this.previewCanvas.height = this.app.height;
    }

    onMouseDown(e, x, y) {
        // Check if clicking on first point to close path
        if (this.isDrawing && this.currentPath && this.currentPath.points.length >= 2) {
            const firstPt = this.currentPath.points[0];
            const dist = Math.sqrt((x - firstPt.x) ** 2 + (y - firstPt.y) ** 2);
            if (dist < 10) {
                // Close the path
                this.currentPath.closed = true;
                this.commitPath();
                return;
            }
        }

        if (!this.isDrawing) {
            // Start a new path
            this.startNewPath(x, y);
        } else {
            // Add point to existing path
            this.addPoint(x, y);
        }

        this.isDraggingHandle = true;
    }

    onMouseMove(e, x, y) {
        if (this.isDraggingHandle && this.currentPoint) {
            // Drag to create/adjust handles
            const pt = this.currentPoint;
            const dx = x - pt.x;
            const dy = y - pt.y;

            if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
                // Create symmetric handles
                pt.type = 'symmetric';
                pt.handleOut = { x: dx, y: dy };
                pt.handleIn = { x: -dx, y: -dy };
            }

            this.updatePreview(x, y);
        } else if (this.isDrawing) {
            // Preview line to cursor
            this.updatePreview(x, y);
        }
    }

    onMouseUp(e, x, y) {
        this.isDraggingHandle = false;
        this.currentPoint = null;

        if (this.isDrawing) {
            this.updatePreview(x, y);
        }
    }

    onKeyDown(e) {
        if (!this.isDrawing) return;

        if (e.key === 'Enter') {
            if (e.ctrlKey || e.metaKey) {
                // Close path
                if (this.currentPath.points.length >= 3) {
                    this.currentPath.closed = true;
                }
            }
            // Commit path
            if (this.currentPath.points.length >= 2) {
                this.commitPath();
            } else {
                this.cancelPath();
            }
            e.preventDefault();
        } else if (e.key === 'Escape') {
            this.cancelPath();
            e.preventDefault();
        } else if (e.key === 'Backspace') {
            // Remove last point
            if (this.currentPath.points.length > 1) {
                this.currentPath.points.pop();
                this.updatePreview();
            } else {
                this.cancelPath();
            }
            e.preventDefault();
        }
    }

    startNewPath(x, y) {
        this.isDrawing = true;

        const fgColor = this.fillColor || this.app.foregroundColor || '#000000';
        const bgColor = this.strokeColor || this.app.backgroundColor || '#000000';

        this.currentPath = new PathShape({
            fillColor: fgColor,
            strokeColor: bgColor,
            strokeWidth: this.strokeWidth,
            fill: this.fill,
            stroke: this.stroke,
            closed: false
        });

        this.addPoint(x, y);
        this.setupPreviewCanvas();
    }

    addPoint(x, y) {
        const pt = this.currentPath.addPoint(x, y, { type: 'corner' });
        this.currentPoint = pt;
        this.updatePreview(x, y);
    }

    updatePreview(mouseX, mouseY) {
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);

        if (!this.currentPath || this.currentPath.points.length === 0) {
            this.app.renderer.clearPreviewLayer();
            return;
        }

        // Draw the path so far
        this.currentPath.render(this.previewCtx);

        // Draw preview line to cursor
        if (mouseX !== undefined && mouseY !== undefined && this.currentPath.points.length > 0) {
            const lastPt = this.currentPath.points[this.currentPath.points.length - 1];

            this.previewCtx.save();
            this.previewCtx.strokeStyle = this.currentPath.strokeColor;
            this.previewCtx.lineWidth = 1;
            this.previewCtx.setLineDash([5, 5]);

            this.previewCtx.beginPath();

            // If last point has handle out, draw curve preview
            if (lastPt.handleOut) {
                const hOut = lastPt.getHandleOutAbs();
                this.previewCtx.moveTo(lastPt.x, lastPt.y);
                this.previewCtx.quadraticCurveTo(hOut.x, hOut.y, mouseX, mouseY);
            } else {
                this.previewCtx.moveTo(lastPt.x, lastPt.y);
                this.previewCtx.lineTo(mouseX, mouseY);
            }

            this.previewCtx.stroke();
            this.previewCtx.setLineDash([]);
            this.previewCtx.restore();
        }

        // Draw control points
        for (let i = 0; i < this.currentPath.points.length; i++) {
            const pt = this.currentPath.points[i];

            // Draw anchor point
            this.previewCtx.fillStyle = i === 0 ? '#ff6600' : '#0078d4';
            this.previewCtx.strokeStyle = '#ffffff';
            this.previewCtx.lineWidth = 1;
            this.previewCtx.beginPath();
            this.previewCtx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
            this.previewCtx.fill();
            this.previewCtx.stroke();

            // Draw handles
            if (pt.handleIn) {
                const hIn = pt.getHandleInAbs();
                this.drawHandle(pt.x, pt.y, hIn.x, hIn.y);
            }
            if (pt.handleOut) {
                const hOut = pt.getHandleOutAbs();
                this.drawHandle(pt.x, pt.y, hOut.x, hOut.y);
            }
        }

        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    drawHandle(anchorX, anchorY, handleX, handleY) {
        // Line from anchor to handle
        this.previewCtx.strokeStyle = '#0078d4';
        this.previewCtx.lineWidth = 1;
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(anchorX, anchorY);
        this.previewCtx.lineTo(handleX, handleY);
        this.previewCtx.stroke();

        // Handle circle
        this.previewCtx.fillStyle = '#ffffff';
        this.previewCtx.strokeStyle = '#0078d4';
        this.previewCtx.beginPath();
        this.previewCtx.arc(handleX, handleY, 4, 0, Math.PI * 2);
        this.previewCtx.fill();
        this.previewCtx.stroke();
    }

    commitPath() {
        if (!this.currentPath || this.currentPath.points.length < 2) {
            this.cancelPath();
            return;
        }

        const layer = this.getOrCreateVectorLayer();
        if (layer.locked) {
            this.cancelPath();
            return;
        }

        this.app.history.saveState('Draw Path');

        layer.addShape(this.currentPath);
        layer.selectShape(this.currentPath.id);

        this.app.history.finishState();

        this.cleanup();
        this.app.renderer.requestRender();

        // Auto-switch to vector-edit tool
        this.app.toolManager.select('select');
    }

    cancelPath() {
        this.cleanup();
    }

    cleanup() {
        this.currentPath = null;
        this.currentPoint = null;
        this.isDrawing = false;
        this.isDraggingHandle = false;
        this.app.renderer.clearPreviewLayer();
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

    getHint() {
        if (!this.isDrawing) {
            return 'Click to start path, drag for curves';
        }
        return 'Click to add points, Enter to finish, Ctrl+Enter to close, Esc to cancel';
    }

    onPropertyChanged(id, value) {
        if (id === 'fill' || id === 'stroke') {
            this[id] = value;
        } else if (id === 'fillColor') {
            this.fillColor = value;
        } else if (id === 'strokeColor') {
            this.strokeColor = value;
        } else if (id === 'strokeWidth') {
            this.strokeWidth = Number(value);
        }

        // Update current path preview if drawing
        if (this.isDrawing && this.currentPath) {
            if (id === 'fillColor') {
                this.currentPath.fillColor = this.fillColor || this.app.foregroundColor;
            } else if (id === 'strokeColor') {
                this.currentPath.strokeColor = this.strokeColor || this.app.backgroundColor;
            } else if (id === 'strokeWidth') {
                this.currentPath.strokeWidth = this.strokeWidth;
            } else if (id === 'fill') {
                this.currentPath.fill = this.fill;
            } else if (id === 'stroke') {
                this.currentPath.stroke = this.stroke;
            }
            this.updatePreview();
        }
    }

    // API execution
    executeAction(action, params) {
        if (action === 'draw' && params.points && params.points.length >= 2) {
            const layer = this.getOrCreateVectorLayer();
            if (layer.locked) {
                return { success: false, error: 'Layer is locked' };
            }

            this.app.history.saveState('Draw Path');

            const path = new PathShape({
                fillColor: params.fillColor || params.color || this.fillColor || this.app.foregroundColor,
                strokeColor: params.strokeColor || this.strokeColor || this.app.backgroundColor,
                strokeWidth: params.strokeWidth ?? this.strokeWidth,
                fill: params.fill ?? this.fill,
                stroke: params.stroke ?? this.stroke,
                closed: params.closed ?? false
            });

            // Add points
            for (const pt of params.points) {
                if (Array.isArray(pt)) {
                    // Simple [x, y] format
                    path.addPoint(pt[0], pt[1]);
                } else {
                    // Object with optional handles
                    path.addPoint(pt.x, pt.y, {
                        type: pt.type || 'corner',
                        handleIn: pt.handleIn,
                        handleOut: pt.handleOut
                    });
                }
            }

            layer.addShape(path);

            this.app.history.finishState();
            this.app.renderer.requestRender();

            return { success: true, shapeId: path.id };
        }

        return { success: false, error: `Unknown action: ${action}. Use 'draw' with points array.` };
    }
}
