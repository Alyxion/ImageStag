/**
 * MoveTool - Move and resize layer contents.
 *
 * Features:
 * - Move layer by dragging anywhere on it
 * - Resize layer by dragging corner/edge handles
 * - Optional aspect ratio constraint (toggle with shift key)
 * - All operations recorded in history for undo/redo
 */
import { Tool } from './Tool.js';

// Handle identifiers
const HANDLE_NONE = null;
const HANDLE_TL = 'tl';  // top-left
const HANDLE_TR = 'tr';  // top-right
const HANDLE_BL = 'bl';  // bottom-left
const HANDLE_BR = 'br';  // bottom-right
const HANDLE_T = 't';    // top
const HANDLE_B = 'b';    // bottom
const HANDLE_L = 'l';    // left
const HANDLE_R = 'r';    // right

export class MoveTool extends Tool {
    static id = 'move';
    static name = 'Move';
    static icon = 'move';
    static iconEntity = '&#11128;';  // Move arrows
    static group = 'move';
    static groupShortcut = 'v';
    static priority = 10;
    static cursor = 'move';
    static layerTypes = { raster: true, text: true, svg: true, group: false };

    constructor(app) {
        super(app);

        // Tool settings
        this.maintainAspectRatio = true;  // Enabled by default (like most design apps)

        // Interaction state
        this.isMoving = false;
        this.isResizing = false;
        this.activeHandle = HANDLE_NONE;

        // Starting position/state
        this.startX = 0;
        this.startY = 0;
        this.initialOffsetX = 0;
        this.initialOffsetY = 0;
        this.initialWidth = 0;
        this.initialHeight = 0;
        this.initialAspectRatio = 1;

        // Shift key state
        this.shiftPressed = false;

        // Handle size in screen pixels
        this.handleSize = 8;
        this.handleHitRadius = 10;

        // Current mouse position for cursor updates
        this.mouseX = 0;
        this.mouseY = 0;
    }

    activate() {
        super.activate();
        // Show layer bounds when move tool is active
        this.app.renderer.showLayerBounds = true;
        this.app.renderer.requestRender();

        // Listen for layer changes to update handles
        this._onLayerChanged = () => {
            this.app.renderer.requestRender();
        };
        this.app.eventBus?.on('layer:activated', this._onLayerChanged);
        this.app.eventBus?.on('layer:added', this._onLayerChanged);
        this.app.eventBus?.on('layer:removed', this._onLayerChanged);
        this.app.eventBus?.on('layer:reordered', this._onLayerChanged);
    }

    deactivate() {
        super.deactivate();
        // Hide layer bounds when switching tools
        this.app.renderer.showLayerBounds = false;
        this.app.renderer.requestRender();

        // Remove layer change listeners
        if (this._onLayerChanged) {
            this.app.eventBus?.off('layer:activated', this._onLayerChanged);
            this.app.eventBus?.off('layer:added', this._onLayerChanged);
            this.app.eventBus?.off('layer:removed', this._onLayerChanged);
            this.app.eventBus?.off('layer:reordered', this._onLayerChanged);
            this._onLayerChanged = null;
        }
    }

