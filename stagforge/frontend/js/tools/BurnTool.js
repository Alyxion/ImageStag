/**
 * BurnTool - Darken areas by painting.
 *
 * Simulates burning in traditional photography darkroom techniques.
 * Can target shadows, midtones, or highlights.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class BurnTool extends Tool {
    static id = 'burn';
    static name = 'Burn';
    static icon = 'burn';
    static iconEntity = '&#9790;';  // Moon
    static group = 'dodge';
    static priority = 20;  // After dodge in same group
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Tool properties
        this.size = 20;
        this.exposure = 50;  // 0-100
        this.range = 'midtones'; // shadows, midtones, highlights

        // Cursor overlay
        this.brushCursor = new BrushCursor();

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

    onMouseDown(e, x, y, coords) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isDrawing = true;

        // Store in DOCUMENT space (stable across layer expansion)
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;
        this.lastX = docX;
        this.lastY = docY;

        // Save state for undo
        this.app.history.saveState('Burn');

        // Apply burn at initial position
        this.burnAtDocCoords(layer, docX, docY);
        layer.touch();
    }

    onMouseMove(e, x, y, coords) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Use DOCUMENT coordinates (stable across layer expansion)
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        // Burn along the path (using document coordinates)
        this.burnLineAtDocCoords(layer, this.lastX, this.lastY, docX, docY);
        layer.touch();

        this.lastX = docX;
        this.lastY = docY;
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

    // Calculate how much to affect a pixel based on its luminance and the target range
    getRangeWeight(luminance) {
        // luminance is 0-255
        const l = luminance / 255;

        switch (this.range) {
            case 'shadows':
                // Affect dark areas more, fade out at midtones
                return l < 0.33 ? 1 : Math.max(0, 1 - (l - 0.33) / 0.33);
            case 'highlights':
                // Affect bright areas more, fade in from midtones
                return l > 0.67 ? 1 : Math.max(0, (l - 0.33) / 0.33);
            case 'midtones':
            default:
                // Bell curve centered on midtones
                return 1 - Math.abs(l - 0.5) * 2;
        }
    }

    /**
     * Burn at document coordinates.
     */
    burnAtDocCoords(layer, docX, docY) {
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);
        const exposure = this.exposure / 100;

        // Expand layer if needed (may change layer offset/size)
        // Use expandToIncludeDocPoint which handles rotated layers correctly
        if (layer.expandToIncludeDocPoint) {
            layer.expandToIncludeDocPoint(docX, docY, halfSize);
        } else if (layer.expandToInclude) {
            layer.expandToInclude(docX - halfSize, docY - halfSize, size, size);
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

        const sampleX = Math.max(0, Math.round(canvasX - halfSize));
        const sampleY = Math.max(0, Math.round(canvasY - halfSize));
        const sampleW = Math.min(size, layer.width - sampleX);
        const sampleH = Math.min(size, layer.height - sampleY);

        if (sampleW <= 0 || sampleH <= 0) return;

        let sourceData;
        try {
            sourceData = layer.ctx.getImageData(sampleX, sampleY, sampleW, sampleH);
        } catch (e) {
            return;
        }

        const data = sourceData.data;
        const centerX = canvasX - sampleX;
        const centerY = canvasY - sampleY;
        const radius = halfSize;

        for (let py = 0; py < sampleH; py++) {
            for (let px = 0; px < sampleW; px++) {
                const dx = px - centerX;
                const dy = py - centerY;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist <= radius) {
                    const idx = (py * sampleW + px) * 4;

                    // Calculate luminance
                    const luminance = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
                    const rangeWeight = this.getRangeWeight(luminance);

                    // Soft falloff at edges
                    const falloff = 1 - (dist / radius);
                    const amount = exposure * falloff * rangeWeight * 0.3; // 0.3 for subtlety

                    // Darken by moving toward black
                    data[idx] = Math.max(0, data[idx] - data[idx] * amount);
                    data[idx + 1] = Math.max(0, data[idx + 1] - data[idx + 1] * amount);
                    data[idx + 2] = Math.max(0, data[idx + 2] - data[idx + 2] * amount);
                    // Keep alpha unchanged
                }
            }
        }

        layer.ctx.putImageData(sourceData, sampleX, sampleY);
    }

    /**
     * Legacy burnAt for layer-local coordinates (used by API executeAction).
     */
    burnAt(layer, x, y) {
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

        this.burnAtDocCoords(layer, docX, docY);
    }

    /**
     * Burn along a line (document coordinates).
     */
    burnLineAtDocCoords(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.burnAtDocCoords(layer, x, y);
        }
    }

    /**
     * Legacy burnLine for layer-local coordinates (used by API executeAction).
     */
    burnLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.burnAt(layer, x, y);
        }
    }

    onPropertyChanged(id, value) {
        if (id === 'size') {
            this.size = value;
        } else if (id === 'exposure') {
            this.exposure = value;
        } else if (id === 'range') {
            this.range = value;
        }
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 200, step: 1, value: this.size },
            { id: 'exposure', name: 'Exposure', type: 'range', min: 1, max: 100, step: 1, value: this.exposure },
            {
                id: 'range',
                name: 'Range',
                type: 'select',
                options: [
                    { value: 'shadows', label: 'Shadows' },
                    { value: 'midtones', label: 'Midtones' },
                    { value: 'highlights', label: 'Highlights' }
                ],
                value: this.range
            }
        ];
    }

    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'stroke' && params.points && params.points.length >= 1) {
            if (params.size !== undefined) this.size = params.size;
            if (params.exposure !== undefined) this.exposure = params.exposure;
            if (params.range !== undefined) this.range = params.range;

            this.app.history.saveState('Burn');

            const points = params.points;
            this.burnAt(layer, points[0][0], points[0][1]);

            for (let i = 1; i < points.length; i++) {
                this.burnLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.app.history.finishState();
            layer.touch();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
