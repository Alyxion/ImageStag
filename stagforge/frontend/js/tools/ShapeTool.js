/**
 * ShapeTool - Draw rectangles, ellipses, and lines.
 */
import { Tool } from './Tool.js';

export class ShapeTool extends Tool {
    static id = 'shape';
    static name = 'Shape';
    static icon = 'shape';
    static iconEntity = '&#9671;';  // Diamond
    static group = 'shapes';
    static priority = 40;  // After polygon
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // Shape properties
        this.shapeType = 'rectangle'; // rectangle, ellipse, line
        this.strokeWidth = 2;
        this.fill = true;
        this.stroke = true;

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

        // Save state for undo - history auto-detects changed region
        this.app.history.saveState('Shape');
    }

    onMouseMove(e, x, y) {
        if (!this.isDrawing) return;

        // Clear and redraw preview
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        this.drawShape(this.previewCtx, this.startX, this.startY, x, y, e.shiftKey);

        // Render with preview overlay
        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    onMouseUp(e, x, y) {
        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Draw final shape to layer
        this.drawShape(layer.ctx, this.startX, this.startY, x, y, e.shiftKey);

        this.isDrawing = false;
        this.app.renderer.clearPreviewLayer();
        // Finish history capture
        this.app.history.finishState();
        this.app.renderer.requestRender();
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.app.renderer.clearPreviewLayer();
            // Abort history capture since shape wasn't drawn
            this.app.history.abortCapture();
        }
    }

    drawShape(ctx, x1, y1, x2, y2, constrain) {
        let width = x2 - x1;
        let height = y2 - y1;

        // Constrain to square/circle if shift held
        if (constrain && this.shapeType !== 'line') {
            const size = Math.max(Math.abs(width), Math.abs(height));
            width = Math.sign(width) * size || size;
            height = Math.sign(height) * size || size;
        }

        ctx.beginPath();

        switch (this.shapeType) {
            case 'rectangle':
                ctx.rect(x1, y1, width, height);
                break;

            case 'ellipse':
                const centerX = x1 + width / 2;
                const centerY = y1 + height / 2;
                const radiusX = Math.abs(width / 2);
                const radiusY = Math.abs(height / 2);
                if (radiusX > 0 && radiusY > 0) {
                    ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
                }
                break;

            case 'line':
                ctx.moveTo(x1, y1);
                if (constrain) {
                    // Constrain to 45-degree angles
                    const angle = Math.atan2(height, width);
                    const snapAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
                    const dist = Math.sqrt(width * width + height * height);
                    ctx.lineTo(x1 + Math.cos(snapAngle) * dist, y1 + Math.sin(snapAngle) * dist);
                } else {
                    ctx.lineTo(x2, y2);
                }
                break;
        }

        if (this.fill && this.shapeType !== 'line') {
            ctx.fillStyle = this.app.foregroundColor || '#000000';
            ctx.fill();
        }

        if (this.stroke) {
            ctx.strokeStyle = this.shapeType === 'line'
                ? (this.app.foregroundColor || '#000000')
                : (this.app.backgroundColor || '#FFFFFF');
            ctx.lineWidth = this.strokeWidth;
            ctx.stroke();
        }
    }

    getProperties() {
        return [
            {
                id: 'shapeType', name: 'Shape', type: 'select',
                options: [
                    { value: 'rectangle', label: 'Rectangle' },
                    { value: 'ellipse', label: 'Ellipse' },
                    { value: 'line', label: 'Line' }
                ],
                value: this.shapeType
            },
            { id: 'fill', name: 'Fill', type: 'checkbox', value: this.fill },
            { id: 'stroke', name: 'Stroke', type: 'checkbox', value: this.stroke },
            { id: 'strokeWidth', name: 'Stroke Width', type: 'range', min: 1, max: 50, step: 1, value: this.strokeWidth }
        ];
    }
}
