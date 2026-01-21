/**
 * SelectionTool - Rectangular selection with marching ants.
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

    constructor(app) {
        super(app);
        this.isSelecting = false;
        this.startX = 0;
        this.startY = 0;
        this.endX = 0;
        this.endY = 0;

        // Current selection (null if none)
        this.selection = null;

        // Double-escape tracking (require Esc-Esc to clear selection)
        this.lastEscapeTime = 0;

        // Marching ants animation
        this.antOffset = 0;
        this.antAnimationId = null;

        // Preview canvas for selection overlay
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');
    }

    activate() {
        super.activate();
        this.startMarchingAnts();
    }

    deactivate() {
        super.deactivate();
        this.stopMarchingAnts();
        this.app.renderer.clearPreviewLayer();
    }

    onMouseDown(e, x, y) {
        // Start new selection - allow starting anywhere in document space
        this.isSelecting = true;
        this.startX = Math.round(x);
        this.startY = Math.round(y);
        this.endX = this.startX;
        this.endY = this.startY;

        // Size preview canvas to document dimensions, not layer dimensions
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;
    }

    onMouseMove(e, x, y) {
        if (!this.isSelecting) return;

        this.endX = Math.round(x);
        this.endY = Math.round(y);

        // Constrain to square if shift held
        if (e.shiftKey) {
            const dx = this.endX - this.startX;
            const dy = this.endY - this.startY;
            const size = Math.max(Math.abs(dx), Math.abs(dy));
            this.endX = this.startX + Math.sign(dx) * size;
            this.endY = this.startY + Math.sign(dy) * size;
        }

        this.drawSelectionPreview();
    }

    onMouseUp(e, x, y) {
        if (!this.isSelecting) return;
        this.isSelecting = false;

        // Finalize selection
        let rect = this.normalizeRect(this.startX, this.startY, this.endX, this.endY);

        // Clamp selection to document bounds
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        rect = this.clampRectToDocument(rect, docWidth, docHeight);

        // Only create selection if it has size after clamping
        if (rect && rect.width > 1 && rect.height > 1) {
            this.selection = rect;
            this.app.eventBus.emit('selection:changed', { selection: this.selection });
        } else {
            this.clearSelection();
        }

        this.drawSelectionPreview();
    }

    onKeyDown(e) {
        // Double-Escape to clear selection (require two Esc presses within 500ms)
        if (e.key === 'Escape') {
            const now = Date.now();
            if (now - this.lastEscapeTime < 500) {
                this.clearSelection();
                this.lastEscapeTime = 0;  // Reset so next single Esc doesn't trigger
            } else {
                this.lastEscapeTime = now;
            }
        }
        // Ctrl+A to select all
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            e.preventDefault();
            this.selectAll();
        }
    }

    selectAll() {
        // Select the entire document area
        const docWidth = this.app.layerStack.width;
        const docHeight = this.app.layerStack.height;
        this.selection = {
            x: 0,
            y: 0,
            width: docWidth,
            height: docHeight
        };

        // Resize preview canvas if needed
        this.previewCanvas.width = docWidth;
        this.previewCanvas.height = docHeight;

        this.app.eventBus.emit('selection:changed', { selection: this.selection });
        this.drawSelectionPreview();
    }

    clearSelection() {
        this.selection = null;
        this.app.renderer.clearPreviewLayer();
        this.app.eventBus.emit('selection:changed', { selection: null });
    }

    normalizeRect(x1, y1, x2, y2) {
        return {
            x: Math.min(x1, x2),
            y: Math.min(y1, y2),
            width: Math.abs(x2 - x1),
            height: Math.abs(y2 - y1)
        };
    }

    /**
     * Clamp a rectangle to document bounds.
     * Returns null if the rect is entirely outside the document.
     */
    clampRectToDocument(rect, docWidth, docHeight) {
        // Calculate clamped bounds
        const left = Math.max(0, rect.x);
        const top = Math.max(0, rect.y);
        const right = Math.min(docWidth, rect.x + rect.width);
        const bottom = Math.min(docHeight, rect.y + rect.height);

        // Check if there's any overlap with document
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

    drawSelectionPreview() {
        this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);

        let rect;
        if (this.isSelecting) {
            rect = this.normalizeRect(this.startX, this.startY, this.endX, this.endY);
        } else if (this.selection) {
            rect = this.selection;
        } else {
            this.app.renderer.clearPreviewLayer();
            return;
        }

        if (rect.width < 1 || rect.height < 1) return;

        // Draw marching ants
        this.previewCtx.strokeStyle = '#000000';
        this.previewCtx.lineWidth = 1;
        this.previewCtx.setLineDash([4, 4]);
        this.previewCtx.lineDashOffset = -this.antOffset;
        this.previewCtx.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.width - 1, rect.height - 1);

        // White dashed line offset
        this.previewCtx.strokeStyle = '#FFFFFF';
        this.previewCtx.lineDashOffset = -this.antOffset + 4;
        this.previewCtx.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.width - 1, rect.height - 1);

        this.previewCtx.setLineDash([]);
        this.app.renderer.setPreviewLayer(this.previewCanvas);
    }

    startMarchingAnts() {
        const animate = () => {
            this.antOffset = (this.antOffset + 0.5) % 8;
            if (this.selection || this.isSelecting) {
                this.drawSelectionPreview();
            }
            this.antAnimationId = requestAnimationFrame(animate);
        };
        animate();
    }

    stopMarchingAnts() {
        if (this.antAnimationId) {
            cancelAnimationFrame(this.antAnimationId);
            this.antAnimationId = null;
        }
    }

    getSelection() {
        return this.selection;
    }

    setSelection(rect) {
        if (rect && rect.width > 0 && rect.height > 0) {
            this.selection = { ...rect };
            this.app.eventBus.emit('selection:changed', { selection: this.selection });
            this.drawSelectionPreview();
        } else {
            this.clearSelection();
        }
    }

    // API execution method
    executeAction(action, params) {
        switch (action) {
            case 'select':
                if (params.x !== undefined && params.y !== undefined &&
                    params.width !== undefined && params.height !== undefined) {
                    this.setSelection({
                        x: params.x,
                        y: params.y,
                        width: params.width,
                        height: params.height
                    });
                    return { success: true, selection: this.selection };
                }
                return { success: false, error: 'Need x, y, width, height' };

            case 'select_all':
                this.selectAll();
                return { success: true, selection: this.selection };

            case 'clear':
            case 'deselect':
                this.clearSelection();
                return { success: true };

            case 'get':
                return { success: true, selection: this.selection };

            default:
                return { success: false, error: `Unknown action: ${action}` };
        }
    }

    getProperties() {
        return [];
    }

    getHint() {
        if (this.selection) {
            return 'Drag to create new selection, Shift for square';
        }
        return 'Drag to select, Shift for square';
    }
}
