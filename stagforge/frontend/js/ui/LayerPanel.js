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

        // Layer buttons
        document.getElementById('layer-add')?.addEventListener('click', () => {
            this.app.layerStack.addLayer({ name: `Layer ${this.app.layerStack.layers.length + 1}` });
            this.renderLayerList();
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
     * Show layer effects panel.
     */
    showEffectsPanel() {
        const layer = this.app.layerStack.getActiveLayer();
        if (!layer) return;

        // Remove existing panel
        document.getElementById('effects-panel')?.remove();

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

        // Close button
        panel.querySelector('.effects-panel-close').addEventListener('click', () => panel.remove());

        // Add effect dropdown
        document.getElementById('effect-type-select')?.addEventListener('change', (e) => {
            if (!e.target.value) return;
            this.addEffectToLayer(layer, e.target.value);
            e.target.value = '';
        });
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

        // Bind events
        list.querySelectorAll('.effect-item').forEach(item => {
            const effectId = item.dataset.effectId;

            item.querySelector('.effect-enabled')?.addEventListener('change', (e) => {
                const effect = layer.getEffect(effectId);
                if (effect) {
                    effect.enabled = e.target.checked;
                    item.classList.toggle('disabled', !effect.enabled);
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

        // Bind param change events
        editor.querySelectorAll('.effect-param').forEach(input => {
            input.addEventListener('input', () => {
                this.updateEffectParam(layer, effect, input);
            });
        });
    }

    /**
     * Render effect parameters as form fields.
     */
    renderEffectParams(effect, params) {
        const fields = [];

        for (const [key, value] of Object.entries(params)) {
            if (key === 'id' || key === 'type') continue;

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
}
