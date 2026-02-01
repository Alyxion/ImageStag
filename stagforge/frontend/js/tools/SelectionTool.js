/**
 * SelectionTool - Rectangular selection.
 *
 * Creates rectangular selections by dragging. The selection is stored in
 * the global SelectionManager as an alpha mask.
 */
import { Tool } from './Tool.js';

export class SelectionTool extends Tool {
    static id = 'selection';
    static name = 'Selection';
    static icon = 'selection';
    static iconEntity = '&#9633;';  // White square
    static group = 'selection';
    static groupShortcut = 'm';
    static priority = 10;
    static cursor = 'crosshair';
    static layerTypes = { raster: true, text: true, svg: true, group: false };

    constructor(app) {
        super(app);
        this.isSelecting = false;
        this.startX = 0;
        this.startY = 0;
        this.endX = 0;
        this.endY = 0;

        // Preview canvas for drag preview
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');
    }

    activate() {
        super.activate();
        // SelectionManager handles marching ants, just ensure it's animating
        this.app.selectionManager?.startAnimation();
    }

    deactivate() {
        super.deactivate();
        // Don't stop animation - selection persists across tool switches
        // Don't clear preview - SelectionManager owns it now
    }

    onMouseDown(e, x, y, coords) {
        // Use document coordinates
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        this.isSelecting = true;
        this.startX = Math.round(docX);
        this.startY = Math.round(docY);
        this.endX = this.startX;
        this.endY = this.startY;

        // Size preview canvas to document
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;

        this.drawDragPreview();
    }

    onMouseMove(e, x, y, coords) {
        if (!this.isSelecting) return;

        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        this.endX = Math.round(docX);
        this.endY = Math.round(docY);

        // Constrain to square if shift held
        if (e.shiftKey) {
            const dx = this.endX - this.startX;
            const dy = this.endY - this.startY;
            const size = Math.max(Math.abs(dx), Math.abs(dy));
            this.endX = this.startX + Math.sign(dx) * size;
            this.endY = this.startY + Math.sign(dy) * size;
        }

        this.drawDragPreview();
    }

    onMouseUp(e, x, y, coords) {
        if (!this.isSelecting) return;
        this.isSelecting = false;

        // Calculate final rectangle
        let rect = this.normalizeRect(this.startX, this.startY, this.endX, this.endY);

        // Clamp to document bounds
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        rect = this.clampRectToDocument(rect, docWidth, docHeight);

        // Set selection via SelectionManager
        if (rect && rect.width > 1 && rect.height > 1) {
            this.app.selectionManager?.setRect(rect.x, rect.y, rect.width, rect.height);
        } else {
            this.app.selectionManager?.clear();
        }
    }

    normalizeRect(x1, y1, x2, y2) {
        return {
            x: Math.min(x1, x2),
            y: Math.min(y1, y2),
            width: Math.abs(x2 - x1),
            height: Math.abs(y2 - y1)
        };
    }

    clampRectToDocument(rect, docWidth, docHeight) {
        const left = Math.max(0, rect.x);
        const top = Math.max(0, rect.y);
        const right = Math.min(docWidth, rect.x + rect.width);
        const bottom = Math.min(docHeight, rect.y + rect.height);

        if (right <= left || bottom <= top) {
            return null;
        }

        return {
            x: left,
            y: top,
            width: right - left,
            height: bottom - top
        };
    }

    /**
     * Draw a simple rectangle preview during drag.
     */
    drawDragPreview() {
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);

        const rect = this.normalizeRect(this.startX, this.startY, this.endX, this.endY);
        if (rect.width < 1 || rect.height < 1) {
            this.app.renderer?.clearPreviewLayer();
            return;
        }

        // Draw simple dashed rectangle during drag
        this.previewCtx.strokeStyle = '#000000';
        this.previewCtx.lineWidth = 1;
        this.previewCtx.setLineDash([4, 4]);
        this.previewCtx.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.width - 1, rect.height - 1);

        this.previewCtx.strokeStyle = '#FFFFFF';
        this.previewCtx.lineDashOffset = 4;
        this.previewCtx.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.width - 1, rect.height - 1);

        this.previewCtx.setLineDash([]);
        this.previewCtx.lineDashOffset = 0;

        this.app.renderer?.setPreviewLayer(this.previewCanvas);
    }

    // API execution method
    executeAction(action, params) {
        switch (action) {
            case 'select':
                if (params.x !== undefined && params.y !== undefined &&
                    params.width !== undefined && params.height !== undefined) {
                    this.app.selectionManager?.setRect(params.x, params.y, params.width, params.height);
                    return { success: true, bounds: this.app.selectionManager?.getBounds() };
                }
                return { success: false, error: 'Need x, y, width, height' };

            case 'select_all':
                this.app.selectionManager?.selectAll();
                return { success: true, bounds: this.app.selectionManager?.getBounds() };

            case 'clear':
            case 'deselect':
                this.app.selectionManager?.clear();
                return { success: true };

            case 'invert':
                this.app.selectionManager?.invert();
                return { success: true, bounds: this.app.selectionManager?.getBounds() };

            case 'get':
                return {
                    success: true,
                    hasSelection: this.app.selectionManager?.hasSelection || false,
                    bounds: this.app.selectionManager?.getBounds()
                };

            default:
                return { success: false, error: `Unknown action: ${action}` };
        }
    }

    getProperties() {
        return [];
    }

    getHint() {
        if (this.app.selectionManager?.hasSelection) {
            return 'Drag to create new selection, Shift for square, Ctrl+D to deselect';
        }
        return 'Drag to select, Shift for square';
    }
}
