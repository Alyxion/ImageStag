/**
 * SharpenTool - Paint sharpen effect on specific areas.
 *
 * Increases local contrast/sharpness where you paint, useful for enhancing details.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class SharpenTool extends Tool {
    static id = 'sharpen';
    static name = 'Sharpen';
    static icon = 'triangle';
    static shortcut = null;
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Tool properties
        this.size = 20;
        this.strength = 30; // 0-100, sharpen intensity (lower default for subtle effect)

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
        this.app.history.saveState('Sharpen');

        // Apply sharpen at initial position
        this.sharpenAt(layer, x, y);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Sharpen along the path
        this.sharpenLine(layer, this.lastX, this.lastY, x, y);

        this.lastX = x;
        this.lastY = y;
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

    sharpenAt(layer, x, y) {
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);
        const strength = this.strength / 100;

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

        // Sample area with padding for kernel
        const padding = 1;
        const sampleX = Math.max(0, Math.round(canvasX - halfSize) - padding);
        const sampleY = Math.max(0, Math.round(canvasY - halfSize) - padding);
        const sampleW = Math.min(size + padding * 2, layer.width - sampleX);
        const sampleH = Math.min(size + padding * 2, layer.height - sampleY);

        if (sampleW <= 0 || sampleH <= 0) return;

        let sourceData;
        try {
            sourceData = layer.ctx.getImageData(sampleX, sampleY, sampleW, sampleH);
        } catch (e) {
            return;
        }

        // Apply unsharp mask (sharpen)
        const sharpened = this.unsharpMask(sourceData, strength);

        // Blend sharpened result with original based on brush shape
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
                    // Soft falloff at edges
                    const falloff = 1 - (dist / radius);
                    const blend = falloff;

                    sourceData.data[idx] = Math.round(
                        sourceData.data[idx] * (1 - blend) + sharpened.data[idx] * blend
                    );
                    sourceData.data[idx + 1] = Math.round(
                        sourceData.data[idx + 1] * (1 - blend) + sharpened.data[idx + 1] * blend
                    );
                    sourceData.data[idx + 2] = Math.round(
                        sourceData.data[idx + 2] * (1 - blend) + sharpened.data[idx + 2] * blend
                    );
                    // Keep original alpha
                }
            }
        }

        layer.ctx.putImageData(sourceData, sampleX, sampleY);
    }

    unsharpMask(imageData, amount) {
        const w = imageData.width;
        const h = imageData.height;
        const src = imageData.data;
        const result = new Uint8ClampedArray(src.length);

        // Use moderate sharpen amount (0.1 to 0.8 range)
        // amount is 0-1 from strength/100
        const sharpenAmount = amount * 0.8;

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const idx = (y * w + x) * 4;

                // Get surrounding pixels for edge detection
                const getPixel = (px, py, ch) => {
                    px = Math.min(w - 1, Math.max(0, px));
                    py = Math.min(h - 1, Math.max(0, py));
                    return src[(py * w + px) * 4 + ch];
                };

                for (let ch = 0; ch < 3; ch++) {
                    const center = src[idx + ch];

                    // 3x3 neighborhood average (blur approximation)
                    const avg = (
                        getPixel(x - 1, y - 1, ch) +
                        getPixel(x, y - 1, ch) +
                        getPixel(x + 1, y - 1, ch) +
                        getPixel(x - 1, y, ch) +
                        center +
                        getPixel(x + 1, y, ch) +
                        getPixel(x - 1, y + 1, ch) +
                        getPixel(x, y + 1, ch) +
                        getPixel(x + 1, y + 1, ch)
                    ) / 9;

                    // Unsharp mask: original + (original - blur) * amount
                    const diff = center - avg;
                    result[idx + ch] = Math.min(255, Math.max(0,
                        Math.round(center + diff * sharpenAmount)
                    ));
                }

                // Copy alpha
                result[idx + 3] = src[idx + 3];
            }
        }

        return new ImageData(result, w, h);
    }

    sharpenLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.3);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.sharpenAt(layer, x, y);
        }
    }

    onPropertyChanged(id, value) {
        if (id === 'size') {
            this.size = value;
        } else if (id === 'strength') {
            this.strength = value;
        }
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 200, step: 1, value: this.size },
            { id: 'strength', name: 'Strength', type: 'range', min: 1, max: 100, step: 1, value: this.strength }
        ];
    }

    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'stroke' && params.points && params.points.length >= 1) {
            if (params.size !== undefined) this.size = params.size;
            if (params.strength !== undefined) this.strength = params.strength;

            this.app.history.saveState('Sharpen');

            const points = params.points;
            this.sharpenAt(layer, points[0][0], points[0][1]);

            for (let i = 1; i < points.length; i++) {
                this.sharpenLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
