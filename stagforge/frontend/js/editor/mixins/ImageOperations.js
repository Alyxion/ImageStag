/**
 * ImageOperations Mixin
 *
 * Handles image-level operations: new from clipboard, resize, canvas size.
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - newDocument(width, height): Creates new document
 *   - updateLayerList(): Updates layer panel
 *   - updateNavigator(): Updates navigator panel
 */
/** Maximum document dimension in pixels */
const MAX_DOCUMENT_SIZE = 8000;

export const ImageOperationsMixin = {
    data() {
        return {
            // Resize dialog
            resizeDialogVisible: false,
            resizeWidth: 800,
            resizeHeight: 600,
            resizeLockAspect: true,
            _resizeOrigWidth: 800,
            _resizeOrigHeight: 800,

            // Canvas Size dialog
            canvasSizeDialogVisible: false,
            canvasNewWidth: 800,
            canvasNewHeight: 600,
            canvasAnchor: 4, // 0-8, default center (4)
        };
    },
    methods: {
        /**
         * Create a new document from the system clipboard image.
         */
        async newFromClipboard() {
            try {
                const clipboardItems = await navigator.clipboard.read();
                let imageBlob = null;
                for (const item of clipboardItems) {
                    for (const type of item.types) {
                        if (type.startsWith('image/')) {
                            imageBlob = await item.getType(type);
                            break;
                        }
                    }
                    if (imageBlob) break;
                }
                if (!imageBlob) {
                    console.warn('No image found on clipboard');
                    return;
                }

                // Decode image
                const bitmap = await createImageBitmap(imageBlob);
                const w = bitmap.width;
                const h = bitmap.height;

                // Create new document at image dimensions
                await this.newDocument(w, h);

                // Draw onto background layer
                const app = this.getState();
                if (!app) return;
                const layer = app.layerStack?.getActiveLayer();
                if (layer && layer.ctx) {
                    layer.ctx.drawImage(bitmap, 0, 0);
                    layer.invalidateImageCache();
                }
                bitmap.close();

                app.renderer?.requestRender();
                this.updateLayerList();
                this.updateNavigator();
            } catch (e) {
                console.error('New from clipboard failed:', e);
            }
        },

        /**
         * Show the Resize dialog, pre-populated with current document dimensions.
         */
        showResizeDialog() {
            const app = this.getState();
            if (!app?.layerStack) return;
            this.resizeWidth = app.layerStack.width;
            this.resizeHeight = app.layerStack.height;
            this._resizeOrigWidth = app.layerStack.width;
            this._resizeOrigHeight = app.layerStack.height;
            this.resizeLockAspect = true;
            this.resizeDialogVisible = true;
        },

        /**
         * Called when resize width input changes (maintains aspect ratio if locked).
         */
        onResizeWidthChange() {
            if (this.resizeLockAspect && this._resizeOrigWidth > 0) {
                const ratio = this._resizeOrigHeight / this._resizeOrigWidth;
                this.resizeHeight = Math.round(this.resizeWidth * ratio);
            }
        },

        /**
         * Called when resize height input changes (maintains aspect ratio if locked).
         */
        onResizeHeightChange() {
            if (this.resizeLockAspect && this._resizeOrigHeight > 0) {
                const ratio = this._resizeOrigWidth / this._resizeOrigHeight;
                this.resizeWidth = Math.round(this.resizeHeight * ratio);
            }
        },

        /**
         * Apply the resize operation to all layers.
         */
        async applyResize() {
            const app = this.getState();
            if (!app?.layerStack || !app?.history) return;

            const oldW = app.layerStack.width;
            const oldH = app.layerStack.height;
            const newW = Math.min(MAX_DOCUMENT_SIZE, Math.max(1, Math.round(this.resizeWidth)));
            const newH = Math.min(MAX_DOCUMENT_SIZE, Math.max(1, Math.round(this.resizeHeight)));

            if (newW === oldW && newH === oldH) {
                this.resizeDialogVisible = false;
                return;
            }

            const scaleX = newW / oldW;
            const scaleY = newH / oldH;

            // Save history (structural change) - capture before state
            app.history.beginCapture('Resize Image', []);
            app.history.beginStructuralChange();

            // Store each layer's pre-resize state for undo
            for (const layer of app.layerStack.layers) {
                if (layer.isGroup && layer.isGroup()) continue;
                await app.history.storeResizedLayer(layer);
            }

            // Scale each layer
            for (const layer of app.layerStack.layers) {
                if (layer.isGroup && layer.isGroup()) continue;

                const layerNewW = Math.max(1, Math.round(layer.width * scaleX));
                const layerNewH = Math.max(1, Math.round(layer.height * scaleY));
                const layerNewOX = Math.round(layer.offsetX * scaleX);
                const layerNewOY = Math.round(layer.offsetY * scaleY);

                if (layer.ctx && layer.canvas) {
                    // Raster layer: scale canvas content
                    const tmpCanvas = document.createElement('canvas');
                    tmpCanvas.width = layerNewW;
                    tmpCanvas.height = layerNewH;
                    const tmpCtx = tmpCanvas.getContext('2d');
                    tmpCtx.imageSmoothingEnabled = true;
                    tmpCtx.imageSmoothingQuality = 'high';
                    tmpCtx.drawImage(layer.canvas, 0, 0, layerNewW, layerNewH);

                    layer.canvas.width = layerNewW;
                    layer.canvas.height = layerNewH;
                    layer.width = layerNewW;
                    layer.height = layerNewH;
                    layer.ctx.drawImage(tmpCanvas, 0, 0);
                    layer.invalidateImageCache();
                } else {
                    // Non-raster (vector/text): just update dimensions
                    layer.width = layerNewW;
                    layer.height = layerNewH;
                }

                layer.offsetX = layerNewOX;
                layer.offsetY = layerNewOY;
            }

            // Update document dimensions
            this._updateDocDimensions(app, newW, newH);

            app.history.commitCapture();
            app.renderer?.requestRender();
            this.updateLayerList();
            this.updateNavigator();

            this.resizeDialogVisible = false;
        },

        /**
         * Show the Canvas Size dialog, pre-populated with current document dimensions.
         */
        showCanvasSizeDialog() {
            const app = this.getState();
            if (!app?.layerStack) return;
            this.canvasNewWidth = app.layerStack.width;
            this.canvasNewHeight = app.layerStack.height;
            this.canvasAnchor = 4; // center
            this.canvasSizeDialogVisible = true;
        },

        /**
         * Apply the canvas size change.
         */
        applyCanvasSize() {
            const app = this.getState();
            if (!app?.layerStack || !app?.history) return;

            const oldW = app.layerStack.width;
            const oldH = app.layerStack.height;
            const newW = Math.min(MAX_DOCUMENT_SIZE, Math.max(1, Math.round(this.canvasNewWidth)));
            const newH = Math.min(MAX_DOCUMENT_SIZE, Math.max(1, Math.round(this.canvasNewHeight)));

            if (newW === oldW && newH === oldH) {
                this.canvasSizeDialogVisible = false;
                return;
            }

            // Compute offsets based on anchor position
            const anchorCol = this.canvasAnchor % 3; // 0=left, 1=center, 2=right
            const anchorRow = Math.floor(this.canvasAnchor / 3); // 0=top, 1=middle, 2=bottom

            let dx = 0, dy = 0;
            if (anchorCol === 1) dx = Math.round((newW - oldW) / 2);
            else if (anchorCol === 2) dx = newW - oldW;

            if (anchorRow === 1) dy = Math.round((newH - oldH) / 2);
            else if (anchorRow === 2) dy = newH - oldH;

            // Save history (structural change)
            app.history.beginCapture('Canvas Size', []);
            app.history.beginStructuralChange();

            // Shift all layer offsets
            for (const layer of app.layerStack.layers) {
                if (layer.isGroup && layer.isGroup()) continue;
                layer.offsetX += dx;
                layer.offsetY += dy;
                if (layer.invalidateImageCache) {
                    layer.invalidateImageCache();
                }
            }

            // Update document dimensions
            this._updateDocDimensions(app, newW, newH);

            app.history.commitCapture();
            app.renderer?.requestRender();
            this.updateLayerList();
            this.updateNavigator();

            this.canvasSizeDialogVisible = false;
        },

        /**
         * Update all document dimension references.
         * @param {Object} app - App state
         * @param {number} w - New width
         * @param {number} h - New height
         */
        /**
         * Sync docWidth/docHeight from the current layerStack (for status bar).
         */
        syncDocDimensions() {
            const app = this.getState();
            if (!app?.layerStack) return;
            this.docWidth = app.layerStack.width;
            this.docHeight = app.layerStack.height;
        },

        _updateDocDimensions(app, w, h) {
            app.layerStack.width = w;
            app.layerStack.height = h;
            app.width = w;
            app.height = h;
            app.canvasWidth = w;
            app.canvasHeight = h;
            this.docWidth = w;
            this.docHeight = h;
            app.renderer?.resize(w, h);

            // Update the Document object so serialization/auto-save picks up new dimensions
            const doc = app.documentManager?.getActiveDocument();
            if (doc) {
                doc.width = w;
                doc.height = h;
            }
        },
    },
};

export default ImageOperationsMixin;
