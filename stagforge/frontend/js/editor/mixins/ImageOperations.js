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

/** Document presets for New Document dialog */
const DOC_PRESETS = {
    // Screen presets (default DPI: 96)
    vga: { width: 640, height: 480, dpi: 96 },
    hd: { width: 1280, height: 720, dpi: 96 },
    fhd: { width: 1920, height: 1080, dpi: 96 },
    qhd: { width: 2560, height: 1440, dpi: 96 },
    '4k': { width: 3840, height: 2160, dpi: 96 },
    // Print presets (DPI specified in name)
    a4_72: { width: 595, height: 842, dpi: 72 },
    a4_150: { width: 1240, height: 1754, dpi: 150 },
    a4_300: { width: 2480, height: 3508, dpi: 300 },
    letter_300: { width: 2550, height: 3300, dpi: 300 },
    // Custom - no preset values
    custom: null
};

export const ImageOperationsMixin = {
    data() {
        return {
            // New Document dialog
            newDocDialogVisible: false,
            newDocWidth: 1920,
            newDocHeight: 1080,
            newDocDpi: 96,
            newDocBackground: 'white',  // 'none', 'white', 'black', 'gray', or hex color like '#FF0000'
            newDocPreset: 'fhd',
            newDocColorPickerOpen: false,

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
         * Show the New Document dialog with defaults.
         */
        showNewDocDialog() {
            // Reset to defaults (FHD screen preset)
            this.newDocWidth = 1920;
            this.newDocHeight = 1080;
            this.newDocDpi = 96;
            this.newDocBackground = 'white';
            this.newDocPreset = 'fhd';
            this.newDocDialogVisible = true;
        },

        /**
         * Show the Load from URL dialog.
         */
        showLoadFromUrlDialog() {
            this.loadFromUrlValue = '';
            this.loadFromUrlMode = 'document';  // Create new document
            this.loadFromUrlDialogVisible = true;
        },

        /**
         * Load an image from the entered URL.
         * Supports both raster images (PNG, JPEG, WebP) and SVG files.
         * Mode can be 'document' (create new doc) or 'layer' (add to current doc).
         */
        async loadFromUrl() {
            const url = this.loadFromUrlValue?.trim();
            if (!url) return;

            const mode = this.loadFromUrlMode || 'document';
            this.loadFromUrlDialogVisible = false;
            this.statusMessage = 'Loading image from URL...';

            try {
                // Try direct fetch first, fall back to proxy for CORS issues
                let response;
                try {
                    response = await fetch(url);
                } catch (corsError) {
                    // Try using backend proxy for CORS-blocked URLs
                    const proxyUrl = `${this.apiBase}/proxy?url=${encodeURIComponent(url)}`;
                    response = await fetch(proxyUrl);
                }

                if (!response.ok) {
                    throw new Error(`Failed to fetch: ${response.status}`);
                }

                const contentType = response.headers.get('content-type') || '';
                const isSvg = contentType.includes('svg') || url.toLowerCase().endsWith('.svg');
                const name = url.split('/').pop()?.split('?')[0] || 'Loaded Image';
                const app = this.getState();

                if (mode === 'layer' && !app?.layerStack) {
                    throw new Error('No active document to add layer to');
                }

                if (!app?.documentManager) {
                    throw new Error('Document manager not available');
                }

                if (isSvg) {
                    await this._loadSvgFromUrl(response, name, mode, app);
                } else {
                    await this._loadRasterFromUrl(response, name, mode, app);
                }

                this.updateDocumentTabs();
                this.updateLayerList();

            } catch (error) {
                console.error('Failed to load image from URL:', error);
                this.statusMessage = `Error: ${error.message}`;
            }
        },

        /**
         * Load SVG from URL response
         */
        async _loadSvgFromUrl(response, name, mode, app) {
            const svgContent = await response.text();
            const { SVGLayer } = await import('/static/js/core/SVGLayer.js');

            // Create temp layer to get natural dimensions
            const temp = new SVGLayer({ width: 1, height: 1, svgContent });
            const w = temp.naturalWidth || 800;
            const h = temp.naturalHeight || 600;

            if (mode === 'layer') {
                // Add as layer to existing document
                const docW = app.layerStack.width;
                const docH = app.layerStack.height;

                // Scale to fit document if larger
                let targetW = w;
                let targetH = h;
                if (w > docW || h > docH) {
                    const scale = Math.min(docW / w, docH / h);
                    targetW = Math.round(w * scale);
                    targetH = Math.round(h * scale);
                }

                // Center in document
                const offsetX = Math.round((docW - targetW) / 2);
                const offsetY = Math.round((docH - targetH) / 2);

                app.history.beginCapture('Add SVG Layer from URL', []);
                app.history.beginStructuralChange();

                const layer = new SVGLayer({
                    width: targetW,
                    height: targetH,
                    offsetX,
                    offsetY,
                    name,
                    svgContent,
                });
                await layer.render();
                app.layerStack.addLayer(layer);
                app.history.commitCapture();
                app.renderer?.requestRender();

                this.statusMessage = 'SVG layer added from URL';
            } else {
                // Create new document
                app.documentManager.createDocument({
                    width: w,
                    height: h,
                    name,
                    activate: true,
                    empty: true
                });

                await this.$nextTick();

                const layer = new SVGLayer({
                    width: w,
                    height: h,
                    offsetX: 0,
                    offsetY: 0,
                    name,
                    svgContent,
                });
                await layer.render();

                app.layerStack.addLayer(layer);
                app.layerStack.setActiveLayer(0);
                app.renderer?.requestRender();
                app.history?.saveState('Load SVG from URL');

                this.statusMessage = 'SVG loaded from URL';
            }
        },

        /**
         * Load raster image from URL response
         */
        async _loadRasterFromUrl(response, name, mode, app) {
            const blob = await response.blob();
            if (!blob.type.startsWith('image/')) {
                throw new Error('URL does not point to a valid image');
            }

            // Create image element to get dimensions
            const img = new Image();
            const imageUrl = URL.createObjectURL(blob);

            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = () => reject(new Error('Failed to load image'));
                img.src = imageUrl;
            });

            if (mode === 'layer') {
                // Add as layer to existing document
                const docW = app.layerStack.width;
                const docH = app.layerStack.height;

                // Scale to fit document if larger
                let targetW = img.width;
                let targetH = img.height;
                let scale = 1;
                if (img.width > docW || img.height > docH) {
                    scale = Math.min(docW / img.width, docH / img.height);
                    targetW = Math.round(img.width * scale);
                    targetH = Math.round(img.height * scale);
                }

                // Center in document
                const offsetX = Math.round((docW - targetW) / 2);
                const offsetY = Math.round((docH - targetH) / 2);

                const { Layer } = await import('/static/js/core/Layer.js');

                app.history.beginCapture('Add Layer from URL', []);
                app.history.beginStructuralChange();

                const layer = new Layer({
                    width: targetW,
                    height: targetH,
                    name,
                });
                layer.offsetX = offsetX;
                layer.offsetY = offsetY;

                // Draw scaled image
                layer.ctx.drawImage(img, 0, 0, targetW, targetH);

                app.layerStack.addLayer(layer);
                app.history.commitCapture();
                app.renderer?.requestRender();

                this.statusMessage = 'Layer added from URL';
            } else {
                // Create new document
                app.documentManager.createDocument({
                    width: img.width,
                    height: img.height,
                    name,
                    activate: true
                });

                await this.$nextTick();

                const layer = app.layerStack?.getActiveLayer();
                if (layer) {
                    layer.ctx.drawImage(img, 0, 0);
                    app.renderer?.requestRender();
                    app.history?.saveState('Load from URL');
                }

                this.statusMessage = 'Image loaded from URL';
            }

            URL.revokeObjectURL(imageUrl);
        },

        /**
         * Show the AI Generate dialog.
         */
        showAIGenerateDialog() {
            this.aiGeneratePrompt = '';
            this.aiGenerateWidth = 1024;
            this.aiGenerateHeight = 1024;
            this.aiGenerateDialogVisible = true;
        },

        /**
         * Apply a document preset (updates width/height/dpi).
         * @param {string} presetId - Preset identifier
         */
        applyNewDocPreset(presetId) {
            const preset = DOC_PRESETS[presetId];
            if (preset) {
                this.newDocWidth = preset.width;
                this.newDocHeight = preset.height;
                this.newDocDpi = preset.dpi;
            }
            this.newDocPreset = presetId;
        },

        /**
         * Called when width/height inputs change manually.
         * Switches preset to 'custom'.
         */
        onNewDocDimensionChange() {
            this.newDocPreset = 'custom';
        },

        /**
         * Compute the real size in meters based on pixels and DPI.
         * @returns {{ width: string, height: string }} Size in meters (formatted)
         */
        getNewDocSizeInMeters() {
            const dpi = this.newDocDpi || 96;
            // 1 inch = 0.0254 meters
            const widthMeters = (this.newDocWidth / dpi) * 0.0254;
            const heightMeters = (this.newDocHeight / dpi) * 0.0254;

            // Format with appropriate precision
            const formatSize = (m) => {
                if (m >= 1) {
                    return m.toFixed(2) + ' m';
                } else if (m >= 0.01) {
                    return (m * 100).toFixed(1) + ' cm';
                } else {
                    return (m * 1000).toFixed(1) + ' mm';
                }
            };

            return {
                width: formatSize(widthMeters),
                height: formatSize(heightMeters)
            };
        },

        /**
         * Open the color picker popup.
         */
        openNewDocColorPicker() {
            this.newDocColorPickerOpen = true;
        },

        /**
         * Close the color picker popup.
         */
        closeNewDocColorPicker() {
            this.newDocColorPickerOpen = false;
        },

        /**
         * Handle color input change (live updates).
         * @param {Event} event - Input event from color input
         */
        onNewDocBgColorChange(event) {
            this.newDocBackground = event.target.value;
        },

        /**
         * Get the preview color for the background.
         * @returns {string} CSS color value or 'transparent'
         */
        getNewDocBgPreviewColor() {
            switch (this.newDocBackground) {
                case 'none': return 'transparent';
                case 'white': return '#FFFFFF';
                case 'black': return '#000000';
                case 'gray': return '#808080';
                default: return this.newDocBackground;
            }
        },

        /**
         * Get the current color value for the color input.
         * @returns {string} Hex color
         */
        getNewDocBgInputColor() {
            if (this.newDocBackground.startsWith('#')) {
                return this.newDocBackground;
            }
            // Return equivalent hex for presets
            switch (this.newDocBackground) {
                case 'white': return '#FFFFFF';
                case 'black': return '#000000';
                case 'gray': return '#808080';
                default: return '#FFFFFF';
            }
        },

        /**
         * Create a new document with the specified settings.
         */
        async createNewDocument() {
            // Validate dimensions
            const w = Math.min(MAX_DOCUMENT_SIZE, Math.max(1, Math.round(this.newDocWidth)));
            const h = Math.min(MAX_DOCUMENT_SIZE, Math.max(1, Math.round(this.newDocHeight)));

            // Create the document
            await this.newDocument(w, h);

            // Set DPI on the document
            const app = this.getState();
            const doc = app?.documentManager?.getActiveDocument();
            if (doc) {
                doc.dpi = this.newDocDpi;
            }

            // Fill background if not transparent
            if (this.newDocBackground !== 'none') {
                const layer = app?.layerStack?.getActiveLayer();
                if (layer && layer.ctx) {
                    // Determine fill color - preset names or hex color
                    let fillColor;
                    switch (this.newDocBackground) {
                        case 'white': fillColor = '#FFFFFF'; break;
                        case 'black': fillColor = '#000000'; break;
                        case 'gray': fillColor = '#808080'; break;
                        default:
                            // Assume it's a hex color if not a preset name
                            fillColor = this.newDocBackground.startsWith('#') ? this.newDocBackground : '#FFFFFF';
                    }
                    layer.ctx.fillStyle = fillColor;
                    layer.ctx.fillRect(0, 0, w, h);
                    layer.invalidateImageCache();
                }
            }

            app?.renderer?.requestRender();
            this.updateLayerList();
            this.updateNavigator();
            this.newDocDialogVisible = false;
        },

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

                // Set DPI to 96 for clipboard content (screen content default)
                const app = this.getState();
                const doc = app?.documentManager?.getActiveDocument();
                if (doc) {
                    doc.dpi = 96;
                }

                // Draw onto background layer
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

        // ==================== Selection Dialogs ====================

        /**
         * Show grow/shrink selection dialog
         * @param {string} mode - 'grow' or 'shrink'
         */
        showGrowShrinkDialog(mode) {
            this.growShrinkMode = mode;
            this.growShrinkRadius = 5;
            this.growShrinkDialogVisible = true;
            this.closeMenu();
        },

        /**
         * Apply grow/shrink to selection
         */
        async applyGrowShrink() {
            const app = this.getState();
            if (!app?.selectionManager) return;

            const radius = Math.max(1, Math.round(this.growShrinkRadius));

            if (this.growShrinkMode === 'grow') {
                await app.selectionManager.grow(radius);
            } else {
                await app.selectionManager.shrink(radius);
            }

            app.renderer?.requestRender();
            this.growShrinkDialogVisible = false;
        },

        /**
         * Show save selection dialog
         */
        showSaveSelectionDialog() {
            this.saveSelectionName = 'Selection 1';
            const doc = this.documentManager?.activeDocument;
            if (doc?.savedSelections?.length > 0) {
                this.saveSelectionName = `Selection ${doc.savedSelections.length + 1}`;
            }
            this.saveSelectionDialogVisible = true;
            this.closeMenu();
        },

        /**
         * Save current selection with given name
         */
        saveSelection() {
            const app = this.getState();
            if (!app?.selectionManager) return;

            const name = this.saveSelectionName.trim() || 'Selection';
            app.selectionManager.saveSelection(name);
            this.updateSavedSelectionsState();
            this.saveSelectionDialogVisible = false;
        },

        /**
         * Show load selection dialog
         */
        showLoadSelectionDialog() {
            const doc = this.documentManager?.activeDocument;
            this.savedSelectionsList = doc?.savedSelections || [];
            this.loadSelectionMode = 'replace';
            this.loadSelectionDialogVisible = true;
            this.closeMenu();
        },

        /**
         * Load a saved selection
         * @param {string} name - Selection name
         */
        loadSelection(name) {
            const app = this.getState();
            if (!app?.selectionManager) return;

            app.selectionManager.loadSelection(name, this.loadSelectionMode);
            app.renderer?.requestRender();
            this.hasSelection = app.selectionManager.hasSelection();
            this.loadSelectionDialogVisible = false;
        },

        /**
         * Delete a saved selection
         * @param {string} name - Selection name
         */
        deleteSavedSelection(name) {
            const app = this.getState();
            if (!app?.selectionManager) return;

            app.selectionManager.deleteSelection(name);
            this.updateSavedSelectionsState();

            // Update the list for the dialog
            const doc = this.documentManager?.activeDocument;
            this.savedSelectionsList = doc?.savedSelections || [];
        },

        /**
         * Update hasSavedSelections state
         */
        updateSavedSelectionsState() {
            const doc = this.documentManager?.activeDocument;
            this.hasSavedSelections = !!(doc?.savedSelections?.length > 0);
        },
    },
};

export default ImageOperationsMixin;
