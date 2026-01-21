/**
 * MagicWandTool - Select areas by color similarity (flood fill selection).
 */
import { Tool } from './Tool.js';

export class MagicWandTool extends Tool {
    static id = 'magicwand';
    static name = 'Magic Wand';
    static icon = 'magicwand';
    static iconEntity = '&#10022;';  // Star/wand
    static group = 'quicksel';
    static groupShortcut = 'w';
    static priority = 10;
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // Magic wand properties
        this.tolerance = 32;     // 0-255, how similar colors must be
        this.contiguous = true;  // Only select connected pixels

        // Selection mask
        this.selectionMask = null;
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        // Convert document coordinates to layer canvas coordinates
        let canvasX = x, canvasY = y;
        if (layer.docToCanvas) {
            const canvasCoords = layer.docToCanvas(x, y);
            canvasX = canvasCoords.x;
            canvasY = canvasCoords.y;
        }

        const intX = Math.floor(canvasX);
        const intY = Math.floor(canvasY);

        // Check if click is within layer bounds
        if (intX < 0 || intX >= layer.width || intY < 0 || intY >= layer.height) {
            return; // Click is outside the layer
        }

        // Get image data
        const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);

        // Perform selection
        const selection = this.contiguous
            ? this.floodSelect(imageData, intX, intY)
            : this.globalSelect(imageData, intX, intY);

        // Convert to selection rect (bounding box) in layer canvas coords
        const layerBounds = this.getSelectionBounds(selection, layer.width, layer.height);

        if (layerBounds) {
            // Convert layer canvas bounds to document coordinates
            const docTopLeft = layer.canvasToDoc(layerBounds.x, layerBounds.y);
            const bounds = {
                x: docTopLeft.x,
                y: docTopLeft.y,
                width: layerBounds.width,
                height: layerBounds.height
            };

            // Get selection tool and set the selection
            const selectionTool = this.app.toolManager.tools.get('selection');
            if (selectionTool) {
                selectionTool.setSelection(bounds);
                // Store the mask for potential future use
                this.selectionMask = selection;
            }

            this.app.eventBus.emit('selection:changed', { selection: bounds, mask: selection });
        }
    }

    floodSelect(imageData, startX, startY) {
        const { width, height, data } = imageData;
        const selected = new Uint8Array(width * height);

        // Get target color
        const startIdx = (startY * width + startX) * 4;
        const targetR = data[startIdx];
        const targetG = data[startIdx + 1];
        const targetB = data[startIdx + 2];
        const targetA = data[startIdx + 3];

        // Stack-based flood fill
        const stack = [[startX, startY]];
        const tolerance = this.tolerance;

        while (stack.length > 0) {
            const [x, y] = stack.pop();

            if (x < 0 || x >= width || y < 0 || y >= height) continue;

            const idx = y * width + x;
            if (selected[idx]) continue;

            const pixelIdx = idx * 4;
            const r = data[pixelIdx];
            const g = data[pixelIdx + 1];
            const b = data[pixelIdx + 2];
            const a = data[pixelIdx + 3];

            // Check color similarity
            if (this.colorMatch(r, g, b, a, targetR, targetG, targetB, targetA, tolerance)) {
                selected[idx] = 1;

                // Add neighbors
                stack.push([x + 1, y]);
                stack.push([x - 1, y]);
                stack.push([x, y + 1]);
                stack.push([x, y - 1]);
            }
        }

        return selected;
    }

    globalSelect(imageData, startX, startY) {
        const { width, height, data } = imageData;
        const selected = new Uint8Array(width * height);

        // Get target color
        const startIdx = (startY * width + startX) * 4;
        const targetR = data[startIdx];
        const targetG = data[startIdx + 1];
        const targetB = data[startIdx + 2];
        const targetA = data[startIdx + 3];

        const tolerance = this.tolerance;

        // Check all pixels
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                const pixelIdx = idx * 4;

                const r = data[pixelIdx];
                const g = data[pixelIdx + 1];
                const b = data[pixelIdx + 2];
                const a = data[pixelIdx + 3];

                if (this.colorMatch(r, g, b, a, targetR, targetG, targetB, targetA, tolerance)) {
                    selected[idx] = 1;
                }
            }
        }

        return selected;
    }

    colorMatch(r1, g1, b1, a1, r2, g2, b2, a2, tolerance) {
        const dr = Math.abs(r1 - r2);
        const dg = Math.abs(g1 - g2);
        const db = Math.abs(b1 - b2);
        const da = Math.abs(a1 - a2);

        return dr <= tolerance && dg <= tolerance && db <= tolerance && da <= tolerance;
    }

    getSelectionBounds(mask, width, height) {
        let minX = width, minY = height, maxX = 0, maxY = 0;
        let found = false;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (mask[y * width + x]) {
                    found = true;
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        if (!found) return null;

        return {
            x: minX,
            y: minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }

    getProperties() {
        return [
            { id: 'tolerance', name: 'Tolerance', type: 'range', min: 0, max: 255, step: 1, value: this.tolerance },
            { id: 'contiguous', name: 'Contiguous', type: 'checkbox', value: this.contiguous }
        ];
    }

    onPropertyChanged(id, value) {
        if (id === 'contiguous') {
            this.contiguous = value;
        }
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) {
            return { success: false, error: 'No active layer' };
        }

        if (action === 'select') {
            const x = params.x !== undefined ? params.x : 0;
            const y = params.y !== undefined ? params.y : 0;

            if (params.tolerance !== undefined) this.tolerance = params.tolerance;
            if (params.contiguous !== undefined) this.contiguous = params.contiguous;

            const intX = Math.floor(x);
            const intY = Math.floor(y);

            const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);
            const selection = this.contiguous
                ? this.floodSelect(imageData, intX, intY)
                : this.globalSelect(imageData, intX, intY);

            const bounds = this.getSelectionBounds(selection, layer.width, layer.height);

            if (bounds) {
                const selectionTool = this.app.toolManager.tools.get('selection');
                if (selectionTool) {
                    selectionTool.setSelection(bounds);
                }
                return { success: true, selection: bounds };
            }

            return { success: false, error: 'No pixels selected' };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
