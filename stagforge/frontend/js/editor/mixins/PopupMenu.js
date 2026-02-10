/**
 * PopupMenu Mixin
 *
 * Handles popup menus, tablet menus, and layer context menus.
 * Provides a unified menu system for both desktop and tablet modes.
 *
 * Required component data:
 *   - currentUIMode: String ('desktop' or 'tablet')
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - selectLayer(layerId): Selects a layer
 *   - showEffectsPanel(): Shows layer effects panel
 *   - duplicateLayer(): Duplicates current layer
 *   - deleteLayer(): Deletes current layer
 *   - mergeDown(): Merges layer down
 *   - moveLayerUp/Down(): Moves layer in stack
 *   - ungroupSelectedLayers(): Ungroups layers
 *   - groupSelectedLayers(): Groups selected layers
 *   - updateLayerList(): Updates layer panel
 */
/** Helper to generate a phosphor icon img tag */
function pIcon(name) {
    const map = {
        'rename': 'ui-edit', 'ungroup': 'ui-folder', 'delete': 'ui-trash',
        'move-up': 'ui-caret-up', 'move-down': 'ui-caret-down',
        'effects': 'sparkle', 'duplicate': 'ui-copy', 'merge': 'ui-download',
        'group': 'ui-folder-simple', 'folder': 'ui-folder-simple',
        'rasterize': 'ui-grid',
        'filter': 'ui-filter',
        'sliders': 'ui-sliders',
    };
    const file = map[name] || name;
    return `<img src="/static/icons/${file}.svg" class="phosphor-icon" alt="${name}">`;
}

