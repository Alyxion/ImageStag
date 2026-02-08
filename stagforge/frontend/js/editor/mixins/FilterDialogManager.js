import { getIcon } from '/static/js/config/EditorConfig.js';
import { getToolIcon as getToolIconFromTools, toolIcons } from '/static/js/tools/index.js';

/**
 * FilterDialogManager Mixin
 *
 * Handles filter dialog, rasterize prompt, preferences dialog, and tool icon lookup.
 *
 * Required component data:
 *   - activeMenu: String
 *   - activeSubmenu: String
 *   - filterParams: Object
 *   - currentFilter: Object
 *   - filterDialogVisible: Boolean
 *   - filterPreviewEnabled: Boolean
 *   - filterPreviewState: ImageData
 *   - filterPreviewDebounce: Number
 *   - showRasterizePrompt: Boolean
 *   - rasterizeLayerId: String
 *   - rasterizeCallback: Function
 *   - preferencesDialogVisible: Boolean
 *   - prefRenderingSVG: Boolean
 *   - prefSupersampleLevel: Number
 *   - prefAntialiasing: Boolean
 *   - statusMessage: String
 *   - apiBase: String
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - getSelection(): Returns the current selection
 *   - updateLayerList(): Refreshes the layers panel
 *   - closeMenu(): Close active menus
 */
