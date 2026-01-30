import { getCategoryName } from '/static/js/config/EditorConfig.js';

/**
 * DocumentUIManager Mixin
 *
 * Handles document tabs, image sources, layer list management, and UI mode changes.
 *
 * Required component data:
 *   - imageSources: Object
 *   - expandedSources: Object
 *   - sampleImages: Array
 *   - documentTabs: Array
 *   - layers: Array
 *   - activeLayerId: String
 *   - activeLayerOpacity: Number
 *   - activeLayerBlendMode: String
 *   - currentUIMode: String
 *   - tabletPanelOpen: String
 *   - tabletDrawerOpen: String
 *   - limitedSettings: Object
 *   - showToolPanel: Boolean
 *   - showRibbon: Boolean
 *   - showRightPanel: Boolean
 *   - apiBase: String
 *   - statusMessage: String
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - selectTool(): Select a tool by ID
 *   - loadSampleImage(): Load a sample image
 *   - fitToWindow(): Fit canvas to window
 *   - syncTabletToolProperties(): Sync tablet UI properties
 */
export const DocumentUIManagerMixin = {
    methods: {
        // ==================== Image Sources Methods ====================

        /**
         * Load available image sources from backend
         */
        async loadImageSources() {
            try {
                const response = await fetch(`${this.apiBase}/images/sources`);
                if (response.ok) {
                    const sources = await response.json();
                    // Load images for each source
                    for (const source of sources) {
                        const imgResponse = await fetch(`${this.apiBase}/images/${source.id}/list`);
                        if (imgResponse.ok) {
                            const images = await imgResponse.json();
                            this.imageSources[source.id] = images;
                            this.expandedSources[source.id] = source.id === 'skimage'; // Expand skimage by default
                        }
                    }
                }
            } catch (e) {
                console.warn('Failed to load image sources:', e);
            }
        },

        /**
         * Toggle expansion of a source category
         * @param {string} source - Source identifier
         */
        toggleSourceCategory(source) {
            this.expandedSources[source] = !this.expandedSources[source];
        },

        /**
         * Format source name for display
         * @param {string} source - Source identifier
         * @returns {string} Display name
         */
        formatSourceName(source) {
            const names = {
                'skimage': 'scikit-image Samples',
                'wikimedia': 'Wikimedia Commons',
                'unsplash': 'Unsplash',
            };
            return names[source] || source;
        },

        /**
         * Load an image from a source
         * @param {string} source - Source identifier
         * @param {Object} img - Image metadata
         */
        async loadSourceImage(source, img) {
            try {
                const response = await fetch(`${this.apiBase}/images/${source}/${img.id}`);
                if (response.ok) {
                    const metadata = await response.json();
                    // Load as new layer
                    await this.loadSampleImage({ id: img.id, source, ...metadata });
                    this.statusMessage = `Loaded: ${img.name}`;
                }
            } catch (e) {
                console.error('Failed to load image:', e);
                this.statusMessage = 'Failed to load image';
            }
        },

        // ==================== Document Tab Methods ====================

        /**
         * Update document tabs from document manager.
         * Also updates _hasActiveDocument reactive flag for UI state.
         */
        updateDocumentTabs() {
            const app = this.getState();
            if (!app?.documentManager) {
                this._hasActiveDocument = false;
                return;
            }
            this.documentTabs = app.documentManager.getDocumentList();
            // Update reactive flag - true if there's an active document with a layer stack
            this._hasActiveDocument = !!(app.layerStack && app.documentManager.activeDocumentId);
        },

        /**
         * Activate a document by ID
         * @param {string} documentId - Document identifier
         */
        activateDocument(documentId) {
            const app = this.getState();
            if (!app?.documentManager) return;
            app.documentManager.setActiveDocument(documentId);
        },

        /**
         * Close a document by ID
         * @param {string} documentId - Document identifier
         */
        closeDocument(documentId) {
            const app = this.getState();
            if (!app?.documentManager) return;
            app.documentManager.closeDocument(documentId);
        },

        /**
         * Show new document dialog
         */
        showNewDocumentDialog() {
            // Open the New Document dialog from ImageOperations mixin
            this.showNewDocDialog();
        },

        /**
         * Show close document confirmation dialog
         * @param {Object} document - Document object
         * @param {Function} callback - Callback with result
         */
        showCloseDocumentDialog(document, callback) {
            // Simple confirmation dialog for unsaved changes
            const confirmed = confirm(`"${document.name}" has unsaved changes. Close anyway?`);
            if (callback) callback(confirmed);
        },

        // ==================== Layer List Methods ====================

        /**
         * Update the layer list from layer stack
         * Layers are shown in internal order (index 0 first)
         * Rendering is bottom-to-top (high index rendered first, low index on top)
         */
        updateLayerList() {
            const app = this.getState();
            if (!app?.layerStack) {
                this.layers = [];
                return;
            }
            this.layers = app.layerStack.layers.slice().map(l => {
                const isGroup = l.isGroup ? l.isGroup() : false;
                const isSVG = l.isSVG ? l.isSVG() : false;
                const isVector = l.isVector ? l.isVector() : false;
                const isText = l.isText ? l.isText() : false;
                // Determine layer type (SVG is a subtype of vector but shown separately)
                let layerType = 'raster';
                if (isGroup) layerType = 'group';
                else if (isSVG) layerType = 'svg';
                else if (isVector) layerType = 'vector';
                else if (isText) layerType = 'text';
                return {
                    id: l.id,
                    name: l.name,
                    visible: l.visible,
                    locked: l.locked,
                    opacity: l.opacity,
                    blendMode: l.blendMode,
                    isVector: isVector,
                    isText: isText,
                    isSVG: isSVG,
                    isGroup: isGroup,
                    parentId: l.parentId || null,
                    expanded: l.expanded ?? true,
                    // Layer type for API
                    type: layerType,
                    // Layer dimensions and position (groups don't have dimensions)
                    width: l.width || 0,
                    height: l.height || 0,
                    offsetX: l.offsetX ?? 0,
                    offsetY: l.offsetY ?? 0,
                    // Calculate indent level based on parentId chain
                    indentLevel: this.getLayerIndentLevel(l, app.layerStack),
                };
            });
            this.activeLayerId = app.layerStack.getActiveLayer()?.id;
            this.updateLayerControls();
            // Update thumbnails after Vue has updated the DOM
            this.$nextTick(() => this.updateLayerThumbnails());
        },

        /**
         * Get indent level for a layer based on parent chain
         * @param {Object} layer - Layer object
         * @param {Object} layerStack - Layer stack reference
         * @returns {number} Indent level
         */
        getLayerIndentLevel(layer, layerStack) {
            let level = 0;
            let parentId = layer.parentId;
            while (parentId) {
                level++;
                const parent = layerStack.getLayerById(parentId);
                parentId = parent?.parentId;
            }
            return level;
        },

        /**
         * Update layer thumbnail canvases
         */
        updateLayerThumbnails() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const thumbSize = 40;

            for (const layer of app.layerStack.layers) {
                const refKey = 'layerThumb_' + layer.id;
                const thumbCanvas = this.$refs[refKey];
                if (!thumbCanvas || !thumbCanvas[0]) continue;

                const canvas = thumbCanvas[0];
                const ctx = canvas.getContext('2d');

                // Draw transparency grid background
                const gridSize = 5;
                for (let y = 0; y < thumbSize; y += gridSize) {
                    for (let x = 0; x < thumbSize; x += gridSize) {
                        const isLight = ((x / gridSize) + (y / gridSize)) % 2 === 0;
                        ctx.fillStyle = isLight ? '#ffffff' : '#cccccc';
                        ctx.fillRect(x, y, gridSize, gridSize);
                    }
                }

                // Draw layer content using renderThumbnail (handles transforms)
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';

                if (layer.renderThumbnail) {
                    // Use renderThumbnail which handles rotation/scale transforms
                    const thumb = layer.renderThumbnail(thumbSize, thumbSize);
                    ctx.drawImage(thumb.canvas, 0, 0);
                } else if (layer.canvas) {
                    // Fallback for layers without renderThumbnail (groups, etc.)
                    const layerWidth = layer.width || layer.canvas?.width || thumbSize;
                    const layerHeight = layer.height || layer.canvas?.height || thumbSize;
                    const scale = Math.min(thumbSize / layerWidth, thumbSize / layerHeight);
                    const scaledWidth = layerWidth * scale;
                    const scaledHeight = layerHeight * scale;
                    const offsetX = (thumbSize - scaledWidth) / 2;
                    const offsetY = (thumbSize - scaledHeight) / 2;
                    ctx.drawImage(layer.canvas, offsetX, offsetY, scaledWidth, scaledHeight);
                }
            }
        },

        /**
         * Update layer controls (opacity, blend mode) from active layer
         */
        updateLayerControls() {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer) {
                // Ensure opacity is a valid number (default to 100 if undefined/NaN)
                const opacity = typeof layer.opacity === 'number' && !isNaN(layer.opacity)
                    ? layer.opacity
                    : 1.0;
                this.activeLayerOpacity = Math.round(opacity * 100);
                this.activeLayerBlendMode = layer.blendMode || 'normal';
            } else {
                // No active layer - reset to defaults
                this.activeLayerOpacity = 100;
                this.activeLayerBlendMode = 'normal';
            }
        },

        // ==================== UI Mode Methods ====================

        /**
         * Set UI mode (desktop, tablet, limited)
         * @param {string} mode - Mode name
         */
        setUIMode(mode) {
            const app = this.getState();
            if (app?.uiConfig) {
                app.uiConfig.setMode(mode);
            }
            // Always apply mode directly — UIConfig may skip notification
            // if its stored mode already matches (e.g. after page reload)
            if (this.currentUIMode !== mode) {
                this.currentUIMode = mode;
                this.onModeChange(mode);
            }
            this.closeMenu();
        },

        /**
         * Handle mode change events
         * @param {string} mode - New mode name
         */
        onModeChange(mode) {
            // Handle mode-specific UI changes
            console.log('UI mode changed to:', mode);

            // Close any open panels/drawers
            this.tabletPanelOpen = null;
            this.tabletDrawerOpen = null;

            // Load mode-specific settings from UIConfig
            const app = this.getState();
            if (mode === 'limited' && app?.uiConfig) {
                const limitedConfig = app.uiConfig.getModeSettings('limited');
                this.limitedSettings = { ...this.limitedSettings, ...limitedConfig };

                // Ensure we only show allowed tools - switch to first allowed tool if current is not allowed
                if (!this.limitedSettings.allowedTools.includes(this.currentToolId)) {
                    const firstTool = this.limitedSettings.allowedTools[0] || 'brush';
                    this.selectTool(firstTool);
                }
            }

            // Update visibility based on mode
            if (mode === 'desktop') {
                this.showToolPanel = true;
                this.showRibbon = true;
                this.showRightPanel = true;
            } else if (mode === 'tablet') {
                // Tablet mode - CSS handles visibility via data-mode attribute
                this.showToolPanel = false;  // CSS hides desktop panel
                this.showRibbon = false;     // CSS hides ribbon
                this.showRightPanel = false; // CSS hides right panel
            } else if (mode === 'limited') {
                // Limited mode - minimal UI, CSS handles most of it
                this.showToolPanel = false;
                this.showRibbon = false;
                this.showRightPanel = false;
            }

            // Refit canvas to new available space
            this.$nextTick(() => {
                this.fitToWindow();
            });
        },

        // ==================== Tool Properties Methods ====================

        /**
         * Update tool properties display from current tool
         */
        updateToolProperties() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (!tool) {
                this.toolProperties = [];
                return;
            }
            this.toolProperties = tool.getProperties ? tool.getProperties() : [];

            // Sync brush preset state
            if (this.currentToolId === 'brush') {
                const presetProp = this.toolProperties.find(p => p.id === 'preset');
                if (presetProp) {
                    this.currentBrushPreset = presetProp.value;
                    const opt = presetProp.options.find(o => o.value === presetProp.value);
                    this.currentBrushPresetName = opt ? opt.label : presetProp.value;
                }
            }
        },

        /**
         * Update tool hint display from current tool
         */
        updateToolHint() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (!tool || !tool.getHint) {
                this.toolHint = null;
                return;
            }
            this.toolHint = tool.getHint();
        },

        // ==================== View Menu Methods ====================

        /**
         * Show view menu
         * @param {Event} e - Click event
         */
        showViewMenu(e) {
            this.showMenu('view', e);
        },

        // ==================== Category Formatting ====================

        /**
         * Format filter category for display
         * @param {string} category - Category identifier
         * @returns {string} Display name
         */
        formatCategory(category) {
            return getCategoryName(category);
        },

        // ==================== Submenu Handling ====================

        /**
         * Open a submenu (for filter categories)
         * @param {string} category - Category to show
         * @param {Event} event - Mouse event
         */
        openSubmenu(category, event) {
            this.cancelSubmenuClose();
            this.activeSubmenu = category;
            const rect = event.target.getBoundingClientRect();
            this.submenuPosition = {
                top: rect.top + 'px',
                left: (rect.right + 2) + 'px'
            };
        },

        /**
         * Open a file menu submenu (New from, etc.)
         * @param {string} submenuId - Submenu identifier
         * @param {Event} event - Mouse event
         */
        openFileSubmenu(submenuId, event) {
            this.openSubmenu(submenuId, event);
        },

        /**
         * Close submenu after delay
         */
        closeSubmenuDelayed() {
            this.submenuCloseTimeout = setTimeout(() => {
                this.activeSubmenu = null;
            }, 150);
        },

        /**
         * Cancel pending submenu close
         */
        cancelSubmenuClose() {
            if (this.submenuCloseTimeout) {
                clearTimeout(this.submenuCloseTimeout);
                this.submenuCloseTimeout = null;
            }
        },

        // ==================== Backend Data Loading ====================

        /**
         * Load filters and image sources from backend
         */
        async loadBackendData() {
            const app = this.getState();
            if (!app?.pluginManager) return;
            // Skip API calls when backend is disabled or offline
            const mode = app.backendMode || this.currentBackendMode || 'on';
            if (mode === 'off' || mode === 'offline') return;

            try {
                const filtersResponse = await fetch(`${this.apiBase}/filters`);
                if (filtersResponse.ok) {
                    const data = await filtersResponse.json();
                    const backendFilters = (data.filters || []).map(f => ({
                        ...f,
                        source: f.source || 'python',
                    }));
                    // Merge: keep WASM filters, add backend-only filters
                    const wasmIds = new Set(this.filters.filter(f => f.source === 'wasm').map(f => f.id));
                    const wasmFilters = this.filters.filter(f => f.source === 'wasm');
                    const backendOnly = backendFilters.filter(f => !wasmIds.has(f.id));
                    this.filters = [...wasmFilters, ...backendOnly];
                }

                const sourcesResponse = await fetch(`${this.apiBase}/images/sources`);
                if (sourcesResponse.ok) {
                    const sourcesData = await sourcesResponse.json();
                    const sources = sourcesData.sources || [];
                    // Load images from all sources
                    for (const source of sources) {
                        const imagesResponse = await fetch(`${this.apiBase}/images/${source.id}`);
                        if (imagesResponse.ok) {
                            const imagesData = await imagesResponse.json();
                            const images = imagesData.images || [];
                            // Store for File menu (first source only)
                            if (!this.sampleImages.length) {
                                this.sampleImages = images.map(img => ({
                                    id: img.id,
                                    name: img.name,
                                    source: source.id,
                                }));
                            }
                            // Store for Sources panel
                            this.imageSources[source.id] = images.map(img => ({
                                id: img.id,
                                name: img.name,
                            }));
                            // Expand first source by default
                            if (!Object.keys(this.expandedSources).length) {
                                this.expandedSources[source.id] = true;
                            }
                        }
                    }
                }
            } catch (e) {
                console.error('Failed to load backend data:', e);
            }
        },

        // ==================== Public Document Methods ====================

        /**
         * Create a new document with specified dimensions
         * @param {number} width - Document width
         * @param {number} height - Document height
         */
        async newDocument(width, height) {
            const app = this.getState();
            if (!app) return;

            this.docWidth = width;
            this.docHeight = height;
            app.canvasWidth = width;
            app.canvasHeight = height;

            // Clear auto-save data before creating new document
            if (app.autoSave) {
                await app.autoSave.clear();
            }

            // Use DocumentManager if available (proper multi-document approach)
            if (app.documentManager) {
                // Remove all existing documents without auto-creating
                const docs = [...app.documentManager.documents];
                for (const doc of docs) {
                    const idx = app.documentManager.documents.indexOf(doc);
                    if (idx !== -1) {
                        app.documentManager.documents.splice(idx, 1);
                        doc.dispose();
                    }
                }
                app.documentManager.activeDocumentId = null;

                // Create new document through DocumentManager
                app.documentManager.createDocument({
                    width: width,
                    height: height,
                    name: 'Untitled',
                    activate: true
                });
            } else {
                // Fallback: Reset layer stack directly
                const { LayerStack } = await import('/static/js/core/LayerStack.js');
                app.layerStack = new LayerStack(width, height, app.eventBus);
                app.renderer.layerStack = app.layerStack;
                app.renderer.resize(width, height);

                // Create initial background layer filled with white at full doc size
                const bgLayer = app.layerStack.addLayer({ name: 'Background' });
                bgLayer.fillArea('#FFFFFF', 0, 0, width, height);

                app.history.clear();
            }

            this.updateLayerList();
            this.fitToWindow();
            this.emitStateUpdate();
        },
    },
};

export default DocumentUIManagerMixin;
