/**
 * MagicWandTool - Select areas by color similarity (flood fill selection).
 *
 * Creates selections based on color similarity. The selection is stored in
 * the global SelectionManager as an alpha mask.
 */
import { Tool } from './Tool.js';

export class MagicWandTool extends Tool {
    static id = 'magicwand';
    static name = 'Magic Wand';
    static icon = 'magicwand';
    static iconEntity = '&#10022;';  // Star/wand
    static group = 'selection';
    static groupShortcut = null;
    static priority = 30;
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // Magic wand properties
        this.tolerance = 32;     // 0-255, how similar colors must be
        this.contiguous = true;  // Only select connected pixels
    }

    activate() {
        super.activate();
        this.app.selectionManager?.startAnimation();
    }

    deactivate() {
        super.deactivate();
        // Don't clear selection on tool switch
    }

    onMouseDown(e, x, y, coords) {
        // x, y are in layer-local coordinates (for sampling the layer canvas)
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        const intX = Math.floor(x);
        const intY = Math.floor(y);

        // Check if click is within layer bounds
        if (intX < 0 || intX >= layer.width || intY < 0 || intY >= layer.height) {
            return;
        }

        // Get image data from layer
        const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);

        // Perform flood selection on layer
        const layerMask = this.contiguous
            ? this.floodSelect(imageData, intX, intY)
            : this.globalSelect(imageData, intX, intY);

        // Convert layer mask to document mask
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        const docMask = new Uint8Array(docWidth * docHeight);

        // Map layer pixels to document coordinates
        for (let ly = 0; ly < layer.height; ly++) {
            for (let lx = 0; lx < layer.width; lx++) {
                if (layerMask[ly * layer.width + lx]) {
                    // Convert layer coords to document coords
                    const docX = lx + layer.offsetX;
                    const docY = ly + layer.offsetY;

                    // Check bounds
                    if (docX >= 0 && docX < docWidth && docY >= 0 && docY < docHeight) {
                        docMask[docY * docWidth + docX] = 255;
                    }
                }
            }
        }

        // Set selection via SelectionManager
        this.app.selectionManager?.setMask(docMask, docWidth, docHeight);
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

    getProperties() {
        return [
            { id: 'tolerance', name: 'Tolerance', type: 'range', min: 0, max: 255, step: 1, value: this.tolerance },
            { id: 'contiguous', name: 'Contiguous', type: 'checkbox', value: this.contiguous }
        ];
    }

    onPropertyChanged(id, value) {
        if (id === 'tolerance') {
            this.tolerance = value;
        } else if (id === 'contiguous') {
            this.contiguous = value;
        }
    }

    getHint() {
        return 'Click to select similar colors';
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

            if (intX < 0 || intX >= layer.width || intY < 0 || intY >= layer.height) {
                return { success: false, error: 'Point outside layer bounds' };
            }

            const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);
            const layerMask = this.contiguous
                ? this.floodSelect(imageData, intX, intY)
                : this.globalSelect(imageData, intX, intY);

            // Convert to document mask
            const docWidth = this.app.layerStack.width;
            const docHeight = this.app.layerStack.height;
            const docMask = new Uint8Array(docWidth * docHeight);

            for (let ly = 0; ly < layer.height; ly++) {
                for (let lx = 0; lx < layer.width; lx++) {
                    if (layerMask[ly * layer.width + lx]) {
                        const docX = lx + layer.offsetX;
                        const docY = ly + layer.offsetY;
                        if (docX >= 0 && docX < docWidth && docY >= 0 && docY < docHeight) {
                            docMask[docY * docWidth + docX] = 255;
                        }
                    }
                }
            }

            this.app.selectionManager?.setMask(docMask, docWidth, docHeight);
            return { success: true, bounds: this.app.selectionManager?.getBounds() };
        }

        if (action === 'clear' || action === 'deselect') {
            this.app.selectionManager?.clear();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