    /**
     * Get the bounding box of the active layer in document coordinates.
     * Returns the untransformed layer bounds (used for non-rotated display).
     * @returns {{x: number, y: number, width: number, height: number}|null}
     */
    getLayerBounds() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.isGroup?.()) return null;

        return {
            x: layer.offsetX ?? 0,
            y: layer.offsetY ?? 0,
            width: layer.width,
            height: layer.height
        };
    }

    /**
     * Get the handle positions in document coordinates.
     * For transformed layers, returns handles at the actual transformed corner positions.
     * @returns {Array<{id: string, x: number, y: number, cursor: string}>}
     */
    getHandles() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.isGroup?.()) return [];

        const bounds = this.getLayerBounds();
        if (!bounds) return [];

        const { x, y, width, height } = bounds;

        // Check if layer has transform methods and is actually transformed
        const hasTransformMethod = typeof layer.layerToDoc === 'function';
        const isTransformed = typeof layer.hasTransform === 'function' && layer.hasTransform();

        // Get corner positions - use layerToDoc for transformed layers
        let tl, tr, bl, br, t, b, l, r;

        if (hasTransformMethod && isTransformed) {
            // Transform layer corners to document space
            tl = layer.layerToDoc(0, 0);
            tr = layer.layerToDoc(width, 0);
            bl = layer.layerToDoc(0, height);
            br = layer.layerToDoc(width, height);
            // Edge midpoints
            t = layer.layerToDoc(width / 2, 0);
            b = layer.layerToDoc(width / 2, height);
            l = layer.layerToDoc(0, height / 2);
            r = layer.layerToDoc(width, height / 2);
        } else {
            // Simple positions for non-transformed layers
            tl = { x: x, y: y };
            tr = { x: x + width, y: y };
            bl = { x: x, y: y + height };
            br = { x: x + width, y: y + height };
            t = { x: x + width / 2, y: y };
            b = { x: x + width / 2, y: y + height };
            l = { x: x, y: y + height / 2 };
            r = { x: x + width, y: y + height / 2 };
        }

        return [
            // Corners
            { id: HANDLE_TL, x: tl.x, y: tl.y, cursor: 'nwse-resize' },
            { id: HANDLE_TR, x: tr.x, y: tr.y, cursor: 'nesw-resize' },
            { id: HANDLE_BL, x: bl.x, y: bl.y, cursor: 'nesw-resize' },
            { id: HANDLE_BR, x: br.x, y: br.y, cursor: 'nwse-resize' },
            // Edges
            { id: HANDLE_T, x: t.x, y: t.y, cursor: 'ns-resize' },
            { id: HANDLE_B, x: b.x, y: b.y, cursor: 'ns-resize' },
            { id: HANDLE_L, x: l.x, y: l.y, cursor: 'ew-resize' },
            { id: HANDLE_R, x: r.x, y: r.y, cursor: 'ew-resize' },
        ];
    }

    /**
     * Find which handle (if any) is at the given document coordinates.
     * @param {number} docX
     * @param {number} docY
     * @returns {Object|null} Handle object or null
     */
    getHandleAt(docX, docY) {
        const handles = this.getHandles();
        const hitRadius = this.handleHitRadius / this.app.renderer.zoom;

        for (const handle of handles) {
            const dx = docX - handle.x;
            const dy = docY - handle.y;
            if (Math.abs(dx) <= hitRadius && Math.abs(dy) <= hitRadius) {
                return handle;
            }
        }
        return null;
    }

    /**
     * Update cursor based on mouse position.
     */
    updateCursor(docX, docY) {
        const handle = this.getHandleAt(docX, docY);
        if (handle) {
            this.app.displayCanvas.style.cursor = handle.cursor;
        } else {
            this.app.displayCanvas.style.cursor = 'move';
        }
    }

    async onMouseDown(e, x, y, coords) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) return;

        this.shiftPressed = e.shiftKey;

        // Use document coordinates for move/resize - layer coords create feedback loop
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        // Check if clicking on a resize handle
        const handle = this.getHandleAt(docX, docY);

        if (handle) {
            // Start resizing
            this.isResizing = true;
            this.activeHandle = handle.id;
            this.startX = docX;
            this.startY = docY;
            this.initialOffsetX = layer.offsetX ?? 0;
            this.initialOffsetY = layer.offsetY ?? 0;
            this.initialWidth = layer.width;
            this.initialHeight = layer.height;
            this.initialAspectRatio = layer.width / layer.height;

            // Begin history capture for resize - store full layer state
            this.app.history.beginCapture('Resize Layer', []);
            await this.app.history.storeResizedLayer(layer);
        } else {
            // Start moving
            this.isMoving = true;
            this.startX = docX;
            this.startY = docY;
            this.initialOffsetX = layer.offsetX ?? 0;
            this.initialOffsetY = layer.offsetY ?? 0;

            // Begin history capture for move
            this.app.history.beginCapture('Move Layer', []);
            this.app.history.beginStructuralChange();
        }
    }

    onMouseMove(e, x, y, coords) {
        // Use document coordinates for move/resize - layer coords create feedback loop
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;

        this.mouseX = docX;
        this.mouseY = docY;
        this.shiftPressed = e.shiftKey;

        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked || layer.isGroup?.()) {
            this.updateCursor(docX, docY);
            return;
        }

        if (this.isResizing) {
            this.handleResize(layer, docX, docY);
            this.app.renderer.requestRender();
        } else if (this.isMoving) {
            // Calculate total movement from start position
            const dx = Math.round(docX - this.startX);
            const dy = Math.round(docY - this.startY);

            // Update layer offset
            layer.offsetX = this.initialOffsetX + dx;
            layer.offsetY = this.initialOffsetY + dy;

            this.app.renderer.requestRender();
        } else {
            // Update cursor based on hover
            this.updateCursor(docX, docY);
        }
    }

    /**
     * Handle resize operation.
     */
    handleResize(layer, mouseX, mouseY) {
        const dx = mouseX - this.startX;
        const dy = mouseY - this.startY;

        // Determine if we should maintain aspect ratio
        // Setting XOR shift key (shift toggles the setting)
        const maintainRatio = this.maintainAspectRatio !== this.shiftPressed;

        let newWidth = this.initialWidth;
        let newHeight = this.initialHeight;
        let newOffsetX = this.initialOffsetX;
        let newOffsetY = this.initialOffsetY;

        // Calculate new dimensions based on which handle is being dragged
        switch (this.activeHandle) {
            case HANDLE_BR: // Bottom-right - most common
                newWidth = Math.max(1, this.initialWidth + dx);
                newHeight = Math.max(1, this.initialHeight + dy);
                break;

            case HANDLE_BL: // Bottom-left
                newWidth = Math.max(1, this.initialWidth - dx);
                newHeight = Math.max(1, this.initialHeight + dy);
                newOffsetX = this.initialOffsetX + (this.initialWidth - newWidth);
                break;

            case HANDLE_TR: // Top-right
                newWidth = Math.max(1, this.initialWidth + dx);
                newHeight = Math.max(1, this.initialHeight - dy);
                newOffsetY = this.initialOffsetY + (this.initialHeight - newHeight);
                break;

            case HANDLE_TL: // Top-left
                newWidth = Math.max(1, this.initialWidth - dx);
                newHeight = Math.max(1, this.initialHeight - dy);
                newOffsetX = this.initialOffsetX + (this.initialWidth - newWidth);
                newOffsetY = this.initialOffsetY + (this.initialHeight - newHeight);
                break;

            case HANDLE_R: // Right edge
                newWidth = Math.max(1, this.initialWidth + dx);
                break;

            case HANDLE_L: // Left edge
                newWidth = Math.max(1, this.initialWidth - dx);
                newOffsetX = this.initialOffsetX + (this.initialWidth - newWidth);
                break;

            case HANDLE_B: // Bottom edge
                newHeight = Math.max(1, this.initialHeight + dy);
                break;

            case HANDLE_T: // Top edge
                newHeight = Math.max(1, this.initialHeight - dy);
                newOffsetY = this.initialOffsetY + (this.initialHeight - newHeight);
                break;
        }

        // Apply aspect ratio constraint if needed
        if (maintainRatio) {
            const isCorner = [HANDLE_TL, HANDLE_TR, HANDLE_BL, HANDLE_BR].includes(this.activeHandle);
            const isHorizontal = [HANDLE_L, HANDLE_R].includes(this.activeHandle);
            const isVertical = [HANDLE_T, HANDLE_B].includes(this.activeHandle);

            if (isCorner) {
                // For corners, use the dimension that changed more
                const widthRatio = newWidth / this.initialWidth;
                const heightRatio = newHeight / this.initialHeight;

                if (Math.abs(widthRatio - 1) > Math.abs(heightRatio - 1)) {
                    // Width changed more, adjust height
                    const targetHeight = Math.round(newWidth / this.initialAspectRatio);
                    if (this.activeHandle === HANDLE_TL || this.activeHandle === HANDLE_TR) {
                        newOffsetY = this.initialOffsetY + this.initialHeight - targetHeight;
                    }
                    newHeight = targetHeight;
                } else {
                    // Height changed more, adjust width
                    const targetWidth = Math.round(newHeight * this.initialAspectRatio);
                    if (this.activeHandle === HANDLE_TL || this.activeHandle === HANDLE_BL) {
                        newOffsetX = this.initialOffsetX + this.initialWidth - targetWidth;
                    }
                    newWidth = targetWidth;
                }
            } else if (isHorizontal) {
                // Horizontal edge - adjust height to match
                const targetHeight = Math.round(newWidth / this.initialAspectRatio);
                // Center the height change
                newOffsetY = this.initialOffsetY + (this.initialHeight - targetHeight) / 2;
                newHeight = targetHeight;
            } else if (isVertical) {
                // Vertical edge - adjust width to match
                const targetWidth = Math.round(newHeight * this.initialAspectRatio);
                // Center the width change
                newOffsetX = this.initialOffsetX + (this.initialWidth - targetWidth) / 2;
                newWidth = targetWidth;
            }
        }

        // Ensure minimum size
        newWidth = Math.max(1, Math.round(newWidth));
        newHeight = Math.max(1, Math.round(newHeight));

        // Only scale if dimensions actually changed
        if (newWidth !== layer.width || newHeight !== layer.height) {
            // Calculate scale factors
            const scaleX = newWidth / layer.width;
            const scaleY = newHeight / layer.height;

            // Use synchronous resize for interactive feedback
            // Store original dimensions
            const origWidth = layer.width;
            const origHeight = layer.height;

            // For pixel layers, we need to rescale from original
            if (!layer.isVector?.() && !layer.isSVG?.()) {
                // For pixel layers, scale from initial state
                const srcScaleX = newWidth / this.initialWidth;
                const srcScaleY = newHeight / this.initialHeight;

                // Quick browser-native resize for preview
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = this.initialWidth;
                tempCanvas.height = this.initialHeight;
                const tempCtx = tempCanvas.getContext('2d');

                // If we have cached initial content, use it
                if (!this._initialContent) {
                    this._initialContent = layer.ctx.getImageData(0, 0, layer.width, layer.height);
                    tempCtx.putImageData(this._initialContent, 0, 0);
                    this._initialCanvas = tempCanvas;
                }

                // Resize layer canvas
                layer.canvas.width = newWidth;
                layer.canvas.height = newHeight;
                layer.width = newWidth;
                layer.height = newHeight;

                // Draw scaled content using browser's bicubic
                layer.ctx.imageSmoothingEnabled = true;
                layer.ctx.imageSmoothingQuality = 'high';
                layer.ctx.drawImage(this._initialCanvas, 0, 0, newWidth, newHeight);

                layer.invalidateImageCache();
                layer.invalidateEffectCache?.();
            } else if (layer.isSVG?.()) {
                // For SVG layers, just update dimensions for preview
                layer.width = newWidth;
                layer.height = newHeight;
                if (layer._canvas) {
                    layer._canvas.width = newWidth;
                    layer._canvas.height = newHeight;
                }
                if (layer.canvas) {
                    layer.canvas.width = newWidth;
                    layer.canvas.height = newHeight;
                }
            }
        }

        // Update offset (for non-vector layers)
        layer.offsetX = Math.round(newOffsetX);
        layer.offsetY = Math.round(newOffsetY);
    }

    async onMouseUp(e, x, y, coords) {
        if (this.isResizing) {
            const layer = this.app.layerStack.getActiveLayer();

            // For pixel layers, do final high-quality Lanczos resize
            if (layer && !layer.isSVG?.() && this._initialContent) {
                const newWidth = layer.width;
                const newHeight = layer.height;

                // Import Lanczos
                const { lanczosResample } = await import('../utils/lanczos.js');

                // Resize canvas to initial size first
                layer.canvas.width = this._initialWidth || this.initialWidth;
                layer.canvas.height = this._initialHeight || this.initialHeight;
                layer.ctx.putImageData(this._initialContent, 0, 0);

                // Get source data
                const srcData = layer.ctx.getImageData(0, 0, this.initialWidth, this.initialHeight);

                // Apply Lanczos resize
                const dstData = lanczosResample(srcData, newWidth, newHeight);

                // Update canvas with final result
                layer.canvas.width = newWidth;
                layer.canvas.height = newHeight;
                layer.width = newWidth;
                layer.height = newHeight;
                layer.ctx.putImageData(dstData, 0, 0);

                layer.invalidateImageCache();
                layer.invalidateEffectCache?.();
            }

            // For SVG layers, trigger re-render
            if (layer?.isSVG?.()) {
                await layer.render?.();
            }

            // Clear cached initial content
            this._initialContent = null;
            this._initialCanvas = null;
            this._initialWidth = null;
            this._initialHeight = null;

            this.isResizing = false;
            this.activeHandle = HANDLE_NONE;
            this.app.history.commitCapture();
            this.app.renderer.requestRender();
        }

        if (this.isMoving) {
            this.isMoving = false;
            this.app.history.commitCapture();
        }
    }

    onMouseLeave(e) {
        // Keep state on mouse leave to allow continued dragging
    }

    onKeyDown(e) {
        if (e.key === 'Shift') {
            this.shiftPressed = true;
        }
    }

    onKeyUp(e) {
        if (e.key === 'Shift') {
            this.shiftPressed = false;
        }
    }

    /**
     * Draw resize handles overlay.
     * NOTE: Handles are now drawn by Renderer.drawLayerBoundingBoxes()
     * which correctly handles layer transforms via canvas context transforms.
     * This method is kept for backwards compatibility but does nothing.
     */
    drawOverlay(ctx, docToScreen) {
        // Handles are drawn by Renderer.drawLayerBoundingBoxes()
        // which correctly applies canvas transforms for rotated layers
    }

    getProperties() {
        return [
            {
                id: 'maintainAspectRatio',
                name: '',  // No label text
                type: 'toggle',
                icon: 'link',  // Chain link icon for aspect ratio lock
                hint: 'Keep aspect ratio (Shift to toggle)',
                value: this.maintainAspectRatio
            }
        ];
    }

    onPropertyChanged(id, value) {
        if (id === 'maintainAspectRatio') {
            this.maintainAspectRatio = value;
        }
    }

    /**
     * Get contextual hint for the tool.
     */
    getHint() {
        if (this.isResizing) {
            const hint = this.maintainAspectRatio
                ? 'Hold Shift to resize freely'
                : 'Hold Shift to lock aspect ratio';
            return hint;
        }
        return 'Drag to move layer. Drag handles to resize.';
    }

    // API execution
    executeAction(action, params) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active layer or layer is locked' };
        }

        if (action === 'move' && params.dx !== undefined && params.dy !== undefined) {
            this.app.history.beginCapture('Move Layer', []);
            this.app.history.beginStructuralChange();

            layer.offsetX = (layer.offsetX ?? 0) + params.dx;
            layer.offsetY = (layer.offsetY ?? 0) + params.dy;

            this.app.history.commitCapture();
            this.app.renderer.requestRender();
            return { success: true };
        }

        if (action === 'set_position' && params.x !== undefined && params.y !== undefined) {
            this.app.history.beginCapture('Move Layer', []);
            this.app.history.beginStructuralChange();

            layer.offsetX = params.x;
            layer.offsetY = params.y;

            this.app.history.commitCapture();
            this.app.renderer.requestRender();
            return { success: true };
        }

        if (action === 'resize') {
            const width = params.width ?? layer.width;
            const height = params.height ?? layer.height;
            const maintainRatio = params.maintainAspectRatio ?? false;

            this.app.history.beginCapture('Resize Layer', []);
            this.app.history.beginStructuralChange();

            let targetWidth = width;
            let targetHeight = height;

            if (maintainRatio) {
                const aspectRatio = layer.width / layer.height;
                if (params.width !== undefined && params.height === undefined) {
                    targetHeight = Math.round(targetWidth / aspectRatio);
                } else if (params.height !== undefined && params.width === undefined) {
                    targetWidth = Math.round(targetHeight * aspectRatio);
                }
            }

            // Use async scale method
            layer.scaleTo?.(targetWidth, targetHeight).then(() => {
                this.app.history.commitCapture();
                this.app.renderer.requestRender();
            });

            return { success: true, async: true };
        }

        if (action === 'scale') {
            const scaleX = params.scaleX ?? params.scale ?? 1;
            const scaleY = params.scaleY ?? params.scale ?? 1;

            this.app.history.beginCapture('Scale Layer', []);
            this.app.history.beginStructuralChange();

            layer.scale?.(scaleX, scaleY).then(() => {
                this.app.history.commitCapture();
                this.app.renderer.requestRender();
            });

            return { success: true, async: true };
        }

        return { success: false, error: `Unknown action: ${action}. Use 'move', 'set_position', 'resize', or 'scale'.` };
    }
}
