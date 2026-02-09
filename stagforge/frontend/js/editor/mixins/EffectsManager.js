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
                // Direct property modification - manually invalidate
                if (layer.invalidateEffectCache) {
                    layer.invalidateEffectCache();
                }
            }
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

            // Bind angle dial events
            const angleDial = propsPane.querySelector('.angle-dial');
            if (angleDial) {
                if (effect.type === 'gradientOverlay') {
                    this.bindGradientAngleDialEvents(angleDial, layer, effect, app);
                } else {
                    this.bindAngleDialEvents(angleDial, layer, effect, app);
                }
                // Set initial dial rotation
                const angle = parseInt(angleDial.dataset.angle) || 0;
                this.updateAngleDialVisual(angleDial, angle);
            }

            // Bind gradient editor events
            if (effect.type === 'gradientOverlay') {
                this.bindGradientEditorEvents(propsPane, layer, effect, app);
            }
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
                        // Direct property modification - manually invalidate
                        if (layer.invalidateEffectCache) {
                            layer.invalidateEffectCache();
                        }
                    }
                });

                item.querySelector('.effect-edit')?.addEventListener('click', () => {
                    this.showEffectEditor(layer, effectId);
                });

                item.querySelector('.effect-delete')?.addEventListener('click', () => {
                    layer.removeEffect(effectId);
                    this.renderEffectsList(layer);
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
            // Gradient overlay has a completely custom UI
            if (effect.type === 'gradientOverlay') {
                return this.renderGradientEffectParams(effect);
            }

            const fields = [];

            // Base opacity slider (all effects)
            const opacityPct = Math.round((effect.opacity ?? 1.0) * 100);
            fields.push(`
                <label class="effect-param-row">
                    <span>Opacity</span>
                    <input type="range" class="effect-param" data-param="opacity"
                           min="0" max="100" step="1" value="${opacityPct}">
                    <span class="effect-param-value">${opacityPct}%</span>
                </label>
            `);

            const hasShadowOffset = 'offsetX' in params && 'offsetY' in params;

            // For shadow effects, add angle/distance controls with dial
            if (hasShadowOffset) {
                const angle = Math.round(Math.atan2(params.offsetY, params.offsetX) * 180 / Math.PI);
                const distance = Math.round(Math.sqrt(params.offsetX ** 2 + params.offsetY ** 2));
                fields.push(`
                    <div class="effect-param-row effect-angle-row">
                        <span>Angle</span>
                        <div class="angle-dial-container">
                            <div class="angle-dial" data-angle="${angle}">
                                <div class="angle-dial-line"></div>
                            </div>
                            <input type="number" class="effect-param angle-input" data-param="angle"
                                   min="-180" max="180" value="${angle}">&deg;
                        </div>
                    </div>
                    <label class="effect-param-row">
                        <span>Distance</span>
                        <input type="range" class="effect-param" data-param="distance"
                               min="0" max="100" step="1" value="${distance}">
                        <span class="effect-param-value">${distance}px</span>
                    </label>
                `);
            }

            for (const [key, value] of Object.entries(params)) {
                if (key === 'id' || key === 'type') continue;
                // Skip offsetX/offsetY if we're showing angle/distance instead
                if (hasShadowOffset && (key === 'offsetX' || key === 'offsetY')) continue;

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
                    const isNonNegative = ['blur', 'spread', 'size', 'radius', 'distance'].includes(key);
                    const min = isOpacity ? 0 : (isNonNegative ? 0 : -100);
                    const max = isOpacity ? 100 : 100;
                    const step = 1;
                    const displayValue = isOpacity ? Math.round(value * 100) : value;
                    field = `
                        <label class="effect-param-row">
                            <span>${this.formatParamName(key)}</span>
                            <input type="range" class="effect-param" data-param="${key}"
                                   min="${min}" max="${max}" step="${step}" value="${displayValue}">
                            <span class="effect-param-value">${isOpacity ? displayValue + '%' : value}</span>
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
                    const options = this.getEffectParamOptions(key, effect.type);
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
        getEffectParamOptions(key, effectType) {
            if (effectType === 'gradientOverlay' && key === 'style') {
                return ['linear', 'radial', 'angle', 'reflected', 'diamond'];
            }
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
                    const isPercent = ['scaleX', 'scaleY', 'offsetX', 'offsetY'].includes(param);
                    const isOpacity = param.toLowerCase().includes('opacity');
                    display.textContent = isOpacity ? Math.round(value) + '%' : (isPercent ? value + '%' : (param === 'distance' ? value + 'px' : value));
                }
                // Convert 0-100 range slider to 0.0-1.0 for opacity fields
                if (param.toLowerCase().includes('opacity')) {
                    value = value / 100;
                }
            } else {
                value = input.value;
            }

            // Handle angle/distance -> offsetX/offsetY sync (for shadow effects, not gradient)
            if ((param === 'angle' || param === 'distance') && effect.type !== 'gradientOverlay') {
                this.syncAngleDistanceToOffset(effect, param, value, input);
            } else {
                effect[param] = value;
            }

            // Invalidate effect cache and signal renderer to re-composite
            if (layer.invalidateEffectCache) {
                layer.invalidateEffectCache();
            }
            if (layer.markChanged) {
                layer.markChanged();
            }
        },

        /**
         * Sync angle/distance values to offsetX/offsetY
         * @param {Object} effect - The effect object
         * @param {string} changedParam - Which param changed ('angle' or 'distance')
         * @param {number} value - The new value
         * @param {HTMLInputElement} input - The input element (for finding siblings)
         */
        syncAngleDistanceToOffset(effect, changedParam, value, input) {
            const container = input.closest('.effects-props-content');
            const angleInput = container?.querySelector('[data-param="angle"]');
            const distanceInput = container?.querySelector('[data-param="distance"]');
            const angleDial = container?.querySelector('.angle-dial');

            let angle = angleInput ? parseFloat(angleInput.value) : 0;
            let distance = distanceInput ? parseFloat(distanceInput.value) : 0;

            if (changedParam === 'angle') {
                angle = value;
                // Update dial visual
                if (angleDial) {
                    this.updateAngleDialVisual(angleDial, angle);
                    angleDial.dataset.angle = angle;
                }
            } else if (changedParam === 'distance') {
                distance = Math.max(0, value); // Ensure non-negative
            }

            // Convert angle (degrees) and distance to offsetX/offsetY
            const radians = angle * Math.PI / 180;
            effect.offsetX = Math.round(Math.cos(radians) * distance);
            effect.offsetY = Math.round(Math.sin(radians) * distance);
        },

        /**
         * Update angle dial visual (line rotation)
         * @param {HTMLElement} dial - The dial element
         * @param {number} angle - Angle in degrees
         */
        updateAngleDialVisual(dial, angle) {
            const line = dial.querySelector('.angle-dial-line');
            if (line) {
                line.style.transform = `rotate(${angle}deg)`;
            }
        },

        /**
         * Bind angle dial events for gradient overlay (sets angle directly).
         */
        bindGradientAngleDialEvents(dial, layer, effect, app) {
            const container = dial.closest('.effects-props-content');
            const angleInput = container?.querySelector('[data-param="angle"]');

            const updateAngle = (e) => {
                const rect = dial.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const clientY = e.touches ? e.touches[0].clientY : e.clientY;
                let angle = Math.round(Math.atan2(clientY - centerY, clientX - centerX) * 180 / Math.PI);

                this.updateAngleDialVisual(dial, angle);
                dial.dataset.angle = angle;
                if (angleInput) angleInput.value = angle;
                effect.angle = angle;
                if (layer.invalidateEffectCache) layer.invalidateEffectCache();
            };

            const onMouseDown = (e) => {
                e.preventDefault();
                dial.classList.add('dragging');
                updateAngle(e);
                const onMouseMove = (e) => updateAngle(e);
                const onMouseUp = () => {
                    dial.classList.remove('dragging');
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    document.removeEventListener('touchmove', onMouseMove);
                    document.removeEventListener('touchend', onMouseUp);
                };
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
                document.addEventListener('touchmove', onMouseMove, { passive: false });
                document.addEventListener('touchend', onMouseUp);
            };

            dial.addEventListener('mousedown', onMouseDown);
            dial.addEventListener('touchstart', (e) => { e.preventDefault(); onMouseDown(e); }, { passive: false });
        },

        /**
         * Bind mouse/touch events for angle dial dragging
         * @param {HTMLElement} dial - The dial element
         * @param {Object} layer - The layer object
         * @param {Object} effect - The effect object
         * @param {Object} app - The app state
         */
        bindAngleDialEvents(dial, layer, effect, app) {
            const container = dial.closest('.effects-props-content');
            const angleInput = container?.querySelector('[data-param="angle"]');

            const updateAngle = (e) => {
                const rect = dial.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;

                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const clientY = e.touches ? e.touches[0].clientY : e.clientY;

                const dx = clientX - centerX;
                const dy = clientY - centerY;
                let angle = Math.round(Math.atan2(dy, dx) * 180 / Math.PI);

                // Update visual
                this.updateAngleDialVisual(dial, angle);
                dial.dataset.angle = angle;

                // Update input
                if (angleInput) {
                    angleInput.value = angle;
                }

                // Sync to offsetX/offsetY
                this.syncAngleDistanceToOffset(effect, 'angle', angle, angleInput || dial);

                // Direct effect parameter modification - manually invalidate
                if (layer.invalidateEffectCache) {
                    layer.invalidateEffectCache();
                }
            };

            const onMouseDown = (e) => {
                e.preventDefault();
                dial.classList.add('dragging');
                updateAngle(e);

                const onMouseMove = (e) => {
                    updateAngle(e);
                };

                const onMouseUp = () => {
                    dial.classList.remove('dragging');
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    document.removeEventListener('touchmove', onMouseMove);
                    document.removeEventListener('touchend', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
                document.addEventListener('touchmove', onMouseMove, { passive: false });
                document.addEventListener('touchend', onMouseUp);
            };

            dial.addEventListener('mousedown', onMouseDown);
            dial.addEventListener('touchstart', (e) => {
                e.preventDefault();
                onMouseDown(e);
            }, { passive: false });
        },

        /**
         * Render custom gradient effect parameters UI
         * @param {Object} effect - The gradient overlay effect
         * @returns {string} HTML string for the gradient editor
         */
        renderGradientEffectParams(effect) {
            const stops = effect.gradient || [
                { position: 0.0, color: '#000000' },
                { position: 1.0, color: '#FFFFFF' }
            ];
            const styleOptions = ['linear', 'radial', 'angle', 'reflected', 'diamond'];
            const currentStyle = effect.style || 'linear';
            const opacityPct = Math.round((effect.opacity ?? 1.0) * 100);

            return `
                <label class="effect-param-row">
                    <span>Opacity</span>
                    <input type="range" class="effect-param" data-param="opacity"
                           min="0" max="100" step="1" value="${opacityPct}">
                    <span class="effect-param-value">${opacityPct}%</span>
                </label>
                <label class="effect-param-row">
                    <span>Style</span>
                    <select class="effect-param gradient-style-select" data-param="style">
                        ${styleOptions.map(s => `<option value="${s}" ${s === currentStyle ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`).join('')}
                    </select>
                </label>

                <div class="gradient-editor" data-effect-id="${effect.id}">
                    <div class="gradient-bar-container">
                        <canvas class="gradient-preview" width="200" height="20"></canvas>
                        <div class="gradient-stops-track">
                            ${stops.map((s, i) => `
                                <div class="gradient-stop ${i === 0 ? 'selected' : ''}"
                                     data-index="${i}"
                                     style="left: ${s.position * 100}%">
                                    <div class="gradient-stop-handle" style="background: ${s.color}"></div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <div class="gradient-stop-editor">
                        <label class="effect-param-row">
                            <span>Color</span>
                            <input type="color" class="gradient-stop-color" value="${stops[0]?.color || '#000000'}">
                        </label>
                        <label class="effect-param-row">
                            <span>Position</span>
                            <input type="range" class="gradient-stop-position" min="0" max="100" step="1" value="${Math.round((stops[0]?.position || 0) * 100)}">
                            <span class="effect-param-value">${Math.round((stops[0]?.position || 0) * 100)}%</span>
                        </label>
                    </div>
                </div>

                <div class="effect-param-row effect-angle-row">
                    <span>Angle</span>
                    <div class="angle-dial-container">
                        <div class="angle-dial" data-angle="${effect.angle ?? 90}">
                            <div class="angle-dial-line"></div>
                        </div>
                        <input type="number" class="effect-param angle-input" data-param="angle"
                               min="-180" max="360" value="${effect.angle ?? 90}">&deg;
                    </div>
                </div>

                <label class="effect-param-row">
                    <span>Scale X</span>
                    <input type="range" class="effect-param" data-param="scaleX"
                           min="10" max="200" step="1" value="${effect.scaleX ?? 100}">
                    <span class="effect-param-value">${effect.scaleX ?? 100}%</span>
                </label>
                <label class="effect-param-row">
                    <span>Scale Y</span>
                    <input type="range" class="effect-param" data-param="scaleY"
                           min="10" max="200" step="1" value="${effect.scaleY ?? 100}">
                    <span class="effect-param-value">${effect.scaleY ?? 100}%</span>
                </label>
                <label class="effect-param-row">
                    <span>Offset X</span>
                    <input type="range" class="effect-param" data-param="offsetX"
                           min="-100" max="100" step="1" value="${effect.offsetX ?? 0}">
                    <span class="effect-param-value">${effect.offsetX ?? 0}%</span>
                </label>
                <label class="effect-param-row">
                    <span>Offset Y</span>
                    <input type="range" class="effect-param" data-param="offsetY"
                           min="-100" max="100" step="1" value="${effect.offsetY ?? 0}">
                    <span class="effect-param-value">${effect.offsetY ?? 0}%</span>
                </label>
                <label class="effect-param-row">
                    <span>Reverse</span>
                    <input type="checkbox" class="effect-param" data-param="reverse" ${effect.reverse ? 'checked' : ''}>
                </label>
            `;
        },

        /**
         * Bind gradient editor events (called after rendering gradient params).
         * Must be called from selectEffectType after innerHTML is set.
         * @param {HTMLElement} container - The props container
         * @param {Object} layer - The layer object
         * @param {Object} effect - The gradient overlay effect
         * @param {Object} app - The app state
         */
        bindGradientEditorEvents(container, layer, effect, app) {
            const gradEditor = container.querySelector('.gradient-editor');
            if (!gradEditor) return;

            let selectedStopIndex = 0;

            const updatePreview = () => {
                const canvas = gradEditor.querySelector('.gradient-preview');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                const stops = effect.gradient || [];
                const sorted = [...stops].sort((a, b) => a.position - b.position);

                const grad = ctx.createLinearGradient(0, 0, canvas.width, 0);
                for (const stop of sorted) {
                    const pos = effect.reverse ? 1.0 - stop.position : stop.position;
                    grad.addColorStop(Math.max(0, Math.min(1, pos)), stop.color);
                }
                ctx.fillStyle = grad;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
            };

            const syncStopsUI = () => {
                const track = gradEditor.querySelector('.gradient-stops-track');
                if (!track) return;
                const stops = effect.gradient || [];
                track.innerHTML = stops.map((s, i) => `
                    <div class="gradient-stop ${i === selectedStopIndex ? 'selected' : ''}"
                         data-index="${i}"
                         style="left: ${s.position * 100}%">
                        <div class="gradient-stop-handle" style="background: ${s.color}"></div>
                    </div>
                `).join('');
                bindStopEvents();
                updateStopEditor();
            };

            const updateStopEditor = () => {
                const stops = effect.gradient || [];
                const stop = stops[selectedStopIndex];
                if (!stop) return;
                const colorInput = gradEditor.querySelector('.gradient-stop-color');
                const posInput = gradEditor.querySelector('.gradient-stop-position');
                const posValue = posInput?.nextElementSibling;
                if (colorInput) colorInput.value = stop.color;
                if (posInput) posInput.value = Math.round(stop.position * 100);
                if (posValue) posValue.textContent = Math.round(stop.position * 100) + '%';
            };

            const invalidateLayer = () => {
                if (layer.invalidateEffectCache) layer.invalidateEffectCache();
            };

            const bindStopEvents = () => {
                gradEditor.querySelectorAll('.gradient-stop').forEach(el => {
                    el.addEventListener('mousedown', (e) => {
                        e.preventDefault();
                        selectedStopIndex = parseInt(el.dataset.index);
                        gradEditor.querySelectorAll('.gradient-stop').forEach(s => s.classList.remove('selected'));
                        el.classList.add('selected');
                        updateStopEditor();

                        // Drag to reposition
                        const track = gradEditor.querySelector('.gradient-bar-container');
                        const trackRect = track.getBoundingClientRect();
                        const onMove = (e) => {
                            const x = Math.max(0, Math.min(1, (e.clientX - trackRect.left) / trackRect.width));
                            effect.gradient[selectedStopIndex].position = x;
                            el.style.left = (x * 100) + '%';
                            updatePreview();
                            updateStopEditor();
                            invalidateLayer();
                        };
                        const onUp = () => {
                            document.removeEventListener('mousemove', onMove);
                            document.removeEventListener('mouseup', onUp);
                        };
                        document.addEventListener('mousemove', onMove);
                        document.addEventListener('mouseup', onUp);
                    });
                });
            };

            // Click on gradient bar to add a stop
            const barContainer = gradEditor.querySelector('.gradient-bar-container');
            barContainer?.addEventListener('dblclick', (e) => {
                const rect = barContainer.getBoundingClientRect();
                const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));

                // Interpolate color at this position
                const stops = effect.gradient || [];
                let color = '#808080';
                if (stops.length >= 2) {
                    const sorted = [...stops].sort((a, b) => a.position - b.position);
                    for (let i = 0; i < sorted.length - 1; i++) {
                        if (pos >= sorted[i].position && pos <= sorted[i + 1].position) {
                            // Simple hex interpolation
                            const t = (pos - sorted[i].position) / (sorted[i + 1].position - sorted[i].position);
                            const c1 = this._parseHexColor(sorted[i].color);
                            const c2 = this._parseHexColor(sorted[i + 1].color);
                            const r = Math.round(c1.r + (c2.r - c1.r) * t);
                            const g = Math.round(c1.g + (c2.g - c1.g) * t);
                            const b = Math.round(c1.b + (c2.b - c1.b) * t);
                            color = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
                            break;
                        }
                    }
                }

                effect.gradient.push({ position: pos, color });
                selectedStopIndex = effect.gradient.length - 1;
                syncStopsUI();
                updatePreview();
                invalidateLayer();
            });

            // Color input for selected stop
            const colorInput = gradEditor.querySelector('.gradient-stop-color');
            colorInput?.addEventListener('input', () => {
                if (effect.gradient[selectedStopIndex]) {
                    effect.gradient[selectedStopIndex].color = colorInput.value;
                    syncStopsUI();
                    updatePreview();
                    invalidateLayer();
                }
            });

            // Position input for selected stop
            const posInput = gradEditor.querySelector('.gradient-stop-position');
            posInput?.addEventListener('input', () => {
                if (effect.gradient[selectedStopIndex]) {
                    const pos = parseInt(posInput.value) / 100;
                    effect.gradient[selectedStopIndex].position = pos;
                    const posValue = posInput.nextElementSibling;
                    if (posValue) posValue.textContent = Math.round(pos * 100) + '%';
                    syncStopsUI();
                    updatePreview();
                    invalidateLayer();
                }
            });

            // Initial setup
            bindStopEvents();
            updatePreview();
        },

        /**
         * Parse hex color string to RGB object.
         */
        _parseHexColor(hex) {
            hex = hex.replace('#', '');
            return {
                r: parseInt(hex.substring(0, 2), 16) || 0,
                g: parseInt(hex.substring(2, 4), 16) || 0,
                b: parseInt(hex.substring(4, 6), 16) || 0
            };
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
