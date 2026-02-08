/**
 * CropTool - Crop the canvas to a selected region.
 */
import { Tool } from './Tool.js';

export class CropTool extends Tool {
    static id = 'crop';
    static name = 'Crop';
    static icon = 'crop';
    static iconEntity = '&#8862;';  // Crop frame
    static group = 'crop';
    static groupShortcut = 'c';
    static priority = 10;
    static cursor = 'crosshair';

    constructor(app) {
        super(app);

        // State
        this.isSelecting = false;
        this.startX = 0;
        this.startY = 0;
        this.endX = 0;
        this.endY = 0;
        this.cropRect = null;

        // Preview canvas
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');
    }

    onMouseDown(e) {
        const { docX: x, docY: y } = e;
        // Use document dimensions, not layer dimensions
        const docWidth = this.app.layerStack?.width || this.app.canvasWidth;
        const docHeight = this.app.layerStack?.height || this.app.canvasHeight;
        if (!docWidth || !docHeight) return;

        this.isSelecting = true;
        this.startX = x;
        this.startY = y;
        this.endX = x;
        this.endY = y;

        // Set up preview canvas using document dimensions
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;
    }

    onMouseMove(e) {
        if (!this.isSelecting) return;
        const { docX: x, docY: y } = e;

        this.endX = x;
        this.endY = y;

        // Constrain to square if shift held
        if (e.shiftKey) {
            const dx = this.endX - this.startX;
            const dy = this.endY - this.startY;
            const size = Math.max(Math.abs(dx), Math.abs(dy));
            this.endX = this.startX + Math.sign(dx) * size;
            this.endY = this.startY + Math.sign(dy) * size;
        }

        this.drawPreview();
    }

    onMouseUp(e) {
        if (!this.isSelecting) return;

        this.isSelecting = false;
        this.cropRect = this.normalizeRect(this.startX, this.startY, this.endX, this.endY);

        if (this.cropRect.width < 5 || this.cropRect.height < 5) {
            this.cropRect = null;
            this.app.renderer.clearPreviewLayer();
            return;
        }

        this.drawPreview();
    }

    onKeyDown(e) {
        if (e.key === 'Enter' && this.cropRect) {
            this.applyCrop();
        } else if (e.key === 'Escape') {
            this.cancelCrop();
        }
    }

    normalizeRect(x1, y1, x2, y2) {
        return {
            x: Math.max(0, Math.floor(Math.min(x1, x2))),
            y: Math.max(0, Math.floor(Math.min(y1, y2))),
            width: Math.ceil(Math.abs(x2 - x1)),
            height: Math.ceil(Math.abs(y2 - y1))
        };
    }

    drawPreview() {
        // Use document dimensions for preview
        const docWidth = this.app.layerStack?.width || this.app.canvasWidth;
        const docHeight = this.app.layerStack?.height || this.app.canvasHeight;
        if (!docWidth || !docHeight) return;

        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);

