/**
 * LayerPanel - Layer list and management UI.
 */
import { BlendModes } from '../core/BlendModes.js';
import * as LayerEffects from '../core/LayerEffects.js';

export class LayerPanel {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.container = document.getElementById('layer-panel');
        this.render();
        this.bindEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="panel-header">
                <span>Layers</span>
            </div>
            <div class="layer-controls">
                <select id="blend-mode" class="layer-blend-mode">
                    ${BlendModes.getAllModes().map(m =>
                        `<option value="${m.id}">${m.name}</option>`
                    ).join('')}
                </select>
                <div class="layer-opacity-row">
                    <label>Opacity:</label>
                    <input type="range" id="layer-opacity" min="0" max="100" value="100">
                    <span id="layer-opacity-value">100%</span>
                </div>
            </div>
            <div class="layer-list" id="layer-list"></div>
            <div class="layer-buttons">
                <button id="layer-add" title="Add Layer">+</button>
                <button id="layer-delete" title="Delete Layer">-</button>
                <button id="layer-duplicate" title="Duplicate Layer">D</button>
                <button id="layer-merge" title="Merge Down">M</button>
                <button id="layer-effects" title="Layer Effects">fx</button>
            </div>
        `;

        this.renderLayerList();
    }

    renderLayerList() {
        const list = document.getElementById('layer-list');
        if (!list) return;

        const layers = this.app.layerStack.layers;
        const activeIndex = this.app.layerStack.activeLayerIndex;

        // Render from top to bottom (reverse order)
        list.innerHTML = layers.slice().reverse().map((layer, reverseIdx) => {
            const idx = layers.length - 1 - reverseIdx;
            const isActive = idx === activeIndex;
            return `
                <div class="layer-item ${isActive ? 'active' : ''}" data-index="${idx}">
                    <button class="layer-visibility ${layer.visible ? 'visible' : ''}"
                            data-action="toggle-visibility" data-index="${idx}">
                        ${layer.visible ? '👁' : '○'}
                    </button>
                    <span class="layer-name">${layer.name}</span>
                    ${layer.locked ? '<span class="layer-locked">🔒</span>' : ''}
                </div>
            `;
        }).join('');
    }

    bindEvents() {
        // Layer list clicks
        this.container.addEventListener('click', (e) => {
            const layerItem = e.target.closest('.layer-item');
            const action = e.target.dataset.action;

            if (action === 'toggle-visibility') {
                const idx = parseInt(e.target.dataset.index);
                const layer = this.app.layerStack.layers[idx];
                if (layer) {
                    layer.visible = !layer.visible;
                    this.renderLayerList();
                    this.app.renderer.requestRender();
                }
                e.stopPropagation();
            } else if (layerItem) {
                const idx = parseInt(layerItem.dataset.index);
                this.app.layerStack.setActiveLayer(idx);
                this.renderLayerList();
                this.updateControls();
            }
        });

        // Blend mode
        document.getElementById('blend-mode')?.addEventListener('change', (e) => {
            const layer = this.app.layerStack.getActiveLayer();
            if (layer) {
                layer.blendMode = e.target.value;
                this.app.renderer.requestRender();
            }
        });

        // Opacity
        document.getElementById('layer-opacity')?.addEventListener('input', (e) => {
            const layer = this.app.layerStack.getActiveLayer();
            if (layer) {
                layer.opacity = parseInt(e.target.value) / 100;
                document.getElementById('layer-opacity-value').textContent = `${e.target.value}%`;
                this.app.renderer.requestRender();
            }
        });

        // Layer buttons - show menu on click
        document.getElementById('layer-add')?.addEventListener('click', (e) => {
            this.showAddLayerMenu(e.target);
        });

        document.getElementById('layer-delete')?.addEventListener('click', () => {
            // Note: Layer deletion is a structural change, not pixel-based
            this.app.history.saveState('Delete Layer');
            this.app.layerStack.removeLayer(this.app.layerStack.activeLayerIndex);
            this.app.history.finishState();
            this.renderLayerList();
            this.app.renderer.requestRender();
        });

        document.getElementById('layer-duplicate')?.addEventListener('click', () => {
            // Note: Layer duplication is a structural change, not pixel-based
            this.app.history.saveState('Duplicate Layer');
            this.app.layerStack.duplicateLayer(this.app.layerStack.activeLayerIndex);
            this.app.history.finishState();
            this.renderLayerList();
            this.app.renderer.requestRender();
        });

        document.getElementById('layer-merge')?.addEventListener('click', () => {
            // Merge modifies the bottom layer's pixels
            this.app.history.saveState('Merge Layers');
            this.app.layerStack.mergeDown(this.app.layerStack.activeLayerIndex);
            this.app.history.finishState();
            this.renderLayerList();
            this.app.renderer.requestRender();
        });

        // Layer effects button
        document.getElementById('layer-effects')?.addEventListener('click', () => {
            this.showEffectsPanel();
        });

        // Right-click context menu on layers
        this.container.addEventListener('contextmenu', (e) => {
            const layerItem = e.target.closest('.layer-item');
            if (layerItem) {
                e.preventDefault();
                const idx = parseInt(layerItem.dataset.index);
                this.app.layerStack.setActiveLayer(idx);
                this.renderLayerList();
                this.updateControls();
                this.showLayerContextMenu(e.clientX, e.clientY);
            }
        });

        // Event listeners
        this.app.eventBus.on('layer:added', () => this.update());
        this.app.eventBus.on('layer:removed', () => this.update());
        this.app.eventBus.on('layer:activated', () => this.update());
        this.app.eventBus.on('layers:restored', () => this.update());
    }

    updateControls() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        const blendSelect = document.getElementById('blend-mode');
        const opacitySlider = document.getElementById('layer-opacity');
        const opacityValue = document.getElementById('layer-opacity-value');

        // Ensure opacity is a valid number (fix NaN issue for vector layers)
        const opacity = typeof layer.opacity === 'number' && !isNaN(layer.opacity)
            ? layer.opacity
            : 1.0;

        if (blendSelect) blendSelect.value = layer.blendMode || 'normal';
        if (opacitySlider) opacitySlider.value = Math.round(opacity * 100);
        if (opacityValue) opacityValue.textContent = `${Math.round(opacity * 100)}%`;
    }

    update() {
        this.renderLayerList();
        this.updateControls();
    }

    /**
     * Show context menu for layer.
     */
    showLayerContextMenu(x, y) {
        // Remove existing menu
        document.getElementById('layer-context-menu')?.remove();

        const menu = document.createElement('div');
        menu.id = 'layer-context-menu';
        menu.className = 'context-menu';
        menu.style.left = `${x}px`;
        menu.style.top = `${y}px`;
        menu.innerHTML = `
            <div class="menu-item" data-action="effects">Layer Effects...</div>
            <div class="menu-separator"></div>
            <div class="menu-item" data-action="duplicate">Duplicate Layer</div>
            <div class="menu-item" data-action="delete">Delete Layer</div>
            <div class="menu-separator"></div>
            <div class="menu-item" data-action="merge">Merge Down</div>
        `;

        document.body.appendChild(menu);

        menu.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                if (action === 'effects') this.showEffectsPanel();
                else if (action === 'duplicate') document.getElementById('layer-duplicate')?.click();
                else if (action === 'delete') document.getElementById('layer-delete')?.click();
                else if (action === 'merge') document.getElementById('layer-merge')?.click();
                menu.remove();
            });
        });

        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', () => menu.remove(), { once: true });
        }, 0);
    }

    /**
     * Commit effects changes to history if the layer's effects changed.
     */
    commitEffectsIfChanged() {
        if (!this._effectsLayerId || !this._effectsBefore) return;

        const layer = this.app.layerStack.getLayerById(this._effectsLayerId);
        if (!layer) return;

        // Get current effects state
        const effectsAfter = layer.effects ? layer.effects.map(e => e.serialize()) : [];

        // Compare
        const beforeJson = JSON.stringify(this._effectsBefore);
        const afterJson = JSON.stringify(effectsAfter);

        if (beforeJson !== afterJson) {
            // Create history entry with layer-specific effect snapshot
            this.app.history.beginCapture('Modify Layer Effects', []);
            this.app.history.captureEffectsBefore(this._effectsLayerId, this._effectsBefore);
            this.app.history.commitCapture();

            // Mark document as modified for auto-save
            this.app.documentManager?.getActiveDocument()?.markModified();
        }
    }

    /**
     * Show layer effects panel.
     */
    showEffectsPanel() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        // Remove existing panel
        document.getElementById('effects-panel')?.remove();
        document.getElementById('effect-editor')?.remove();

        // Capture initial effects state for this layer only (for history diff)
        this._effectsLayerId = layer.id;
        this._effectsBefore = layer.effects ? layer.effects.map(e => e.serialize()) : [];

        const panel = document.createElement('div');
        panel.id = 'effects-panel';
        panel.className = 'effects-panel';
        panel.innerHTML = `
            <div class="effects-panel-header">
                <span>Layer Effects - ${layer.name}</span>
                <button class="effects-panel-close">&times;</button>
            </div>
            <div class="effects-panel-content">
                <div class="effects-list" id="effects-list"></div>
                <div class="effects-add">
                    <select id="effect-type-select">
                        <option value="">Add Effect...</option>
                        ${LayerEffects.getAvailableEffects().map(e =>
                            `<option value="${e.type}">${e.displayName}</option>`
                        ).join('')}
                    </select>
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // Center panel
        panel.style.left = `${(window.innerWidth - 350) / 2}px`;
        panel.style.top = `${(window.innerHeight - 400) / 2}px`;

