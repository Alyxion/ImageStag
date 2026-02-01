/**
 * Toolbar - Top toolbar with menus and quick actions.
 */
export class Toolbar {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.container = document.getElementById('toolbar');
        this.render();
        this.bindEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="toolbar-left">
                <div class="toolbar-menu">
                    <button class="toolbar-menu-btn" data-menu="file">File</button>
                    <button class="toolbar-menu-btn" data-menu="edit">Edit</button>
                    <button class="toolbar-menu-btn" data-menu="filter">Filter</button>
                </div>
            </div>
            <div class="toolbar-center">
                <!-- Spacer for layout balance -->
            </div>
            <div class="toolbar-right">
                <span class="toolbar-zoom" id="zoom-display">100%</span>
                <button class="toolbar-btn" id="zoom-fit" title="Fit to window">Fit</button>
                <button class="toolbar-btn" id="zoom-100" title="100%">1:1</button>
            </div>
        `;
    }

    bindEvents() {
        // Menu buttons
        this.container.querySelectorAll('.toolbar-menu-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.showMenu(e.target.dataset.menu, e.target));
        });

        // Zoom buttons
        document.getElementById('zoom-fit')?.addEventListener('click', () => {
            this.app.renderer.fitToViewport();
        });

        document.getElementById('zoom-100')?.addEventListener('click', () => {
            this.app.renderer.zoom = 1;
            this.app.renderer.updateDynamicLayerScale();
            this.app.renderer.centerCanvas();
            this.updateZoomDisplay();
        });

        // Listen for zoom changes
        this.app.eventBus.on('zoom:changed', () => this.updateZoomDisplay());
    }

    showMenu(menuId, anchor) {
        // Remove existing menu
        this.hideMenu();

        const menu = document.createElement('div');
        menu.className = 'toolbar-dropdown';
        menu.id = 'active-menu';

        const rect = anchor.getBoundingClientRect();
        menu.style.left = `${rect.left}px`;
        menu.style.top = `${rect.bottom}px`;

        switch (menuId) {
            case 'file':
                menu.innerHTML = this.getFileMenu();
                break;
            case 'edit':
                menu.innerHTML = this.getEditMenu();
                break;
            case 'filter':
                menu.innerHTML = this.getFilterMenu();
                break;
            case 'image':
                menu.innerHTML = this.getImageMenu();
                break;
        }

        document.body.appendChild(menu);

        // Add click handlers
        menu.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.handleMenuAction(e.target.dataset.action);
                this.hideMenu();
            });
        });

        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', this.hideMenuHandler = () => this.hideMenu(), { once: true });
        }, 0);
    }

    hideMenu() {
        const menu = document.getElementById('active-menu');
        if (menu) menu.remove();
    }

    getFileMenu() {
        return `
            <div class="menu-item" data-action="new">New Document</div>
            <div class="menu-separator"></div>
            <div class="menu-item" data-action="export-png">Export as PNG</div>
            <div class="menu-item" data-action="export-jpg">Export as JPEG</div>
        `;
    }

    getEditMenu() {
        const status = this.app.history.getStatus();
        return `
            <div class="menu-item ${status.canUndo ? '' : 'disabled'}" data-action="undo">Undo (Ctrl+Z)</div>
            <div class="menu-item ${status.canRedo ? '' : 'disabled'}" data-action="redo">Redo (Ctrl+Y)</div>
            <div class="menu-separator"></div>
            <div class="menu-item" data-action="clear-layer">Clear Layer</div>
        `;
    }

    getFilterMenu() {
        const filters = this.app.pluginManager.getAllFilters();
        const byCategory = {};

        for (const filter of filters) {
            const cat = filter.category || 'other';
            if (!byCategory[cat]) byCategory[cat] = [];
            byCategory[cat].push(filter);
        }

        let html = '';
        for (const [category, catFilters] of Object.entries(byCategory)) {
            html += `<div class="menu-header">${category}</div>`;
            for (const filter of catFilters) {
                const badge = filter.source === 'python' ? ' [Py]' : '';
                html += `<div class="menu-item" data-action="filter:${filter.id}">${filter.name}${badge}</div>`;
            }
        }

        return html || '<div class="menu-item disabled">No filters available</div>';
    }

    getImageMenu() {
        const sources = this.app.pluginManager.getImageSources();
        let html = '';

        for (const source of sources) {
            html += `<div class="menu-header">${source.name}</div>`;
            for (const image of source.images || []) {
                html += `<div class="menu-item" data-action="load:${source.id}:${image.id}">${image.name}</div>`;
            }
        }

        return html || '<div class="menu-item disabled">No images available</div>';
    }

    async handleMenuAction(action) {
        if (!action) return;

        if (action === 'new') {
            this.app.newDocument(800, 600);
        } else if (action === 'undo') {
            await this.app.history.undo();
        } else if (action === 'redo') {
            await this.app.history.redo();
        } else if (action === 'clear-layer') {
            const layer = this.app.layerStack.getActiveLayer();
            if (layer && !layer.locked) {
                this.app.history.saveState('Clear Layer');
                layer.clear();
                this.app.history.finishState();
                this.app.renderer.requestRender();
            }
        } else if (action === 'export-png') {
            this.exportImage('png');
        } else if (action === 'export-jpg') {
            this.exportImage('jpeg');
        } else if (action.startsWith('filter:')) {
            const filterId = action.slice(7);
            await this.applyFilter(filterId);
        } else if (action.startsWith('load:')) {
            const [, sourceId, imageId] = action.split(':');
            await this.loadImage(sourceId, imageId);
        }
    }

    async applyFilter(filterId) {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer || layer.locked) return;

        this.app.history.saveState('Filter');

        try {
            await this.app.pluginManager.applyFilter(filterId, layer);
            this.app.history.finishState();
        } catch (error) {
            console.error('Filter error:', error);
            this.app.history.abortCapture();
            alert(`Filter error: ${error.message}`);
        }
    }

    async loadImage(sourceId, imageId) {
        try {
            await this.app.pluginManager.loadSampleImage(sourceId, imageId);
        } catch (error) {
            console.error('Load error:', error);
            alert(`Failed to load image: ${error.message}`);
        }
    }

    exportImage(format) {
        const { compositeCanvas } = this.app.renderer;
        const mimeType = format === 'jpeg' ? 'image/jpeg' : 'image/png';
        const ext = format === 'jpeg' ? 'jpg' : 'png';

        const dataUrl = compositeCanvas.toDataURL(mimeType, 0.9);
        const link = document.createElement('a');
        link.download = `stagforge-export.${ext}`;
        link.href = dataUrl;
        link.click();
    }

    updateZoomDisplay() {
        const display = document.getElementById('zoom-display');
        if (display) {
            display.textContent = `${Math.round(this.app.renderer.zoom * 100)}%`;
        }
    }

    update() {
        this.updateZoomDisplay();
    }
}
