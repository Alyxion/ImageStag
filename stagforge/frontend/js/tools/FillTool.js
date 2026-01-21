/**
 * FillTool - Flood fill (paint bucket).
 */
import { Tool } from './Tool.js';

export class FillTool extends Tool {
    static id = 'fill';
    static name = 'Paint Bucket';
    static icon = 'fill';
    static shortcut = 'g';
    static cursor = 'crosshair';

    constructor(app) {
        super(app);
        this.tolerance = 32; // 0-255
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) return;

        // Check if this is a vector layer - offer to rasterize
        if (layer.isVector && layer.isVector()) {
            this.app.showRasterizeDialog(layer, (confirmed) => {
                if (confirmed) {
                    // Layer has been rasterized, do the fill
                    this.doFill(x, y);
                }
            });
            return;
        }

        this.doFill(x, y);
    }

    doFill(x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        // Convert document coordinates to layer canvas coordinates
        let canvasX = x, canvasY = y;
        if (layer.docToCanvas) {
            const canvasCoords = layer.docToCanvas(x, y);
            canvasX = canvasCoords.x;
            canvasY = canvasCoords.y;
        }

        // Round coordinates
        canvasX = Math.floor(canvasX);
        canvasY = Math.floor(canvasY);

        // Check bounds
        if (canvasX < 0 || canvasX >= layer.width || canvasY < 0 || canvasY >= layer.height) return;

        // Use canvas coordinates for fill
        x = canvasX;
        y = canvasY;

        // Save state for undo - history system auto-detects changed region
        this.app.history.saveState('Fill');

        // Get fill color
        const fillColor = this.app.foregroundColor || '#000000';
        const fillRgba = this.hexToRgba(fillColor);

        // Perform flood fill
        this.floodFill(layer, x, y, fillRgba);

        // Finish history capture - auto-detects changed pixels
        this.app.history.finishState();
        this.app.renderer.requestRender();
    }

    floodFill(layer, startX, startY, fillColor) {
        const imageData = layer.getImageData();
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;

        // Check for active selection to constrain fill
        const selectionTool = this.app.toolManager?.tools.get('selection');
        const selection = selectionTool?.getSelection();
        let selBounds = null;

        if (selection && selection.width > 0 && selection.height > 0) {
            // Convert selection to layer coordinates if needed
            let selX = selection.x, selY = selection.y;
            if (layer.docToCanvas) {
                const coords = layer.docToCanvas(selection.x, selection.y);
                selX = coords.x;
                selY = coords.y;
            }
            selBounds = {
                left: Math.max(0, Math.floor(selX)),
                top: Math.max(0, Math.floor(selY)),
                right: Math.min(width, Math.ceil(selX + selection.width)),
                bottom: Math.min(height, Math.ceil(selY + selection.height))
            };

            // Check if click is within selection
            if (startX < selBounds.left || startX >= selBounds.right ||
                startY < selBounds.top || startY >= selBounds.bottom) {
                return; // Click outside selection, do nothing
            }
        }

        // Get target color at click position
        const targetIdx = (startY * width + startX) * 4;
        const targetColor = {
            r: data[targetIdx],
            g: data[targetIdx + 1],
            b: data[targetIdx + 2],
            a: data[targetIdx + 3]
        };

        // Don't fill if clicking on the same color
        if (this.colorsMatch(targetColor, fillColor, 0)) return;

        // Stack-based flood fill
        const stack = [[startX, startY]];
        const visited = new Set();

        while (stack.length > 0) {
            const [x, y] = stack.pop();

            // Check bounds (use selection bounds if available)
            if (selBounds) {
                if (x < selBounds.left || x >= selBounds.right ||
                    y < selBounds.top || y >= selBounds.bottom) continue;
            } else {
                if (x < 0 || x >= width || y < 0 || y >= height) continue;
            }

            // Check if visited
            const key = y * width + x;
            if (visited.has(key)) continue;
            visited.add(key);

            const idx = key * 4;
            const currentColor = {
                r: data[idx],
                g: data[idx + 1],
                b: data[idx + 2],
                a: data[idx + 3]
            };

            // Check if color matches target within tolerance
            if (!this.colorsMatch(currentColor, targetColor, this.tolerance)) continue;

            // Fill pixel
            data[idx] = fillColor.r;
            data[idx + 1] = fillColor.g;
            data[idx + 2] = fillColor.b;
            data[idx + 3] = fillColor.a;

            // Add neighbors
            stack.push([x + 1, y]);
            stack.push([x - 1, y]);
            stack.push([x, y + 1]);
            stack.push([x, y - 1]);
        }

        layer.setImageData(imageData);
    }

    colorsMatch(c1, c2, tolerance) {
        return Math.abs(c1.r - c2.r) <= tolerance &&
               Math.abs(c1.g - c2.g) <= tolerance &&
               Math.abs(c1.b - c2.b) <= tolerance &&
               Math.abs(c1.a - c2.a) <= tolerance;
    }

    hexToRgba(hex) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return { r, g, b, a: 255 };
    }

    getProperties() {
        return [
            { id: 'tolerance', name: 'Tolerance', type: 'range', min: 0, max: 255, step: 1, value: this.tolerance }
        ];
    }
}
