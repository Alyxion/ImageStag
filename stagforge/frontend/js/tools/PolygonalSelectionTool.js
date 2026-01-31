/**
 * PolygonalSelectionTool - Create selections by clicking points to form a polygon.
 *
 * Click to add vertices, double-click or click near start to close.
 * The selection is stored in the global SelectionManager as an alpha mask.
 */
import { Tool } from './Tool.js';

export class PolygonalSelectionTool extends Tool {
    static id = 'polygonal-selection';
    static name = 'Polygonal Selection';
    static icon = 'polygon';
    static iconEntity = '&#11040;';  // Pentagon shape
    static group = 'selection';
    static groupShortcut = null;
    static priority = 25;
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // State
        this.isActive = false;
        this.points = [];

        // Close threshold - distance to first point to close polygon
        this.closeThreshold = 10;

        // Soft edge (feather) - pixels of falloff at edges
        this.feather = 0;  // Default hard edge for polygonal

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');

        // Animation for preview
        this.antOffset = 0;
        this.animationId = null;

        // Mouse position for preview line to cursor
        this.currentX = 0;
        this.currentY = 0;
    }

    activate() {
        super.activate();
        // Start SelectionManager animation
        this.app.selectionManager?.startAnimation();
    }

    deactivate() {
        super.deactivate();
        this.stopPreviewAnimation();
        this.cancelSelection();
    }

    onMouseDown(e, x, y, coords) {
        // Use document coordinates
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        // Check if clicking near start point to close
        if (this.points.length >= 3) {
            const startX = this.points[0][0];
            const startY = this.points[0][1];
            const dist = Math.sqrt((docX - startX) ** 2 + (docY - startY) ** 2);

            if (dist < this.closeThreshold) {
                this.completeSelection();
                return;
            }
        }

        // Start new selection if not active
        if (!this.isActive) {
            this.isActive = true;
            this.points = [];

            // Set up preview canvas
            const docWidth = this.app.layerStack.width;
            const docHeight = this.app.layerStack.height;
            this.previewCanvas.width = docWidth;
            this.previewCanvas.height = docHeight;

            this.startPreviewAnimation();
        }

        // Add point
        this.points.push([docX, docY]);
        this.drawPreview();
    }

    onMouseMove(e, x, y, coords) {
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        this.currentX = docX;
        this.currentY = docY;

        // Update preview while creating polygon
        if (this.isActive && this.points.length > 0) {
            this.drawPreview();
        }
    }

    onDblClick(e, x, y, coords) {
        // Double-click completes selection
        if (this.isActive && this.points.length >= 3) {
            this.completeSelection();
        }
    }

    onKeyDown(e) {
        if (!this.isActive) return;

        if (e.key === 'Enter') {
            // Complete selection
            if (this.points.length >= 3) {
                this.completeSelection();
            }
            e.preventDefault();
        } else if (e.key === 'Escape') {
            // Cancel selection
            this.cancelSelection();
            e.preventDefault();
        } else if (e.key === 'Backspace' || e.key === 'Delete') {
            // Remove last point
            if (this.points.length > 0) {
                this.points.pop();
                if (this.points.length === 0) {
                    this.cancelSelection();
                } else {
                    this.drawPreview();
                }
            }
            e.preventDefault();
        }
    }

    completeSelection() {
        this.stopPreviewAnimation();

        if (this.points.length < 3) {
            this.app.selectionManager?.clear();
        } else {
            // Set selection via SelectionManager with feather
            this.app.selectionManager?.setPolygon(this.points, this.feather);
        }

        this.points = [];
        this.isActive = false;
        this.app.renderer?.clearPreviewLayer();
    }

    cancelSelection() {
        this.stopPreviewAnimation();
        this.points = [];
        this.isActive = false;
        this.app.renderer?.clearPreviewLayer();
    }

    startPreviewAnimation() {
        if (this.animationId) return;

        const animate = () => {
            this.antOffset = (this.antOffset + 0.5) % 8;
            if (this.isActive && this.points.length > 0) {
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

        if (this.points.length === 0) return;

        // Draw the polygon path
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(this.points[0][0], this.points[0][1]);

        for (let i = 1; i < this.points.length; i++) {
            this.previewCtx.lineTo(this.points[i][0], this.points[i][1]);
        }

        // Draw line to current mouse position
        this.previewCtx.lineTo(this.currentX, this.currentY);

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

        // Draw vertex points
        this.previewCtx.fillStyle = '#FFFFFF';
        this.previewCtx.strokeStyle = '#000000';
        this.previewCtx.lineWidth = 1;

        for (let i = 0; i < this.points.length; i++) {
            const [px, py] = this.points[i];
            this.previewCtx.beginPath();
            this.previewCtx.arc(px, py, 3, 0, Math.PI * 2);
            this.previewCtx.fill();
            this.previewCtx.stroke();
        }

        // Highlight start point if we can close
        if (this.points.length >= 3) {
            const startX = this.points[0][0];
            const startY = this.points[0][1];
            const dist = Math.sqrt((this.currentX - startX) ** 2 + (this.currentY - startY) ** 2);

            if (dist < this.closeThreshold) {
                this.previewCtx.fillStyle = '#00FF00';
                this.previewCtx.beginPath();
                this.previewCtx.arc(startX, startY, 5, 0, Math.PI * 2);
                this.previewCtx.fill();
                this.previewCtx.stroke();
            }
        }

        this.app.renderer?.setPreviewLayer(this.previewCanvas);
    }

    getProperties() {
        return [
            { id: 'feather', name: 'Feather', type: 'range', min: 0, max: 50, step: 1, value: this.feather, unit: 'px' }
        ];
    }

    onPropertyChanged(id, value) {
        if (id === 'feather') {
            this.feather = value;
        }
    }

    getHint() {
        if (!this.isActive) {
            return 'Click to start polygon selection';
        }
        if (this.points.length < 3) {
            return `Click to add vertices (${this.points.length} points)`;
        }
        return `Click to add vertices, click start point or Enter to complete (${this.points.length} points)`;
    }

    // API execution
    executeAction(action, params) {
        if (action === 'select' && params.points && params.points.length >= 3) {
            const feather = params.feather ?? this.feather;
            this.app.selectionManager?.setPolygon(params.points, feather);
            return { success: true, bounds: this.app.selectionManager?.getBounds() };
        }

        if (action === 'clear' || action === 'deselect') {
            this.app.selectionManager?.clear();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
