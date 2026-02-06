/**
 * MenuManager Mixin
 *
 * Handles menu bar interactions: file, edit, view, filter, image menus.
 * Also handles menu actions and positioning.
 *
 * Required component data:
 *   - activeMenu: String|null
 *   - menuPosition: Object { top, left }
 *   - colorPickerVisible: Boolean
 *   - tabletColorPickerOpen: Boolean
 *   - showBrushPresetMenu: Boolean
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - newDocument(width, height): Creates new document
 *   - fileOpen(): Opens a document
 *   - fileSave(): Saves document
 *   - fileSaveAs(): Saves document as new file
 *   - loadSampleImage(img): Loads a sample image
 *   - exportPNG(): Exports document as PNG
 *   - clipboardCut/Copy/Paste/PasteInPlace(): Clipboard operations
 *   - selectAll/deselect(): Selection operations
 *   - updateLayerList(): Updates layer panel
 *   - applyFilter(id, params): Applies a filter
 *   - zoomIn/zoomOut/fitToView(): Zoom operations
 *   - setZoomPercent(percent): Sets zoom level
 *   - updateNavigator(): Updates navigator panel
 *   - updateHistoryState(): Refreshes history state
 */
export const MenuManagerMixin = {
    methods: {
        /**
         * Show the File menu dropdown
         * @param {Event} e - Click event
         */
        showFileMenu(e) {
            this.showMenu('file', e);
        },

        /**
         * Show the Edit menu dropdown
         * @param {Event} e - Click event
         */
        showEditMenu(e) {
            this.updateHistoryState(); // Refresh history state for menu
            this.showMenu('edit', e);
        },

        /**
         * Show the Filter menu dropdown
         * @param {Event} e - Click event
         */
        showFilterMenu(e) {
            this.showMenu('filter', e);
        },

        /**
         * Show the Image menu dropdown
         * @param {Event} e - Click event
         */
        showImageMenu(e) {
            this.showMenu('image', e);
        },

        /**
         * Show the View menu dropdown
         * @param {Event} e - Click event
         */
        showViewMenu(e) {
            this.showMenu('view', e);
        },

        /**
         * Show the Layer menu dropdown
         * @param {Event} e - Click event
         */
        showLayerMenu(e) {
            this.showMenu('layer', e);
        },

        /**
         * Show the Select menu dropdown
         * @param {Event} e - Click event
         */
        showSelectMenu(e) {
            this.showMenu('select', e);
        },

        /**
         * Generic menu display handler
         * @param {string} menu - Menu identifier
         * @param {Event} e - Click event for positioning
         */
        showMenu(menu, e) {
            e.stopPropagation();
            const rect = e.target.getBoundingClientRect();
            this.menuPosition = {
                top: rect.bottom + 'px',
                left: rect.left + 'px',
            };
            this.activeMenu = this.activeMenu === menu ? null : menu;
        },

        /**
         * Close all open menus
         * @param {Event} event - Optional click event to check target
         */
        closeMenu(event) {
            // Don't close menus if clicking inside them
            if (event && event.target) {
                // Check if click is inside brush preset dropdown or menu
                const brushDropdown = event.target.closest('.brush-preset-dropdown');
                const brushMenu = event.target.closest('.brush-preset-menu');
                if (brushDropdown || brushMenu) {
                    return; // Don't close, let the specific handler manage it
                }

                // Check if click is inside other menus
                const menuBar = event.target.closest('.menu-bar');
                const colorPicker = event.target.closest('.color-picker-popup');
                const tabletColorPicker = event.target.closest('.tablet-color-picker-popup');
                const addLayerMenu = event.target.closest('.add-layer-menu');
                const libraryDialog = event.target.closest('.library-dialog');
                if (menuBar || colorPicker || tabletColorPicker || addLayerMenu || libraryDialog) {
                    return;
                }
            }

            this.activeMenu = null;
            this.colorPickerVisible = false;
            this.tabletColorPickerOpen = false;
            this.showBrushPresetMenu = false;
            this.showAddLayerMenu = false;
            // Note: Don't close libraryDialogOpen here - it has its own close button/overlay
        },

        /**
         * Handle menu action selection
         * @param {string} action - Action identifier
         * @param {*} data - Optional action data
         */
        async menuAction(action, data) {
            this.closeMenu();
            const app = this.getState();

            switch (action) {
                case 'new':
                    this.showNewDocDialog();
                    break;
                case 'new_from_clipboard':
                    await this.newFromClipboard();
                    break;
                case 'open':
                    this.fileOpen();
                    break;
                case 'recent_documents':
                    this.welcomeFilter = 'recent';
                    this.activateHome();
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
                case 'load':
                    if (data) await this.loadSampleImage(data);
                    break;
                case 'export':
                    this.exportPNG();
                    break;
                case 'export_as':
                    this.showExportDialog();
                    break;
                case 'export_again':
                    this.exportAgain();
                    break;
                case 'undo':
                    app?.history?.undo();
                    break;
                case 'redo':
                    app?.history?.redo();
                    break;
                case 'cut':
                    this.clipboardCut();
                    break;
                case 'copy':
                    this.clipboardCopy();
                    break;
                case 'copy_merged':
                    this.clipboardCopyMerged();
                    break;
                case 'paste':
                    this.clipboardPaste();
                    break;
                case 'paste_in_place':
                    this.clipboardPasteInPlace();
                    break;
                case 'select_all':
                    this.selectAll();
                    break;
                case 'deselect':
                    this.deselect();
                    break;
                case 'reselect':
                    this.reselect();
                    break;
                case 'invert_selection':
                    this.invertSelection();
                    break;
                case 'delete_selection':
                    this.deleteSelection();
                    break;
                case 'fill_fg':
                    this.fillSelectionWithColor(this.getState()?.foregroundColor || '#000000');
                    break;
                case 'fill_bg':
                    this.fillSelectionWithColor(this.getState()?.backgroundColor || '#FFFFFF');
                    break;
                case 'filter':
                    if (data) await this.applyFilter(data.id, {});
                    break;
                case 'flatten':
                    app?.history?.saveState('Flatten Image');
                    app?.layerStack?.flattenAll();
                    this.updateLayerList();
                    break;
                case 'zoom_in':
                    this.zoomIn();
                    this.updateNavigator();
                    break;
                case 'zoom_out':
                    this.zoomOut();
                    this.updateNavigator();
                    break;
                case 'zoom_fit':
                    this.fitToView();
                    this.updateNavigator();
                    break;
                case 'zoom_100':
                    this.setZoomPercent(100);
                    break;
                case 'resize':
                    this.showResizeDialog();
                    break;
                case 'canvas_size':
                    this.showCanvasSizeDialog();
                    break;
                case 'transform':
                    this.showTransformDialog();
                    break;
                case 'reset_transform':
                    this.resetTransform();
                    break;
            }
        },

        /**
         * Rotate the canvas/document by specified degrees
         * @param {number} degrees - 90, 180, or 270
         */
        async rotateCanvas(degrees) {
            const app = this.getState();
            if (!app) return;

            const doc = app.documentManager?.getActiveDocument();
            if (!doc) return;

            // Use structural change pattern for proper undo (document dimensions change)
            app.history?.beginCapture(`Rotate ${degrees}°`, []);
            app.history?.beginStructuralChange();

            // Store all layers that will be modified during rotation
            // - Raster layers: pixel data is transposed
            // - Vector layers: shape coordinates are transformed
            // - SVG layers: rendered canvas is transposed
            // - Text layers: only rotation property changes (handled via layerMeta)
            for (const layer of doc.layerStack.layers) {
                // Skip groups
                if (layer.isGroup && layer.isGroup()) continue;
                // Text layers only change rotation property - handled by layerMeta
                if (layer.isText?.()) continue;
                // SVG layers have rendered canvas transposed - need full state
                if (layer.isSVG?.()) {
                    await app.history?.storeResizedLayer(layer);
                    continue;
                }
                // Raster layers have pixel data transposed - need full state
                if (layer.canvas instanceof HTMLCanvasElement) {
                    await app.history?.storeResizedLayer(layer);
                }
            }

            await doc.rotateCanvas(degrees);

            // Update app dimensions to match rotated document
            app.width = doc.width;
            app.height = doc.height;

            // Update renderer's composite canvas dimensions to match new document size
            app.renderer?.resize(doc.width, doc.height);

            // Re-center the canvas after rotation
            app.renderer?.centerCanvas();

            app.history?.commitCapture();

            this.updateLayerList();
            this.updateNavigator();
            this.closeMenu();
        },

        /**
         * Flip the canvas horizontally (convenience wrapper for mirrorCanvas).
         */
        async flipHorizontal() {
            await this.mirrorCanvas('horizontal');
        },

        /**
         * Flip the canvas vertically (convenience wrapper for mirrorCanvas).
         */
        async flipVertical() {
            await this.mirrorCanvas('vertical');
        },

        /**
         * Mirror the canvas/document horizontally or vertically
         * @param {'horizontal' | 'vertical'} direction - Mirror direction
         */
        async mirrorCanvas(direction) {
            const app = this.getState();
            if (!app) return;

            const doc = app.documentManager?.getActiveDocument();
            if (!doc) return;

            // Use structural change pattern for proper undo
            app.history?.beginCapture(`Mirror ${direction}`, []);
            app.history?.beginStructuralChange();

            // Store all layers that will be modified during mirroring
            for (const layer of doc.layerStack.layers) {
                // Skip groups
                if (layer.isGroup && layer.isGroup()) continue;
                // Text layers use scaleX/scaleY - handled by layerMeta
                if (layer.isText?.()) continue;
                // SVG layers modify svgContent - need full state
                if (layer.isSVG?.()) {
                    await app.history?.storeResizedLayer(layer);
                    continue;
                }
                // Raster layers flip pixel data - need full state
                if (layer.canvas instanceof HTMLCanvasElement) {
                    await app.history?.storeResizedLayer(layer);
                }
            }

            await doc.mirrorCanvas(direction);

            app.history?.commitCapture();

            this.updateLayerList();
            this.updateNavigator();
            this.closeMenu();
        },
    },
};

export default MenuManagerMixin;
