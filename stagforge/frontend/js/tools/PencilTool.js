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
    static layerTypes = { raster: true, text: false, svg: false, group: false };

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

    onMouseDown(e) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // SVG layers cannot be drawn on (they're imported, not editable)
        if (layer.isSVG && layer.isSVG()) {
            return;
        }

        this.startDrawing(e);
    }

    startDrawing(e) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isDrawing = true;

        // Store in DOCUMENT space (stable across layer expansion)
        const { docX, docY } = e;
        this.lastX = Math.round(docX);
        this.lastY = Math.round(docY);

        // Save state for undo
        this.app.history.saveState('Pencil Stroke');

        // Draw initial pixel/block
        this.drawPixelAtDocCoords(layer, this.lastX, this.lastY);
        layer.touch();
    }

    onMouseMove(e) {
        // Always track cursor for overlay (use document coords for docToScreen)
        const { docX, docY } = e;
        this.brushCursor.update(docX, docY, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        const newX = Math.round(docX);
        const newY = Math.round(docY);

        // Draw a line of pixels using Bresenham's algorithm
        this.drawLineAtDocCoords(layer, this.lastX, this.lastY, newX, newY);

        this.lastX = newX;
        this.lastY = newY;
        layer.touch();
    }

    onMouseUp(e) {
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
     * Draw a single pixel or block at the specified document coordinates.
     * Uses fillRect for crisp, non-anti-aliased drawing.
     */
    drawPixelAtDocCoords(layer, docX, docY) {
        const halfSize = Math.floor(this.size / 2);

        // Expand layer if needed (may change layer offset/size)
        // Use expandToIncludeDocPoint which handles rotated layers correctly
        if (layer.expandToIncludeDocPoint) {
            layer.expandToIncludeDocPoint(docX, docY, halfSize);
        } else if (layer.expandToInclude) {
            layer.expandToInclude(docX - halfSize, docY - halfSize, this.size, this.size);
        }

        // Convert doc→layer AFTER expansion (geometry may have changed)
        const hasTransform = layer.hasTransform && layer.hasTransform();
        let canvasX, canvasY;
        if (hasTransform && layer.docToLayer) {
            const local = layer.docToLayer(docX, docY);
            canvasX = local.x;
            canvasY = local.y;
        } else {
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
        layer.ctx.fillRect(
            Math.round(canvasX - halfSize),
            Math.round(canvasY - halfSize),
            this.size,
            this.size
        );

        layer.ctx.globalAlpha = 1.0;
    }

    /**
     * Legacy drawPixel for layer-local coordinates (used by API executeAction).
     */
    drawPixel(layer, x, y) {
        // x, y are in layer-local coordinates
        const hasTransform = layer.hasTransform && layer.hasTransform();

        let docX, docY;
        if (hasTransform && layer.layerToDoc) {
            const doc = layer.layerToDoc(x, y);
            docX = doc.x;
            docY = doc.y;
        } else {
            docX = x + (layer.offsetX || 0);
            docY = y + (layer.offsetY || 0);
        }

        this.drawPixelAtDocCoords(layer, docX, docY);
    }

    /**
     * Draw a line using Bresenham's algorithm for crisp pixel lines (document coordinates).
     */
    drawLineAtDocCoords(layer, x0, y0, x1, y1) {
        const dx = Math.abs(x1 - x0);
        const dy = Math.abs(y1 - y0);
        const sx = x0 < x1 ? 1 : -1;
        const sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;

        let x = x0;
        let y = y0;

        while (true) {
            this.drawPixelAtDocCoords(layer, x, y);

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

    /**
     * Legacy drawLine for layer-local coordinates (used by API executeAction).
     */
    drawLine(layer, x0, y0, x1, y1) {
        // Convert layer-local to doc coords first
        const hasTransform = layer.hasTransform && layer.hasTransform();

        let doc0X, doc0Y, doc1X, doc1Y;
        if (hasTransform && layer.layerToDoc) {
            const d0 = layer.layerToDoc(x0, y0);
            const d1 = layer.layerToDoc(x1, y1);
            doc0X = d0.x;
            doc0Y = d0.y;
            doc1X = d1.x;
            doc1Y = d1.y;
        } else {
            doc0X = x0 + (layer.offsetX || 0);
            doc0Y = y0 + (layer.offsetY || 0);
            doc1X = x1 + (layer.offsetX || 0);
            doc1Y = y1 + (layer.offsetY || 0);
        }

        this.drawLineAtDocCoords(layer, Math.round(doc0X), Math.round(doc0Y), Math.round(doc1X), Math.round(doc1Y));
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

            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
