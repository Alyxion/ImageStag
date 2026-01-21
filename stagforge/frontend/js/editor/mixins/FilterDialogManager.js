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
                     param.type === 'checkbox' ? false : '');
            }

            this.currentFilter = filter;
            this.filterDialogVisible = true;
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
                if (render) {
                    app.renderer.requestRender();
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
         * Apply filter directly without dialog
         * @param {Object} filter - Filter configuration
         */
        async applyFilterDirect(filter) {
            const app = this.getState();
            if (!app) return;

            app.history.saveState('Filter: ' + filter.name);
            this.statusMessage = 'Applying ' + filter.name + '...';

            try {
                await this.applyFilterToLayer(filter.id, {}, true);
                app.history.finishState();
                this.statusMessage = filter.name + ' applied';
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
            app.history.saveState('Filter: ' + this.currentFilter.name);
            app.history.finishState();

            this.statusMessage = this.currentFilter.name + ' applied';
            this.filterDialogVisible = false;
            this.currentFilter = null;
            this.filterPreviewState = null;
        },

        /**
         * Cancel filter dialog and restore original state
         */
        cancelFilterDialog() {
            // Restore original state
            this.restoreFilterPreviewState();

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

            // Create binary payload
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
            const resultImageData = new ImageData(
                new Uint8ClampedArray(resultBytes),
                imageData.width,
                imageData.height
            );

            // Put result back at the correct position (selection offset)
            layer.ctx.putImageData(resultImageData, filterX, filterY);

            if (renderAfter) {
                app.renderer.requestRender();
            }
        },

        // ==================== Rasterize Dialog Methods ====================

        /**
         * Confirm rasterize and execute callback
         */
        confirmRasterize() {
            const app = this.getState();
            if (!app || !this.rasterizeLayerId) {
                this.cancelRasterize();
                return;
            }

            // Save state before rasterizing
            app.history.saveState('Rasterize Layer');

            // Rasterize the layer
            app.layerStack.rasterizeLayer(this.rasterizeLayerId);
            app.renderer.requestRender();

            app.history.finishState();

            // Update layers display
            this.updateLayerList();

            // Call the callback
            const callback = this.rasterizeCallback;
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
            }
            this.preferencesDialogVisible = true;
        },

        /**
         * Close preferences dialog without saving
         */
        closePreferencesDialog() {
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
            }
            this.preferencesDialogVisible = false;

            // Re-render any vector layers with new settings
            this.reRenderVectorLayers();
        },

        /**
         * Re-render all vector layers with current settings
         */
        async reRenderVectorLayers() {
            const app = this.getState();
            if (!app?.layerStack) return;

            for (const layer of app.layerStack.layers) {
                if (layer.type === 'vector' && layer.renderFinal) {
                    await layer.renderFinal();
                }
            }
            app.renderer?.requestRender();
        },

        // ==================== Tool Icon Lookup ====================

        /**
         * Get HTML entity for tool or UI icon
         * Checks tool icons first, then falls back to UI icons
         * @param {string} icon - Icon identifier
         * @returns {string} HTML entity
         */
        getToolIcon(icon) {
            // Check tool icons first (auto-discovered from tools)
            if (toolIcons[icon]) {
                return toolIcons[icon];
            }
            // Fall back to UI icons from EditorConfig
            return getIcon(icon);
        },
    },
};

export default FilterDialogManagerMixin;
