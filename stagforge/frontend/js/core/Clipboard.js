/**
 * Clipboard - Manages copy, cut, and paste operations.
 */
export class Clipboard {
    constructor(app) {
        this.app = app;
        this.buffer = null; // { imageData, width, height, x, y }
    }

    /**
     * Copy the current selection or entire layer to clipboard.
     * Selection coordinates are in document space and need to be converted
     * to layer canvas coordinates using the layer's offset.
     * @param {Object} selection - Optional selection rect {x, y, width, height} in document coords
     * @returns {boolean} Success
     */
    copy(selection = null) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return false;

        let docX, docY, width, height;
        let canvasX, canvasY;

        if (selection && selection.width > 0 && selection.height > 0) {
            // Selection is in document coordinates
            docX = Math.floor(selection.x);
            docY = Math.floor(selection.y);
            width = Math.ceil(selection.width);
            height = Math.ceil(selection.height);

            // Convert document coords to layer canvas coords
            const localCoords = layer.docToCanvas(docX, docY);
            canvasX = localCoords.x;
            canvasY = localCoords.y;

            // Clamp to layer bounds
            const clampedLeft = Math.max(0, canvasX);
            const clampedTop = Math.max(0, canvasY);
            const clampedRight = Math.min(layer.width, canvasX + width);
            const clampedBottom = Math.min(layer.height, canvasY + height);

            // Adjust for clamping
            width = clampedRight - clampedLeft;
            height = clampedBottom - clampedTop;
            canvasX = clampedLeft;
            canvasY = clampedTop;

            // Recalculate document position for the clamped region
            const clampedDoc = layer.canvasToDoc(canvasX, canvasY);
            docX = clampedDoc.x;
            docY = clampedDoc.y;
        } else {
            // Copy entire layer - use layer's full canvas
            canvasX = 0;
            canvasY = 0;
            width = layer.width;
            height = layer.height;
            docX = layer.offsetX;
            docY = layer.offsetY;
        }

        if (width <= 0 || height <= 0) return false;

        const imageData = layer.ctx.getImageData(canvasX, canvasY, width, height);
        this.buffer = {
            imageData,
            width,
            height,
            sourceX: docX,  // Store document coordinates for paste-in-place
            sourceY: docY
        };

