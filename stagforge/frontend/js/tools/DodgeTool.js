/**
 * DodgeTool - Lighten areas by painting.
 *
 * Simulates dodging in traditional photography darkroom techniques.
 * Can target shadows, midtones, or highlights.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class DodgeTool extends Tool {
    static id = 'dodge';
    static name = 'Dodge';
    static icon = 'sun';
    static shortcut = 'o';
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

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isDrawing = true;
        this.lastX = x;
        this.lastY = y;

        // Save state for undo
        this.app.history.saveState('Dodge');

        // Apply dodge at initial position
        this.dodgeAt(layer, x, y);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Dodge along the path
        this.dodgeLine(layer, this.lastX, this.lastY, x, y);

        this.lastX = x;
        this.lastY = y;
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

    dodgeAt(layer, x, y) {
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);
        const exposure = this.exposure / 100;

        // Expand layer if needed
        if (layer.expandToInclude) {
            layer.expandToInclude(x - halfSize, y - halfSize, size, size);
        }

        // Convert to layer coordinates
        let canvasX = x, canvasY = y;
        if (layer.docToCanvas) {
            const coords = layer.docToCanvas(x, y);
            canvasX = coords.x;
            canvasY = coords.y;
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

                    // Lighten by moving toward white
                    data[idx] = Math.min(255, data[idx] + (255 - data[idx]) * amount);
                    data[idx + 1] = Math.min(255, data[idx + 1] + (255 - data[idx + 1]) * amount);
                    data[idx + 2] = Math.min(255, data[idx + 2] + (255 - data[idx + 2]) * amount);
                    // Keep alpha unchanged
                }
            }
        }

        layer.ctx.putImageData(sourceData, sampleX, sampleY);
    }

    dodgeLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.dodgeAt(layer, x, y);
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

            this.app.history.saveState('Dodge');

            const points = params.points;
            this.dodgeAt(layer, points[0][0], points[0][1]);

            for (let i = 1; i < points.length; i++) {
                this.dodgeLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
