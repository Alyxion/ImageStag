/**
 * FilterManager Mixin
 *
 * Handles the dynamic filters panel UI: showing/hiding the panel,
 * toggling filters, rendering filter parameters, and filter editing.
 * Follows the same pattern as EffectsManager.
 *
 * Required component data:
 *   - _filterLayer: Object (internal)
 *   - _filterLayerId: String (internal)
 *   - _filtersBefore: Array (internal)
 *   - _selectedFilterId: String (internal)
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - makePanelDraggable(element, handle): Makes a panel draggable
 */
import { DynamicFilter } from '/static/js/core/DynamicFilter.js';
import { renderFilterParams } from './FilterParamsRenderer.js';
import { getCategoryName, filterCategoryOrder } from '/static/js/config/EditorConfig.js';

export const FilterManagerMixin = {
    methods: {
        /**
         * Show the dynamic filters panel for the active layer.
         */
        showFilterPanel() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const layer = app.layerStack.getActiveLayer();
            if (!layer) return;

            // Remove existing panels
            document.getElementById('filter-panel')?.remove();

            // Capture initial filters state for history diff
            this._filterLayerId = layer.id;
            this._filtersBefore = layer.filters ? layer.filters.map(f => typeof f.serialize === 'function' ? f.serialize() : { ...f }) : [];

            const panel = document.createElement('div');
            panel.id = 'filter-panel';
            panel.className = 'filter-panel';
            panel.innerHTML = `
                <div class="filter-panel-header">
                    <span id="filter-panel-title">Layer Filters - ${layer.name}</span>
                    <button class="filter-panel-close">&times;</button>
                </div>
                <div class="filter-panel-body">
                    <div class="filter-list-pane">
                        <div class="filter-list" id="filter-list"></div>
                        <div class="filter-toolbar">
                            <button class="filter-toolbar-btn" id="filter-add" title="Add Filter">+</button>
                            <button class="filter-toolbar-btn" id="filter-move-up" title="Move Up">&uarr;</button>
                            <button class="filter-toolbar-btn" id="filter-move-down" title="Move Down">&darr;</button>
                            <button class="filter-toolbar-btn" id="filter-delete" title="Delete"><img src="/static/icons/ui-trash.svg" class="phosphor-icon" alt="delete"></button>
                        </div>
                    </div>
                    <div class="filter-props-pane" id="filter-props">
                        <div class="filter-props-empty">Select a filter to edit parameters</div>
                    </div>
                </div>
                <div class="filter-panel-footer">
                    <button class="btn-ok" id="filter-panel-ok">OK</button>
                </div>
            `;

            document.body.appendChild(panel);

            // Center panel
            panel.style.left = ((window.innerWidth - 540) / 2) + 'px';
            panel.style.top = ((window.innerHeight - 420) / 2) + 'px';

            // Make draggable
            this.makePanelDraggable(panel, panel.querySelector('.filter-panel-header'));

            // Store references
            this._filterLayer = layer;
            this._selectedFilterId = null;

            // Render the filter list
            this._renderFilterList();

            // Bind toolbar events
            panel.querySelector('#filter-add').addEventListener('click', (e) => {
                this._showAddFilterMenu(e.target);
            });
            panel.querySelector('#filter-move-up').addEventListener('click', () => {
                this._moveSelectedFilter(-1);
            });
            panel.querySelector('#filter-move-down').addEventListener('click', () => {
                this._moveSelectedFilter(1);
            });
            panel.querySelector('#filter-delete').addEventListener('click', () => {
                this._deleteSelectedFilter();
            });

            // Close/OK
            const closePanel = () => {
                this._commitFilterHistory();
                panel.remove();
                // Remove any lingering add-filter menus
                document.getElementById('filter-add-menu')?.remove();
            };
            panel.querySelector('.filter-panel-close').addEventListener('click', closePanel);
            panel.querySelector('#filter-panel-ok').addEventListener('click', closePanel);
        },

        /**
         * Render the filter list in the left pane.
         */
        _renderFilterList() {
            const list = document.getElementById('filter-list');
            if (!list) return;

            const layer = this._filterLayer;
            if (!layer || !layer.filters || layer.filters.length === 0) {
                list.innerHTML = '<div class="filter-list-empty">No filters applied</div>';
                return;
            }

            list.innerHTML = layer.filters.map(f => `
                <div class="filter-row ${f.enabled ? 'enabled' : ''} ${f.id === this._selectedFilterId ? 'selected' : ''}"
                     data-filter-id="${f.id}">
                    <input type="checkbox" class="filter-checkbox" ${f.enabled ? 'checked' : ''}>
                    <span class="filter-label">${f.name}</span>
                </div>
            `).join('');

            // Bind events
            list.querySelectorAll('.filter-row').forEach(row => {
                const filterId = row.dataset.filterId;
                const checkbox = row.querySelector('.filter-checkbox');

                checkbox.addEventListener('change', (e) => {
                    e.stopPropagation();
                    const filter = layer.getFilter(filterId);
                    if (filter) {
                        filter.enabled = checkbox.checked;
                        row.classList.toggle('enabled', checkbox.checked);
                        layer.invalidateFilterCache();
                    }
                });

                row.addEventListener('click', (e) => {
                    if (e.target === checkbox) return;
                    this._selectFilter(filterId);
                });
            });
        },

        /**
         * Select a filter for editing in the right pane.
         * @param {string} filterId
         */
        _selectFilter(filterId) {
            this._selectedFilterId = filterId;
            const layer = this._filterLayer;
            const filter = layer?.getFilter(filterId);

            // Update selection UI
            document.querySelectorAll('#filter-list .filter-row').forEach(row => {
                row.classList.toggle('selected', row.dataset.filterId === filterId);
            });

            // Update header title to show selected filter
            const titleEl = document.getElementById('filter-panel-title');
            const layerName = this._filterLayer?.name || 'Layer';
            if (titleEl) {
                titleEl.textContent = filter
                    ? `Layer Filters - ${layerName} - ${filter.name}`
                    : `Layer Filters - ${layerName}`;
            }

            const propsPane = document.getElementById('filter-props');
            if (!propsPane || !filter) {
                if (propsPane) {
                    propsPane.innerHTML = '<div class="filter-props-empty">Select a filter to edit parameters</div>';
                }
                return;
            }

            // Get filter definition from PluginManager
            const app = this.getState();
            const allFilters = app?.pluginManager?.getAllFilters() || [];
            const filterDef = allFilters.find(f => f.id === filter.filterId);

            if (!filterDef || !filterDef.params || filterDef.params.length === 0) {
                propsPane.innerHTML = `
                    <div class="filter-props-empty">No adjustable parameters</div>
                `;
                return;
            }

            const { html, bindEvents } = renderFilterParams(filterDef, filter.params, { embedded: true });

            propsPane.innerHTML = `
                <div class="filter-props-content">${html}</div>
            `;

            bindEvents(propsPane.querySelector('.filter-props-content'), (paramId, value) => {
                // Parameter changed — invalidate cache
                layer.invalidateFilterCache();
            });
        },

        /**
         * Show the add-filter dropdown menu.
         * @param {HTMLElement} anchor
         */
        _showAddFilterMenu(anchor) {
            // Remove existing menu
            document.getElementById('filter-add-menu')?.remove();

            const app = this.getState();
            const allFilters = app?.pluginManager?.getAllFilters() || [];

            if (allFilters.length === 0) return;

            // Group by category
            const categories = {};
            for (const f of allFilters) {
                const cat = f.category || 'Other';
                if (!categories[cat]) categories[cat] = [];
                categories[cat].push(f);
            }

            // Build menu with category items that have nested submenus
            const menu = document.createElement('div');
            menu.id = 'filter-add-menu';
            menu.className = 'filter-add-menu';

            // Sort categories using the standard order
            const sortedKeys = [
                ...filterCategoryOrder.filter(k => categories[k]),
                ...Object.keys(categories).filter(k => !filterCategoryOrder.includes(k))
            ];

            let html = '';
            for (const category of sortedKeys) {
                html += `<div class="filter-add-category-item" data-category="${category}">
                    <span>${getCategoryName(category)}</span><span class="submenu-arrow">&#9654;</span>
                </div>`;
            }
            menu.innerHTML = html;

            // Position relative to anchor, flipping up if not enough space below
            document.body.appendChild(menu);
            const rect = anchor.getBoundingClientRect();
            const menuHeight = menu.offsetHeight;
            const viewportHeight = window.innerHeight;
            const spaceBelow = viewportHeight - rect.bottom;
            const spaceAbove = rect.top;

            menu.style.left = rect.left + 'px';
            if (spaceBelow >= menuHeight || spaceBelow >= spaceAbove) {
                menu.style.top = rect.bottom + 'px';
                if (spaceBelow < menuHeight) {
                    menu.style.maxHeight = (spaceBelow - 8) + 'px';
                }
            } else {
                menu.style.bottom = (viewportHeight - rect.top) + 'px';
                if (spaceAbove < menuHeight) {
                    menu.style.maxHeight = (spaceAbove - 8) + 'px';
                }
            }

            // Active submenu tracking
            let activeSubmenu = null;
            let closeTimer = null;

            const cancelClose = () => {
                if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
            };

            const scheduleClose = () => {
                cancelClose();
                closeTimer = setTimeout(() => {
                    if (activeSubmenu) { activeSubmenu.remove(); activeSubmenu = null; }
                    menu.remove();
                    document.removeEventListener('mousedown', outsideHandler);
                }, 300);
            };

            const closeAll = () => {
                cancelClose();
                if (activeSubmenu) { activeSubmenu.remove(); activeSubmenu = null; }
                menu.remove();
                document.removeEventListener('mousedown', outsideHandler);
            };

            const showSubmenu = (categoryItem) => {
                cancelClose();
                // Remove old submenu
                if (activeSubmenu) { activeSubmenu.remove(); activeSubmenu = null; }

                const category = categoryItem.dataset.category;
                const filters = categories[category];
                if (!filters) return;

                // Highlight active category
                menu.querySelectorAll('.filter-add-category-item').forEach(el => el.classList.remove('active'));
                categoryItem.classList.add('active');

                const sub = document.createElement('div');
                sub.className = 'filter-add-submenu';

                let subHtml = '';
                for (const f of filters) {
                    subHtml += `<div class="filter-add-item" data-filter-id="${f.id}" data-filter-name="${f.name}" data-filter-source="${f.source || 'wasm'}">${f.name}</div>`;
                }
                sub.innerHTML = subHtml;
                document.body.appendChild(sub);

                // Position submenu next to the category item
                const itemRect = categoryItem.getBoundingClientRect();
                const menuRect = menu.getBoundingClientRect();
                const subWidth = sub.offsetWidth;
                const subHeight = sub.offsetHeight;
                const vw = window.innerWidth;
                const vh = window.innerHeight;

                // Horizontal: prefer right of menu, flip left if no room
                if (menuRect.right + subWidth <= vw) {
                    sub.style.left = menuRect.right + 'px';
                } else {
                    sub.style.left = (menuRect.left - subWidth) + 'px';
                }

                // Vertical: align top with category item, adjust if overflows
                let top = itemRect.top;
                if (top + subHeight > vh - 8) top = vh - 8 - subHeight;
                if (top < 8) top = 8;
                sub.style.top = top + 'px';
                if (subHeight > vh - 16) sub.style.maxHeight = (vh - 16) + 'px';

                // Bind filter item clicks
                sub.querySelectorAll('.filter-add-item').forEach(item => {
                    item.addEventListener('click', () => {
                        this._addFilterFromMenuItem(item, allFilters);
                        closeAll();
                    });
                });

                // Keep alive while hovering submenu
                sub.addEventListener('mouseenter', cancelClose);
                sub.addEventListener('mouseleave', scheduleClose);

                activeSubmenu = sub;
            };

            // Hover to switch submenus; keep alive while in menu
            menu.addEventListener('mouseenter', cancelClose);
            menu.addEventListener('mouseleave', scheduleClose);

            menu.querySelectorAll('.filter-add-category-item').forEach(item => {
                item.addEventListener('mouseenter', () => showSubmenu(item));
                item.addEventListener('click', () => showSubmenu(item));
            });

            // Close on outside click
            const outsideHandler = (e) => {
                if (!menu.contains(e.target) && (!activeSubmenu || !activeSubmenu.contains(e.target))) {
                    closeAll();
                }
            };
            setTimeout(() => document.addEventListener('mousedown', outsideHandler), 0);
        },

        /**
         * Add a filter from a menu item element.
         * @private
         */
        _addFilterFromMenuItem(item, allFilters) {
            const filterId = item.dataset.filterId;
            const filterName = item.dataset.filterName;
            const source = item.dataset.filterSource;

            const filterDef = allFilters.find(f => f.id === filterId);
            const params = {};
            if (filterDef?.params) {
                for (const param of filterDef.params) {
                    params[param.id] = param.default !== undefined ? param.default :
                        (param.type === 'range' ? param.min :
                         param.type === 'select' ? param.options?.[0] :
                         param.type === 'checkbox' ? false :
                         param.type === 'color' ? '#FFFFFF' : '');
                }
            }

            const dynamicFilter = new DynamicFilter({
                filterId,
                name: filterName,
                params,
                source,
            });

            this._filterLayer.addFilter(dynamicFilter);
            this._renderFilterList();
            this._selectFilter(dynamicFilter.id);
            this.updateLayerList();
        },

        /**
         * Move the selected filter up or down.
         * @param {number} direction - -1 for up, 1 for down
         */
        _moveSelectedFilter(direction) {
            if (!this._selectedFilterId || !this._filterLayer) return;

            const layer = this._filterLayer;
            const index = layer.filters.findIndex(f => f.id === this._selectedFilterId);
            if (index < 0) return;

            const newIndex = index + direction;
            if (newIndex < 0 || newIndex >= layer.filters.length) return;

            layer.moveFilter(this._selectedFilterId, newIndex);
            this._renderFilterList();
        },

        /**
         * Delete the selected filter.
         */
        _deleteSelectedFilter() {
            if (!this._selectedFilterId || !this._filterLayer) return;

            this._filterLayer.removeFilter(this._selectedFilterId);
            this._selectedFilterId = null;
            this._renderFilterList();
            this.updateLayerList();

            // Clear props pane
            const propsPane = document.getElementById('filter-props');
            if (propsPane) {
                propsPane.innerHTML = '<div class="filter-props-empty">Select a filter to edit parameters</div>';
            }
        },

        /**
         * Commit filter changes to history if there were modifications.
         */
        _commitFilterHistory() {
            const app = this.getState();
            if (!app?.history || !this._filterLayerId) return;

            const layer = app.layerStack.getLayerById(this._filterLayerId);
            if (!layer) {
                this._filterLayerId = null;
                this._filtersBefore = null;
                return;
            }

            const filtersAfter = layer.filters ? layer.filters.map(f => typeof f.serialize === 'function' ? f.serialize() : { ...f }) : [];
            const beforeJson = JSON.stringify(this._filtersBefore);
            const afterJson = JSON.stringify(filtersAfter);

            if (beforeJson !== afterJson) {
                app.history.saveState('Modify Layer Filters');
                app.history.finishState();

                // Mark document modified for auto-save
                app.documentManager?.getActiveDocument()?.markModified();
            }

            this._filterLayerId = null;
            this._filtersBefore = null;
        },
    },
};

export default FilterManagerMixin;
