/**
 * CropTool - Crop the canvas to a selected region.
 */
import { Tool } from './Tool.js';

export class CropTool extends Tool {
    static id = 'crop';
    static name = 'Crop';
    static icon = 'crop';
    static shortcut = 'c';
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

    onMouseDown(e, x, y) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        this.isSelecting = true;
        this.startX = x;
        this.startY = y;
        this.endX = x;
        this.endY = y;

        // Set up preview canvas
        this.previewCanvas.width = layer.width;
        this.previewCanvas.height = layer.height;
    }

    onMouseMove(e, x, y) {
        if (!this.isSelecting) return;

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

    onMouseUp(e, x, y) {
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
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

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

    applyCrop() {
        if (!this.cropRect || this.cropRect.width < 1 || this.cropRect.height < 1) {
            this.cancelCrop();
            return;
        }

        const { x, y, width, height } = this.cropRect;

        // Clamp to canvas bounds
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        const cropX = Math.max(0, Math.min(x, layer.width - 1));
        const cropY = Math.max(0, Math.min(y, layer.height - 1));
        const cropW = Math.min(width, layer.width - cropX);
        const cropH = Math.min(height, layer.height - cropY);

        if (cropW < 1 || cropH < 1) {
            this.cancelCrop();
            return;
        }

        // Note: Crop is a special case that changes canvas dimensions.
        // For now we save state for all layers - this will capture full layer data.
        this.app.history.saveState('Crop');

        // Crop all layers
        for (const layerItem of this.app.layerStack.layers) {
            const imageData = layerItem.ctx.getImageData(cropX, cropY, cropW, cropH);

            // Resize canvas
            layerItem.canvas.width = cropW;
            layerItem.canvas.height = cropH;
            layerItem.width = cropW;
            layerItem.height = cropH;

            // Put cropped data
            layerItem.ctx.putImageData(imageData, 0, 0);
        }

        // Update app dimensions
        this.app.canvasWidth = cropW;
        this.app.canvasHeight = cropH;
        this.app.renderer.resize(cropW, cropH);
        this.app.renderer.fitToViewport();

        // Note: finishState won't work correctly for crop since canvas size changed.
        // This is a known limitation - crop requires special structural handling.
        // For now, we abort the capture since before/after dimensions differ.
        this.app.history.abortCapture();

        this.app.eventBus.emit('canvas:resized', { width: cropW, height: cropH });

        this.cancelCrop();
        this.app.renderer.requestRender();
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
    executeAction(action, params) {
        if (action === 'crop') {
            const x = params.x !== undefined ? params.x : 0;
            const y = params.y !== undefined ? params.y : 0;
            const width = params.width;
            const height = params.height;

            if (!width || !height) {
                return { success: false, error: 'Width and height required' };
            }

            this.cropRect = { x, y, width, height };
            this.applyCrop();
            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
