/**
 * BrushTool - Freehand painting with configurable brush.
 */
import { Tool } from './Tool.js';
import { BrushPresets, DEFAULT_PRESET, getPreset } from '../data/BrushPresets.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class BrushTool extends Tool {
    static id = 'brush';
    static name = 'Brush';
    static icon = 'brush';
    static iconEntity = '&#10002;';  // Paintbrush
    static group = 'brush';
    static groupShortcut = 'b';
    static priority = 10;
    static cursor = 'none';  // Hide default cursor, we draw our own
    static limitedMode = true;  // Available in simple mode

    constructor(app) {
        super(app);

        // Brush properties
        this.size = 20;
        this.hardness = 100; // 0-100, affects edge softness
        this.opacity = 100;  // 0-100
        this.flow = 100;     // 0-100, affects buildup
        this.currentPreset = DEFAULT_PRESET;

        // Apply default preset
        this.applyPreset(DEFAULT_PRESET);

        // State
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;

        // Cursor position for overlay
        this.cursorX = 0;
        this.cursorY = 0;

        // Brush cursor overlay
        this.brushCursor = new BrushCursor();

        // Point history for spline smoothing (stores last 4 points)
        this.pointHistory = [];

        // Brush stamp cache
        this.brushStamp = null;
        this.stampColor = '#000000';
        this.updateBrushStamp();
    }

    activate() {
        super.activate();
        // Note: BrushCursor is not used - Vue component handles cursor overlay for brush tool
        this.app.renderer.requestRender();
    }

    deactivate() {
        super.deactivate();
        this.app.renderer.requestRender();
    }

    // Note: drawOverlay is intentionally not implemented for BrushTool
    // The Vue component (canvas_editor.js) handles the cursor overlay for brush/eraser/spray
    // to avoid double cursors and ensure consistent behavior across all UI modes

    applyPreset(presetId) {
        const preset = getPreset(presetId);
        if (preset) {
            this.size = preset.size;
            this.hardness = preset.hardness;
            this.opacity = preset.opacity;
            this.flow = preset.flow;
            this.currentPreset = presetId;
            this.updateBrushStamp();
        }
    }

    updateBrushStamp() {
        // Use higher resolution for better anti-aliasing, minimum 2x for small brushes
        const baseSize = Math.max(1, Math.ceil(this.size));
        const scale = baseSize < 10 ? 4 : (baseSize < 20 ? 2 : 1);
        const size = baseSize * scale;

        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');

        // Enable anti-aliasing
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        const radius = size / 2;
        const hardness = this.hardness / 100;

        // Parse color from app
        const color = this.app.foregroundColor || '#000000';
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);

        if (hardness >= 0.99) {
            // Hard brush - draw a proper anti-aliased circle
            ctx.beginPath();
            ctx.arc(radius, radius, radius - 0.5, 0, Math.PI * 2);
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.fill();
        } else {
            // Soft brush - use radial gradient with smooth falloff
            const gradient = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
            const coreSize = hardness;

            // Add more color stops for smoother gradient
            gradient.addColorStop(0, `rgba(${r},${g},${b},1)`);
            gradient.addColorStop(coreSize * 0.5, `rgba(${r},${g},${b},1)`);
            gradient.addColorStop(coreSize, `rgba(${r},${g},${b},0.9)`);
            gradient.addColorStop(coreSize + (1 - coreSize) * 0.3, `rgba(${r},${g},${b},0.5)`);
            gradient.addColorStop(coreSize + (1 - coreSize) * 0.6, `rgba(${r},${g},${b},0.2)`);
            gradient.addColorStop(1, `rgba(${r},${g},${b},0)`);

            // Draw as a circle, not a rectangle
            ctx.beginPath();
            ctx.arc(radius, radius, radius, 0, Math.PI * 2);
            ctx.fillStyle = gradient;
            ctx.fill();
        }

        // If we upscaled, create the final stamp at the correct size
        if (scale > 1) {
            const finalCanvas = document.createElement('canvas');
            finalCanvas.width = baseSize;
            finalCanvas.height = baseSize;
            const finalCtx = finalCanvas.getContext('2d');
            finalCtx.imageSmoothingEnabled = true;
            finalCtx.imageSmoothingQuality = 'high';
            finalCtx.drawImage(canvas, 0, 0, baseSize, baseSize);
            this.brushStamp = finalCanvas;
        } else {
            this.brushStamp = canvas;
        }

        this.stampColor = color;
    }

    onMouseDown(e, x, y, coords) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // SVG layers cannot be painted on (they're imported, not editable)
        if (layer.isSVG && layer.isSVG()) {
            return;
        }

        // Check if this is a vector layer - offer to rasterize
        if (layer.isVector && layer.isVector()) {
            this.app.showRasterizeDialog(layer, (confirmed) => {
                if (confirmed) {
                    // Layer has been rasterized, start drawing
                    this.startDrawing(e, x, y, coords);
                }
            });
            return;
        }

        this.startDrawing(e, x, y, coords);
    }

    startDrawing(e, x, y, coords) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Can't draw on groups (they have no canvas)
        if (layer.isGroup?.()) return;

        // Check if color changed
        if (this.stampColor !== this.app.foregroundColor) {
            this.updateBrushStamp();
        }

        this.isDrawing = true;

        // Store in DOCUMENT space (stable across layer expansion)
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;
        this.lastX = docX;
        this.lastY = docY;

        // Reset point history for spline smoothing (in document space)
        this.pointHistory = [{ x: docX, y: docY }];

        // Save state for undo - history system auto-detects changed region
        this.app.history.saveState('Brush Stroke');

        // Draw initial stamp (drawStamp handles doc→layer conversion internally)
        this.drawStampAtDocCoords(layer, docX, docY);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y, coords) {
        // Always track cursor for overlay (layer-local for display)
        this.cursorX = x;
        this.cursorY = y;
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) return;

        // Use DOCUMENT coordinates (stable across layer expansion)
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        // Add point to history (in document space)
        this.pointHistory.push({ x: docX, y: docY });

        // Use spline interpolation for smooth curves
        if (this.pointHistory.length >= 4) {
            // Draw spline segment using the last 4 points
            const p0 = this.pointHistory[this.pointHistory.length - 4];
            const p1 = this.pointHistory[this.pointHistory.length - 3];
            const p2 = this.pointHistory[this.pointHistory.length - 2];
            const p3 = this.pointHistory[this.pointHistory.length - 1];

            this.drawCatmullRomSegment(layer, p0, p1, p2, p3);

            // Keep only last 4 points to limit memory
            if (this.pointHistory.length > 4) {
                this.pointHistory = this.pointHistory.slice(-4);
            }
        } else if (this.pointHistory.length >= 2) {
            // Not enough points for spline yet, use linear
            this.drawLine(layer, this.lastX, this.lastY, docX, docY);
        }

        this.lastX = docX;
        this.lastY = docY;
        this.app.renderer.requestRender();
    }

    onMouseUp(e, x, y, coords) {
        if (this.isDrawing) {
            // Use DOCUMENT coordinates
            const docX = coords?.docX ?? x;
            const docY = coords?.docY ?? y;

            // Flush any remaining points with linear interpolation
            const layer = this.app.layerStack.getActiveLayer();
            if (layer && this.pointHistory.length >= 2) {
                // Draw from last drawn point to current position
                const last = this.pointHistory[this.pointHistory.length - 1];
                if (last.x !== docX || last.y !== docY) {
                    this.drawLine(layer, last.x, last.y, docX, docY);
                    this.app.renderer.requestRender();
                }
            }

            this.isDrawing = false;
            this.pointHistory = [];
            // Finish history capture - auto-detects changed pixels
            this.app.history.finishState();
        }
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.pointHistory = [];
            // Finish history capture even if mouse leaves
            this.app.history.finishState();
        }
    }

    /**
     * Draw a brush stamp at document coordinates.
     * This method handles layer expansion and coordinate conversion.
     * @param {Layer} layer - The layer to draw on
     * @param {number} docX - X in document space
     * @param {number} docY - Y in document space
     */
    drawStampAtDocCoords(layer, docX, docY) {
        const halfSize = this.size / 2;

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
            // Non-transformed: simple offset subtraction
            canvasX = docX - (layer.offsetX || 0);
            canvasY = docY - (layer.offsetY || 0);
        }

        // Draw at layer-local coordinates
        layer.ctx.globalAlpha = (this.opacity / 100) * (this.flow / 100);
        layer.ctx.drawImage(this.brushStamp, canvasX - halfSize, canvasY - halfSize);
        layer.ctx.globalAlpha = 1.0;
    }

    /**
     * Legacy drawStamp for layer-local coordinates (used by API executeAction).
     * Converts layer coords to doc coords then calls drawStampAtDocCoords.
     */
    drawStamp(layer, x, y) {
        // x, y are in layer-local coordinates
        const hasTransform = layer.hasTransform && layer.hasTransform();

        let docX, docY;
        if (hasTransform && layer.layerToDoc) {
            const doc = layer.layerToDoc(x, y);
            docX = doc.x;
            docY = doc.y;
        } else {
            // Non-transformed: simple offset addition
            docX = x + (layer.offsetX || 0);
            docY = y + (layer.offsetY || 0);
        }

        this.drawStampAtDocCoords(layer, docX, docY);
    }

    /**
     * Draw a line of stamps between two points (in document coordinates).
     */
    drawLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.drawStampAtDocCoords(layer, x, y);
        }
    }

    /**
     * Draw a smooth Catmull-Rom spline segment between p1 and p2.
     * Uses p0 and p3 as control points for curvature.
     * Points are in document coordinates.
     */
    drawCatmullRomSegment(layer, p0, p1, p2, p3) {
        // Calculate approximate arc length for adaptive stepping
        const chordLength = Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);
        const spacing = Math.max(1, this.size * 0.2);
        const steps = Math.max(2, Math.ceil(chordLength / spacing));

        // Catmull-Rom spline interpolation (centripetal, alpha=0.5 for smoothness)
        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const point = this.catmullRom(p0, p1, p2, p3, t);
            this.drawStampAtDocCoords(layer, point.x, point.y);
        }
    }

    /**
     * Catmull-Rom spline interpolation.
     * Returns a point on the curve between p1 and p2 at parameter t (0-1).
     */
    catmullRom(p0, p1, p2, p3, t) {
        const t2 = t * t;
        const t3 = t2 * t;

        // Catmull-Rom basis functions
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
        if (id === 'preset') {
            this.applyPreset(value);
        } else if (id === 'size' || id === 'hardness') {
            this[id] = value;
            this.updateBrushStamp();
        } else if (id === 'opacity' || id === 'flow') {
            this[id] = value;
        }
    }

    getProperties() {
        return [
            {
                id: 'preset',
                name: 'Preset',
                type: 'select',
                options: BrushPresets.map(p => ({ value: p.id, label: p.name })),
                value: this.currentPreset
            },
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 200, step: 1, value: this.size },
            { id: 'hardness', name: 'Hardness', type: 'range', min: 0, max: 100, step: 1, value: this.hardness },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 1, max: 100, step: 1, value: this.opacity },
            { id: 'flow', name: 'Flow', type: 'range', min: 1, max: 100, step: 1, value: this.flow }
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
            if (params.size !== undefined) this.size = params.size;
            if (params.hardness !== undefined) this.hardness = params.hardness;
            if (params.opacity !== undefined) this.opacity = params.opacity;
            if (params.flow !== undefined) this.flow = params.flow;
            if (params.color) {
                this.app.foregroundColor = params.color;
            }
            this.updateBrushStamp();

            // Save state - history auto-detects changed region
            this.app.history.saveState('Brush Stroke');

            const points = params.points;

            // Draw first point
            this.drawStamp(layer, points[0][0], points[0][1]);

            // Draw lines between consecutive points
            for (let i = 1; i < points.length; i++) {
                this.drawLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            // Finish state - auto-detects changed pixels
            this.app.history.finishState();

            this.app.renderer.requestRender();
            return { success: true };
        }

        if (action === 'dot' && params.x !== undefined && params.y !== undefined) {
            if (params.size !== undefined) this.size = params.size;
            if (params.color) {
                this.app.foregroundColor = params.color;
            }
            this.updateBrushStamp();

            // Save state - history auto-detects changed region
            this.app.history.saveState('Brush Dot');

            this.drawStamp(layer, params.x, params.y);

            // Finish state - auto-detects changed pixels
            this.app.history.finishState();

            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
