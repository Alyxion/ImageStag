/**
 * CloneStampTool - Clone/sample pixels from one area and paint them elsewhere.
 *
 * Alt+click to set the source point, then paint to clone from that area.
 * The offset between source and destination is maintained while painting.
 *
 * Visual feedback:
 * - Source point shows a crosshair when set
 * - While painting, source indicator follows cursor movement
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class CloneStampTool extends Tool {
    static id = 'clonestamp';
    static name = 'Clone Stamp';
    static icon = 'clone';
    static iconEntity = '&#128274;';  // Stamp
    static group = 'stamp';
    static groupShortcut = 's';
    static priority = 10;
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Stamp properties
        this.size = 20;
        this.hardness = 50; // 0-100, softer default for natural blending
        this.opacity = 100;
        this.flow = 100;
        this.aligned = true; // Keep offset consistent across strokes

        // Source state
        this.sourceX = null;
        this.sourceY = null;
        this.sourceLayerId = null;
        this.hasSource = false;

        // Offset between source and destination
        this.offsetX = 0;
        this.offsetY = 0;

        // Drawing state
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;

        // Current cursor position for source indicator
        this.currentX = 0;
        this.currentY = 0;

        // Brush cursor overlay for current position
        this.brushCursor = new BrushCursor();

        // Brush stamp for soft edges
        this.brushStamp = null;
        this.updateBrushStamp();
    }

    activate() {
        super.activate();
        this.brushCursor.setVisible(true);
        this.app.renderer.requestRender();
    }

    deactivate() {
        super.deactivate();
        this.brushCursor.setVisible(false);
        this.app.renderer.clearOverlay?.();
    }

    /**
     * Draw overlay showing source indicator and brush cursor.
     * Called by Renderer after compositing layers.
     *
     * @param {CanvasRenderingContext2D} ctx - The display canvas context
     * @param {Function} docToScreen - Function to convert doc coords to screen coords
     */
    drawOverlay(ctx, docToScreen) {
        const zoom = this.app.renderer?.zoom || 1;

        // Always draw brush cursor at current position
        this.brushCursor.draw(ctx, docToScreen, zoom);

        // Draw source indicator only if source is set
        if (!this.hasSource) return;

        // Calculate source indicator position
        // If we have an offset (started painting), show source relative to cursor
        // Otherwise show the original source point
        let indicatorX, indicatorY;

        if (this.offsetX !== 0 || this.offsetY !== 0) {
            // Source moves relative to cursor
            indicatorX = this.currentX + this.offsetX;
            indicatorY = this.currentY + this.offsetY;
        } else {
            // Show original source point
            indicatorX = this.sourceX;
            indicatorY = this.sourceY;
        }

        // Convert to screen coordinates
        const screen = docToScreen(indicatorX, indicatorY);
        const x = screen.x;
        const y = screen.y;

        // Get brush size in screen space
        const radius = (this.size / 2) * zoom;

        ctx.save();

        // Draw source circle
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.stroke();

        // Draw crosshair
        ctx.setLineDash([]);
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 1;
        const crossSize = Math.max(10, radius + 5);

        ctx.beginPath();
        // Horizontal line
        ctx.moveTo(x - crossSize, y);
        ctx.lineTo(x - radius - 3, y);
        ctx.moveTo(x + radius + 3, y);
        ctx.lineTo(x + crossSize, y);
        // Vertical line
        ctx.moveTo(x, y - crossSize);
        ctx.lineTo(x, y - radius - 3);
        ctx.moveTo(x, y + radius + 3);
        ctx.lineTo(x, y + crossSize);
        ctx.stroke();

        // Draw small center point
        ctx.fillStyle = '#00FFFF';
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    updateBrushStamp() {
        const size = Math.max(1, Math.ceil(this.size));
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');

        const radius = size / 2;
        const hardness = this.hardness / 100;

        if (hardness >= 0.99) {
            // Hard edge - solid circle
            ctx.beginPath();
            ctx.arc(radius, radius, radius - 0.5, 0, Math.PI * 2);
            ctx.fillStyle = 'white';
            ctx.fill();
        } else {
            // Soft edge - radial gradient
            const gradient = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
            const coreSize = hardness;
            gradient.addColorStop(0, 'rgba(255,255,255,1)');
            gradient.addColorStop(coreSize, 'rgba(255,255,255,0.9)');
            gradient.addColorStop(coreSize + (1 - coreSize) * 0.5, 'rgba(255,255,255,0.3)');
            gradient.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.beginPath();
            ctx.arc(radius, radius, radius, 0, Math.PI * 2);
            ctx.fillStyle = gradient;
            ctx.fill();
        }

        this.brushStamp = canvas;
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Alt+click sets the source point
        if (e.altKey) {
            this.sourceX = x;
            this.sourceY = y;
            this.sourceLayerId = layer.id;
            this.hasSource = true;

            // Always reset offset when setting a new source point
            // The offset will be recalculated on first paint stroke
            this.offsetX = 0;
            this.offsetY = 0;

            // Redraw to show source indicator
            this.app.renderer.requestRender();
            return;
        }

        // Can't paint without a source
        if (!this.hasSource) {
            console.warn('Clone Stamp: Alt+click to set source point first');
            return;
        }

        this.startDrawing(x, y, layer);
    }

    startDrawing(x, y, layer) {
        // Calculate offset on first stroke or if not aligned
        if (this.offsetX === 0 && this.offsetY === 0) {
            this.offsetX = this.sourceX - x;
            this.offsetY = this.sourceY - y;
        }

        this.isDrawing = true;
        this.lastX = x;
        this.lastY = y;

        // Save state for undo
        this.app.history.saveState('Clone Stamp');

        // Draw initial stamp
        this.cloneStamp(layer, x, y);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for source indicator and brush cursor
        this.currentX = x;
        this.currentY = y;
        this.brushCursor.update(x, y, this.size);

        // Request render to update overlays
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Draw line of stamps between last position and current
        this.cloneLine(layer, this.lastX, this.lastY, x, y);

        this.lastX = x;
        this.lastY = y;
        this.app.renderer.requestRender();
    }

    onMouseUp(e, x, y) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.app.history.finishState();

            // Reset offset if not aligned mode
            if (!this.aligned) {
                this.offsetX = 0;
                this.offsetY = 0;
            }
        }
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.app.history.finishState();
        }
    }

    cloneStamp(layer, destX, destY) {
        // Calculate source position
        const srcX = destX + this.offsetX;
        const srcY = destY + this.offsetY;

        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);

        // Expand layer if needed
        if (layer.expandToInclude) {
            layer.expandToInclude(destX - halfSize, destY - halfSize, size, size);
        }

        // Get source layer
        const sourceLayer = this.sourceLayerId ?
            this.app.layerStack.getLayerById(this.sourceLayerId) :
            layer;

        if (!sourceLayer) return;

        // Convert coordinates to layer canvas space
        let srcCanvasX = srcX, srcCanvasY = srcY;
        let destCanvasX = destX, destCanvasY = destY;

        if (sourceLayer.docToCanvas) {
            const srcCoords = sourceLayer.docToCanvas(srcX, srcY);
            srcCanvasX = srcCoords.x;
            srcCanvasY = srcCoords.y;
        }
        if (layer.docToCanvas) {
            const destCoords = layer.docToCanvas(destX, destY);
            destCanvasX = destCoords.x;
            destCanvasY = destCoords.y;
        }

        // Sample source pixels
        const sampleX = Math.round(srcCanvasX - halfSize);
        const sampleY = Math.round(srcCanvasY - halfSize);

        // Clamp to valid source region
        const clampedX = Math.max(0, Math.min(sampleX, sourceLayer.width - size));
        const clampedY = Math.max(0, Math.min(sampleY, sourceLayer.height - size));
        const sampleWidth = Math.min(size, sourceLayer.width - clampedX);
        const sampleHeight = Math.min(size, sourceLayer.height - clampedY);

        if (sampleWidth <= 0 || sampleHeight <= 0) return;

        // Get source image data
        let sourceData;
        try {
            sourceData = sourceLayer.ctx.getImageData(clampedX, clampedY, sampleWidth, sampleHeight);
        } catch (e) {
            return; // Can't sample from outside canvas
        }

        // Create temporary canvas for the cloned pixels
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = sampleWidth;
        tempCanvas.height = sampleHeight;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.putImageData(sourceData, 0, 0);

        // Apply brush mask if soft edges
        if (this.hardness < 100) {
            tempCtx.globalCompositeOperation = 'destination-in';
            tempCtx.drawImage(
                this.brushStamp,
                0, 0, this.brushStamp.width, this.brushStamp.height,
                0, 0, sampleWidth, sampleHeight
            );
        }

        // Draw to destination
        const prevAlpha = layer.ctx.globalAlpha;
        layer.ctx.globalAlpha = (this.opacity / 100) * (this.flow / 100);

        const drawX = Math.round(destCanvasX - halfSize) + (clampedX - sampleX);
        const drawY = Math.round(destCanvasY - halfSize) + (clampedY - sampleY);
        layer.ctx.drawImage(tempCanvas, drawX, drawY);

        layer.ctx.globalAlpha = prevAlpha;
    }

    cloneLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.cloneStamp(layer, x, y);
        }
    }

    onPropertyChanged(id, value) {
        if (id === 'size' || id === 'hardness') {
            this[id] = value;
            this.updateBrushStamp();
        } else if (id === 'opacity' || id === 'flow') {
            this[id] = value;
        } else if (id === 'aligned') {
            this.aligned = value === true || value === 'true';
        }
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 200, step: 1, value: this.size },
            { id: 'hardness', name: 'Hardness', type: 'range', min: 0, max: 100, step: 1, value: this.hardness },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 1, max: 100, step: 1, value: this.opacity },
            { id: 'flow', name: 'Flow', type: 'range', min: 1, max: 100, step: 1, value: this.flow },
            { id: 'aligned', name: 'Aligned', type: 'checkbox', value: this.aligned }
        ];
    }

    getHint() {
        if (!this.hasSource) {
            return 'Alt+click to set clone source';
        }
        return 'Paint to clone from source. Alt+click to set new source.';
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'setSource') {
            if (params.x === undefined || params.y === undefined) {
                return { success: false, error: 'Source x and y required' };
            }
            this.sourceX = params.x;
            this.sourceY = params.y;
            this.sourceLayerId = params.layerId || layer.id;
            this.hasSource = true;
            this.offsetX = 0;
            this.offsetY = 0;
            return { success: true };
        }

        if (action === 'stroke' && params.points && params.points.length >= 1) {
            if (!this.hasSource) {
                return { success: false, error: 'No source point set. Use setSource first.' };
            }

            if (params.size !== undefined) {
                this.size = params.size;
                this.updateBrushStamp();
            }
            if (params.opacity !== undefined) this.opacity = params.opacity;

            this.app.history.saveState('Clone Stamp');

            const points = params.points;

            // Set offset from first point
            this.offsetX = this.sourceX - points[0][0];
            this.offsetY = this.sourceY - points[0][1];

            // Draw stamps
            this.cloneStamp(layer, points[0][0], points[0][1]);
            for (let i = 1; i < points.length; i++) {
                this.cloneLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
