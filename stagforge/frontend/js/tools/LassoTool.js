/**
 * LassoTool - Freeform selection by drawing.
 *
 * Creates selections by drawing a freeform shape. The selection is stored in
 * the global SelectionManager as an alpha mask.
 */
import { Tool } from './Tool.js';

export class LassoTool extends Tool {
    static id = 'lasso';
    static name = 'Lasso';
    static icon = 'lasso';
    static iconEntity = '&#10551;';  // Lasso curve
    static group = 'selection';
    static groupShortcut = null;
    static priority = 20;
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // State
        this.isDrawing = false;
        this.points = [];

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');

        // Animation for preview
        this.antOffset = 0;
        this.animationId = null;
    }

    activate() {
        super.activate();
        // Start SelectionManager animation
        this.app.selectionManager?.startAnimation();
    }

    deactivate() {
        super.deactivate();
        this.stopPreviewAnimation();
        // Don't clear selection on tool switch
    }

    onMouseDown(e, x, y, coords) {
        // Use document coordinates
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        this.isDrawing = true;
        this.points = [[docX, docY]];

        // Set up preview canvas
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;

        this.startPreviewAnimation();
        this.drawPreview();
    }

    onMouseMove(e, x, y, coords) {
        if (!this.isDrawing) return;

        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        // Add point with minimum distance
        const lastPoint = this.points[this.points.length - 1];
        const dist = Math.sqrt((docX - lastPoint[0]) ** 2 + (docY - lastPoint[1]) ** 2);

        if (dist > 3) {
            this.points.push([docX, docY]);
            this.drawPreview();
        }
    }

    onMouseUp(e, x, y, coords) {
        if (!this.isDrawing) return;

        this.isDrawing = false;
        this.stopPreviewAnimation();

        if (this.points.length < 3) {
            this.app.selectionManager?.clear();
            return;
        }

        // Set selection via SelectionManager
        this.app.selectionManager?.setPolygon(this.points);
        this.points = [];
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.stopPreviewAnimation();

            if (this.points.length >= 3) {
                this.app.selectionManager?.setPolygon(this.points);
            } else {
                this.app.selectionManager?.clear();
            }
            this.points = [];
        }
    }

    startPreviewAnimation() {
        if (this.animationId) return;

        const animate = () => {
            this.antOffset = (this.antOffset + 0.5) % 8;
            if (this.isDrawing && this.points.length > 0) {
                this.drawPreview();
            }
            this.animationId = requestAnimationFrame(animate);
        };
        animate();
    }

    stopPreviewAnimation() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    drawPreview() {
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);

        if (this.points.length < 2) return;

        // Draw the lasso path
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(this.points[0][0], this.points[0][1]);

        for (let i = 1; i < this.points.length; i++) {
            this.previewCtx.lineTo(this.points[i][0], this.points[i][1]);
        }

        // Close path back to start
        this.previewCtx.lineTo(this.points[0][0], this.points[0][1]);

        // Fill with semi-transparent blue
        this.previewCtx.fillStyle = 'rgba(0, 120, 212, 0.15)';
        this.previewCtx.fill();

        // Draw marching ants border
        this.previewCtx.strokeStyle = '#000000';
        this.previewCtx.lineWidth = 1;
        this.previewCtx.setLineDash([4, 4]);
        this.previewCtx.lineDashOffset = -this.antOffset;
        this.previewCtx.stroke();

        this.previewCtx.strokeStyle = '#FFFFFF';
        this.previewCtx.lineDashOffset = -this.antOffset + 4;
        this.previewCtx.stroke();

        this.previewCtx.setLineDash([]);

        this.app.renderer?.setPreviewLayer(this.previewCanvas);
    }

    getProperties() {
        return [];
    }

    getHint() {
        return 'Draw freeform selection, release to complete';
    }

    // API execution
    executeAction(action, params) {
        if (action === 'select' && params.points && params.points.length >= 3) {
            this.app.selectionManager?.setPolygon(params.points);
            return { success: true, bounds: this.app.selectionManager?.getBounds() };
        }

        if (action === 'clear' || action === 'deselect') {
            this.app.selectionManager?.clear();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
