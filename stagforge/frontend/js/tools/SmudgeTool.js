/**
 * SmudgeTool - Push and blend colors like wet paint.
 *
 * Drags colors in the direction of the stroke, creating a finger painting effect.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class SmudgeTool extends Tool {
    static id = 'smudge';
    static name = 'Smudge';
    static icon = 'droplet';
    static shortcut = null;
    static cursor = 'none';

    constructor(app) {
        super(app);

        // Tool properties
        this.size = 20;
        this.strength = 50; // 0-100, how much to smudge

        // Cursor overlay
        this.brushCursor = new BrushCursor();

        // State
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;

        // Smudge buffer - holds the color being smudged
        this.smudgeBuffer = null;
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
        this.app.history.saveState('Smudge');

        // Sample initial color from under the brush
        this.sampleSmudgeBuffer(layer, x, y);
    }

    onMouseMove(e, x, y) {
        // Always track cursor for overlay
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();

        if (!this.isDrawing) return;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Smudge along the path
        this.smudgeLine(layer, this.lastX, this.lastY, x, y);

        this.lastX = x;
        this.lastY = y;
    }

    onMouseUp(e, x, y) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.smudgeBuffer = null;
            this.app.history.finishState();
        }
    }

    onMouseLeave(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.smudgeBuffer = null;
            this.app.history.finishState();
        }
    }

    sampleSmudgeBuffer(layer, x, y) {
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);

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

        if (sampleW <= 0 || sampleH <= 0) {
            this.smudgeBuffer = null;
            return;
        }

        try {
            this.smudgeBuffer = layer.ctx.getImageData(sampleX, sampleY, sampleW, sampleH);
        } catch (e) {
            this.smudgeBuffer = null;
        }
    }

    smudgeAt(layer, x, y) {
        if (!this.smudgeBuffer) return;

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

        const destX = Math.round(canvasX - halfSize);
        const destY = Math.round(canvasY - halfSize);

        // Get current pixels at destination
        const clampedX = Math.max(0, destX);
        const clampedY = Math.max(0, destY);
        const w = Math.min(this.smudgeBuffer.width, layer.width - clampedX);
        const h = Math.min(this.smudgeBuffer.height, layer.height - clampedY);

        if (w <= 0 || h <= 0) return;

        let destData;
        try {
            destData = layer.ctx.getImageData(clampedX, clampedY, w, h);
        } catch (e) {
            return;
        }

        // Blend smudge buffer with destination
        const smudgeData = this.smudgeBuffer.data;
        const destPixels = destData.data;

        // Calculate offset in smudge buffer
        const offsetX = clampedX - destX;
        const offsetY = clampedY - destY;

        for (let py = 0; py < h; py++) {
            for (let px = 0; px < w; px++) {
                const srcIdx = ((py + offsetY) * this.smudgeBuffer.width + (px + offsetX)) * 4;
                const destIdx = (py * w + px) * 4;

                // Check if within brush circle
                const dx = (px + offsetX) - this.smudgeBuffer.width / 2;
                const dy = (py + offsetY) - this.smudgeBuffer.height / 2;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const radius = this.size / 2;

                if (dist <= radius) {
                    // Calculate falloff for softer edges
                    const falloff = 1 - (dist / radius) * 0.5;
                    const blendStrength = strength * falloff;

                    // Blend colors
                    destPixels[destIdx] = Math.round(
                        destPixels[destIdx] * (1 - blendStrength) + smudgeData[srcIdx] * blendStrength
                    );
                    destPixels[destIdx + 1] = Math.round(
                        destPixels[destIdx + 1] * (1 - blendStrength) + smudgeData[srcIdx + 1] * blendStrength
                    );
                    destPixels[destIdx + 2] = Math.round(
                        destPixels[destIdx + 2] * (1 - blendStrength) + smudgeData[srcIdx + 2] * blendStrength
                    );
                    destPixels[destIdx + 3] = Math.round(
                        destPixels[destIdx + 3] * (1 - blendStrength) + smudgeData[srcIdx + 3] * blendStrength
                    );
                }
            }
        }

        // Apply blended result
        layer.ctx.putImageData(destData, clampedX, clampedY);

        // Update smudge buffer with new sample (partial pickup)
        const pickupStrength = strength * 0.5;
        for (let i = 0; i < smudgeData.length; i += 4) {
            const py = Math.floor((i / 4) / this.smudgeBuffer.width);
            const px = (i / 4) % this.smudgeBuffer.width;

            if (px - offsetX >= 0 && px - offsetX < w &&
                py - offsetY >= 0 && py - offsetY < h) {
                const destIdx = ((py - offsetY) * w + (px - offsetX)) * 4;
                smudgeData[i] = Math.round(
                    smudgeData[i] * (1 - pickupStrength) + destPixels[destIdx] * pickupStrength
                );
                smudgeData[i + 1] = Math.round(
                    smudgeData[i + 1] * (1 - pickupStrength) + destPixels[destIdx + 1] * pickupStrength
                );
                smudgeData[i + 2] = Math.round(
                    smudgeData[i + 2] * (1 - pickupStrength) + destPixels[destIdx + 2] * pickupStrength
                );
                smudgeData[i + 3] = Math.round(
                    smudgeData[i + 3] * (1 - pickupStrength) + destPixels[destIdx + 3] * pickupStrength
                );
            }
        }
    }

    smudgeLine(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.15);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.smudgeAt(layer, x, y);
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

        if (action === 'stroke' && params.points && params.points.length >= 2) {
            if (params.size !== undefined) this.size = params.size;
            if (params.strength !== undefined) this.strength = params.strength;

            this.app.history.saveState('Smudge');

            const points = params.points;
            this.sampleSmudgeBuffer(layer, points[0][0], points[0][1]);

            for (let i = 1; i < points.length; i++) {
                this.smudgeLine(layer, points[i-1][0], points[i-1][1], points[i][0], points[i][1]);
            }

            this.smudgeBuffer = null;
            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
