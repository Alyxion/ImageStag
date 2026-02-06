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
import {
    MAX_DIMENSION,
    SUGGESTED_MAX_WIDTH,
    clampDimension,
    checkDimensionLimits,
    getSuggestedDimensions,
    formatBytes
} from '../../config/limits.js';

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

import { generateDocumentIdentity, preloadConfigs, getIconPicker } from '../../utils/DocumentNameGenerator.js';

export const ImageOperationsMixin = {
    computed: {
        /**
         * Validation error for New Document dialog.
         * @returns {string|null} Error message or null if valid
         */
        newDocDimensionError() {
            if (this.newDocWidth > MAX_DIMENSION) {
                return `Width exceeds maximum of ${MAX_DIMENSION}px`;
            }
            if (this.newDocHeight > MAX_DIMENSION) {
                return `Height exceeds maximum of ${MAX_DIMENSION}px`;
            }
            if (this.newDocWidth < 1 || this.newDocHeight < 1) {
                return 'Dimensions must be at least 1px';
            }
            return null;
        },

        /**
         * Validation error for Resize dialog.
         * @returns {string|null} Error message or null if valid
         */
        resizeDimensionError() {
            if (this.resizeWidth > MAX_DIMENSION) {
                return `Width exceeds maximum of ${MAX_DIMENSION}px`;
            }
            if (this.resizeHeight > MAX_DIMENSION) {
                return `Height exceeds maximum of ${MAX_DIMENSION}px`;
            }
            if (this.resizeWidth < 1 || this.resizeHeight < 1) {
                return 'Dimensions must be at least 1px';
            }
            return null;
        },

        /**
         * Validation error for Canvas Size dialog.
         * @returns {string|null} Error message or null if valid
         */
        canvasSizeDimensionError() {
            if (this.canvasNewWidth > MAX_DIMENSION) {
                return `Width exceeds maximum of ${MAX_DIMENSION}px`;
            }
            if (this.canvasNewHeight > MAX_DIMENSION) {
                return `Height exceeds maximum of ${MAX_DIMENSION}px`;
            }
            if (this.canvasNewWidth < 1 || this.canvasNewHeight < 1) {
                return 'Dimensions must be at least 1px';
            }
            return null;
        },
    },
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
            newDocName: '',
            newDocIcon: '🎨',
            newDocColor: '#E0E7FF',
            newDocWidthCm: 0,
            newDocHeightCm: 0,
            iconPickerIcons: [],
            iconPickerOpen: false,
            iconPickerStyle: {},

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

            // Limits (exposed for templates)
            maxDimension: MAX_DIMENSION,

            // Oversized image dialog
            oversizedDialogVisible: false,
            oversizedOriginalWidth: 0,
            oversizedOriginalHeight: 0,
            oversizedSuggestedWidth: 0,
            oversizedSuggestedHeight: 0,
            oversizedCallback: null,
        };
    },
    methods: {
        /**
         * Show the New Document dialog with defaults.
         */
        async showNewDocDialog() {
            // Preload configs (cached after first load)
            await preloadConfigs();

            // Load icon picker icons
            this.iconPickerIcons = getIconPicker();

            // Generate a new document identity
            const identity = generateDocumentIdentity();
            this.newDocName = identity.name;
            this.newDocIcon = identity.icon;
            this.newDocColor = identity.color;

            // Reset to defaults (FHD screen preset)
            this.newDocWidth = 1920;
            this.newDocHeight = 1080;
            this.newDocDpi = 96;
            this.newDocBackground = 'white';
            this.newDocPreset = 'fhd';
            this.iconPickerOpen = false;
            this.newDocDialogVisible = true;

            // Calculate cm values
            this.updateCmFromPixels();
        },

        /**
         * Regenerate document identity (name, icon, color).
         */
        regenerateDocIdentity() {
            const identity = generateDocumentIdentity();
            this.newDocName = identity.name;
            this.newDocIcon = identity.icon;
            this.newDocColor = identity.color;
        },

        /**
         * Toggle icon picker popover and position it near the input.
         */
        toggleIconPicker(event) {
            if (this.iconPickerOpen) {
                this.iconPickerOpen = false;
                return;
            }
            // Position near the button
            const btn = event.target;
            const rect = btn.getBoundingClientRect();
            this.iconPickerStyle = {
                top: `${rect.bottom + 4}px`,
                left: `${rect.left}px`
            };
            this.iconPickerOpen = true;
        },

        /**
         * Select an icon from the picker.
         */
        selectIcon(icon) {
            this.newDocIcon = icon;
            this.iconPickerOpen = false;
        },

        /**
         * Update cm values from pixel dimensions.
         */
        updateCmFromPixels() {
            const dpi = this.newDocDpi || 96;
            // 1 inch = 2.54 cm
            this.newDocWidthCm = parseFloat(((this.newDocWidth / dpi) * 2.54).toFixed(2));
            this.newDocHeightCm = parseFloat(((this.newDocHeight / dpi) * 2.54).toFixed(2));
        },

        /**
         * Update pixel dimensions from cm values.
         */
        updatePixelsFromCm() {
            const dpi = this.newDocDpi || 96;
            // 1 inch = 2.54 cm
            this.newDocWidth = Math.round((this.newDocWidthCm / 2.54) * dpi);
            this.newDocHeight = Math.round((this.newDocHeightCm / 2.54) * dpi);
            this.newDocPreset = 'custom';
        },

        /**
         * Handle width cm input change.
         * Does NOT clamp - allows user to see validation error.
         */
        onNewDocWidthCmChange() {
            const dpi = this.newDocDpi || 96;
            let px = Math.round((this.newDocWidthCm / 2.54) * dpi);
            px = Math.max(0, px);
            this.newDocWidth = px;
            this.newDocPreset = 'custom';
        },

        /**
         * Handle height cm input change.
         * Does NOT clamp - allows user to see validation error.
         */
        onNewDocHeightCmChange() {
            const dpi = this.newDocDpi || 96;
            let px = Math.round((this.newDocHeightCm / 2.54) * dpi);
            px = Math.max(0, px);
            this.newDocHeight = px;
            this.newDocPreset = 'custom';
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
            const { SVGLayer } = await import('/static/js/core/StaticSVGLayer.js');

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

                this.statusMessage = 'SVG layer added from URL';
            } else {
                // Create new document - check for oversized
                let docW = w;
                let docH = h;
                const check = checkDimensionLimits(docW, docH);

                if (!check.valid) {
                    // Scale down to suggested dimensions
                    const suggested = getSuggestedDimensions(docW, docH);
                    docW = suggested.width;
                    docH = suggested.height;
                    this.statusMessage = `SVG scaled from ${w}×${h} to ${docW}×${docH}`;
                }

                app.documentManager.createDocument({
                    width: docW,
                    height: docH,
                    name,
                    activate: true,
                    empty: true
                });

                await this.$nextTick();

                const layer = new SVGLayer({
                    width: docW,
                    height: docH,
                    offsetX: 0,
                    offsetY: 0,
                    name,
                    svgContent,
                });
                await layer.render();

                app.layerStack.addLayer(layer);
                app.layerStack.setActiveLayer(0);
                app.history?.saveState('Load SVG from URL');

                if (check.valid) {
                    this.statusMessage = 'SVG loaded from URL';
                }
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

                const { Layer } = await import('/static/js/core/PixelLayer.js');

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

                this.statusMessage = 'Layer added from URL';
            } else {
                // Create new document - check for oversized
                let docW = img.width;
                let docH = img.height;
                const check = checkDimensionLimits(docW, docH);

                if (!check.valid) {
                    // Scale down to suggested dimensions
                    const suggested = getSuggestedDimensions(docW, docH);
                    docW = suggested.width;
                    docH = suggested.height;
                    this.statusMessage = `Image scaled from ${img.width}×${img.height} to ${docW}×${docH}`;
                }

                app.documentManager.createDocument({
                    width: docW,
                    height: docH,
                    name,
                    activate: true
                });

                await this.$nextTick();

                const layer = app.layerStack?.getActiveLayer();
                if (layer) {
                    // Draw scaled if needed
                    layer.ctx.drawImage(img, 0, 0, docW, docH);
                    layer.invalidateImageCache();
                    app.history?.saveState('Load from URL');
                }

                if (check.valid) {
                    this.statusMessage = 'Image loaded from URL';
                }
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
            this.updateCmFromPixels();
        },

        /**
         * Called when width/height inputs change manually.
         * Switches preset to 'custom' and updates cm values.
         * Does NOT clamp - allows user to see validation error.
         */
        onNewDocDimensionChange() {
            // Ensure positive integer but don't clamp to max
            this.newDocWidth = Math.max(0, Math.round(this.newDocWidth) || 0);
            this.newDocHeight = Math.max(0, Math.round(this.newDocHeight) || 0);
            this.newDocPreset = 'custom';
            this.updateCmFromPixels();
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
            // Block if validation error
            if (this.newDocDimensionError) return;

            // Validate dimensions
            const w = clampDimension(this.newDocWidth);
            const h = clampDimension(this.newDocHeight);

            // Create the document with identity
            await this.newDocument({
                width: w,
                height: h,
                name: this.newDocName,
                icon: this.newDocIcon,
                color: this.newDocColor
            });

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
                const origW = bitmap.width;
                const origH = bitmap.height;

                // Check for oversized image
                const check = checkDimensionLimits(origW, origH);

                if (!check.valid) {
                    // Show dialog and handle via callback
                    this._clipboardBitmap = bitmap;
                    this.checkAndHandleOversizedImage(origW, origH, async (w, h) => {
                        await this._createDocumentFromBitmap(this._clipboardBitmap, w, h, origW, origH);
                        this._clipboardBitmap.close();
                        this._clipboardBitmap = null;
                    });
                } else {
                    // Dimensions OK, proceed directly
                    await this._createDocumentFromBitmap(bitmap, origW, origH, origW, origH);
                    bitmap.close();
                }
            } catch (e) {
                console.error('New from clipboard failed:', e);
            }
        },

        /**
         * Helper to create document from bitmap with optional scaling.
         */
        async _createDocumentFromBitmap(bitmap, docW, docH, srcW, srcH) {
            await this.newDocument(docW, docH);

            const app = this.getState();
            const doc = app?.documentManager?.getActiveDocument();
            if (doc) {
                doc.dpi = 96;
            }

            if (!app) return;
            const layer = app.layerStack?.getActiveLayer();
            if (layer && layer.ctx) {
                // Draw scaled if needed
                layer.ctx.drawImage(bitmap, 0, 0, docW, docH);
                layer.invalidateImageCache();
            }

            this.updateLayerList();
            this.updateNavigator();

            if (docW !== srcW || docH !== srcH) {
                this.statusMessage = `Image scaled from ${srcW}×${srcH} to ${docW}×${docH}`;
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
         * Does NOT clamp - allows user to see validation error.
         */
        onResizeWidthChange() {
            // Ensure positive integer
            this.resizeWidth = Math.max(0, Math.round(this.resizeWidth) || 0);
            if (this.resizeLockAspect && this._resizeOrigWidth > 0) {
                const ratio = this._resizeOrigHeight / this._resizeOrigWidth;
                this.resizeHeight = Math.max(0, Math.round(this.resizeWidth * ratio));
            }
        },

        /**
         * Called when resize height input changes (maintains aspect ratio if locked).
         * Does NOT clamp - allows user to see validation error.
         */
        onResizeHeightChange() {
            // Ensure positive integer
            this.resizeHeight = Math.max(0, Math.round(this.resizeHeight) || 0);
            if (this.resizeLockAspect && this._resizeOrigHeight > 0) {
                const ratio = this._resizeOrigWidth / this._resizeOrigHeight;
                this.resizeWidth = Math.max(0, Math.round(this.resizeHeight * ratio));
            }
        },

        /**
         * Apply the resize operation to all layers.
         */
        async applyResize() {
            // Block if validation error
            if (this.resizeDimensionError) return;

            const app = this.getState();
            if (!app?.layerStack || !app?.history) return;

            const oldW = app.layerStack.width;
            const oldH = app.layerStack.height;
            const newW = clampDimension(this.resizeWidth);
            const newH = clampDimension(this.resizeHeight);

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
            // Block if validation error
            if (this.canvasSizeDimensionError) return;

            const app = this.getState();
            if (!app?.layerStack || !app?.history) return;

            const oldW = app.layerStack.width;
            const oldH = app.layerStack.height;
            const newW = clampDimension(this.canvasNewWidth);
            const newH = clampDimension(this.canvasNewHeight);

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

        // ==================== Oversized Image Handling ====================

        /**
         * Check if image dimensions exceed limits and show dialog if so.
         * @param {number} width - Original width
         * @param {number} height - Original height
         * @param {Function} callback - Called with (width, height) when user confirms
         * @returns {boolean} True if dialog was shown, false if dimensions are OK
         */
        checkAndHandleOversizedImage(width, height, callback) {
            const check = checkDimensionLimits(width, height);

            if (check.valid) {
                // Dimensions OK, proceed directly
                callback(width, height);
                return false;
            }

            // Get suggested dimensions (prefer UHD scaling)
            const suggested = getSuggestedDimensions(width, height);

            this.oversizedOriginalWidth = width;
            this.oversizedOriginalHeight = height;
            this.oversizedSuggestedWidth = suggested.width;
            this.oversizedSuggestedHeight = suggested.height;
            this.oversizedCallback = callback;
            this.oversizedDialogVisible = true;

            return true;
        },

        /**
         * User confirmed using suggested (scaled down) dimensions.
         */
        confirmOversizedSuggested() {
            if (this.oversizedCallback) {
                this.oversizedCallback(this.oversizedSuggestedWidth, this.oversizedSuggestedHeight);
            }
            this.oversizedDialogVisible = false;
            this.oversizedCallback = null;
        },

        /**
         * User chose to use maximum allowed dimensions.
         */
        confirmOversizedMaximum() {
            const w = clampDimension(this.oversizedOriginalWidth);
            const h = clampDimension(this.oversizedOriginalHeight);
            // Maintain aspect ratio at max dimension
            const scale = Math.min(MAX_DIMENSION / this.oversizedOriginalWidth, MAX_DIMENSION / this.oversizedOriginalHeight);
            const finalW = Math.floor(this.oversizedOriginalWidth * scale);
            const finalH = Math.floor(this.oversizedOriginalHeight * scale);

            if (this.oversizedCallback) {
                this.oversizedCallback(finalW, finalH);
            }
            this.oversizedDialogVisible = false;
            this.oversizedCallback = null;
        },

        /**
         * User cancelled the oversized image operation.
         */
        cancelOversized() {
            this.oversizedDialogVisible = false;
            this.oversizedCallback = null;
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
            const app = this.getState();
            const doc = app?.documentManager?.activeDocument;
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
            const app = this.getState();
            const doc = app?.documentManager?.activeDocument;
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
            this.hasSelection = app.selectionManager.hasSelection;
            this.loadSelectionDialogVisible = false;
        },

        /**
         * Delete a saved selection
         * @param {string} name - Selection name
         */
        deleteSavedSelection(name) {
            const app = this.getState();
            if (!app?.selectionManager) return;

            app.selectionManager.deleteSavedSelection(name);
            this.updateSavedSelectionsState();

            // Update the list for the dialog
            const doc = app.documentManager?.activeDocument;
            this.savedSelectionsList = doc?.savedSelections || [];
        },

        /**
         * Update hasSavedSelections state
         */
        updateSavedSelectionsState() {
            const app = this.getState();
            const doc = app?.documentManager?.activeDocument;
            this.hasSavedSelections = !!(doc?.savedSelections?.length > 0);
        },
    },
};

export default ImageOperationsMixin;
