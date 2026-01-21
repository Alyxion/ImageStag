/**
 * EraserTool - Erase to transparency.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class EraserTool extends Tool {
    static id = 'eraser';
    static name = 'Eraser';
    static icon = 'eraser';
    static shortcut = 'e';
    static cursor = 'none';  // Hide default cursor, we draw our own

    constructor(app) {
        super(app);

        // Eraser properties
        this.size = 20;
        this.hardness = 100;
        this.opacity = 100;

        // Cursor position for overlay
        this.cursorX = 0;
        this.cursorY = 0;

        // Brush cursor overlay
        this.brushCursor = new BrushCursor();

        // State
        this.isErasing = false;
        this.lastX = 0;
        this.lastY = 0;

        // Point history for spline smoothing
        this.pointHistory = [];

        // Eraser stamp cache
        this.eraserStamp = null;
        this.updateEraserStamp();
    }

    activate() {
        super.activate();
        // Note: BrushCursor is not used - Vue component handles cursor overlay for eraser tool
        this.app.renderer.requestRender();
    }

    deactivate() {
        super.deactivate();
        this.app.renderer.requestRender();
    }

    // Note: drawOverlay is intentionally not implemented for EraserTool
    // The Vue component (canvas_editor.js) handles the cursor overlay for brush/eraser/spray
    // to avoid double cursors and ensure consistent behavior across all UI modes

    updateEraserStamp() {
        const size = Math.max(1, Math.ceil(this.size));
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');

        const radius = size / 2;
        const hardness = this.hardness / 100;

        // Create radial gradient for soft eraser
        const gradient = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);

        if (hardness >= 0.99) {
            gradient.addColorStop(0, 'rgba(0,0,0,1)');
            gradient.addColorStop(1, 'rgba(0,0,0,1)');
        } else {
            const coreSize = hardness;
            gradient.addColorStop(0, 'rgba(0,0,0,1)');
            gradient.addColorStop(coreSize, 'rgba(0,0,0,1)');
            gradient.addColorStop(1, 'rgba(0,0,0,0)');
        }

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, size, size);

        this.eraserStamp = canvas;
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Check if this is a vector layer - offer to rasterize
        if (layer.isVector && layer.isVector()) {
            this.app.showRasterizeDialog(layer, (confirmed) => {
                if (confirmed) {
                    // Layer has been rasterized, start erasing
                    this.startErasing(e, x, y);
                }
            });
            return;
        }

        this.startErasing(e, x, y);
    }

    startErasing(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) return;

        this.isErasing = true;
        this.lastX = x;
        this.lastY = y;

        // Reset point history for spline smoothing
        this.pointHistory = [{ x, y }];

        // Save state for undo - history system auto-detects changed region
        this.app.history.saveState('Eraser');

        // Erase initial stamp
        this.eraseStamp(layer, x, y);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.cursorX = x;
        this.cursorY = y;
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isErasing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) return;

        // Add point to history
        this.pointHistory.push({ x, y });

        // Use spline interpolation for smooth curves
        if (this.pointHistory.length >= 4) {
            const p0 = this.pointHistory[this.pointHistory.length - 4];
            const p1 = this.pointHistory[this.pointHistory.length - 3];
            const p2 = this.pointHistory[this.pointHistory.length - 2];
            const p3 = this.pointHistory[this.pointHistory.length - 1];

            this.eraseCatmullRomSegment(layer, p0, p1, p2, p3);

            if (this.pointHistory.length > 4) {
                this.pointHistory = this.pointHistory.slice(-4);
            }
        } else if (this.pointHistory.length >= 2) {
            this.eraseLine(layer, this.lastX, this.lastY, x, y);
        }

        this.lastX = x;
        this.lastY = y;
        this.app.renderer.requestRender();
    }

    onMouseUp(e, x, y) {
        if (this.isErasing) {
            // Flush remaining points
            const layer = this.app.layerStack.getActiveLayer();
            if (layer && this.pointHistory.length >= 2) {
                const last = this.pointHistory[this.pointHistory.length - 1];
                if (last.x !== x || last.y !== y) {
                    this.eraseLine(layer, last.x, last.y, x, y);
                    this.app.renderer.requestRender();
                }
            }

            this.isErasing = false;
            this.pointHistory = [];
            // Finish history capture - auto-detects changed pixels
            this.app.history.finishState();
        }
    }

    onMouseLeave(e) {
        if (this.isErasing) {
            this.isErasing = false;
            this.pointHistory = [];
            // Finish history capture even if mouse leaves
            this.app.history.finishState();
        }
    }

    eraseStamp(layer, x, y) {
        const halfSize = this.size / 2;

        // Convert document coordinates to layer canvas coordinates
        let canvasX = x, canvasY = y;
        if (layer.docToCanvas) {
            const canvasCoords = layer.docToCanvas(x, y);
            canvasX = canvasCoords.x;
            canvasY = canvasCoords.y;
        }

        layer.ctx.globalCompositeOperation = 'destination-out';
        layer.ctx.globalAlpha = this.opacity / 100;
        layer.ctx.drawImage(this.eraserStamp, canvasX - halfSize, canvasY - halfSize);
        layer.ctx.globalCompositeOperation = 'source-over';
        layer.ctx.globalAlpha = 1.0;
    }

    eraseLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.eraseStamp(layer, x, y);
        }
    }

    /**
     * Erase along a smooth Catmull-Rom spline segment between p1 and p2.
     */
    eraseCatmullRomSegment(layer, p0, p1, p2, p3) {
        const chordLength = Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);
        const spacing = Math.max(1, this.size * 0.2);
        const steps = Math.max(2, Math.ceil(chordLength / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const point = this.catmullRom(p0, p1, p2, p3, t);
            this.eraseStamp(layer, point.x, point.y);
        }
    }

    /**
     * Catmull-Rom spline interpolation.
     */
    catmullRom(p0, p1, p2, p3, t) {
        const t2 = t * t;
        const t3 = t2 * t;

        const x = 0.5 * (
            (2 * p1.x) +
            (-p0.x + p2.x) * t +
            (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
            (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3
        );

        const y = 0.5 * (
            (2 * p1.y) +
            (-p0.y + p2.y) * t +
            (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
            (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3
        );

        return { x, y };
    }

    onPropertyChanged(id, value) {
        if (id === 'size' || id === 'hardness') {
            this.updateEraserStamp();
        }
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 200, step: 1, value: this.size },
            { id: 'hardness', name: 'Hardness', type: 'range', min: 0, max: 100, step: 1, value: this.hardness },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 1, max: 100, step: 1, value: this.opacity }
        ];
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'stroke' && params.points && params.points.length >= 1) {
            if (params.size !== undefined) this.size = params.size;
            if (params.hardness !== undefined) this.hardness = params.hardness;
            if (params.opacity !== undefined) this.opacity = params.opacity;
            this.updateEraserStamp();

            // Save state - history auto-detects changed region
            this.app.history.saveState('Eraser');

            const points = params.points;

            // Erase first point
            this.eraseStamp(layer, points[0][0], points[0][1]);

            // Erase lines between consecutive points
            for (let i = 1; i < points.length; i++) {
                this.eraseLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            // Finish state - auto-detects changed pixels
            this.app.history.finishState();

            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
