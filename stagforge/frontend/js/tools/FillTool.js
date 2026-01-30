/**
 * FillTool - Flood fill (paint bucket).
 *
 * Supports alpha-based selection masking for feathered/soft edge selections.
 * When a selection exists, fill respects the mask alpha values.
 */
import { Tool } from './Tool.js';

export class FillTool extends Tool {
    static id = 'fill';
    static name = 'Paint Bucket';
    static icon = 'fill';
    static iconEntity = '&#9832;';  // Bucket
    static group = 'fill';
    static groupShortcut = 'g';
    static priority = 10;
    static cursor = 'crosshair';

    constructor(app) {
        super(app);
        this.tolerance = 12; // 0-100 (percentage)
    }

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) return;

        // SVG layers cannot be filled (they're imported, not editable)
        if (layer.isSVG && layer.isSVG()) {
            return;
        }

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

        // x, y are in layer-local coordinates (pre-transformed by app.js)
        // Convert to document coordinates for expansion logic
        const offsetX = layer.offsetX || 0;
        const offsetY = layer.offsetY || 0;
        const docX = Math.floor(x + offsetX);
        const docY = Math.floor(y + offsetY);

        // Check document bounds
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        if (docX < 0 || docX >= docWidth || docY < 0 || docY >= docHeight) return;

        // Round layer-local coordinates
        let localX = Math.floor(x);
        let localY = Math.floor(y);

        // Determine if we're clicking in a transparent area:
        // - Layer is 0x0 (empty)
        // - Click is outside current layer bounds
        // - Click is inside layer but pixel alpha is 0
        let isTransparentArea = false;
        let needsExpansion = false;

        if (layer.width === 0 || layer.height === 0) {
            // Empty layer - definitely transparent
            isTransparentArea = true;
            needsExpansion = true;
        } else if (localX < 0 || localX >= layer.width || localY < 0 || localY >= layer.height) {
            // Click outside current layer bounds - transparent
            isTransparentArea = true;
            needsExpansion = true;
        } else {
            // Check pixel alpha at click position
            const imageData = layer.ctx.getImageData(localX, localY, 1, 1);
            if (imageData.data[3] === 0) {
                isTransparentArea = true;
                needsExpansion = true;
            }
        }

        // Save state for undo - history system auto-detects changed region
        this.app.history.saveState('Fill');

        // Get fill color
        const fillColor = this.app.foregroundColor || '#000000';
        const fillRgba = this.hexToRgba(fillColor);

        if (needsExpansion) {
            // Expand layer to document bounds for transparent area fill
            layer.expandToInclude(0, 0, docWidth, docHeight);

            // Recalculate local coordinates after expansion
            localX = docX - (layer.offsetX || 0);
            localY = docY - (layer.offsetY || 0);
        }

        // Perform flood fill
        this.floodFill(layer, localX, localY, fillRgba);

        if (needsExpansion) {
            // Shrink layer back to fit actual content
            layer.trimToContent();
        }

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
        const selectionManager = this.app.selectionManager;
        const hasSelection = selectionManager?.hasSelection;
        const selection = hasSelection ? selectionManager.getBounds() : null;
        let selBounds = null;

        // Layer offset for document coordinate conversion
        const offsetX = layer.offsetX || 0;
        const offsetY = layer.offsetY || 0;

        if (selection && selection.width > 0 && selection.height > 0) {
            // Convert selection corners from document to layer-local coordinates
            let selX = selection.x, selY = selection.y;
            let selX2 = selection.x + selection.width, selY2 = selection.y + selection.height;
            if (layer.docToLayer) {
                const tl = layer.docToLayer(selection.x, selection.y);
                const br = layer.docToLayer(selX2, selY2);
                selX = tl.x;
                selY = tl.y;
                selX2 = br.x;
                selY2 = br.y;
            } else if (layer.docToCanvas) {
                const tl = layer.docToCanvas(selection.x, selection.y);
                const br = layer.docToCanvas(selX2, selY2);
                selX = tl.x;
                selY = tl.y;
                selX2 = br.x;
                selY2 = br.y;
            }
            // Normalize bounds (handle negative transforms)
            selBounds = {
                left: Math.max(0, Math.floor(Math.min(selX, selX2))),
                top: Math.max(0, Math.floor(Math.min(selY, selY2))),
                right: Math.min(width, Math.ceil(Math.max(selX, selX2))),
                bottom: Math.min(height, Math.ceil(Math.max(selY, selY2)))
            };

            // Check if click is within selection mask (not just bounds)
            const startDocX = startX + offsetX;
            const startDocY = startY + offsetY;
            if (selectionManager.getMaskAt(startDocX, startDocY) === 0) {
                return; // Click outside selection mask, do nothing
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

        // Convert tolerance from % to 0-255
        const tolerance255 = Math.round(this.tolerance * 255 / 100);

        // Track which pixels to fill and their mask values (for feathered edges)
        const pixelsToFill = [];

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

            // Check selection mask for non-rectangular selections
            let maskAlpha = 255;
            if (hasSelection) {
                const docX = x + offsetX;
                const docY = y + offsetY;
                maskAlpha = selectionManager.getMaskAt(docX, docY);
                if (maskAlpha === 0) continue; // Outside selection mask
            }

            const idx = key * 4;
            const currentColor = {
                r: data[idx],
                g: data[idx + 1],
                b: data[idx + 2],
                a: data[idx + 3]
            };

            // Check if color matches target within tolerance
            if (!this.colorsMatch(currentColor, targetColor, tolerance255)) continue;

            // Store pixel info for later alpha-blended filling
            pixelsToFill.push({ x, y, idx, maskAlpha });

            // Add neighbors
            stack.push([x + 1, y]);
            stack.push([x - 1, y]);
            stack.push([x, y + 1]);
            stack.push([x, y - 1]);
        }

        // Apply fill with alpha blending based on mask values
        for (const pixel of pixelsToFill) {
            const { idx, maskAlpha } = pixel;

            if (maskAlpha === 255) {
                // Fully selected - direct fill
                data[idx] = fillColor.r;
                data[idx + 1] = fillColor.g;
                data[idx + 2] = fillColor.b;
                data[idx + 3] = fillColor.a;
            } else {
                // Partially selected (feathered edge) - alpha blend
                const alpha = maskAlpha / 255;
                data[idx] = Math.round(fillColor.r * alpha + data[idx] * (1 - alpha));
                data[idx + 1] = Math.round(fillColor.g * alpha + data[idx + 1] * (1 - alpha));
                data[idx + 2] = Math.round(fillColor.b * alpha + data[idx + 2] * (1 - alpha));
                data[idx + 3] = Math.max(data[idx + 3], maskAlpha);
            }
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
            { id: 'tolerance', name: 'Tolerance', type: 'range', min: 0, max: 100, step: 1, value: this.tolerance, unit: '%' }
        ];
    }
}