        // Draw darkened overlay outside crop area
        this.previewCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        this.previewCtx.fillRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);

        // Clear the crop area
        const rect = this.isSelecting
            ? this.normalizeRect(this.startX, this.startY, this.endX, this.endY)
            : this.cropRect;

        if (rect && rect.width > 0 && rect.height > 0) {
            this.previewCtx.clearRect(rect.x, rect.y, rect.width, rect.height);

            // Draw crop border
            this.previewCtx.strokeStyle = '#FFFFFF';
            this.previewCtx.lineWidth = 2;
            this.previewCtx.strokeRect(rect.x, rect.y, rect.width, rect.height);

            // Draw rule of thirds guides
            this.previewCtx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
            this.previewCtx.lineWidth = 1;

            const thirdW = rect.width / 3;
            const thirdH = rect.height / 3;

            // Vertical lines
            this.previewCtx.beginPath();
            this.previewCtx.moveTo(rect.x + thirdW, rect.y);
            this.previewCtx.lineTo(rect.x + thirdW, rect.y + rect.height);
            this.previewCtx.moveTo(rect.x + thirdW * 2, rect.y);
            this.previewCtx.lineTo(rect.x + thirdW * 2, rect.y + rect.height);
            // Horizontal lines
            this.previewCtx.moveTo(rect.x, rect.y + thirdH);
            this.previewCtx.lineTo(rect.x + rect.width, rect.y + thirdH);
            this.previewCtx.moveTo(rect.x, rect.y + thirdH * 2);
            this.previewCtx.lineTo(rect.x + rect.width, rect.y + thirdH * 2);
            this.previewCtx.stroke();

            // Draw dimensions
            this.previewCtx.fillStyle = '#FFFFFF';
            this.previewCtx.font = '12px Arial';
            this.previewCtx.fillText(
                `${rect.width} x ${rect.height}`,
                rect.x + 5,
                rect.y + rect.height - 5
            );

            // Show "Press Enter to crop" hint
            if (!this.isSelecting && this.cropRect) {
                this.previewCtx.fillText(
                    'Press Enter to crop, Escape to cancel',
                    rect.x + 5,
                    rect.y + 15
                );
            }
        }

        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    async applyCrop() {
        if (!this.cropRect || this.cropRect.width < 1 || this.cropRect.height < 1) {
            this.cancelCrop();
            return;
        }

        const { x, y, width, height } = this.cropRect;

        // Clamp to DOCUMENT bounds, not layer bounds
        const docWidth = this.app.layerStack?.width || this.app.canvasWidth;
        const docHeight = this.app.layerStack?.height || this.app.canvasHeight;
        if (!docWidth || !docHeight) return;

        const cropX = Math.max(0, Math.min(x, docWidth - 1));
        const cropY = Math.max(0, Math.min(y, docHeight - 1));
        const cropW = Math.min(width, docWidth - cropX);
        const cropH = Math.min(height, docHeight - cropY);

        if (cropW < 1 || cropH < 1) {
            this.cancelCrop();
            return;
        }

        const doc = this.app.documentManager?.getActiveDocument();

        // Crop is a structural change: dimensions change + layer content changes.
        this.app.history.beginCapture('Crop', []);
        this.app.history.beginStructuralChange();

        // Collect ALL layers across ALL pages for history capture
        const allPages = doc ? doc.pages : [{ layerStack: this.app.layerStack }];
        for (const page of allPages) {
            for (const layer of page.layerStack.layers) {
                if (layer.ctx) {
                    await this.app.history.storeResizedLayer(layer);
                }
            }
        }

        // Crop layers on ALL pages
        for (const page of allPages) {
            for (const layer of page.layerStack.layers) {
                this._cropLayer(layer, cropX, cropY, cropW, cropH);
            }
            page.layerStack.width = cropW;
            page.layerStack.height = cropH;
        }

        // Update document, app, and renderer dimensions
        if (doc) {
            doc.width = cropW;
            doc.height = cropH;
        }
        this.app.canvasWidth = cropW;
        this.app.canvasHeight = cropH;
        this.app.renderer.resize(cropW, cropH);
        this.app.renderer.fitToViewport();

        this.app.history.commitCapture();

        this.app.eventBus.emit('canvas:resized', { width: cropW, height: cropH });

        this.cancelCrop();
        this.app.renderer.requestRender();
    }

    /**
     * Crop a single layer (all frames) to the given crop region.
     * @param {Object} layer
     * @param {number} cropX
     * @param {number} cropY
     * @param {number} cropW
     * @param {number} cropH
     */
    _cropLayer(layer, cropX, cropY, cropW, cropH) {
        const layerOffsetX = layer.offsetX || 0;
        const layerOffsetY = layer.offsetY || 0;

        if (layer.ctx) {
            // Raster layer: crop ALL frames
            const frames = layer._frames || [];
            for (const frame of frames) {
                this._cropFrame(frame.canvas, frame.ctx, layerOffsetX, layerOffsetY,
                                cropX, cropY, cropW, cropH);
            }
            layer.width = cropW;
            layer.height = cropH;
            layer.offsetX = 0;
            layer.offsetY = 0;
        } else {
            // Vector/SVG layer: adjust offset to simulate crop
            layer.offsetX = layerOffsetX - cropX;
            layer.offsetY = layerOffsetY - cropY;
            layer._docWidth = cropW;
            layer._docHeight = cropH;

            if (layer.shapes) {
                for (const shape of layer.shapes) {
                    if (shape.x !== undefined) shape.x -= cropX;
                    if (shape.y !== undefined) shape.y -= cropY;
                    if (shape.x1 !== undefined) shape.x1 -= cropX;
                    if (shape.y1 !== undefined) shape.y1 -= cropY;
                    if (shape.x2 !== undefined) shape.x2 -= cropX;
                    if (shape.y2 !== undefined) shape.y2 -= cropY;
                    if (shape.points) {
                        shape.points = shape.points.map(p => ({ x: p.x - cropX, y: p.y - cropY }));
                    }
                }
            }
        }
    }

    /**
     * Crop a single frame canvas to the given crop region.
     */
    _cropFrame(canvas, ctx, layerOffsetX, layerOffsetY, cropX, cropY, cropW, cropH) {
        const docLeft = Math.max(layerOffsetX, cropX);
        const docRight = Math.min(layerOffsetX + canvas.width, cropX + cropW);
        const docTop = Math.max(layerOffsetY, cropY);
        const docBottom = Math.min(layerOffsetY + canvas.height, cropY + cropH);

        if (docRight <= docLeft || docBottom <= docTop) {
            // No overlap — clear
            canvas.width = cropW;
            canvas.height = cropH;
        } else {
            const srcX = docLeft - layerOffsetX;
            const srcY = docTop - layerOffsetY;
            const srcW = docRight - docLeft;
            const srcH = docBottom - docTop;
            const imageData = ctx.getImageData(srcX, srcY, srcW, srcH);

            const dstX = docLeft - cropX;
            const dstY = docTop - cropY;

            canvas.width = cropW;
            canvas.height = cropH;
            ctx.putImageData(imageData, dstX, dstY);
        }
    }

    cancelCrop() {
        this.cropRect = null;
        this.isSelecting = false;
        this.app.renderer.clearPreviewLayer();
    }

    deactivate() {
        super.deactivate();
        this.cancelCrop();
    }

    getProperties() {
        return [];
    }

    getHint() {
        if (this.cropRect) {
            return 'Enter to apply crop, Escape to cancel';
        }
        return 'Drag to select crop area, Shift for square';
    }

    // API execution
    async executeAction(action, params) {
        if (action === 'crop') {
            const x = params.x !== undefined ? params.x : 0;
            const y = params.y !== undefined ? params.y : 0;
            const width = params.width;
            const height = params.height;

            if (!width || !height) {
                return { success: false, error: 'Width and height required' };
            }

            this.cropRect = { x, y, width, height };
            await this.applyCrop();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