        this.app.eventBus.emit('clipboard:copy', { width, height });
        this.writeToSystemClipboard(imageData, width, height);
        return true;
    }

    /**
     * Copy merged - copies from all visible layers composited together.
     * @param {Object} selection - Optional selection rect {x, y, width, height}
     * @returns {boolean} Success
     */
    copyMerged(selection = null) {
        const layerStack = this.app.layerStack;
        if (!layerStack || layerStack.layers.length === 0) return false;

        // Determine bounds
        let x, y, width, height;
        const docWidth = this.app.width || layerStack.width;
        const docHeight = this.app.height || layerStack.height;

        if (selection && selection.width > 0 && selection.height > 0) {
            x = Math.max(0, Math.floor(selection.x));
            y = Math.max(0, Math.floor(selection.y));
            width = Math.min(Math.ceil(selection.width), docWidth - x);
            height = Math.min(Math.ceil(selection.height), docHeight - y);
        } else {
            x = 0;
            y = 0;
            width = docWidth;
            height = docHeight;
        }

        if (width <= 0 || height <= 0) return false;

        // Create composite canvas
        const compositeCanvas = document.createElement('canvas');
        compositeCanvas.width = width;
        compositeCanvas.height = height;
        const ctx = compositeCanvas.getContext('2d');

        // Draw all visible layers (bottom to top = last to first with index 0 = top)
        for (let i = layerStack.layers.length - 1; i >= 0; i--) {
            const layer = layerStack.layers[i];
            if (!layer.visible) continue;
            // Skip groups - they have no canvas
            if (layer.isGroup && layer.isGroup()) continue;
            ctx.globalAlpha = layer.opacity;
            const offsetX = (layer.offsetX ?? 0) - x;
            const offsetY = (layer.offsetY ?? 0) - y;
            ctx.drawImage(layer.canvas, offsetX, offsetY);
        }
        ctx.globalAlpha = 1.0;

        // Get merged image data
        const imageData = ctx.getImageData(0, 0, width, height);
        this.buffer = {
            imageData,
            width,
            height,
            sourceX: x,
            sourceY: y
        };

        this.app.eventBus.emit('clipboard:copy', { width, height, merged: true });
        this.writeToSystemClipboard(imageData, width, height);
        return true;
    }

    /**
     * Write image data to the system clipboard as PNG.
     * @param {ImageData} imageData
     * @param {number} width
     * @param {number} height
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
            // System clipboard not available — internal buffer still works
        }
    }

    /**
     * Cut the current selection (copy + clear).
     * Selection coordinates are in document space.
     * @param {Object} selection - Selection rect {x, y, width, height} in document coords
     * @param {boolean} trimLayer - Whether to trim the layer to content bounds after cut
     * @returns {boolean} Success
     */
    cut(selection = null, trimLayer = true) {
        if (!this.copy(selection)) return false;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return false;

        this.app.history.saveState('Cut');

        if (selection && selection.width > 0 && selection.height > 0) {
            // Convert document coords to layer canvas coords
            const localCoords = layer.docToCanvas(selection.x, selection.y);
            let canvasX = Math.floor(localCoords.x);
            let canvasY = Math.floor(localCoords.y);
            let width = Math.ceil(selection.width);
            let height = Math.ceil(selection.height);

            // Clamp to layer bounds
            const clampedLeft = Math.max(0, canvasX);
            const clampedTop = Math.max(0, canvasY);
            const clampedRight = Math.min(layer.width, canvasX + width);
            const clampedBottom = Math.min(layer.height, canvasY + height);

            width = clampedRight - clampedLeft;
            height = clampedBottom - clampedTop;

            if (width > 0 && height > 0) {
                // Clear selection area in layer canvas coordinates
                layer.ctx.clearRect(clampedLeft, clampedTop, width, height);

                // Trim layer to remaining content if significant portion was cut
                if (trimLayer) {
                    const cutArea = width * height;
                    const layerArea = layer.width * layer.height;
                    // Trim if cut area was more than 20% of layer
                    if (cutArea > layerArea * 0.2) {
                        layer.trimToContent();
                    }
                }
            }
        } else {
            // Clear entire layer
            layer.ctx.clearRect(0, 0, layer.width, layer.height);
        }

        this.app.history.finishState();
        this.app.renderer.requestRender();
        this.app.eventBus.emit('clipboard:cut', { width: this.buffer.width, height: this.buffer.height });
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
            // Create a layer sized to the pasted content, not full document size
            targetLayer = this.app.layerStack.addLayer({
                name: 'Pasted',
                width: this.buffer.width,
                height: this.buffer.height,
                offsetX: x,
                offsetY: y
            });

            // Draw image data at (0,0) since the layer offset handles positioning
            targetLayer.ctx.putImageData(this.buffer.imageData, 0, 0);
        } else {
            targetLayer = this.app.layerStack.getActiveLayer();
            if (!targetLayer) return false;

            // Create temp canvas to hold image data
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = this.buffer.width;
            tempCanvas.height = this.buffer.height;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.putImageData(this.buffer.imageData, 0, 0);

            // Draw to target layer at position
            targetLayer.ctx.drawImage(tempCanvas, x, y);
        }

        this.app.history.finishState();
        this.app.renderer.requestRender();
        this.app.eventBus.emit('clipboard:paste', {
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
     * If found, loads it into the internal buffer and pastes as new layer.
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
                const ctx = canvas.getContext('2d');
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
            // Permission denied or no image — fall through
        }
        return false;
    }

    /**
     * Check if clipboard has content.
     * @returns {boolean}
     */
    hasContent() {
        return this.buffer !== null;
    }

    /**
     * Get clipboard info.
     * @returns {Object|null}
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
        this.app.eventBus.emit('clipboard:clear');
    }

    /**
     * Set clipboard from raw RGBA data (for API use).
     * @param {Uint8ClampedArray} data - RGBA pixel data
     * @param {number} width
     * @param {number} height
     * @param {number} sourceX
     * @param {number} sourceY
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
     * @returns {Object|null}
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
