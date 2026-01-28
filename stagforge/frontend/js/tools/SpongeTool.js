/**
 * SpongeTool - Saturate or desaturate colors by painting.
 *
 * In saturate mode, increases color intensity.
 * In desaturate mode, removes color toward grayscale.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class SpongeTool extends Tool {
    static id = 'sponge';
    static name = 'Sponge';
    static icon = 'sponge';
    static iconEntity = '&#9724;';  // Disc
    static group = 'dodge';
    static priority = 30;  // After burn
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Tool properties
        this.size = 20;
        this.flow = 50;  // 0-100, intensity
        this.mode = 'saturate'; // saturate or desaturate

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
        this.app.history.saveState('Sponge');

        // Apply sponge at initial position
        this.spongeAt(layer, x, y);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Sponge along the path
        this.spongeLine(layer, this.lastX, this.lastY, x, y);

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

    // Convert RGB to HSL
    rgbToHsl(r, g, b) {
        r /= 255;
        g /= 255;
        b /= 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h, s;
        const l = (max + min) / 2;

        if (max === min) {
            h = s = 0;
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

            switch (max) {
                case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
                case g: h = ((b - r) / d + 2) / 6; break;
                case b: h = ((r - g) / d + 4) / 6; break;
            }
        }

        return { h, s, l };
    }

    // Convert HSL to RGB
    hslToRgb(h, s, l) {
        let r, g, b;

        if (s === 0) {
            r = g = b = l;
        } else {
            const hue2rgb = (p, q, t) => {
                if (t < 0) t += 1;
                if (t > 1) t -= 1;
                if (t < 1/6) return p + (q - p) * 6 * t;
                if (t < 1/2) return q;
                if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                return p;
            };

            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }

        return {
            r: Math.round(r * 255),
            g: Math.round(g * 255),
            b: Math.round(b * 255)
        };
    }

    spongeAt(layer, x, y) {
        // x, y are in layer-local coordinates (pre-transformed by app.js)
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);
        const flow = this.flow / 100;

        let canvasX, canvasY;

        // For transformed layers, don't expand - work directly in layer-local space
        if (layer.hasTransform && layer.hasTransform()) {
            canvasX = x;
            canvasY = y;
        } else {
            // Non-transformed layers: expand if needed
            let docX = x + (layer.offsetX || 0);
            let docY = y + (layer.offsetY || 0);

            if (layer.expandToInclude) {
                layer.expandToInclude(docX - halfSize, docY - halfSize, size, size);
            }

            // Re-convert doc→layer AFTER expansion (offset may have changed)
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

                    // Skip fully transparent pixels
                    if (data[idx + 3] === 0) continue;

                    // Convert to HSL
                    const hsl = this.rgbToHsl(data[idx], data[idx + 1], data[idx + 2]);

                    // Soft falloff at edges
                    const falloff = 1 - (dist / radius);
                    const amount = flow * falloff * 0.2; // 0.2 for subtlety

                    // Adjust saturation based on mode
                    if (this.mode === 'saturate') {
                        // Increase saturation
                        hsl.s = Math.min(1, hsl.s + (1 - hsl.s) * amount);
                    } else {
                        // Decrease saturation
                        hsl.s = Math.max(0, hsl.s - hsl.s * amount);
                    }

                    // Convert back to RGB
                    const rgb = this.hslToRgb(hsl.h, hsl.s, hsl.l);

                    data[idx] = rgb.r;
                    data[idx + 1] = rgb.g;
                    data[idx + 2] = rgb.b;
                    // Keep alpha unchanged
                }
            }
        }

        layer.ctx.putImageData(sourceData, sampleX, sampleY);
    }

    spongeLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.25);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.spongeAt(layer, x, y);
        }
    }

    onPropertyChanged(id, value) {
        if (id === 'size') {
            this.size = value;
        } else if (id === 'flow') {
            this.flow = value;
        } else if (id === 'mode') {
            this.mode = value;
        }
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 200, step: 1, value: this.size },
            { id: 'flow', name: 'Flow', type: 'range', min: 1, max: 100, step: 1, value: this.flow },
            {
                id: 'mode',
                name: 'Mode',
                type: 'select',
                options: [
                    { value: 'saturate', label: 'Saturate' },
                    { value: 'desaturate', label: 'Desaturate' }
                ],
                value: this.mode
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
            if (params.flow !== undefined) this.flow = params.flow;
            if (params.mode !== undefined) this.mode = params.mode;

            this.app.history.saveState('Sponge');

            const points = params.points;
            this.spongeAt(layer, points[0][0], points[0][1]);

            for (let i = 1; i < points.length; i++) {
                this.spongeLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
