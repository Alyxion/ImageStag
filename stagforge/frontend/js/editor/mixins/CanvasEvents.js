/**
 * CanvasEvents Mixin
 *
 * Handles canvas mouse and wheel events: mousedown, mousemove, mouseup,
 * doubleclick, mouseleave, mouseenter, and wheel zoom.
 *
 * Required component data:
 *   - isPanning: Boolean
 *   - lastPanX: Number
 *   - lastPanY: Number
 *   - coordsX: Number
 *   - coordsY: Number
 *   - mouseOverCanvas: Boolean
 *   - showCursorOverlay: Boolean
 *   - isPointerActive: Boolean
 *
 * Required component refs:
 *   - mainCanvas: HTMLCanvasElement
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateNavigator(): Refreshes the navigator panel
 *   - markNavigatorDirty(): Marks navigator for debounced update
 *   - updateCursorOverlayPosition(x, y): Updates cursor overlay
 *   - updateBrushCursor(): Updates brush cursor display
 *   - updateToolHint(): Updates tool hint display
 */
import { CanvasEvent } from '/static/js/core/CanvasEvent.js';

export const CanvasEventsMixin = {
    methods: {
        /**
         * Convert document coordinates to layer-local coordinates for the active layer.
         * Handles layer offset and transforms (rotation, scale).
         * @param {Object} app - The app state object
         * @param {number} docX - X in document space
         * @param {number} docY - Y in document space
         * @returns {{ docX: number, docY: number, layerX: number, layerY: number }}
         */
        getLayerCoordinates(app, docX, docY) {
            const layer = app.layerStack.getActiveLayer();
            let layerX = docX;
            let layerY = docY;

            if (layer && layer.docToLayer) {
                const layerCoords = layer.docToLayer(docX, docY);
                layerX = layerCoords.x;
                layerY = layerCoords.y;
            } else if (layer) {
                // Fallback for layers without docToLayer (simple offset)
                layerX = docX - (layer.offsetX || 0);
                layerY = docY - (layer.offsetY || 0);
            }

            return { docX, docY, layerX, layerY };
        },

        /**
         * Handle mouse down on the canvas
         * @param {MouseEvent} e - The mouse event
         */
        handleMouseDown(e) {
            const app = this.getState();
            if (!app) return;

            const rect = this.$refs.mainCanvas.getBoundingClientRect();
            const screenX = e.clientX - rect.left;
            const screenY = e.clientY - rect.top;
            const { x, y } = app.renderer.screenToCanvas(screenX, screenY);

            // Middle mouse for panning
            if (e.button === 1) {
                this.isPanning = true;
                this.lastPanX = e.clientX;
                this.lastPanY = e.clientY;
                return;
            }

            // No document open - ignore tool events
            if (!app.layerStack) return;

            const tool = app.toolManager.currentTool;
            if (!tool) return;

            // Allow certain tools to work outside canvas bounds
            const allowOutsideBounds = ['move', 'hand', 'selection', 'lasso', 'crop'].includes(tool.constructor.id);

            // Check if point is within document bounds for painting tools
            // Use document dimensions directly (not app.width/height) for multi-document support
            if (!allowOutsideBounds) {
                const docWidth = app.documentManager?.getActiveDocument()?.width ?? app.layerStack?.width ?? 0;
                const docHeight = app.documentManager?.getActiveDocument()?.height ?? app.layerStack?.height ?? 0;
                if (x < 0 || x >= docWidth || y < 0 || y >= docHeight) {
                    return; // Don't start painting outside document
                }
            }

            // Convert to layer-local coordinates and build CanvasEvent
            const coords = this.getLayerCoordinates(app, x, y);
            const evt = new CanvasEvent(e, {
                screenX, screenY,
                docX: x, docY: y,
                layerX: coords.layerX, layerY: coords.layerY,
            });
            tool.onMouseDown(evt);
            this.updateToolHint();  // Update hint after tool state may change

            // Sync tool-set cursor to Vue reactive property
            const toolCursor = app.displayCanvas.style.cursor;
            if (toolCursor && this.canvasCursor !== toolCursor) {
                this.canvasCursor = toolCursor;
            }
        },

        /**
         * Handle mouse move on the canvas
         * @param {MouseEvent} e - The mouse event
         */
        handleMouseMove(e) {
            const app = this.getState();
            if (!app) return;

            const rect = this.$refs.mainCanvas.getBoundingClientRect();
            const screenX = e.clientX - rect.left;
            const screenY = e.clientY - rect.top;
            const { x, y } = app.renderer.screenToCanvas(screenX, screenY);

            // Update cursor overlay position if active
            if (this.showCursorOverlay) {
                this.updateCursorOverlayPosition(e.clientX, e.clientY);
            }

            // Update status bar coordinates (show document coords)
            this.coordsX = Math.round(x);
            this.coordsY = Math.round(y);

            // Handle panning
            if (this.isPanning) {
                const dx = e.clientX - this.lastPanX;
                const dy = e.clientY - this.lastPanY;
                app.renderer.pan(dx, dy);
                this.lastPanX = e.clientX;
                this.lastPanY = e.clientY;
                this.updateNavigator();
                return;
            }

            // No document open - ignore tool events
            if (!app.layerStack) return;

            // Convert to layer-local coordinates and build CanvasEvent
            const coords = this.getLayerCoordinates(app, x, y);
            const evt = new CanvasEvent(e, {
                screenX, screenY,
                docX: x, docY: y,
                layerX: coords.layerX, layerY: coords.layerY,
            });
            app.toolManager.currentTool?.onMouseMove(evt);

            // Sync tool-set cursor to Vue reactive property to prevent flicker
            // (Tools set displayCanvas.style.cursor, but Vue's :style binding overwrites it)
            const toolCursor = app.displayCanvas.style.cursor;
            if (toolCursor && this.canvasCursor !== toolCursor) {
                this.canvasCursor = toolCursor;
            }

            // Update navigator during drawing for live feedback (debounced)
            if (e.buttons === 1) {  // Left mouse button is down
                this.markNavigatorDirty();
            }
        },

        /**
         * Handle mouse up on the canvas
         * @param {MouseEvent} e - The mouse event
         */
        handleMouseUp(e) {
            const app = this.getState();
            if (!app) return;

            if (this.isPanning) {
                this.isPanning = false;
                return;
            }

            // No document open - ignore tool events
            if (!app.layerStack) return;

            const rect = this.$refs.mainCanvas.getBoundingClientRect();
            const screenX = e.clientX - rect.left;
            const screenY = e.clientY - rect.top;
            const { x, y } = app.renderer.screenToCanvas(screenX, screenY);

            // Convert to layer-local coordinates and build CanvasEvent
            const coords = this.getLayerCoordinates(app, x, y);
            const evt = new CanvasEvent(e, {
                screenX, screenY,
                docX: x, docY: y,
                layerX: coords.layerX, layerY: coords.layerY,
            });
            app.toolManager.currentTool?.onMouseUp(evt);
            this.updateToolHint();  // Update hint after tool state may change

            // Final navigator update after action completes
            this.updateNavigator();
        },

        /**
         * Handle double click on the canvas
         * @param {MouseEvent} e - The mouse event
         */
        handleDoubleClick(e) {
            const app = this.getState();
            if (!app) return;

            const rect = this.$refs.mainCanvas.getBoundingClientRect();
            const screenX = e.clientX - rect.left;
            const screenY = e.clientY - rect.top;
            const { x, y } = app.renderer.screenToCanvas(screenX, screenY);

            // Check if double-clicking on a text layer
            const layers = app.layerStack.layers;
            for (let i = layers.length - 1; i >= 0; i--) {
                const layer = layers[i];
                if (layer.isText && layer.isText() && layer.visible && !layer.locked) {
                    if (layer.containsPoint(x, y)) {
                        // Switch to text tool and edit this layer
                        app.toolManager.select('text');
                        const textTool = app.toolManager.currentTool;
                        if (textTool && textTool.editTextLayer) {
                            textTool.editTextLayer(layer);
                        }
                        return;
                    }
                }
            }
        },

        /**
         * Handle mouse leave from canvas
         * @param {MouseEvent} e - The mouse event
         */
        handleMouseLeave(e) {
            this.isPanning = false;
            this.mouseOverCanvas = false;
            this.showCursorOverlay = false;
            this.isPointerActive = false;
            const app = this.getState();
            app?.toolManager?.currentTool?.onMouseLeave(e);
        },

        /**
         * Handle mouse enter on canvas
         * @param {MouseEvent} e - The mouse event
         */
        handleMouseEnter(e) {
            this.mouseOverCanvas = true;
            this.isPointerActive = true;
            // Update cursor overlay position first, then show it
            this.updateCursorOverlayPosition(e.clientX, e.clientY);
            this.updateBrushCursor();
        },

        /**
         * Handle mouse wheel for zooming
         * @param {WheelEvent} e - The wheel event
         */
        handleWheel(e) {
            const app = this.getState();
            if (!app?.renderer) return;

            const rect = this.$refs.mainCanvas.getBoundingClientRect();
            const centerX = e.clientX - rect.left;
            const centerY = e.clientY - rect.top;

            const factor = e.deltaY > 0 ? 0.9 : 1.1;
            app.renderer.zoomAt(factor, centerX, centerY);
            this.zoom = app.renderer.zoom;
            this.updateNavigator();
        },
    },
};

export default CanvasEventsMixin;
