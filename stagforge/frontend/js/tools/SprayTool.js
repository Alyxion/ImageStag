/**
 * SprayTool - Airbrush/spray paint effect with random particle distribution.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';

export class SprayTool extends Tool {
    static id = 'spray';
    static name = 'Spray';
    static icon = 'spray';
    static iconEntity = '&#10625;';  // Cloud
    static group = 'brush';
    static priority = 30;  // After brush and pencil
    static cursor = 'none';
    static layerTypes = { raster: true, text: false, svg: false, group: false };

    constructor(app) {
        super(app);

        // Spray properties
        this.size = 30;        // Spray radius
        this.density = 20;     // Particles per spray
        this.opacity = 100;    // Overall opacity

        // Cursor overlay
        this.brushCursor = new BrushCursor();

        // State
        this.isSpraying = false;
        this.sprayInterval = null;
        this.currentX = 0;
        this.currentY = 0;
    }

    activate() {
        super.activate();
        // Note: BrushCursor is not used - Vue component handles cursor overlay for spray tool
        this.app.renderer.requestRender();
    }

    deactivate() {
        super.deactivate();
        this.stopSprayLoop();
        this.app.renderer.requestRender();
    }

    // Note: drawOverlay is intentionally not implemented for SprayTool
    // The Vue component (canvas_editor.js) handles the cursor overlay for brush/eraser/spray
    // to avoid double cursors and ensure consistent behavior across all UI modes

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // SVG layers cannot be sprayed on (they're imported, not editable)
        if (layer.isSVG && layer.isSVG()) {
            return;
        }

        this.startSpraying(e, x, y);
    }

    startSpraying(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.isSpraying = true;
        this.currentX = x;
        this.currentY = y;

        // Save state for undo - history auto-detects changed region
        this.app.history.saveState('Spray');

        // Start spraying
        this.spray(layer, x, y);
        this.startSprayLoop(layer);
    }

    onMouseMove(e, x, y) {
        this.currentX = x;
        this.currentY = y;
        this.brushCursor.update(x, y, this.size);
        this.app.renderer.requestRender();
    }

    onMouseUp(e, x, y) {
        this.stopSprayLoop();
        if (this.isSpraying) {
            this.isSpraying = false;
            // Finish history capture
            this.app.history.finishState();
        }
    }

    onMouseLeave(e) {
        this.stopSprayLoop();
        if (this.isSpraying) {
            this.isSpraying = false;
            // Finish history capture
            this.app.history.finishState();
        }
    }

    deactivate() {
        super.deactivate();
        this.stopSprayLoop();
    }

    startSprayLoop(layer) {
        this.stopSprayLoop();
        this.sprayInterval = setInterval(() => {
            if (this.isSpraying) {
                this.spray(layer, this.currentX, this.currentY);
                this.app.renderer.requestRender();
            }
        }, 50); // Spray every 50ms
    }

    stopSprayLoop() {
        if (this.sprayInterval) {
            clearInterval(this.sprayInterval);
            this.sprayInterval = null;
        }
    }

    spray(layer, x, y) {
        const ctx = layer.ctx;
        const color = this.app.foregroundColor || '#000000';

        ctx.fillStyle = color;
        ctx.globalAlpha = (this.opacity / 100) * 0.3; // Each particle is semi-transparent

        for (let i = 0; i < this.density; i++) {
            // Random angle and distance
            const angle = Math.random() * Math.PI * 2;
            const distance = Math.random() * this.size;

            const px = x + Math.cos(angle) * distance;
            const py = y + Math.sin(angle) * distance;

            // Random particle size (1-3 pixels)
            const particleSize = 1 + Math.random() * 2;

            ctx.beginPath();
            ctx.arc(px, py, particleSize / 2, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.globalAlpha = 1.0;
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 5, max: 100, step: 1, value: this.size },
            { id: 'density', name: 'Density', type: 'range', min: 5, max: 100, step: 1, value: this.density },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 1, max: 100, step: 1, value: this.opacity }
        ];
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'spray') {
            if (params.size !== undefined) this.size = params.size;
            if (params.density !== undefined) this.density = params.density;
            if (params.opacity !== undefined) this.opacity = params.opacity;
            if (params.color) this.app.foregroundColor = params.color;

            const x = params.x !== undefined ? params.x : 0;
            const y = params.y !== undefined ? params.y : 0;
            const count = params.count || 1; // Number of spray bursts

            this.app.history.saveState('Spray');

            for (let i = 0; i < count; i++) {
                this.spray(layer, x, y);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        if (action === 'stroke' && params.points && params.points.length >= 1) {
            if (params.size !== undefined) this.size = params.size;
            if (params.density !== undefined) this.density = params.density;
            if (params.color) this.app.foregroundColor = params.color;

            this.app.history.saveState('Spray Stroke');

            for (const point of params.points) {
                this.spray(layer, point[0], point[1]);
            }

            this.app.history.finishState();
            this.app.renderer.requestRender();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
