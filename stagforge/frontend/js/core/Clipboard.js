/**
 * Clipboard - Manages copy, cut, and paste operations.
 *
 * Uses the global SelectionManager for mask-based operations.
 */
export class Clipboard {
    constructor(app) {
        this.app = app;
        this.buffer = null; // { imageData, width, height, x, y }
    }

    /**
     * Copy the current selection or entire layer to clipboard.
     * Uses the SelectionManager's mask for selection.
     * @returns {boolean} Success
     */
    copy() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return false;

        const selectionManager = this.app.selectionManager;

        // If we have a selection, use it
        if (selectionManager?.hasSelection) {
            return this.copyWithMask(layer, selectionManager);
        }

        // No selection - copy entire layer
        return this.copyEntireLayer(layer);
    }

    /**
     * Copy using selection mask.
     */
    copyWithMask(layer, selectionManager) {
        const bounds = selectionManager.getBounds();
        if (!bounds) return false;

        // Extract from layer using SelectionManager
        const extracted = selectionManager.extractFromLayer(layer);
        if (!extracted) return false;

        // Get the image data from the extracted canvas
        const imageData = extracted.canvas.getContext('2d').getImageData(
            0, 0, extracted.bounds.width, extracted.bounds.height
        );

        this.buffer = {
            imageData,
            width: extracted.bounds.width,
            height: extracted.bounds.height,
            sourceX: extracted.bounds.x,
            sourceY: extracted.bounds.y
        };

        this.app.eventBus?.emit('clipboard:copy', {
            width: this.buffer.width,
            height: this.buffer.height
        });
        this.writeToSystemClipboard(imageData, this.buffer.width, this.buffer.height);
        return true;
    }

    /**
     * Copy entire layer (no selection).
     */
    copyEntireLayer(layer) {
        const width = layer.width;
        const height = layer.height;

        if (width <= 0 || height <= 0) return false;

        const imageData = layer.ctx.getImageData(0, 0, width, height);
        this.buffer = {
            imageData,
            width,
            height,
            sourceX: layer.offsetX || 0,
            sourceY: layer.offsetY || 0
        };

        this.app.eventBus?.emit('clipboard:copy', { width, height });
        this.writeToSystemClipboard(imageData, width, height);
        return true;
    }

    /**
     * Copy merged - copies from all visible layers composited together.
     * Uses layer.rasterizeToDocument() to handle transforms (rotation, scale).
     * Uses the SelectionManager's mask for selection.
     * @returns {boolean} Success
     */
    copyMerged() {
        const layerStack = this.app.layerStack;
        if (!layerStack || layerStack.layers.length === 0) return false;

        const selectionManager = this.app.selectionManager;
        const docWidth = this.app.width || layerStack.width;
        const docHeight = this.app.height || layerStack.height;

        // Determine bounds
        let x, y, width, height;

        if (selectionManager?.hasSelection) {
            const bounds = selectionManager.getBounds();
            if (!bounds) return false;
            x = bounds.x;
            y = bounds.y;
            width = bounds.width;
            height = bounds.height;
        } else {
            x = 0;
            y = 0;
            width = docWidth;
            height = docHeight;
        }

        if (width <= 0 || height <= 0) return false;

        const clipBounds = { x, y, width, height };

        // Create composite canvas
        const compositeCanvas = document.createElement('canvas');
        compositeCanvas.width = width;
        compositeCanvas.height = height;
        const ctx = compositeCanvas.getContext('2d', { willReadFrequently: true });

        // Draw all visible layers (bottom to top)
        // Use rasterizeToDocument to handle transforms
        for (let i = layerStack.layers.length - 1; i >= 0; i--) {
            const layer = layerStack.layers[i];
            if (!layer.visible) continue;
            if (layer.isGroup && layer.isGroup()) continue;

            // Rasterize layer to document space with clipping to selection bounds
            const rasterized = layer.rasterizeToDocument(clipBounds);

            if (rasterized.bounds.width > 0 && rasterized.bounds.height > 0) {
                ctx.globalAlpha = layer.opacity;
                // Draw at the correct position within the composite
                const drawX = rasterized.bounds.x - x;
                const drawY = rasterized.bounds.y - y;
                ctx.drawImage(rasterized.canvas, drawX, drawY);
            }
        }
        ctx.globalAlpha = 1.0;

        // Apply selection mask if present
        if (selectionManager?.hasSelection) {
            const imageData = ctx.getImageData(0, 0, width, height);
            for (let py = 0; py < height; py++) {
                for (let px = 0; px < width; px++) {
                    const docX = x + px;
                    const docY = y + py;
                    const maskValue = selectionManager.getMaskAt(docX, docY);
                    if (maskValue === 0) {
                        const idx = (py * width + px) * 4;
                        imageData.data[idx + 3] = 0; // Clear alpha
                    }
                }
            }
            ctx.putImageData(imageData, 0, 0);
        }

        const imageData = ctx.getImageData(0, 0, width, height);
        this.buffer = {
            imageData,
            width,
            height,
            sourceX: x,
            sourceY: y
        };

        this.app.eventBus?.emit('clipboard:copy', { width, height, merged: true });
        this.writeToSystemClipboard(imageData, width, height);
        return true;
    }

    /**
     * Write image data to the system clipboard as PNG.
     */
    writeToSystemClipboard(imageData, width, height) {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            canvas.getContext('2d').putImageData(imageData, 0, 0);
            canvas.toBlob(blob => {
                if (blob && navigator.clipboard?.write) {
                    navigator.clipboard.write([
                        new ClipboardItem({ 'image/png': blob })
                    ]).catch(() => {});
                }
            }, 'image/png');
        } catch (e) {
            // System clipboard not available
        }
    }

    /**
     * Cut the current selection (copy + clear).
     * Uses the SelectionManager's mask for deletion.
     * @param {boolean} trimLayer - Whether to trim the layer after cut
     * @returns {boolean} Success
     */
    cut(trimLayer = true) {
        if (!this.copy()) return false;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return false;

        const selectionManager = this.app.selectionManager;

        this.app.history.saveState('Cut');

        if (selectionManager?.hasSelection) {
            // Delete selected pixels using mask
            selectionManager.deleteFromLayer(layer);

            // Trim layer to remaining content
            if (trimLayer && layer.trimToContent) {
                layer.trimToContent();
            }
        } else {
            // Clear entire layer
            layer.ctx.clearRect(0, 0, layer.width, layer.height);
        }

        this.app.history.finishState();
        this.app.renderer?.requestRender();
        this.app.eventBus?.emit('clipboard:cut', {
            width: this.buffer.width,
            height: this.buffer.height
        });
        return true;
    }

    /**
     * Delete selection without copying to clipboard.
     * @returns {boolean} Success
     */
    deleteSelection() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return false;

        const selectionManager = this.app.selectionManager;
        if (!selectionManager?.hasSelection) return false;

        this.app.history.saveState('Delete');

        selectionManager.deleteFromLayer(layer);

        this.app.history.finishState();
        this.app.renderer?.requestRender();
        return true;
    }

    /**
     * Paste clipboard content to a new layer or at position.
     * @param {Object} options - { x, y, asNewLayer }
     * @returns {boolean} Success
     */
    paste(options = {}) {
        if (!this.buffer) return false;

        const { x = 0, y = 0, asNewLayer = true } = options;

        this.app.history.saveState('Paste');

        let targetLayer;
        if (asNewLayer) {
            targetLayer = this.app.layerStack.addLayer({
                name: 'Pasted',
                width: this.buffer.width,
                height: this.buffer.height,
                offsetX: x,
                offsetY: y
            });
            targetLayer.ctx.putImageData(this.buffer.imageData, 0, 0);
        } else {
            targetLayer = this.app.layerStack.getActiveLayer();
            if (!targetLayer) return false;

            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = this.buffer.width;
            tempCanvas.height = this.buffer.height;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.putImageData(this.buffer.imageData, 0, 0);

            targetLayer.ctx.drawImage(tempCanvas, x, y);
        }

        this.app.history.finishState();
        this.app.renderer?.requestRender();
        this.app.eventBus?.emit('clipboard:paste', {
            x, y,
            width: this.buffer.width,
            height: this.buffer.height,
            newLayer: asNewLayer
        });
        return true;
    }

    /**
     * Paste in place (at original position).
     * @param {boolean} asNewLayer - Create new layer
     * @returns {boolean} Success
     */
    pasteInPlace(asNewLayer = true) {
        if (!this.buffer) return false;
        return this.paste({
            x: this.buffer.sourceX,
            y: this.buffer.sourceY,
            asNewLayer
        });
    }

    /**
     * Try to read an image from the system clipboard.
     * @returns {Promise<boolean>} Whether a system image was pasted
     */
    async pasteFromSystem() {
        try {
            if (!navigator.clipboard?.read) return false;
            const items = await navigator.clipboard.read();
            for (const item of items) {
                const imageType = item.types.find(t => t.startsWith('image/'));
                if (!imageType) continue;

                const blob = await item.getType(imageType);
                const img = new Image();
                const url = URL.createObjectURL(blob);

                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = url;
                });
                URL.revokeObjectURL(url);

                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d', { willReadFrequently: true });
                ctx.drawImage(img, 0, 0);
                const imageData = ctx.getImageData(0, 0, img.width, img.height);

                this.buffer = {
                    imageData,
                    width: img.width,
                    height: img.height,
                    sourceX: 0,
                    sourceY: 0
                };
                return this.paste({ asNewLayer: true });
            }
        } catch (e) {
            // Permission denied or no image
        }
        return false;
    }

    /**
     * Check if clipboard has content.
     */
    hasContent() {
        return this.buffer !== null;
    }

    /**
     * Get clipboard info.
     */
    getInfo() {
        if (!this.buffer) return null;
        return {
            width: this.buffer.width,
            height: this.buffer.height,
            sourceX: this.buffer.sourceX,
            sourceY: this.buffer.sourceY
        };
    }

    /**
     * Clear clipboard.
     */
    clear() {
        this.buffer = null;
        this.app.eventBus?.emit('clipboard:clear');
    }

    /**
     * Set clipboard from raw RGBA data (for API use).
     */
    setFromData(data, width, height, sourceX = 0, sourceY = 0) {
        const imageData = new ImageData(new Uint8ClampedArray(data), width, height);
        this.buffer = {
            imageData,
            width,
            height,
            sourceX,
            sourceY
        };
    }

    /**
     * Get clipboard as raw RGBA data (for API use).
     */
    getData() {
        if (!this.buffer) return null;
        return {
            data: Array.from(this.buffer.imageData.data),
            width: this.buffer.width,
            height: this.buffer.height,
            sourceX: this.buffer.sourceX,
            sourceY: this.buffer.sourceY
        };
    }
}
