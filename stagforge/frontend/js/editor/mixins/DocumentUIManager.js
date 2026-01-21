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
         * Update document tabs from document manager
         */
        updateDocumentTabs() {
            const app = this.getState();
            if (!app?.documentManager) return;
            this.documentTabs = app.documentManager.getDocumentList();
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
            // For now, create a new document with default settings
            // Could show a dialog for width/height in the future
            const app = this.getState();
            if (!app?.documentManager) return;
            app.documentManager.createDocument({
                width: this.docWidth,
                height: this.docHeight
            });
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
         */
        updateLayerList() {
            const app = this.getState();
            if (!app?.layerStack) return;
            this.layers = app.layerStack.layers.slice().reverse().map(l => {
                const isGroup = l.isGroup ? l.isGroup() : false;
                return {
                    id: l.id,
                    name: l.name,
                    visible: l.visible,
                    locked: l.locked,
                    opacity: l.opacity,
                    blendMode: l.blendMode,
                    isVector: l.isVector ? l.isVector() : false,
                    isText: l.isText ? l.isText() : false,
                    isGroup: isGroup,
                    parentId: l.parentId || null,
                    expanded: l.expanded ?? true,
                    // Layer type for API
                    type: isGroup ? 'group' : (l.isVector?.() ? 'vector' : (l.isText?.() ? 'text' : 'raster')),
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

                // Calculate scaling to fit layer in thumbnail
                const layerWidth = layer.width || layer.canvas?.width || thumbSize;
                const layerHeight = layer.height || layer.canvas?.height || thumbSize;
                const scale = Math.min(thumbSize / layerWidth, thumbSize / layerHeight);
                const scaledWidth = layerWidth * scale;
                const scaledHeight = layerHeight * scale;
                const offsetX = (thumbSize - scaledWidth) / 2;
                const offsetY = (thumbSize - scaledHeight) / 2;

                // Draw layer content
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                if (layer.canvas) {
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
         * Open a submenu
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

            try {
                const filtersResponse = await fetch(`${this.apiBase}/filters`);
                if (filtersResponse.ok) {
                    const data = await filtersResponse.json();
                    this.filters = data.filters || [];
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

            // Reset layer stack (need to import dynamically)
            const { LayerStack } = await import('/static/js/core/LayerStack.js');
            app.layerStack = new LayerStack(width, height, app.eventBus);
            app.renderer.layerStack = app.layerStack;
            app.renderer.resize(width, height);

            // Create initial layer
            const bgLayer = app.layerStack.addLayer({ name: 'Background' });
            bgLayer.fill('#FFFFFF');

            app.history.clear();
            this.updateLayerList();
            this.fitToWindow();
            this.emitStateUpdate();
        },
    },
};

export default DocumentUIManagerMixin;
