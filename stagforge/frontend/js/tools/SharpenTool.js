/**
 * SharpenTool - Paint sharpen effect on specific areas.
 *
 * Increases local contrast/sharpness where you paint, useful for enhancing details.
 * Uses WASM-accelerated sharpen filter when available.
 */
import { Tool } from './Tool.js';
import { BrushCursor } from '../utils/BrushCursor.js';
import init, * as wasm from '/imgstag/wasm/imagestag_rust.js';

// WASM initialization state
let _wasmInitialized = false;
let _wasmInitializing = null;

async function initWasm() {
    if (_wasmInitialized) return true;
    if (_wasmInitializing) return _wasmInitializing;

    _wasmInitializing = (async () => {
        try {
            await init();
            _wasmInitialized = true;
            console.log('[SharpenTool] WASM initialized');
            return true;
        } catch (e) {
            console.warn('[SharpenTool] WASM not available, using JS fallback:', e);
            return false;
        } finally {
            _wasmInitializing = null;
        }
    })();

    return _wasmInitializing;
}

export class SharpenTool extends Tool {
    static id = 'sharpen';
    static name = 'Sharpen';
    static icon = 'sharpen';
    static iconEntity = '&#9650;';  // Triangle
    static group = 'retouch';
    static priority = 30;  // After blur
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
        // Initialize WASM in background
        initWasm();
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
        this.app.history.saveState('Sharpen');

        // Apply sharpen at initial position
        this.sharpenAtDocCoords(layer, docX, docY);
        this.app.renderer.requestRender();
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

        // Sharpen along the path (using document coordinates)
        this.sharpenLineAtDocCoords(layer, this.lastX, this.lastY, docX, docY);

        this.lastX = docX;
        this.lastY = docY;
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

    /**
     * Sharpen at document coordinates.
     */
    sharpenAtDocCoords(layer, docX, docY) {
        const halfSize = this.size / 2;
        const size = Math.ceil(this.size);
        const strength = this.strength / 100;

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

    /**
     * Legacy sharpenAt for layer-local coordinates (used by API executeAction).
     */
    sharpenAt(layer, x, y) {
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

        this.sharpenAtDocCoords(layer, docX, docY);
    }

    unsharpMask(imageData, amount) {
        const w = imageData.width;
        const h = imageData.height;
        const src = imageData.data;

        // Try WASM-accelerated unsharp mask
        if (_wasmInitialized) {
            try {
                // Convert ImageData to flat u8 array
                const inputData = new Uint8Array(src);

                // Use unsharp_mask_wasm: amount (0-2), radius (blur sigma 0.5-3), threshold (0-255)
                // Scale amount from 0-1 to 0.5-2.0 for more visible effect
                const wasmAmount = 0.5 + amount * 1.5;
                const wasmRadius = 1.0;  // sigma for blur
                const wasmThreshold = 0; // no threshold

                const result = wasm.unsharp_mask_wasm(inputData, w, h, 4, wasmAmount, wasmRadius, wasmThreshold);

                return new ImageData(new Uint8ClampedArray(result), w, h);
            } catch (e) {
                console.warn('[SharpenTool] WASM sharpen failed, using JS fallback:', e);
            }
        }

        // Fallback: JavaScript implementation with improved algorithm
        const result = new Uint8ClampedArray(src.length);

        // Scale amount for more visible effect (0-1 → 0.3-1.5)
        const sharpenAmount = 0.3 + amount * 1.2;

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

    /**
     * Sharpen along a line (document coordinates).
     */
    sharpenLineAtDocCoords(layer, x1, y1, x2, y2) {
        const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const spacing = Math.max(1, this.size * 0.3);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            this.sharpenAtDocCoords(layer, x, y);
        }
    }

    /**
     * Legacy sharpenLine for layer-local coordinates (used by API executeAction).
     */
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
