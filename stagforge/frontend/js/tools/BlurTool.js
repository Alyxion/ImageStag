/**
 * BlurTool - Paint blur effect on specific areas.
 *
 * Applies a local blur effect where you paint, useful for softening edges or details.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class BlurTool extends Tool {
    static id = 'blur';
    static name = 'Blur';
    static icon = 'blur';
    static iconEntity = '&#128167;';  // Water drop
    static group = 'retouch';
    static priority = 20;  // After smudge
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Tool properties
        this.size = 20;
        this.strength = 50; // 0-100, blur intensity

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
        this.app.history.saveState('Blur');

        // Apply blur at initial position
        this.blurAt(layer, x, y);
        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Blur along the path
        this.blurLine(layer, this.lastX, this.lastY, x, y);

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

    blurAt(layer, x, y) {
        // x, y are in layer-local coordinates (pre-transformed by app.js)
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);
        const strength = this.strength / 100;

        // Blur kernel size based on strength
        const kernelSize = Math.max(3, Math.round(5 * strength));

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

        // Sample area with padding for blur kernel
        const padding = Math.ceil(kernelSize / 2);
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

        // Apply box blur
        const blurred = this.boxBlur(sourceData, kernelSize);

        // Blend blurred result with original based on brush shape
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
                    const blend = strength * falloff;

                    sourceData.data[idx] = Math.round(
                        sourceData.data[idx] * (1 - blend) + blurred.data[idx] * blend
                    );
                    sourceData.data[idx + 1] = Math.round(
                        sourceData.data[idx + 1] * (1 - blend) + blurred.data[idx + 1] * blend
                    );
                    sourceData.data[idx + 2] = Math.round(
                        sourceData.data[idx + 2] * (1 - blend) + blurred.data[idx + 2] * blend
                    );
                    sourceData.data[idx + 3] = Math.round(
                        sourceData.data[idx + 3] * (1 - blend) + blurred.data[idx + 3] * blend
                    );
                }
            }
        }

        layer.ctx.putImageData(sourceData, sampleX, sampleY);
    }

    boxBlur(imageData, kernelSize) {
        const w = imageData.width;
        const h = imageData.height;
        const src = imageData.data;
        const dst = new Uint8ClampedArray(src.length);
        const half = Math.floor(kernelSize / 2);

        // Horizontal pass
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                let r = 0, g = 0, b = 0, a = 0, count = 0;

                for (let kx = -half; kx <= half; kx++) {
                    const sx = Math.min(w - 1, Math.max(0, x + kx));
                    const idx = (y * w + sx) * 4;
                    r += src[idx];
                    g += src[idx + 1];
                    b += src[idx + 2];
                    a += src[idx + 3];
                    count++;
                }

                const idx = (y * w + x) * 4;
                dst[idx] = r / count;
                dst[idx + 1] = g / count;
                dst[idx + 2] = b / count;
                dst[idx + 3] = a / count;
            }
        }

        // Vertical pass
        const result = new Uint8ClampedArray(src.length);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                let r = 0, g = 0, b = 0, a = 0, count = 0;

                for (let ky = -half; ky <= half; ky++) {
                    const sy = Math.min(h - 1, Math.max(0, y + ky));
                    const idx = (sy * w + x) * 4;
                    r += dst[idx];
                    g += dst[idx + 1];
                    b += dst[idx + 2];
                    a += dst[idx + 3];
                    count++;
                }

                const idx = (y * w + x) * 4;
                result[idx] = r / count;
                result[idx + 1] = g / count;
                result[idx + 2] = b / count;
                result[idx + 3] = a / count;
            }
        }

        return new ImageData(result, w, h);
    }

    blurLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.3);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.blurAt(layer, x, y);
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

            this.app.history.saveState('Blur');

            const points = params.points;
            this.blurAt(layer, points[0][0], points[0][1]);

            for (let i = 1; i < points.length; i++) {
                this.blurLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
