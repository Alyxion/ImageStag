/**
 * PencilTool - Hard-edged, aliased strokes for pixel art.
 *
 * Unlike the brush tool, the pencil creates crisp, non-anti-aliased lines.
 * This is ideal for pixel art where you need precise control over individual pixels.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class PencilTool extends Tool {
    static id = 'pencil';
    static name = 'Pencil';
    static icon = 'pencil';
    static iconEntity = '&#9999;';  // Pencil
    static group = 'brush';
    static priority = 20;  // After brush in same group
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Pencil properties
        this.size = 1;       // Default 1px for pixel art
        this.opacity = 100;  // 0-100

        // Cursor overlay
        this.brushCursor = new BrushCursor({ showCrosshair: true });

        // State
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;
    }

    activate() {
        super.activate();
        this.brushCursor.setVisible(true);
        this.app.renderer.requestRender();
    }

    deactivate() {
        super.deactivate();
        this.brushCursor.setVisible(false);
        this.app.renderer.requestRender();
    }

    drawOverlay(ctx, docToScreen) {
        const zoom = this.app.renderer?.zoom || 1;
        this.brushCursor.draw(ctx, docToScreen, zoom);
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // SVG layers cannot be drawn on (they're imported, not editable)
        if (layer.isSVG && layer.isSVG()) {
            return;
        }

        // Check if this is a vector layer - offer to rasterize
        if (layer.isVector && layer.isVector()) {
            this.app.showRasterizeDialog(layer, (confirmed) => {
                if (confirmed) {
                    this.startDrawing(e, x, y);
                }
            });
            return;
        }

        this.startDrawing(e, x, y);
    }

    startDrawing(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isDrawing = true;
        this.lastX = Math.round(x);
        this.lastY = Math.round(y);

        // Save state for undo
        this.app.history.saveState('Pencil Stroke');

        // Draw initial pixel/block
        this.drawPixel(layer, this.lastX, this.lastY);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        const newX = Math.round(x);
        const newY = Math.round(y);

        // Draw a line of pixels using Bresenham's algorithm
        this.drawLine(layer, this.lastX, this.lastY, newX, newY);

        this.lastX = newX;
        this.lastY = newY;
        this.app.renderer.requestRender();
    }

    onMouseUp(e, x, y) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.app.history.finishState();
        }
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.app.history.finishState();
        }
    }

    /**
     * Draw a single pixel or block at the specified position.
     * Uses fillRect for crisp, non-anti-aliased drawing.
     */
    drawPixel(layer, x, y) {
        // x, y are in layer-local coordinates (pre-transformed by app.js)
        const halfSize = Math.floor(this.size / 2);

        let canvasX, canvasY;

        // For transformed layers, don't expand - draw directly in layer-local space
        if (layer.hasTransform && layer.hasTransform()) {
            canvasX = x;
            canvasY = y;
        } else {
            // Non-transformed layers: expand if needed
            let docX = x + (layer.offsetX || 0);
            let docY = y + (layer.offsetY || 0);

            if (layer.expandToInclude) {
                layer.expandToInclude(
                    docX - halfSize,
                    docY - halfSize,
                    this.size,
                    this.size
                );
            }

            // Re-convert doc→layer AFTER expansion (offset may have changed)
            canvasX = docX - (layer.offsetX || 0);
            canvasY = docY - (layer.offsetY || 0);
        }

        // Disable anti-aliasing for crisp pixels
        layer.ctx.imageSmoothingEnabled = false;

        // Set color and opacity
        const color = this.app.foregroundColor || '#000000';
        layer.ctx.fillStyle = color;
        layer.ctx.globalAlpha = this.opacity / 100;

        // Draw a rectangle for the pencil size
        // For size=1, this draws a single pixel
        layer.ctx.fillRect(
            Math.round(canvasX - halfSize),
            Math.round(canvasY - halfSize),
            this.size,
            this.size
        );

        layer.ctx.globalAlpha = 1.0;
    }

    /**
     * Draw a line using Bresenham's algorithm for crisp pixel lines.
     * This avoids anti-aliasing artifacts by placing pixels exactly on integer coordinates.
     */
    drawLine(layer, x0, y0, x1, y1) {
        const dx = Math.abs(x1 - x0);
        const dy = Math.abs(y1 - y0);
        const sx = x0 < x1 ? 1 : -1;
        const sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;

        let x = x0;
        let y = y0;

        while (true) {
            this.drawPixel(layer, x, y);

            if (x === x1 && y === y1) break;

            const e2 = 2 * err;
            if (e2 > -dy) {
                err -= dy;
                x += sx;
            }
            if (e2 < dx) {
                err += dx;
                y += sy;
            }
        }
    }

    onPropertyChanged(id, value) {
        if (id === 'size') {
            this.size = Math.max(1, Math.round(value));
        } else if (id === 'opacity') {
            this.opacity = value;
        }
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 50, step: 1, value: this.size },
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
            // Apply optional parameters
            if (params.size !== undefined) this.size = Math.max(1, Math.round(params.size));
            if (params.opacity !== undefined) this.opacity = params.opacity;
            if (params.color) {
                this.app.foregroundColor = params.color;
            }

            // Save state
            this.app.history.saveState('Pencil Stroke');

            const points = params.points;

            // Draw first point
            this.drawPixel(layer, Math.round(points[0][0]), Math.round(points[0][1]));

            // Draw lines between consecutive points
            for (let i = 1; i < points.length; i++) {
                this.drawLine(
                    layer,
                    Math.round(points[i-1][0]), Math.round(points[i-1][1]),
                    Math.round(points[i][0]), Math.round(points[i][1])
                );
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        if (action === 'pixel' && params.x !== undefined && params.y !== undefined) {
            if (params.size !== undefined) this.size = Math.max(1, Math.round(params.size));
            if (params.color) {
                this.app.foregroundColor = params.color;
            }

            this.app.history.saveState('Pencil Pixel');
            this.drawPixel(layer, Math.round(params.x), Math.round(params.y));
            this.app.history.finishState();

            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
