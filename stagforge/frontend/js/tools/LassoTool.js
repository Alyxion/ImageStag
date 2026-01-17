/**
 * LassoTool - Freeform selection by drawing.
 */
import { Tool } from './Tool.js';

export class LassoTool extends Tool {
    static id = 'lasso';
    static name = 'Lasso';
    static icon = 'lasso';
    static shortcut = 'l';
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // State
        this.isDrawing = false;
        this.points = [];

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');

        // Marching ants animation
        this.antOffset = 0;
        this.antAnimationId = null;
    }

    activate() {
        super.activate();
        this.startMarchingAnts();
    }

    deactivate() {
        super.deactivate();
        this.stopMarchingAnts();
        this.app.renderer.clearPreviewLayer();
    }

    onMouseDown(e, x, y) {
        this.isDrawing = true;
        this.points = [[x, y]];

        // Set up preview canvas to document dimensions, not layer dimensions
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;

        this.drawPreview();
    }

    onMouseMove(e, x, y) {
        if (!this.isDrawing) return;

        // Add point (with some minimum distance to avoid too many points)
        const lastPoint = this.points[this.points.length - 1];
        const dist = Math.sqrt((x - lastPoint[0]) ** 2 + (y - lastPoint[1]) ** 2);

        if (dist > 3) {
            this.points.push([x, y]);
            this.drawPreview();
        }
    }

    onMouseUp(e, x, y) {
        if (!this.isDrawing) return;

        this.isDrawing = false;

        if (this.points.length < 3) {
            this.clearSelection();
            return;
        }

        // Close the path and create selection
        this.finalizeSelection();
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            if (this.points.length >= 3) {
                this.finalizeSelection();
            } else {
                this.clearSelection();
            }
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
        this.previewCtx.fillStyle = 'rgba(0, 120, 212, 0.2)';
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

        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    finalizeSelection() {
        // Get bounding box of lasso
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

        for (const [x, y] of this.points) {
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        }

        // Clamp to document bounds
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        minX = Math.max(0, Math.floor(minX));
        minY = Math.max(0, Math.floor(minY));
        maxX = Math.min(docWidth, Math.ceil(maxX));
        maxY = Math.min(docHeight, Math.ceil(maxY));

        const bounds = {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY
        };

        // Only create selection if it has area after clamping
        if (bounds.width <= 0 || bounds.height <= 0) {
            this.clearSelection();
            return;
        }

        // Set selection via selection tool
        const selectionTool = this.app.toolManager.tools.get('selection');
        if (selectionTool) {
            selectionTool.setSelection(bounds);
        }

        this.app.eventBus.emit('selection:changed', { selection: bounds, lassoPoints: this.points });
    }

    clearSelection() {
        this.points = [];
        this.app.renderer.clearPreviewLayer();
    }

    startMarchingAnts() {
        const animate = () => {
            this.antOffset = (this.antOffset + 0.5) % 8;
            if (this.points.length > 0) {
                this.drawPreview();
            }
            this.antAnimationId = requestAnimationFrame(animate);
        };
        animate();
    }

    stopMarchingAnts() {
        if (this.antAnimationId) {
            cancelAnimationFrame(this.antAnimationId);
            this.antAnimationId = null;
        }
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
            this.points = params.points;
            this.finalizeSelection();
            return { success: true };
        }

        if (action === 'clear') {
            this.clearSelection();
            const selectionTool = this.app.toolManager.tools.get('selection');
            if (selectionTool) {
                selectionTool.clearSelection();
            }
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