        // Make draggable
        this.makeDraggable(panel, panel.querySelector('.effects-panel-header'));

        // Render effects list
        this.renderEffectsList(layer);

        // Close button - commit changes on close
        panel.querySelector('.effects-panel-close').addEventListener('click', () => {
            this.closeEffectsPanel();
        });

        // Add effect dropdown
        document.getElementById('effect-type-select')?.addEventListener('change', (e) => {
            if (!e.target.value) return;
            this.addEffectToLayer(layer, e.target.value);
            e.target.value = '';
        });
    }

    /**
     * Close the effects panel and commit any changes to history.
     */
    closeEffectsPanel() {
        const panel = document.getElementById('effects-panel');
        const editor = document.getElementById('effect-editor');

        // Commit changes if there were any
        this.commitEffectsIfChanged();

        // Clean up
        this._effectsLayerId = null;
        this._effectsBefore = null;

        panel?.remove();
        editor?.remove();
    }

    /**
     * Render the list of effects for a layer.
     */
    renderEffectsList(layer) {
        const list = document.getElementById('effects-list');
        if (!list) return;

        if (!layer.effects || layer.effects.length === 0) {
            list.innerHTML = '<div class="effects-empty">No effects applied</div>';
            return;
        }

        list.innerHTML = layer.effects.map((effect, idx) => `
            <div class="effect-item ${effect.enabled ? '' : 'disabled'}" data-effect-id="${effect.id}">
                <input type="checkbox" class="effect-enabled" ${effect.enabled ? 'checked' : ''}>
                <span class="effect-name">${LayerEffects.effectRegistry[effect.type]?.displayName || effect.type}</span>
                <button class="effect-edit" title="Edit">&#9998;</button>
                <button class="effect-delete" title="Delete">&times;</button>
            </div>
        `).join('');

        // Bind events (no individual history entries - handled on panel close)
        list.querySelectorAll('.effect-item').forEach(item => {
            const effectId = item.dataset.effectId;

            item.querySelector('.effect-enabled')?.addEventListener('change', (e) => {
                const effect = layer.getEffect(effectId);
                if (effect) {
                    effect.enabled = e.target.checked;
                    item.classList.toggle('disabled', !effect.enabled);
                    layer._effectCacheVersion++;
                    this.app.renderer.requestRender();
                }
            });

            item.querySelector('.effect-edit')?.addEventListener('click', () => {
                this.showEffectEditor(layer, effectId);
            });

            item.querySelector('.effect-delete')?.addEventListener('click', () => {
                layer.removeEffect(effectId);
                this.renderEffectsList(layer);
                this.app.renderer.requestRender();
            });
        });
    }

    /**
     * Add a new effect to the layer.
     * No individual history entry - handled on panel close.
     */
    addEffectToLayer(layer, effectType) {
        const EffectClass = LayerEffects.effectRegistry[effectType];
        if (!EffectClass) return;

        const effect = new EffectClass();
        layer.addEffect(effect);

        this.renderEffectsList(layer);
        this.app.renderer.requestRender();

        // Open editor for new effect
        this.showEffectEditor(layer, effect.id);
    }

    /**
     * Show effect parameter editor.
     */
    showEffectEditor(layer, effectId) {
        const effect = layer.getEffect(effectId);
        if (!effect) return;

        // Remove existing editor
        document.getElementById('effect-editor')?.remove();

        const editor = document.createElement('div');
        editor.id = 'effect-editor';
        editor.className = 'effect-editor';

        const displayName = LayerEffects.effectRegistry[effect.type]?.displayName || effect.type;
        const params = effect.getParams();

        editor.innerHTML = `
            <div class="effect-editor-header">
                <span>${displayName}</span>
                <button class="effect-editor-close">&times;</button>
            </div>
            <div class="effect-editor-content">
                <label class="effect-param-row">
                    <span>Blend Mode</span>
                    <select class="effect-param effect-blend-mode" data-param="blendMode">
                        ${BlendModes.getAllModes().map(m =>
                            `<option value="${m.id}" ${m.id === effect.blendMode ? 'selected' : ''}>${m.name}</option>`
                        ).join('')}
                    </select>
                </label>
                <label class="effect-param-row">
                    <span>Opacity</span>
                    <input type="range" class="effect-param" data-param="opacity"
                           min="0" max="1" step="0.01" value="${effect.opacity}">
                    <span class="effect-param-value">${Math.round(effect.opacity * 100)}%</span>
                </label>
                <div class="effect-params-divider"></div>
                ${this.renderEffectParams(effect, params)}
            </div>
        `;

        document.body.appendChild(editor);

        // Position near effects panel
        const panel = document.getElementById('effects-panel');
        if (panel) {
            const rect = panel.getBoundingClientRect();
            editor.style.left = `${rect.right + 10}px`;
            editor.style.top = `${rect.top}px`;
        }

        // Make draggable
        this.makeDraggable(editor, editor.querySelector('.effect-editor-header'));

        // Close button
        editor.querySelector('.effect-editor-close').addEventListener('click', () => editor.remove());

        // Bind param change events (no individual history - handled on panel close)
        editor.querySelectorAll('.effect-param').forEach(input => {
            // Update values on input/change (immediate visual feedback)
            const updateHandler = () => {
                this.updateEffectParam(layer, effect, input);
            };

            input.addEventListener('input', updateHandler);
            input.addEventListener('change', updateHandler);
        });
    }

    /**
     * Render effect parameters as form fields.
     */
    renderEffectParams(effect, params) {
        const fields = [];

        for (const [key, value] of Object.entries(params)) {
            // Skip base class properties (handled separately) and metadata
            if (key === 'id' || key === 'type' || key === 'opacity' || key === 'blendMode') continue;

            let field = '';
            if (typeof value === 'boolean') {
                field = `
                    <label class="effect-param-row">
                        <span>${this.formatParamName(key)}</span>
                        <input type="checkbox" class="effect-param" data-param="${key}" ${value ? 'checked' : ''}>
                    </label>
                `;
            } else if (typeof value === 'number') {
                const isOpacity = key.toLowerCase().includes('opacity');
                const min = isOpacity ? 0 : -100;
                const max = isOpacity ? 1 : 100;
                const step = isOpacity ? 0.01 : 1;
                field = `
                    <label class="effect-param-row">
                        <span>${this.formatParamName(key)}</span>
                        <input type="range" class="effect-param" data-param="${key}"
                               min="${min}" max="${max}" step="${step}" value="${value}">
                        <span class="effect-param-value">${isOpacity ? Math.round(value * 100) + '%' : value}</span>
                    </label>
                `;
            } else if (typeof value === 'string' && value.startsWith('#')) {
                field = `
                    <label class="effect-param-row">
                        <span>${this.formatParamName(key)}</span>
                        <input type="color" class="effect-param" data-param="${key}" value="${value}">
                    </label>
                `;
            } else if (typeof value === 'string') {
                // Check if it's a select (position, style, etc.)
                const options = this.getParamOptions(key);
                if (options) {
                    field = `
                        <label class="effect-param-row">
                            <span>${this.formatParamName(key)}</span>
                            <select class="effect-param" data-param="${key}">
                                ${options.map(o => `<option value="${o}" ${o === value ? 'selected' : ''}>${o}</option>`).join('')}
                            </select>
                        </label>
                    `;
                } else {
                    field = `
                        <label class="effect-param-row">
                            <span>${this.formatParamName(key)}</span>
                            <input type="text" class="effect-param" data-param="${key}" value="${value}">
                        </label>
                    `;
                }
            }

            if (field) fields.push(field);
        }

        return fields.join('') || '<div class="effects-empty">No parameters</div>';
    }

    /**
     * Get options for select parameters.
     */
    getParamOptions(key) {
        const options = {
            position: ['outside', 'inside', 'center'],
            style: ['innerBevel', 'outerBevel', 'emboss', 'pillowEmboss'],
            direction: ['up', 'down'],
            source: ['edge', 'center']
        };
        return options[key];
    }

    /**
     * Format parameter name for display.
     */
    formatParamName(name) {
        return name.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
    }

    /**
     * Update effect parameter from input.
     */
    updateEffectParam(layer, effect, input) {
        const param = input.dataset.param;
        let value;

        if (input.type === 'checkbox') {
            value = input.checked;
        } else if (input.type === 'range' || input.type === 'number') {
            value = parseFloat(input.value);
            // Update display value
            const display = input.nextElementSibling;
            if (display?.classList.contains('effect-param-value')) {
                const isOpacity = param.toLowerCase().includes('opacity');
                display.textContent = isOpacity ? Math.round(value * 100) + '%' : value;
            }
        } else {
            value = input.value;
        }

        effect[param] = value;
        layer._effectCacheVersion++;
        this.app.renderer.requestRender();
        this.app.documentManager?.activeDocument?.markModified();
    }

    /**
     * Make an element draggable.
     */
    makeDraggable(element, handle) {
        let offsetX, offsetY;

        handle.style.cursor = 'move';

        handle.addEventListener('mousedown', (e) => {
            offsetX = e.clientX - element.offsetLeft;
            offsetY = e.clientY - element.offsetTop;

            const onMouseMove = (e) => {
                element.style.left = `${e.clientX - offsetX}px`;
                element.style.top = `${e.clientY - offsetY}px`;
            };

            const onMouseUp = () => {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    /**
     * Show the add layer menu with options for different layer types.
     */
    showAddLayerMenu(button) {
        // Remove existing menu
        document.getElementById('add-layer-menu')?.remove();

        const rect = button.getBoundingClientRect();
        const menu = document.createElement('div');
        menu.id = 'add-layer-menu';
        menu.className = 'context-menu add-layer-menu';
        menu.style.left = `${rect.left}px`;
        menu.style.bottom = `${window.innerHeight - rect.top + 5}px`;
        menu.innerHTML = `
            <div class="menu-item" data-action="pixel">New Pixel Layer</div>
            <div class="menu-item" data-action="vector">New Vector Layer</div>
            <div class="menu-separator"></div>
            <div class="menu-item menu-submenu" data-action="library">
                From Library
                <span class="submenu-arrow">▶</span>
            </div>
        `;

        document.body.appendChild(menu);

        // Handle menu item clicks
        menu.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = item.dataset.action;
                if (action === 'pixel') {
                    this.addPixelLayer();
                    menu.remove();
                } else if (action === 'library') {
                    // Show library submenu
                    this.showLibrarySubmenu(item, menu);
                    e.stopPropagation();
                }
            });
        });

        // Close on outside click
        setTimeout(() => {
            const closeMenu = (e) => {
                if (!menu.contains(e.target) && e.target !== button) {
                    menu.remove();
                    document.getElementById('library-submenu')?.remove();
                    document.removeEventListener('click', closeMenu);
                }
            };
            document.addEventListener('click', closeMenu);
        }, 0);
    }

    /**
     * Show library submenu with image and SVG samples.
     */
    showLibrarySubmenu(parentItem, parentMenu) {
        // Remove existing submenu
        document.getElementById('library-submenu')?.remove();

        const rect = parentItem.getBoundingClientRect();
        const submenu = document.createElement('div');
        submenu.id = 'library-submenu';
        submenu.className = 'context-menu library-submenu';
        submenu.style.left = `${rect.right + 2}px`;
        submenu.style.top = `${rect.top}px`;
        submenu.innerHTML = `<div class="menu-item menu-loading">Loading...</div>`;

        document.body.appendChild(submenu);

        // Load library items
        this.loadLibraryItems(submenu, parentMenu);
    }

    /**
     * Load library items from API and populate submenu.
     */
    async loadLibraryItems(submenu, parentMenu) {
        try {
            // Fetch both image sources and SVG samples in parallel
            const [imagesRes, svgsRes] = await Promise.all([
                fetch('/api/images/sources').catch(() => null),
                fetch('/api/svg-samples').catch(() => null)
            ]);

            const items = [];

            // Add image sources (skimage samples)
            if (imagesRes?.ok) {
                const imagesData = await imagesRes.json();
                for (const source of imagesData.sources || []) {
                    for (const img of source.images || []) {
                        items.push({
                            type: 'image',
                            id: `${source.id}/${img.id}`,
                            name: img.name || img.id,
                            category: source.name || source.id
                        });
                    }
                }
            }

            // Add SVG samples
            if (svgsRes?.ok) {
                const svgsData = await svgsRes.json();
                for (const svg of svgsData.samples || []) {
                    items.push({
                        type: 'svg',
                        id: svg.path,
                        name: svg.name,
                        category: `SVG: ${svg.category}`
                    });
                }
            }

            if (items.length === 0) {
                submenu.innerHTML = `<div class="menu-item menu-disabled">No items available</div>`;
                return;
            }

            // Group by category
            const grouped = {};
            for (const item of items) {
                if (!grouped[item.category]) {
                    grouped[item.category] = [];
                }
                grouped[item.category].push(item);
            }

            // Render grouped items
            let html = '';
            for (const [category, categoryItems] of Object.entries(grouped)) {
                html += `<div class="menu-category">${category}</div>`;
                for (const item of categoryItems) {
                    html += `<div class="menu-item library-item" data-type="${item.type}" data-id="${item.id}">${item.name}</div>`;
                }
            }

            submenu.innerHTML = html;
            submenu.style.maxHeight = '400px';
            submenu.style.overflowY = 'auto';

            // Bind click events
            submenu.querySelectorAll('.library-item').forEach(item => {
                item.addEventListener('click', () => {
                    const type = item.dataset.type;
                    const id = item.dataset.id;
                    this.addLayerFromLibrary(type, id);
                    submenu.remove();
                    parentMenu.remove();
                });
            });

        } catch (err) {
            console.error('Failed to load library:', err);
            submenu.innerHTML = `<div class="menu-item menu-disabled">Failed to load</div>`;
        }
    }

    /**
     * Add a new pixel layer.
     */
    addPixelLayer() {
        this.app.layerStack.addLayer({ name: `Layer ${this.app.layerStack.layers.length + 1}` });
        this.renderLayerList();
    }

    /**
     * Add a layer from the library (image or SVG).
     */
    async addLayerFromLibrary(type, id) {
        try {
            if (type === 'svg') {
                await this.addSVGLayerFromLibrary(id);
            } else if (type === 'image') {
                await this.addImageLayerFromLibrary(id);
            }
        } catch (err) {
            console.error('Failed to add layer from library:', err);
            alert('Failed to add layer: ' + err.message);
        }
    }

    /**
     * Add an SVG layer from the library.
     */
    async addSVGLayerFromLibrary(path) {
        // Fetch SVG content
        const response = await fetch(`/api/svg-samples/${path}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch SVG: ${response.status}`);
        }
        const svgContent = await response.text();

        // Import and create SVG layer
        const { SVGLayer } = await import('../core/StaticSVGLayer.js');

        // Create a temporary layer to get natural dimensions
        const tempLayer = new SVGLayer({ width: 1, height: 1, svgContent });
        const naturalW = tempLayer.naturalWidth;
        const naturalH = tempLayer.naturalHeight;

        // Calculate dimensions preserving aspect ratio
        const docW = this.app.layerStack.width;
        const docH = this.app.layerStack.height;
        let targetW = naturalW;
        let targetH = naturalH;

        // Scale down if larger than document
        if (naturalW > docW || naturalH > docH) {
            const scale = Math.min(docW / naturalW, docH / naturalH);
            targetW = Math.round(naturalW * scale);
            targetH = Math.round(naturalH * scale);
        }

        // Center in document
        const offsetX = Math.round((docW - targetW) / 2);
        const offsetY = Math.round((docH - targetH) / 2);

        // Track as structural change for undo/redo
        this.app.history.beginCapture('Add SVG Layer', []);
        this.app.history.beginStructuralChange();

        const layer = new SVGLayer({
            width: targetW,
            height: targetH,
            offsetX,
            offsetY,
            name: path.split('/').pop().replace('.svg', ''),
            svgContent: svgContent
        });

        // Render the SVG content
        await layer.render();

        // Add to layer stack
        this.app.layerStack.addLayer(layer);

        this.app.history.commitCapture();
        this.renderLayerList();
        this.app.renderer.requestRender();
    }

    /**
     * Add an image layer from the library (skimage samples).
     */
    async addImageLayerFromLibrary(id) {
        // Fetch image data
        const [sourceId, imageId] = id.split('/');
        const response = await fetch(`/api/images/${sourceId}/${imageId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch image: ${response.status}`);
        }

        // Parse binary response: [4 bytes length][JSON metadata][RGBA data]
        const buffer = await response.arrayBuffer();
        const view = new DataView(buffer);
        const metadataLength = view.getUint32(0, true);
        const metadataJson = new TextDecoder().decode(new Uint8Array(buffer, 4, metadataLength));
        const metadata = JSON.parse(metadataJson);
        const rgbaData = new Uint8ClampedArray(buffer, 4 + metadataLength);

        // Create a new pixel layer with the image dimensions
        const { Layer } = await import('../core/PixelLayer.js');
        const layer = new Layer({
            width: metadata.width,
            height: metadata.height,
            name: metadata.name || imageId
        });

        // Draw the image data onto the layer
        const imageData = new ImageData(rgbaData, metadata.width, metadata.height);
        layer.ctx.putImageData(imageData, 0, 0);

        // Add to layer stack
        this.app.layerStack.addLayer(layer);
        this.renderLayerList();
        this.app.renderer.requestRender();
    }
}