export const PopupMenuMixin = {
    methods: {
        /**
         * Show a popup menu with given options
         * @param {Object} options - Menu configuration
         * @param {Array} options.items - Menu items
         * @param {number} options.x - X position
         * @param {number} options.y - Y position
         * @param {string} options.menuId - Unique menu ID
         * @returns {Promise<string|null>} Selected action or null
         */
        showPopupMenu(options) {
            const { items, x, y, menuId = 'popup-menu' } = options;
            const isTablet = this.currentUIMode === 'tablet';

            // Remove existing menu with same ID
            document.getElementById(menuId)?.remove();
            document.getElementById(menuId + '-overlay')?.remove();

            // For tablet: create fullscreen overlay with grid menu
            if (isTablet) {
                return this.showTabletMenu(items, menuId);
            }

            // Desktop: traditional dropdown menu
            const menu = document.createElement('div');
            menu.id = menuId;
            menu.className = 'popup-menu';

            // Build menu items
            let html = '';
            for (const item of items) {
                if (item.separator) {
                    html += '<div class="popup-menu-separator"></div>';
                    continue;
                }
                const iconHtml = item.icon ? `<span class="popup-menu-icon">${item.icon}</span>` : '';
                const hotkeyHtml = item.hotkey ? `<span class="popup-menu-hotkey">${item.hotkey}</span>` : '';
                html += `<div class="popup-menu-item" data-action="${item.action || ''}">
                    ${iconHtml}
                    <span class="popup-menu-text">${item.text}</span>
                    ${hotkeyHtml}
                </div>`;
            }
            menu.innerHTML = html;

            document.body.appendChild(menu);

            // Position menu, adjusting to keep it on screen
            const menuRect = menu.getBoundingClientRect();
            let posX = x;
            let posY = y;

            if (posX + menuRect.width > window.innerWidth) {
                posX = window.innerWidth - menuRect.width - 10;
            }
            if (posY + menuRect.height > window.innerHeight) {
                posY = window.innerHeight - menuRect.height - 10;
            }
            posX = Math.max(10, posX);
            posY = Math.max(10, posY);

            menu.style.left = posX + 'px';
            menu.style.top = posY + 'px';

            return new Promise((resolve) => {
                const cleanup = () => {
                    menu.remove();
                    document.removeEventListener('mousedown', outsideClickHandler);
                };

                const outsideClickHandler = (e) => {
                    if (!menu.contains(e.target)) {
                        cleanup();
                        resolve(null);
                    }
                };

                menu.querySelectorAll('.popup-menu-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const action = item.dataset.action;
                        cleanup();
                        resolve(action);
                    });
                });

                setTimeout(() => {
                    document.addEventListener('mousedown', outsideClickHandler);
                }, 10);
            });
        },

        /**
         * Show tablet-style grid menu
         * @param {Array} items - Menu items
         * @param {string} menuId - Unique menu ID
         * @returns {Promise<string|null>} Selected action or null
         */
        showTabletMenu(items, menuId) {
            // Create overlay
            const overlay = document.createElement('div');
            overlay.id = menuId + '-overlay';
            overlay.className = 'tablet-menu-overlay';

            // Create menu container
            const menu = document.createElement('div');
            menu.id = menuId;
            menu.className = 'tablet-menu';

            // Filter out separators and build grid items
            const actionItems = items.filter(item => !item.separator);
            let html = '<div class="tablet-menu-grid">';
            for (const item of actionItems) {
                html += `<button class="tablet-menu-item" data-action="${item.action || ''}">
                    <span class="tablet-menu-icon">${item.icon || '●'}</span>
                    <span class="tablet-menu-label">${item.text}</span>
                </button>`;
            }
            html += '</div>';
            html += '<button class="tablet-menu-cancel">Cancel</button>';
            menu.innerHTML = html;

            overlay.appendChild(menu);
            document.body.appendChild(overlay);

            // Animate in
            requestAnimationFrame(() => {
                overlay.classList.add('visible');
            });

            return new Promise((resolve) => {
                const cleanup = () => {
                    overlay.classList.remove('visible');
                    setTimeout(() => overlay.remove(), 200);
                };

                // Handle item clicks
                menu.querySelectorAll('.tablet-menu-item').forEach(item => {
                    const handler = (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const action = item.dataset.action;
                        cleanup();
                        resolve(action);
                    };
                    item.addEventListener('click', handler);
                    item.addEventListener('touchend', handler);
                });

                // Handle cancel button
                const cancelBtn = menu.querySelector('.tablet-menu-cancel');
                const cancelHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    cleanup();
                    resolve(null);
                };
                cancelBtn.addEventListener('click', cancelHandler);
                cancelBtn.addEventListener('touchend', cancelHandler);

                // Handle overlay tap (close)
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) {
                        cleanup();
                        resolve(null);
                    }
                });
                overlay.addEventListener('touchend', (e) => {
                    if (e.target === overlay) {
                        e.preventDefault();
                        cleanup();
                        resolve(null);
                    }
                });
            });
        },

        /**
         * Show layer context menu from touch event
         * @param {Event} event - Touch or click event
         * @param {Object} layer - Layer object
         */
        showLayerContextMenuTouch(event, layer) {
            // Get coordinates from click or touch event
            let x, y;
            if (event.touches && event.touches.length > 0) {
                x = event.touches[0].clientX;
                y = event.touches[0].clientY;
            } else {
                x = event.clientX;
                y = event.clientY;
            }
            // Create a synthetic event object with clientX/clientY
            const syntheticEvent = { clientX: x, clientY: y };
            this.showLayerContextMenu(syntheticEvent, layer);
        },

        /**
         * Show layer context menu
         * @param {Event} event - Click event for positioning
         * @param {Object} layer - Layer object
         */
        async showLayerContextMenu(event, layer) {
            // Select the layer first
            this.selectLayer(layer.id);

            // Get the actual layer instance from LayerStack (Vue object doesn't have methods)
            const app = this.getState();
            const realLayer = app?.layerStack?.getLayerById(layer.id);

            // Build menu items based on layer type
            let items = [];
            if (layer.isGroup) {
                // Group-specific menu
                items = [
                    { icon: pIcon('rename'), text: 'Rename Group...', action: 'rename' },
                    { separator: true },
                    { icon: pIcon('ungroup'), text: 'Ungroup', action: 'ungroup', hotkey: 'Ctrl+Shift+G' },
                    { icon: pIcon('delete'), text: 'Delete Group', action: 'delete' },
                    { separator: true },
                    { icon: pIcon('move-up'), text: 'Move Up', action: 'moveUp' },
                    { icon: pIcon('move-down'), text: 'Move Down', action: 'moveDown' },
                ];
            } else {
                // Regular layer menu
                items = [
                    { icon: pIcon('effects'), text: 'Layer Effects...', action: 'effects' },
                    { icon: pIcon('sliders'), text: 'Layer Filters...', action: 'filters' },
                    { icon: pIcon('rename'), text: 'Rename Layer...', action: 'rename' },
                    { separator: true },
                    { icon: pIcon('duplicate'), text: 'Duplicate Layer', action: 'duplicate' },
                    { icon: pIcon('delete'), text: 'Delete Layer', action: 'delete' },
                    { separator: true },
                    { icon: pIcon('merge'), text: 'Merge Down', action: 'merge' },
                ];

                // Add rasterize option for vector/SVG layers
                if (realLayer?.isVector?.() || realLayer?.isSVG?.()) {
                    items.push({ separator: true });
                    items.push({ icon: pIcon('rasterize'), text: 'Rasterize Layer', action: 'rasterize' });
                }

                items.push({ separator: true });
                items.push({ icon: pIcon('resize'), text: 'Transform...', action: 'transform' });
                items.push({ separator: true });
                items.push({ icon: pIcon('move-up'), text: 'Move Up', action: 'moveUp' });
                items.push({ icon: pIcon('move-down'), text: 'Move Down', action: 'moveDown' });
                items.push({ separator: true });
                items.push({ icon: pIcon('group'), text: 'Add to New Group', action: 'addToGroup', hotkey: 'Ctrl+G' });
            }

            const action = await this.showPopupMenu({
                items,
                x: event.clientX,
                y: event.clientY,
                menuId: 'layer-context-menu'
            });

            // Handle selected action
            if (action) {
                switch (action) {
                    case 'effects': this.showEffectsPanel(); break;
                    case 'filters': this.showFilterPanel(); break;
                    case 'rename': this.renameLayerDialog(layer.id); break;
                    case 'duplicate': this.duplicateLayer(); break;
                    case 'delete': this.deleteLayer(); break;
                    case 'merge': this.mergeDown(); break;
                    case 'moveUp': this.moveLayerUp(); break;
                    case 'moveDown': this.moveLayerDown(); break;
                    case 'rasterize': this.rasterizeActiveLayer(); break;
                    case 'transform': this.showTransformDialog(); break;
                    case 'ungroup': this.ungroupSelectedLayers(); break;
                    case 'addToGroup': this.groupSelectedLayers(); break;
                }
            }
        },

        /**
         * Show rename layer dialog
         * @param {string} layerId - Layer ID to rename
         */
        renameLayerDialog(layerId) {
            const app = this.getState();
            if (!app?.layerStack) return;
            const layer = app.layerStack.getLayerById(layerId);
            if (!layer) return;

            const newName = prompt('Enter new name:', layer.name);
            if (newName && newName.trim()) {
                app.layerStack.renameLayer(layerId, newName.trim());
                this.updateLayerList();
            }
        },
    },
};

export default PopupMenuMixin;
