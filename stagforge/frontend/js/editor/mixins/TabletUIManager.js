/**
 * TabletUIManager Mixin
 *
 * Handles tablet-specific UI methods: panels, popups, menus, tool drag/drop.
 *
 * Required component data:
 *   - tabletLeftDrawerOpen, tabletNavPanelOpen, tabletLayersPanelOpen, etc.
 *   - tabletFileMenuOpen, tabletEditMenuOpen, etc.
 *   - tabletAllTools, toolDragIndex, toolDragOverIndex
 *   - tabletBrushSize, tabletOpacity, tabletHardness
 *   - tabletFontSize, tabletFontFamily, tabletFontWeight, tabletFontStyle
 *   - currentUIMode
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateToolProperty(): Update a tool property
 *   - openColorPicker(): Open the color picker
 *   - Various menu/action methods
 */
export const TabletUIManagerMixin = {
    methods: {
        /**
         * Close all side panels and drawers
         */
        closeAllPanels() {
            // Tools panel (tabletLeftDrawerOpen) stays pinned — only close right panels
            this.tabletNavPanelOpen = false;
            this.tabletLayersPanelOpen = false;
            this.tabletHistoryPanelOpen = false;
            this.tabletFilterPanelOpen = false;
            this.tabletExpandedToolGroup = null;
        },

        /**
         * Toggle a tablet popup menu
         * @param {string} which - Which popup to toggle (file, edit, view, image, zoom)
         */
        toggleTabletPopup(which) {
            // Close all other popups first (including color picker)
            const popups = ['file', 'edit', 'view', 'image', 'zoom'];
            for (const p of popups) {
                if (p !== which) {
                    this[`tablet${p.charAt(0).toUpperCase() + p.slice(1)}MenuOpen`] = false;
                }
            }
            this.tabletColorPickerOpen = false;

            // Toggle the requested popup
            switch (which) {
                case 'file':
                    this.tabletFileMenuOpen = !this.tabletFileMenuOpen;
                    break;
                case 'edit':
                    this.tabletEditMenuOpen = !this.tabletEditMenuOpen;
                    break;
                case 'view':
                    this.tabletViewMenuOpen = !this.tabletViewMenuOpen;
                    break;
                case 'filter':
                    this.tabletFilterPanelOpen = !this.tabletFilterPanelOpen;
                    // Load filter previews when opening the panel
                    if (this.tabletFilterPanelOpen) {
                        this.loadAllFilterPreviews();
                    }
                    break;
                case 'image':
                    this.tabletImageMenuOpen = !this.tabletImageMenuOpen;
                    break;
                case 'zoom':
                    this.tabletZoomMenuOpen = !this.tabletZoomMenuOpen;
                    break;
            }
        },

        /**
         * Close all tablet popups and panels
         */
        closeAllTabletPopups() {
            this.tabletFileMenuOpen = false;
            this.tabletEditMenuOpen = false;
            this.tabletViewMenuOpen = false;
            this.tabletImageMenuOpen = false;
            this.tabletZoomMenuOpen = false;
            this.tabletColorPickerOpen = false;

            // Close non-pinned panels/drawers
            this.closeAllPanels();
        },

        /**
         * Toggle a side panel
         * @param {string} which - Which panel to toggle
         */
        toggleSidePanel(which) {
            const openKey = `tablet${which.charAt(0).toUpperCase() + which.slice(1)}PanelOpen`;
            this[openKey] = !this[openKey];

            // Track active panel for focus handling
            if (this[openKey]) {
                this._activeSidePanel = which;
            } else {
                this._activeSidePanel = null;
            }

            // Persist panel visibility state
            this.savePanelState();
        },

        /**
         * Set focus to a side panel
         * @param {string} which - Which panel to focus
         */
        focusSidePanel(which) {
            this._activeSidePanel = which;
        },

        /**
         * Close a specific side panel
         * @param {string} which - Which panel to close
         */
        closeSidePanel(which) {
            const openKey = `tablet${which.charAt(0).toUpperCase() + which.slice(1)}PanelOpen`;
            this[openKey] = false;
            if (this._activeSidePanel === which) {
                this._activeSidePanel = null;
            }
        },

        /**
         * Handle global click events to close panels
         * @param {Event} event - Click event
         */
        handleGlobalClick(event) {
            if (this.currentUIMode !== 'tablet') return;

            // Check if click was inside any dock stack
            const path = event.composedPath();
            const clickedDock = path.some(el => el.classList && (
                el.classList.contains('tablet-dock-stack') ||
                el.classList.contains('tablet-dock-icon') ||
                el.classList.contains('tablet-dock-panel')
            ));
            if (clickedDock) return;

            // Don't close panels when clicking on canvas
            const clickedCanvas = path.some(el =>
                el.classList && el.classList.contains('canvas-container') ||
                el.tagName === 'CANVAS'
            );
            if (clickedCanvas) return;

            // Don't close panels when clicking on floating panels or menus
            const clickedFloating = path.some(el => el.classList && (
                el.classList.contains('tablet-floating-panel') ||
                el.classList.contains('tablet-menu-popup') ||
                el.classList.contains('tablet-top-bar') ||
                el.classList.contains('tablet-bottom-bar')
            ));
            if (clickedFloating) return;

            // Close flyout and right dock panels (tools panel stays pinned)
            this.tabletExpandedToolGroup = null;
            this.tabletNavPanelOpen = false;
            this.tabletLayersPanelOpen = false;
            this.tabletHistoryPanelOpen = false;
        },

        /**
         * Load a single filter preview — tries WASM first, then backend API.
         * @param {string} filterId - Filter identifier
         */
        async loadFilterPreview(filterId) {
            if (this.filterPreviews[filterId] || this.filterPreviewsLoading[filterId]) {
                return;
            }

            this.filterPreviewsLoading[filterId] = true;

            try {
                // Try client-side WASM preview first
                const app = this.getState();
                const wasmEngine = app?.pluginManager?.wasmEngine;
                if (wasmEngine?.ready && wasmEngine.hasFilter(filterId)) {
                    const dataUrl = this._generateWasmPreview(wasmEngine, filterId);
                    if (dataUrl) {
                        this.filterPreviews[filterId] = dataUrl;
                        return;
                    }
                }

                // Fall back to backend API
                const response = await fetch(`/api/filters/${filterId}/preview`);
                if (response.ok) {
                    const data = await response.json();
                    this.filterPreviews[filterId] = data.preview;
                }
            } catch (err) {
                // Silently ignore — preview is optional
            } finally {
                this.filterPreviewsLoading[filterId] = false;
            }
        },

        /**
         * Generate a filter preview thumbnail using the WASM engine.
         * Creates a small gradient sample image, applies the filter, returns a data URL.
         * @param {Object} wasmEngine - WasmFilterEngine instance
         * @param {string} filterId - Filter identifier
         * @returns {string|null} Data URL or null on failure
         */
        _generateWasmPreview(wasmEngine, filterId) {
            const size = 64;

            // Create a sample image with a color gradient
            if (!this._previewSampleCanvas) {
                const c = document.createElement('canvas');
                c.width = size;
                c.height = size;
                const ctx = c.getContext('2d');

                // Draw a gradient with some structure (colors + edges for edge filters)
                const grad = ctx.createLinearGradient(0, 0, size, size);
                grad.addColorStop(0, '#e74c3c');
                grad.addColorStop(0.33, '#f39c12');
                grad.addColorStop(0.66, '#2ecc71');
                grad.addColorStop(1, '#3498db');
                ctx.fillStyle = grad;
                ctx.fillRect(0, 0, size, size);

                // Add a circle for edge/shape detection filters
                ctx.beginPath();
                ctx.arc(size / 2, size / 2, size / 4, 0, Math.PI * 2);
                ctx.fillStyle = '#ffffff';
                ctx.fill();

                this._previewSampleCanvas = c;
                this._previewSampleData = ctx.getImageData(0, 0, size, size);
            }

            try {
                // Copy sample data so WASM doesn't corrupt the original
                const copy = new ImageData(
                    new Uint8ClampedArray(this._previewSampleData.data),
                    this._previewSampleData.width,
                    this._previewSampleData.height
                );
                const result = wasmEngine.applyFilter(filterId, copy, {});
                const c = document.createElement('canvas');
                c.width = result.width;
                c.height = result.height;
                c.getContext('2d').putImageData(result, 0, 0);
                return c.toDataURL('image/png');
            } catch (e) {
                return null;
            }
        },

        /**
         * Load previews for all filters in the current tab
         */
        async loadAllFilterPreviews() {
            for (const filter of this.filtersInCurrentTab) {
                if (!this.filterPreviews[filter.id]) {
                    this.loadFilterPreview(filter.id);
                }
            }
        },

        /**
         * Switch filter tab and load previews
         * @param {string} category - Filter category
         */
        switchFilterTab(category) {
            this.tabletFilterTab = category;
            this.$nextTick(() => {
                this.loadAllFilterPreviews();
            });
        },

        // ==================== Tool Drag/Drop Methods ====================

        /**
         * Handle tool drag start
         * @param {number} index - Tool index
         * @param {DragEvent} event - Drag event
         */
        onToolDragStart(index, event) {
            this.toolDragIndex = index;
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', index.toString());
            event.target.classList.add('dragging');
        },

        /**
         * Handle tool drag over
         * @param {number} index - Target index
         * @param {DragEvent} event - Drag event
         */
        onToolDragOver(index, event) {
            if (this.toolDragIndex === null || this.toolDragIndex === index) return;
            this.toolDragOverIndex = index;
            event.dataTransfer.dropEffect = 'move';
        },

        /**
         * Handle tool drag leave
         */
        onToolDragLeave() {
            this.toolDragOverIndex = null;
        },

        /**
         * Handle tool drop
         * @param {number} targetIndex - Drop target index
         */
        onToolDrop(targetIndex) {
            if (this.toolDragIndex === null || this.toolDragIndex === targetIndex) return;

            // Reorder the tools array
            const tool = this.tabletAllTools.splice(this.toolDragIndex, 1)[0];
            this.tabletAllTools.splice(targetIndex, 0, tool);

            // Save custom order to localStorage
            this.saveToolOrder();

            // Reset drag state
            this.toolDragIndex = null;
            this.toolDragOverIndex = null;
        },

        /**
         * Handle tool drag end
         * @param {DragEvent} event - Drag event
         */
        onToolDragEnd(event) {
            event.target.classList.remove('dragging');
            this.toolDragIndex = null;
            this.toolDragOverIndex = null;
        },

        /**
         * Save tool order to localStorage
         */
        saveToolOrder() {
            try {
                const order = this.tabletAllTools.map(t => t.id);
                localStorage.setItem('stagforge-tool-order', JSON.stringify(order));
            } catch (e) {
                console.warn('Could not save tool order:', e);
            }
        },

        /**
         * Load tool order from localStorage
         */
        loadToolOrder() {
            try {
                const saved = localStorage.getItem('stagforge-tool-order');
                if (saved) {
                    const order = JSON.parse(saved);
                    const orderedTools = [];
                    const remainingTools = [...this.tabletAllTools];

                    for (const id of order) {
                        const idx = remainingTools.findIndex(t => t.id === id);
                        if (idx !== -1) {
                            orderedTools.push(remainingTools.splice(idx, 1)[0]);
                        }
                    }
                    // Add any new tools that weren't in saved order
                    this.tabletAllTools = [...orderedTools, ...remainingTools];
                }
            } catch (e) {
                console.warn('Could not load tool order:', e);
            }
        },

        /**
         * Show tablet zoom menu (legacy)
         */
        showTabletZoomMenu() {
            this.toggleTabletPopup('zoom');
        },

        /**
         * Handle tablet menu actions
         * @param {string} action - Action name
         * @param {*} param - Optional parameter
         */
        tabletMenuAction(action, param) {
            // Close all menu popups
            this.tabletFileMenuOpen = false;
            this.tabletEditMenuOpen = false;
            this.tabletViewMenuOpen = false;
            this.tabletImageMenuOpen = false;
            switch (action) {
                // File actions
                case 'new':
                    this.showNewDocumentDialog();
                    break;
                case 'new_from_clipboard':
                    this.newFromClipboard();
                    break;
                case 'open':
                    this.fileOpen();
                    break;
                case 'save':
                    this.fileSave();
                    break;
                case 'saveAs':
                    this.fileSaveAs();
                    break;
                case 'saveAsSVG':
                    this.fileSaveAsSVG();
                    break;
                case 'loadSample':
                    if (param) this.loadSampleImage(param);
                    break;
                case 'export':
                    this.menuAction('export');
                    break;
                case 'export_as':
                    this.showExportDialog();
                    break;
                case 'export_again':
                    this.exportAgain();
                    break;
                // Edit actions
                case 'undo':
                    this.undo();
                    break;
                case 'redo':
                    this.redo();
                    break;
                case 'cut':
                    this.cutSelection();
                    break;
                case 'copy':
                    this.copySelection();
                    break;
                case 'paste':
                    this.pasteSelection();
                    break;
                case 'pasteInPlace':
                    this.pasteInPlace();
                    break;
                case 'selectAll':
                    this.selectAll();
                    break;
                case 'deselect':
                    this.deselect();
                    break;
                // Image actions
                case 'flipH':
                    this.flipHorizontal();
                    break;
                case 'flipV':
                    this.flipVertical();
                    break;
                case 'rotate90':
                    this.rotate(90);
                    break;
                case 'rotate-90':
                    this.rotate(-90);
                    break;
                case 'resize':
                    this.showResizeDialog();
                    break;
                case 'canvas_size':
                    this.showCanvasSizeDialog();
                    break;
                case 'flatten':
                    this.menuAction('flatten');
                    break;
                // View actions
                case 'desktop':
                    this.setUIMode('desktop');
                    break;
                case 'limited':
                    this.setUIMode('limited');
                    break;
                case 'toggleTheme':
                    this.toggleTheme();
                    break;
            }
        },

        /**
         * Update tablet navigator canvas — delegates to unified updateNavigator()
         */
        updateTabletNavigator() {
            this.updateNavigator();
        },

        /**
         * Update tablet hardness slider
         * @param {string|number} value - Hardness value (0-100)
         */
        updateTabletHardness(value) {
            this.tabletHardness = parseInt(value);
            this.updateToolProperty('hardness', this.tabletHardness / 100);
        },

        // ==================== Limited Mode Methods ====================

        /**
         * Get display name for a tool
         * @param {string} toolId - Tool identifier
         * @returns {string} Display name
         */
        getToolName(toolId) {
            const toolNames = {
                brush: 'Brush',
                eraser: 'Eraser',
                pencil: 'Pencil',
                fill: 'Fill',
                line: 'Line',
                rect: 'Rectangle',
                circle: 'Ellipse',
                spray: 'Spray',
                eyedropper: 'Eyedropper'
            };
            return toolNames[toolId] || toolId;
        },

        /**
         * Get icon ID for a tool
         * @param {string} toolId - Tool identifier
         * @returns {string} Icon ID
         */
        getToolIconId(toolId) {
            const iconMap = {
                brush: 'brush',
                eraser: 'eraser',
                pencil: 'pencil',
                fill: 'fill',
                line: 'line',
                rect: 'square',
                circle: 'circle',
                spray: 'spray',
                eyedropper: 'eyedropper'
            };
            return iconMap[toolId] || toolId;
        },

        /**
         * Open color picker in limited mode
         */
        openLimitedColorPicker() {
            this.openColorPicker('fg', { target: { getBoundingClientRect: () => ({ left: 16, bottom: 150 }) } });
        },

        // ==================== Tablet Tool Property Methods ====================

        /**
         * Update tablet brush size
         * @param {string|number} value - Size value
         */
        updateTabletBrushSize(value) {
            this.tabletBrushSize = parseInt(value);
            this.updateToolProperty('size', this.tabletBrushSize);
        },

        /**
         * Update tablet opacity
         * @param {string|number} value - Opacity value (0-100)
         */
        updateTabletOpacity(value) {
            this.tabletOpacity = parseInt(value);
            this.updateToolProperty('opacity', this.tabletOpacity / 100);
        },

        /**
         * Update tablet font size
         * @param {string|number} value - Font size
         */
        updateTabletFontSize(value) {
            this.tabletFontSize = parseInt(value);
            this.updateToolProperty('fontSize', this.tabletFontSize);
        },

        /**
         * Update tablet font family
         * @param {string} value - Font family name
         */
        updateTabletFontFamily(value) {
            this.tabletFontFamily = value;
            this.updateToolProperty('fontFamily', value);
        },

        /**
         * Toggle tablet font weight
         */
        toggleTabletFontWeight() {
            this.tabletFontWeight = this.tabletFontWeight === 'bold' ? 'normal' : 'bold';
            this.updateToolProperty('fontWeight', this.tabletFontWeight);
        },

        /**
         * Toggle tablet font style
         */
        toggleTabletFontStyle() {
            this.tabletFontStyle = this.tabletFontStyle === 'italic' ? 'normal' : 'italic';
            this.updateToolProperty('fontStyle', this.tabletFontStyle);
        },

        /**
         * Sync tablet UI with current tool properties
         */
        syncTabletToolProperties() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (tool) {
                // Size
                if (tool.size !== undefined) {
                    this.tabletBrushSize = tool.size;
                    this.tabletShowSize = true;
                } else {
                    this.tabletShowSize = false;
                }

                // Opacity
                if (tool.opacity !== undefined) {
                    this.tabletOpacity = Math.round(tool.opacity * 100);
                    this.tabletShowOpacity = true;
                } else {
                    this.tabletShowOpacity = false;
                }

                // Hardness
                if (tool.hardness !== undefined) {
                    this.tabletHardness = Math.round(tool.hardness * 100);
                    this.tabletShowHardness = true;
                } else {
                    this.tabletShowHardness = false;
                }

                // Text tool properties
                if (tool.constructor.id === 'text') {
                    this.tabletShowTextProps = true;
                    this.tabletFontSize = tool.fontSize || 24;
                    this.tabletFontFamily = tool.fontFamily || 'Arial';
                    this.tabletFontWeight = tool.fontWeight || 'normal';
                    this.tabletFontStyle = tool.fontStyle || 'normal';
                } else {
                    this.tabletShowTextProps = false;
                }
            }

            // Update tablet navigator if nav panel is open
            if (this.tabletNavPanelOpen) {
                this.$nextTick(() => this.updateNavigator());
            }
        },

        /**
         * Placeholder for panel dragging functionality
         * @param {string} panelId - Panel identifier
         * @param {Event} event - Drag event
         */
        startPanelDrag(panelId, event) {
            // Placeholder for future panel dragging functionality
        },
    },
};

export default TabletUIManagerMixin;
