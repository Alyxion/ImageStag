/**
 * EffectsManager Mixin
 *
 * Handles the layer effects panel UI: showing/hiding the panel,
 * toggling effects, rendering effect parameters, and effect editing.
 *
 * Required component data:
 *   - _effectsLayer: Object (internal)
 *   - _effectsLayerId: String (internal)
 *   - _effectsBefore: Array (internal)
 *   - _selectedEffectType: String (internal)
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - makePanelDraggable(element, handle): Makes a panel draggable
 */
export const EffectsManagerMixin = {
    methods: {
        /**
         * Show the layer effects panel for the active layer
         */
        showEffectsPanel() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const layer = app.layerStack.getActiveLayer();
            if (!layer) return;

            // Remove existing panels
            document.getElementById('effects-panel')?.remove();
            document.getElementById('effect-editor')?.remove();

            // Capture initial effects state for this layer only (for history diff)
            this._effectsLayerId = layer.id;
            this._effectsBefore = layer.effects ? layer.effects.map(e => e.serialize()) : [];

            // Get available effects from LayerEffects module
            const LayerEffects = window.LayerEffects;
            let availableEffects = [];
            if (LayerEffects?.getAvailableEffects) {
                availableEffects = LayerEffects.getAvailableEffects();
            } else {
                // Fallback list if LayerEffects not yet loaded
                availableEffects = [
                    { type: 'dropShadow', displayName: 'Drop Shadow' },
                    { type: 'innerShadow', displayName: 'Inner Shadow' },
                    { type: 'outerGlow', displayName: 'Outer Glow' },
                    { type: 'innerGlow', displayName: 'Inner Glow' },
                    { type: 'bevelEmboss', displayName: 'Bevel & Emboss' },
                    { type: 'stroke', displayName: 'Stroke' },
                    { type: 'colorOverlay', displayName: 'Color Overlay' }
                ];
            }

            // Initialize effects array if needed
            if (!layer.effects) layer.effects = [];

            const panel = document.createElement('div');
            panel.id = 'effects-panel';
            panel.className = 'effects-panel';
            panel.innerHTML = `
                <div class="effects-panel-header">
                    <span>Layer Effects - ${layer.name}</span>
                    <button class="effects-panel-close">&times;</button>
                </div>
                <div class="effects-panel-body">
                    <div class="effects-list-pane">
                        <div class="effects-list" id="effects-list">
                            ${availableEffects.map(e => {
                                const existingEffect = layer.effects.find(eff => eff.type === e.type);
                                const isEnabled = existingEffect?.enabled ?? false;
                                return `
                                    <div class="effect-row ${isEnabled ? 'enabled' : ''}" data-effect-type="${e.type}">
                                        <input type="checkbox" class="effect-checkbox" ${isEnabled ? 'checked' : ''}>
                                        <span class="effect-label">${e.displayName}</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                    <div class="effects-props-pane" id="effects-props">
                        <div class="effects-props-empty">Select an effect to edit properties</div>
                    </div>
                </div>
                <div class="effects-panel-footer">
                    <button class="btn-ok" id="effects-ok">OK</button>
                </div>
            `;

            document.body.appendChild(panel);

            // Center panel
            panel.style.left = ((window.innerWidth - 500) / 2) + 'px';
            panel.style.top = ((window.innerHeight - 450) / 2) + 'px';

            // Make draggable
            this.makePanelDraggable(panel, panel.querySelector('.effects-panel-header'));

            // Store references
            this._effectsLayer = layer;
            this._selectedEffectType = null;

            // Bind checkbox and row click events
            panel.querySelectorAll('.effect-row').forEach(row => {
                const effectType = row.dataset.effectType;
                const checkbox = row.querySelector('.effect-checkbox');

                // Checkbox toggle - add/remove effect
                checkbox.addEventListener('change', (e) => {
                    e.stopPropagation();
                    this.toggleEffect(layer, effectType, checkbox.checked);
                    row.classList.toggle('enabled', checkbox.checked);
                    // Show props if enabling
                    if (checkbox.checked) {
                        this.selectEffectType(effectType);
                    }
                });

                // Row click - select for editing
                row.addEventListener('click', (e) => {
                    if (e.target === checkbox) return;
                    // If not enabled, enable it first
                    if (!checkbox.checked) {
                        checkbox.checked = true;
                        this.toggleEffect(layer, effectType, true);
                        row.classList.add('enabled');
                    }
                    this.selectEffectType(effectType);
                });
            });

            // Close button - commit history if effects changed
            const closePanel = () => {
                this.commitEffectsHistory();
                panel.remove();
            };
            panel.querySelector('.effects-panel-close').addEventListener('click', closePanel);
            panel.querySelector('#effects-ok').addEventListener('click', closePanel);
        },

        /**
         * Commit effects changes to history if there were any changes
         */
        commitEffectsHistory() {
            const app = this.getState();
            if (!app?.history || !this._effectsLayerId) return;

            const layer = app.layerStack.getLayerById(this._effectsLayerId);
            if (!layer) {
                this._effectsLayerId = null;
                this._effectsBefore = null;
                return;
            }

            // Get current effects state
            const effectsAfter = layer.effects ? layer.effects.map(e => e.serialize()) : [];

            // Compare
            const beforeJson = JSON.stringify(this._effectsBefore);
            const afterJson = JSON.stringify(effectsAfter);

            if (beforeJson !== afterJson) {
                // Create history entry with layer-specific effect snapshot
                app.history.beginCapture('Modify Layer Effects', []);
                app.history.captureEffectsBefore(this._effectsLayerId, this._effectsBefore);
                app.history.commitCapture();

                // Mark document modified for auto-save
                app.documentManager?.getActiveDocument()?.markModified();
            }

            // Clean up
            this._effectsLayerId = null;
            this._effectsBefore = null;
        },

        /**
         * Toggle an effect on/off for a layer
         * @param {Object} layer - The layer object
         * @param {string} effectType - The effect type identifier
         * @param {boolean} enabled - Whether to enable or disable
         */
        toggleEffect(layer, effectType, enabled) {
            const LayerEffects = window.LayerEffects;

            if (!layer.effects) layer.effects = [];
            const existingEffect = layer.effects.find(e => e.type === effectType);

            if (enabled && !existingEffect) {
                // Add new effect
                const EffectClass = LayerEffects?.effectRegistry?.[effectType];
                if (EffectClass) {
                    const effect = new EffectClass();
                    if (layer.addEffect) {
                        layer.addEffect(effect);
                    } else {
                        // Fallback: manually add to effects array
                        layer.effects.push(effect);
                    }
                }
            } else if (!enabled && existingEffect) {
                // Remove effect
                if (layer.removeEffect) {
                    layer.removeEffect(existingEffect.id);
                } else {
                    layer.effects = layer.effects.filter(e => e.id !== existingEffect.id);
                }
            } else if (enabled && existingEffect) {
                // Re-enable existing effect
                existingEffect.enabled = true;
            }

            const app = this.getState();
            app?.renderer?.requestRender();
        },

        /**
         * Select an effect type for editing in the properties pane
         * @param {string} effectType - The effect type identifier
         */
        selectEffectType(effectType) {
            this._selectedEffectType = effectType;
            const layer = this._effectsLayer;
            const effect = layer?.effects?.find(e => e.type === effectType);

            // Update selection UI
            document.querySelectorAll('.effect-row').forEach(row => {
                row.classList.toggle('selected', row.dataset.effectType === effectType);
            });

            // Render properties
            const propsPane = document.getElementById('effects-props');
            if (!propsPane || !effect) {
                if (propsPane) {
                    propsPane.innerHTML = '<div class="effects-props-empty">Select an effect to edit properties</div>';
                }
                return;
            }

            const LayerEffects = window.LayerEffects;
            const displayName = LayerEffects?.effectRegistry[effect.type]?.displayName || effect.type;
            const params = effect.getParams ? effect.getParams() : effect;

            propsPane.innerHTML = `
                <div class="effects-props-title">${displayName}</div>
                <div class="effects-props-content">
                    ${this.renderEffectParams(effect, params)}
                </div>
            `;

            // Bind param change events
            const app = this.getState();
            propsPane.querySelectorAll('.effect-param').forEach(input => {
                input.addEventListener('input', () => {
                    this.updateEffectParam(layer, effect, input, app);
                });
            });
        },

        /**
         * Render the effects list for a layer
         * @param {Object} layer - The layer object
         */
        renderEffectsList(layer) {
            const list = document.getElementById('effects-list');
            if (!list) return;

            const LayerEffects = window.LayerEffects;
            if (!layer.effects || layer.effects.length === 0) {
                list.innerHTML = '<div class="effects-empty">No effects applied</div>';
                return;
            }

            list.innerHTML = layer.effects.map((effect) => `
                <div class="effect-item ${effect.enabled ? '' : 'disabled'}" data-effect-id="${effect.id}">
                    <input type="checkbox" class="effect-enabled" ${effect.enabled ? 'checked' : ''}>
                    <span class="effect-name">${LayerEffects?.effectRegistry[effect.type]?.displayName || effect.type}</span>
                    <button class="effect-edit" title="Edit">&#9998;</button>
                    <button class="effect-delete" title="Delete">&times;</button>
                </div>
            `).join('');

            const app = this.getState();

            // Bind events
            list.querySelectorAll('.effect-item').forEach(item => {
                const effectId = item.dataset.effectId;

                item.querySelector('.effect-enabled')?.addEventListener('change', (e) => {
                    const effect = layer.getEffect(effectId);
                    if (effect) {
                        effect.enabled = e.target.checked;
                        item.classList.toggle('disabled', !effect.enabled);
                        app?.renderer?.requestRender();
                    }
                });

                item.querySelector('.effect-edit')?.addEventListener('click', () => {
                    this.showEffectEditor(layer, effectId);
                });

                item.querySelector('.effect-delete')?.addEventListener('click', () => {
                    layer.removeEffect(effectId);
                    this.renderEffectsList(layer);
                    app?.renderer?.requestRender();
                });
            });
        },

        /**
         * Add a new effect to a layer
         * @param {Object} layer - The layer object
         * @param {string} effectType - The effect type identifier
         */
        addEffectToLayer(layer, effectType) {
            const LayerEffects = window.LayerEffects;
            const EffectClass = LayerEffects?.effectRegistry[effectType];
            if (!EffectClass) return;

            const effect = new EffectClass();
            layer.addEffect(effect);
            this.renderEffectsList(layer);

            const app = this.getState();
            app?.renderer?.requestRender();

            // Open editor for new effect
            this.showEffectEditor(layer, effect.id);
        },

        /**
         * Show the effect editor popup for a specific effect
         * @param {Object} layer - The layer object
         * @param {string} effectId - The effect ID
         */
        showEffectEditor(layer, effectId) {
            const effect = layer.getEffect(effectId);
            if (!effect) return;

            const LayerEffects = window.LayerEffects;

            // Remove existing editor
            document.getElementById('effect-editor')?.remove();

            const editor = document.createElement('div');
            editor.id = 'effect-editor';
            editor.className = 'effect-editor';

            const displayName = LayerEffects?.effectRegistry[effect.type]?.displayName || effect.type;
            const params = effect.getParams ? effect.getParams() : effect;

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
                editor.style.left = (rect.right + 10) + 'px';
                editor.style.top = rect.top + 'px';
            } else {
                editor.style.left = ((window.innerWidth - 280) / 2 + 200) + 'px';
                editor.style.top = ((window.innerHeight - 300) / 2) + 'px';
            }

            // Make draggable
            this.makePanelDraggable(editor, editor.querySelector('.effect-editor-header'));

            // Close button
            editor.querySelector('.effect-editor-close').addEventListener('click', () => editor.remove());

            // Bind param change events
            const app = this.getState();
            editor.querySelectorAll('.effect-param').forEach(input => {
                input.addEventListener('input', () => {
                    this.updateEffectParam(layer, effect, input, app);
                });
            });
        },

        /**
         * Render effect parameter inputs
         * @param {Object} effect - The effect object
         * @param {Object} params - The effect parameters
         * @returns {string} HTML string for the parameters
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
                    const options = this.getEffectParamOptions(key);
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
        },

        /**
         * Get available options for an effect parameter
         * @param {string} key - Parameter name
         * @returns {Array|null} Array of options or null
         */
        getEffectParamOptions(key) {
            const options = {
                position: ['outside', 'inside', 'center'],
                style: ['innerBevel', 'outerBevel', 'emboss', 'pillowEmboss'],
                direction: ['up', 'down'],
                source: ['edge', 'center']
            };
            return options[key];
        },

        /**
         * Format a parameter name for display
         * @param {string} name - Parameter name in camelCase
         * @returns {string} Formatted name
         */
        formatParamName(name) {
            return name.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
        },

        /**
         * Update an effect parameter value
         * @param {Object} layer - The layer object
         * @param {Object} effect - The effect object
         * @param {HTMLInputElement} input - The input element
         * @param {Object} app - The app state
         */
        updateEffectParam(layer, effect, input, app) {
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
            if (layer._effectCacheVersion !== undefined) {
                layer._effectCacheVersion++;
            }
            app?.renderer?.requestRender();
        },

        /**
         * Make a panel element draggable by its header
         * @param {HTMLElement} element - The panel element
         * @param {HTMLElement} handle - The draggable handle (header)
         */
        makePanelDraggable(element, handle) {
            let offsetX, offsetY;

            handle.style.cursor = 'move';

            handle.addEventListener('mousedown', (e) => {
                offsetX = e.clientX - element.offsetLeft;
                offsetY = e.clientY - element.offsetTop;

                const onMouseMove = (e) => {
                    element.style.left = (e.clientX - offsetX) + 'px';
                    element.style.top = (e.clientY - offsetY) + 'px';
                };

                const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        },
    },
};

export default EffectsManagerMixin;