export const FilterDialogManagerMixin = {
    methods: {
        /**
         * Open filter dialog or apply directly if no params
         * @param {Object} filter - Filter configuration
         */
        openFilterDialog(filter) {
            const app = this.getState();
            if (!app?.layerStack) {
                console.warn('Cannot open filter: no active document');
                return;
            }

            this.activeMenu = null;
            this.activeSubmenu = null;

            // Check if filter has parameters
            const hasParams = filter.params && filter.params.length > 0;

            if (!hasParams) {
                // Apply directly without dialog
                this.applyFilterDirect(filter);
                return;
            }

            // Initialize params with defaults
            this.filterParams = {};
            for (const param of filter.params) {
                this.filterParams[param.id] = param.default !== undefined ? param.default :
                    (param.type === 'range' ? param.min :
                     param.type === 'select' ? param.options[0] :
                     param.type === 'checkbox' ? false :
                     param.type === 'color' ? '#FFFFFF' : '');
            }

            // Apply preset params (from expanded composite filters)
            if (filter.presetParams) {
                Object.assign(this.filterParams, filter.presetParams);
            }

            this.currentFilter = filter;
            this.filterDialogVisible = true;
            this.pushDialog('filter', () => this.cancelFilterDialog());
            this.filterPreviewEnabled = true;
            this.filterPreviewState = null;

            // Save current state for preview/cancel, then apply initial preview
            this.$nextTick(() => {
                this.saveFilterPreviewState();
                // Small delay to ensure state is saved before preview
                setTimeout(() => {
                    this.updateFilterPreview();
                }, 50);
            });
        },

        /**
         * Save current layer state for filter preview
         */
        saveFilterPreviewState() {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer) {
                this.filterPreviewState = layer.ctx.getImageData(0, 0, layer.width, layer.height);
            }
        },

        /**
         * Restore layer state from saved preview state
         * @param {boolean} render - Whether to trigger render after restore
         */
        restoreFilterPreviewState(render = true) {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer && this.filterPreviewState) {
                layer.ctx.putImageData(this.filterPreviewState, 0, 0);
                // Direct pixel modification - manually invalidate
                if (render && layer.invalidateImageCache) {
                    layer.invalidateImageCache();
                }
            }
        },

        /**
         * Toggle filter preview on/off
         */
        toggleFilterPreview() {
            if (this.filterPreviewEnabled) {
                this.updateFilterPreview();
            } else {
                this.restoreFilterPreviewState();
            }
        },

        /**
         * Update filter preview with current params
         */
        async updateFilterPreview() {
            if (!this.filterPreviewEnabled || !this.currentFilter) return;

            // Debounce preview updates
            if (this.filterPreviewDebounce) {
                clearTimeout(this.filterPreviewDebounce);
            }

            this.filterPreviewDebounce = setTimeout(async () => {
                const app = this.getState();
                if (!app || !this.filterPreviewState) return;

                try {
                    // Restore original state first (don't render yet)
                    this.restoreFilterPreviewState(false);

                    // Apply filter with current params and render
                    await this.applyFilterToLayer(this.currentFilter.id, this.filterParams, true);
                } catch (error) {
                    console.error('Preview error:', error);
                    // On error, restore and render original
                    this.restoreFilterPreviewState(true);
                }
            }, 150);
        },

        /**
         * Get display label for filter history/status, reflecting the active sub-operation
         * for expanded composite filters.
         * @param {Object} filter - Filter configuration
         * @param {Object} [params] - Current filter params (defaults to this.filterParams)
         * @returns {string} Display label
         */
        getFilterHistoryLabel(filter, params) {
            if (!filter) return 'Filter';
            if (filter.expandParam && filter.baseName) {
                const p = params || this.filterParams || {};
                const value = p[filter.expandParam];
                if (value != null) {
                    const label = String(value).charAt(0).toUpperCase() + String(value).slice(1);
                    return `${filter.baseName} (${label})`;
                }
            }
            return filter.name;
        },

        /**
         * Apply filter directly without dialog
         * @param {Object} filter - Filter configuration
         */
        async applyFilterDirect(filter) {
            const app = this.getState();
            if (!app?.layerStack) return;

            const historyLabel = this.getFilterHistoryLabel(filter, filter.presetParams || {});
            app.history.saveState('Filter: ' + historyLabel);
            this.statusMessage = 'Applying ' + historyLabel + '...';

            try {
                const params = filter.presetParams ? { ...filter.presetParams } : {};
                await this.applyFilterToLayer(filter.id, params, true);
                app.history.finishState();
                this.statusMessage = historyLabel + ' applied';
            } catch (error) {
                console.error('Filter error:', error);
                app.history.abortCapture();
                this.statusMessage = 'Filter failed: ' + error.message;
            }
        },

        /**
         * Confirm and apply filter from dialog
         */
        async applyFilterConfirm() {
            const app = this.getState();
            if (!app || !this.currentFilter) return;

            // The preview is already applied, just save to history
            const historyLabel = this.getFilterHistoryLabel(this.currentFilter);
            app.history.saveState('Filter: ' + historyLabel);
            app.history.finishState();

            this.statusMessage = historyLabel + ' applied';
            this.popDialog('filter');
            this.filterDialogVisible = false;
            this.currentFilter = null;
            this.filterPreviewState = null;
        },

        /**
         * Reset all filter params to their defaults
         */
        resetFilterParams() {
            if (!this.currentFilter?.params) return;
            for (const param of this.currentFilter.params) {
                this.filterParams[param.id] = param.default !== undefined ? param.default :
                    (param.type === 'range' ? param.min :
                     param.type === 'select' ? param.options[0] :
                     param.type === 'checkbox' ? false :
                     param.type === 'color' ? '#FFFFFF' : '');
            }
            this.updateFilterPreview();
        },

        /**
         * Cancel filter dialog and restore original state
         */
        cancelFilterDialog() {
            // Restore original state
            this.restoreFilterPreviewState();

            this.popDialog('filter');
            this.filterDialogVisible = false;
            this.currentFilter = null;
            this.filterPreviewState = null;
            this.statusMessage = 'Filter cancelled';
        },

        /**
         * Apply filter to the active layer
         * @param {string} filterId - Filter ID
         * @param {Object} params - Filter parameters
         * @param {boolean} renderAfter - Whether to render after applying
         */
        async applyFilterToLayer(filterId, params, renderAfter = true) {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (!layer) return;

            // Check for active selection to constrain filter
            const selection = this.getSelection();
            let filterX = 0, filterY = 0, filterWidth = layer.width, filterHeight = layer.height;

            if (selection && selection.width > 0 && selection.height > 0) {
                // Convert selection to layer coordinates if needed
                let selX = selection.x, selY = selection.y;
                if (layer.docToCanvas) {
                    const coords = layer.docToCanvas(selection.x, selection.y);
                    selX = coords.x;
                    selY = coords.y;
                }
                // Clamp to layer bounds
                filterX = Math.max(0, Math.floor(selX));
                filterY = Math.max(0, Math.floor(selY));
                filterWidth = Math.min(layer.width - filterX, Math.ceil(selection.width));
                filterHeight = Math.min(layer.height - filterY, Math.ceil(selection.height));

                if (filterWidth <= 0 || filterHeight <= 0) return;
            }

            const imageData = layer.ctx.getImageData(filterX, filterY, filterWidth, filterHeight);

            // Determine execution path
            const pluginManager = app?.pluginManager;
            const execMode = app?.uiConfig?.get('filters.executionMode') ?? 'js';
            const wasmEngine = pluginManager?.wasmEngine;

            let resultImageData;

            if (filterId.startsWith('js:')) {
                // Built-in JavaScript filter
                const filter = pluginManager?.jsFilters?.get(filterId);
                if (!filter) throw new Error(`Filter not found: ${filterId}`);
                resultImageData = filter.apply(imageData, params);
            } else if (execMode === 'js' && wasmEngine?.ready && wasmEngine.hasFilter(filterId)) {
                // Client-side WASM execution
                resultImageData = wasmEngine.applyFilter(filterId, imageData, params);
            } else {
                // Server-side execution via binary protocol
                const metadata = JSON.stringify({
                    width: imageData.width,
                    height: imageData.height,
                    params: params
                });
                const metadataBytes = new TextEncoder().encode(metadata);
                const metadataLength = new Uint32Array([metadataBytes.length]);

                const payload = new Uint8Array(4 + metadataBytes.length + imageData.data.length);
                payload.set(new Uint8Array(metadataLength.buffer), 0);
                payload.set(metadataBytes, 4);
                payload.set(imageData.data, 4 + metadataBytes.length);

                const response = await fetch(`${this.apiBase}/filters/${filterId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/octet-stream' },
                    body: payload
                });

                if (!response.ok) {
                    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                    throw new Error(error.detail || 'Filter failed');
                }

                const resultBytes = new Uint8Array(await response.arrayBuffer());
                resultImageData = new ImageData(
                    new Uint8ClampedArray(resultBytes),
                    imageData.width,
                    imageData.height
                );
            }

            // Put result back at the correct position (selection offset)
            layer.ctx.putImageData(resultImageData, filterX, filterY);

            // Direct pixel modification - manually invalidate
            if (renderAfter && layer.invalidateImageCache) {
                layer.invalidateImageCache();
            }
        },

        // ==================== Rasterize Dialog Methods ====================

        /**
         * Confirm rasterize and execute callback
         */
        async confirmRasterize() {
            const app = this.getState();
            if (!app || !this.rasterizeLayerId) {
                this.cancelRasterize();
                return;
            }

            const layer = app.layerStack.getLayerById(this.rasterizeLayerId);
            if (!layer) {
                this.cancelRasterize();
                return;
            }

            // Use structural change for layer replacement
            app.history.beginCapture('Rasterize Layer', []);
            app.history.beginStructuralChange();

            // Store the original layer data for undo (layer will be replaced)
            await app.history.storeDeletedLayer(layer);

            // Rasterize the layer
            app.layerStack.rasterizeLayer(this.rasterizeLayerId);

            app.history.commitCapture();

            // Update layers display
            this.updateLayerList();

            // Call the callback
            const callback = this.rasterizeCallback;
            this.popDialog('rasterize');
            this.showRasterizePrompt = false;
            this.rasterizeLayerId = null;
            this.rasterizeCallback = null;

            if (callback) {
                callback(true);
            }
        },

        /**
         * Cancel rasterize and call callback with false
         */
        cancelRasterize() {
            const callback = this.rasterizeCallback;
            this.popDialog('rasterize');
            this.showRasterizePrompt = false;
            this.rasterizeLayerId = null;
            this.rasterizeCallback = null;

            if (callback) {
                callback(false);
            }
        },

        // ==================== Preferences Dialog Methods ====================

        /**
         * Show preferences dialog
         */
        showPreferencesDialog() {
            this.closeMenu();
            // Load current values from UIConfig
            const app = this.getState();
            if (app?.uiConfig) {
                this.prefRenderingSVG = app.uiConfig.get('rendering.vectorSVGRendering') ?? true;
                this.prefSupersampleLevel = app.uiConfig.get('rendering.vectorSupersampleLevel') ?? 3;
                this.prefAntialiasing = app.uiConfig.get('rendering.vectorAntialiasing') ?? false;
                this.prefFilterExecMode = app.uiConfig.get('filters.executionMode') ?? 'js';
            }
            this.preferencesDialogVisible = true;
            this.pushDialog('preferences', () => this.closePreferencesDialog());
        },

        /**
         * Close preferences dialog without saving
         */
        closePreferencesDialog() {
            this.popDialog('preferences');
            this.preferencesDialogVisible = false;
        },

        /**
         * Save preferences and close dialog
         */
        savePreferences() {
            const app = this.getState();
            if (app?.uiConfig) {
                app.uiConfig.set('rendering.vectorSVGRendering', this.prefRenderingSVG);
                app.uiConfig.set('rendering.vectorSupersampleLevel', this.prefSupersampleLevel);
                app.uiConfig.set('rendering.vectorAntialiasing', this.prefAntialiasing);
                app.uiConfig.set('filters.executionMode', this.prefFilterExecMode);
            }
            this.popDialog('preferences');
            this.preferencesDialogVisible = false;

            // Re-render dynamic layers with new settings
            this.reRenderDynamicLayers();
        },

        /**
         * Re-render all dynamic layers (SVG, text) with current settings
         */
        async reRenderDynamicLayers() {
            const app = this.getState();
            if (!app?.layerStack) return;

            for (const layer of app.layerStack.layers) {
                if (layer.render && (layer.isSVG?.() || layer.isText?.())) {
                    await layer.render();
                }
            }
        },

        // ==================== Tool Icon Lookup ====================

        /**
         * Get HTML entity for tool or UI icon
         * Checks tool icons first, then falls back to UI icons
         * @param {string} icon - Icon identifier
         * @returns {string} HTML entity
         */
        getToolIcon(icon) {
            // Map icon name to SVG file name
            const svgMap = {
                // Tool icons (tool id → filename without extension)
                'move': 'move', 'selection': 'selection', 'lasso': 'lasso',
                'magicwand': 'magicwand', 'crop': 'crop', 'eyedropper': 'eyedropper',
                'clonestamp': 'clonestamp', 'clone': 'clonestamp',
                'smudge': 'smudge', 'blur': 'blur', 'sharpen': 'sharpen',
                'brush': 'brush', 'pencil': 'pencil', 'spray': 'spray',
                'eraser': 'eraser', 'fill': 'fill', 'gradient': 'gradient',
                'dodge': 'dodge', 'burn': 'burn', 'sponge': 'sponge',
                'pen': 'pen', 'rect': 'rect', 'circle': 'circle',
                'polygon': 'polygon', 'shape': 'shape', 'line': 'line',
                'text': 'text', 'hand': 'hand',
                'vectorshapeedit': 'vectorshapeedit', 'cursor': 'vectorshapeedit',
                // UI icons (name → ui-filename)
                'tools': 'ui-tools', 'file': 'ui-file', 'edit': 'ui-edit',
                'view': 'ui-view', 'filter': 'ui-filter', 'image': 'ui-image',
                'undo': 'ui-undo', 'redo': 'ui-redo', 'navigator': 'ui-navigator',
                'layers': 'ui-layers', 'history': 'ui-history',
                'settings': 'ui-settings', 'close': 'ui-close',
                'plus': 'ui-plus', 'minus': 'ui-minus',
                'zoom-in': 'ui-zoom-in', 'zoom-out': 'ui-zoom-out',
                'save': 'ui-save', 'export': 'ui-export',
                'menu': 'ui-menu', 'deselect': 'ui-deselect',
                'eye': 'ui-eye', 'eye-off': 'ui-eye-slash',
                'folder-group': 'ui-folder-simple', 'dots-vertical': 'ui-dots-vertical',
                'lock-closed': 'ui-lock', 'lock-open': 'ui-unlock',
                'trash': 'ui-trash', 'copy': 'ui-copy', 'cut': 'ui-cut',
                'paste': 'ui-paste', 'open': 'ui-open', 'download': 'ui-download',
                'caret-right': 'ui-caret-right', 'caret-down': 'ui-caret-down',
                'check': 'ui-check', 'swap': 'ui-swap',
                'palette': 'palette',
                // Additional UI icons
                'link': 'ui-link', 'sparkle': 'sparkle',
                'import': 'ui-upload', 'upload': 'ui-upload',
                'resize': 'resize', 'invert': 'ui-swap',
                'merge': 'ui-layers', 'grid': 'ui-grid',
            };
            const file = svgMap[icon];
            if (file) {
                return `<img src="/static/icons/${file}.svg" class="phosphor-icon" alt="${icon}">`;
            }
            // Final fallback to HTML entity from EditorConfig
            return getIcon(icon);
        },
    },
};

export default FilterDialogManagerMixin;
