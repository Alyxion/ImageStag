/**
 * TextTool - Add and edit rich text on the canvas.
 *
 * Creates editable text layers with rich formatting support.
 * - Click to create new text layer
 * - Click existing text to edit it
 * - Double-click from any tool to edit text
 * - Supports multiple fonts, sizes, colors within same text block
 * - Text remains editable until layer is rasterized
 */
import { Tool } from './Tool.js';
import { TextLayer } from '../core/TextLayer.js';

export class TextTool extends Tool {
    static id = 'text';
    static name = 'Text';
    static icon = 'text';
    static iconEntity = '&#84;';  // Letter T
    static group = 'text';
    static groupShortcut = 't';
    static priority = 10;
    static cursor = 'text';

    constructor(app) {
        super(app);

        // Default text properties (used for new text)
        this.fontSize = 24;
        this.fontFamily = 'Arial';
        this.fontWeight = 'normal';
        this.fontStyle = 'normal';
        this.textAlign = 'left';

        // Current editing state
        this.isEditing = false;
        this.editingLayer = null;
        this.textX = 0;
        this.textY = 0;

        // Input elements
        this.editorContainer = null;
        this.editorElement = null;
        this.toolbar = null;

        // Prevent canvas from stealing focus
        this._preventCanvasFocus = false;
    }

    activate() {
        super.activate();
        this.app.eventBus?.on('layer:activated', this._onLayerActivated.bind(this));
    }

    deactivate() {
        super.deactivate();
        if (this.isEditing) {
            this.commitText();
        }
        this.app.eventBus?.off('layer:activated', this._onLayerActivated.bind(this));
    }

    _onLayerActivated(data) {
        if (this.isEditing && this.editingLayer && data.layer?.id !== this.editingLayer.id) {
            this.commitText();
        }
    }

    onMouseDown(e, x, y) {
        this._preventCanvasFocus = true;

        // If clicking inside the editor, don't do anything
        if (this.editorContainer && this.editorContainer.contains(e.target)) {
            return;
        }

        // If already editing, commit the current text first
        if (this.isEditing) {
            this.commitText();
        }

        // Check if clicking on an existing text layer
        const clickedLayer = this.findTextLayerAt(x, y);

        if (clickedLayer) {
            this.editTextLayer(clickedLayer);
        } else {
            this.textX = x;
            this.textY = y;
            this.startNewText(x, y);
        }
    }

    /**
     * Find a text layer at the given position.
     */
    findTextLayerAt(x, y) {
        const layers = this.app.layerStack.layers;
        for (let i = layers.length - 1; i >= 0; i--) {
            const layer = layers[i];
            if (layer.isText && layer.isText() && layer.visible && !layer.locked) {
                if (layer.containsPoint(x, y)) {
                    return layer;
                }
            }
        }
        return null;
    }

    /**
     * Start editing an existing text layer.
     */
    editTextLayer(layer) {
        const index = this.app.layerStack.layers.indexOf(layer);
        if (index >= 0) {
            this.app.layerStack.activeLayerIndex = index;
        }

        this.editingLayer = layer;
        this.textX = layer.offsetX;
        this.textY = layer.offsetY;

        // Apply layer's default font settings to tool
        this.fontSize = layer.fontSize;
        this.fontFamily = layer.fontFamily;
        this.fontWeight = layer.fontWeight;
        this.fontStyle = layer.fontStyle;
        this.textAlign = layer.textAlign;

        // Convert runs to HTML and show editor
        const html = TextLayer.runsToHtml(layer.runs, {
            fontSize: layer.fontSize,
            fontFamily: layer.fontFamily,
            fontWeight: layer.fontWeight,
            fontStyle: layer.fontStyle,
            color: layer.color
        });

        this.showRichTextEditor(layer.offsetX, layer.offsetY, html, layer.color);

        layer.select();
        this.app.renderer.requestRender();
    }

    /**
     * Start creating new text.
     */
    startNewText(x, y) {
        this.editingLayer = null;
        this.showRichTextEditor(x, y, '', this.app.foregroundColor || '#000000');
    }

    /**
     * Show the rich text editor with formatting toolbar.
     */
    showRichTextEditor(x, y, initialHtml = '', defaultColor = '#000000') {
        this.cleanup();

        // Store the default color for use when committing
        this._editorDefaultColor = defaultColor;

        const screenPos = this.app.renderer.canvasToScreen(x, y);
        const scaledFontSize = this.fontSize * this.app.renderer.zoom;

        // Create main container
        this.editorContainer = document.createElement('div');
        this.editorContainer.className = 'text-tool-editor-container';
        this.editorContainer.style.cssText = `
            position: fixed;
            left: ${screenPos.x}px;
            top: ${screenPos.y}px;
            z-index: 10000;
            pointer-events: auto;
            display: flex;
            flex-direction: column;
            gap: 4px;
        `;

        // Create formatting toolbar
        this.toolbar = this._createToolbar(defaultColor);
        this.editorContainer.appendChild(this.toolbar);

        // Create contenteditable editor
        this.editorElement = document.createElement('div');
        this.editorElement.className = 'text-tool-editor';
        this.editorElement.contentEditable = 'true';
        this.editorElement.innerHTML = initialHtml || '';
        this.editorElement.setAttribute('placeholder', 'Type text here...');
        this.editorElement.style.cssText = `
            font-size: ${scaledFontSize}px;
            font-family: ${this.fontFamily};
            font-weight: ${this.fontWeight};
            font-style: ${this.fontStyle};
            color: ${defaultColor};
            background: rgba(255, 255, 255, 0.98);
            border: 2px solid #0078d4;
            border-radius: 4px;
            outline: none;
            padding: 8px 12px;
            min-width: 200px;
            min-height: ${scaledFontSize + 20}px;
            max-width: 500px;
            max-height: 400px;
            overflow: auto;
            line-height: 1.3;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            white-space: pre-wrap;
            word-wrap: break-word;
            user-select: text;
            -webkit-user-select: text;
            cursor: text;
        `;

        // Handle keyboard events
        this.editorElement.addEventListener('keydown', (e) => {
            e.stopPropagation();

            if (e.key === 'Escape') {
                e.preventDefault();
                this.cancelText();
            }
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.commitText();
            }
            // Bold: Ctrl+B
            if (e.key === 'b' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this._applyFormat('bold');
            }
            // Italic: Ctrl+I
            if (e.key === 'i' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this._applyFormat('italic');
            }
        });

        this.editorElement.addEventListener('keyup', (e) => e.stopPropagation());
        this.editorElement.addEventListener('keypress', (e) => e.stopPropagation());

        // Handle focus loss
        this.editorElement.addEventListener('blur', (e) => {
            const relatedTarget = e.relatedTarget;
            if (!this.editorContainer?.contains(relatedTarget)) {
                setTimeout(() => {
                    if (this.isEditing && this.editorElement &&
                        !this.editorContainer?.contains(document.activeElement)) {
                        this.commitText();
                    }
                }, 200);
            }
        });

        // Prevent mousedown from bubbling
        this.editorContainer.addEventListener('mousedown', (e) => {
            e.stopPropagation();
        });

        this.editorContainer.appendChild(this.editorElement);
        document.body.appendChild(this.editorContainer);

        this.isEditing = true;

        // Focus editor
        requestAnimationFrame(() => {
            if (this.editorElement) {
                this.editorElement.focus();
                // Move cursor to end if there's content
                if (initialHtml) {
                    const range = document.createRange();
                    range.selectNodeContents(this.editorElement);
                    range.collapse(false);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            }
        });
    }

    /**
     * Create the formatting toolbar.
     */
    _createToolbar(defaultColor) {
        const toolbar = document.createElement('div');
        toolbar.className = 'text-tool-toolbar';
        toolbar.style.cssText = `
            display: flex;
            gap: 4px;
            padding: 6px 8px;
            background: #2d2d2d;
            border-radius: 4px;
            align-items: center;
            flex-wrap: wrap;
        `;

        // Font family select
        const fontSelect = document.createElement('select');
        fontSelect.style.cssText = `
            padding: 4px 8px;
            border: 1px solid #555;
            border-radius: 3px;
            background: #3c3c3c;
            color: white;
            font-size: 12px;
            cursor: pointer;
        `;
        const fonts = ['Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Courier New', 'Verdana', 'Impact', 'Comic Sans MS'];
        fonts.forEach(font => {
            const opt = document.createElement('option');
            opt.value = font;
            opt.textContent = font;
            opt.selected = font === this.fontFamily;
            fontSelect.appendChild(opt);
        });
        fontSelect.addEventListener('change', () => {
            this._applyFormat('fontName', fontSelect.value);
        });
        toolbar.appendChild(fontSelect);

        // Font size select
        const sizeSelect = document.createElement('select');
        sizeSelect.style.cssText = fontSelect.style.cssText;
        const sizes = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 64, 72, 96];
        sizes.forEach(size => {
            const opt = document.createElement('option');
            opt.value = size;
            opt.textContent = size + 'px';
            opt.selected = size === this.fontSize;
            sizeSelect.appendChild(opt);
        });
        sizeSelect.addEventListener('change', () => {
            this._applyFormat('fontSize', sizeSelect.value);
        });
        toolbar.appendChild(sizeSelect);

        // Separator
        toolbar.appendChild(this._createSeparator());

        // Bold button
        const boldBtn = this._createToolbarBtn('B', 'Bold (Ctrl+B)', () => this._applyFormat('bold'));
        boldBtn.style.fontWeight = 'bold';
        toolbar.appendChild(boldBtn);

        // Italic button
        const italicBtn = this._createToolbarBtn('I', 'Italic (Ctrl+I)', () => this._applyFormat('italic'));
        italicBtn.style.fontStyle = 'italic';
        toolbar.appendChild(italicBtn);

        // Separator
        toolbar.appendChild(this._createSeparator());

        // Color picker
        const colorPicker = document.createElement('input');
        colorPicker.type = 'color';
        colorPicker.value = defaultColor;
        colorPicker.title = 'Text Color';
        colorPicker.style.cssText = `
            width: 28px;
            height: 28px;
            border: 1px solid #555;
            border-radius: 3px;
            cursor: pointer;
            padding: 0;
            background: transparent;
        `;
        colorPicker.addEventListener('input', () => {
            this._applyFormat('foreColor', colorPicker.value);
        });
        toolbar.appendChild(colorPicker);

        // Separator
        toolbar.appendChild(this._createSeparator());

        // Confirm button
        const confirmBtn = this._createToolbarBtn('✓', 'Confirm (Ctrl+Enter)', () => this.commitText());
        confirmBtn.style.color = '#4caf50';
        toolbar.appendChild(confirmBtn);

        // Cancel button
        const cancelBtn = this._createToolbarBtn('✕', 'Cancel (Escape)', () => this.cancelText());
        cancelBtn.style.color = '#f44336';
        toolbar.appendChild(cancelBtn);

        return toolbar;
    }

    _createToolbarBtn(text, title, onClick) {
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.title = title;
        btn.style.cssText = `
            width: 28px;
            height: 28px;
            border: 1px solid #555;
            border-radius: 3px;
            background: #3c3c3c;
            color: white;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            onClick();
            this.editorElement?.focus();
        });
        btn.addEventListener('mousedown', (e) => e.preventDefault());
        return btn;
    }

    _createSeparator() {
        const sep = document.createElement('div');
        sep.style.cssText = `
            width: 1px;
            height: 20px;
            background: #555;
            margin: 0 4px;
        `;
        return sep;
    }

    /**
     * Apply formatting command to selected text.
     */
    _applyFormat(command, value = null) {
        if (!this.editorElement) return;

        this.editorElement.focus();

        if (command === 'fontSize') {
            // Font size needs special handling - wrap selection in span
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                if (!range.collapsed) {
                    const span = document.createElement('span');
                    span.style.fontSize = value + 'px';
                    range.surroundContents(span);
                } else {
                    // No selection - apply to typing
                    document.execCommand('insertHTML', false, `<span style="font-size: ${value}px">\u200B</span>`);
                }
            }
        } else if (command === 'fontName') {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                if (!range.collapsed) {
                    const span = document.createElement('span');
                    span.style.fontFamily = value;
                    range.surroundContents(span);
                }
            }
        } else {
            // Use execCommand for bold, italic, foreColor
            document.execCommand(command, false, value);
        }
    }

    /**
     * Commit the text to the canvas.
     */
    commitText() {
        if (!this.editorElement) return;

        const html = this.editorElement.innerHTML.trim();
        const plainText = this.editorElement.textContent.trim();

        if (plainText) {
            // Parse HTML into runs, passing default styles so colors are preserved
            const defaultStyle = {
                color: this._editorDefaultColor || this.app.foregroundColor || '#000000',
                fontSize: this.fontSize,
                fontFamily: this.fontFamily,
                fontWeight: this.fontWeight,
                fontStyle: this.fontStyle
            };
            const runs = TextLayer.htmlToRuns(html, defaultStyle);

            if (this.editingLayer) {
                // Update existing text layer
                this.app.history.saveState('Edit Text');
                this.editingLayer.setRuns(runs);
                this.editingLayer.setFontSize(this.fontSize);
                this.editingLayer.setFontFamily(this.fontFamily);
                this.editingLayer.setTextAlign(this.textAlign);
                this.editingLayer.deselect();
                this.app.history.finishState();
            } else {
                // Create new text layer
                this.createTextLayer(runs, this.textX, this.textY);
            }
            this.app.renderer.requestRender();
        } else if (this.editingLayer) {
            this.editingLayer.deselect();
            this.app.renderer.requestRender();
        }

        this.cleanup();
    }

    /**
     * Cancel text entry.
     */
    cancelText() {
        if (this.editingLayer) {
            this.editingLayer.deselect();
            this.app.renderer.requestRender();
        }
        this.cleanup();
    }

    /**
     * Create a new text layer with rich text runs.
     */
    createTextLayer(runs, x, y) {
        // If runs is a string (plain text), convert to single run
        if (typeof runs === 'string') {
            runs = [{ text: runs }];
        }

        const textLayer = new TextLayer({
            name: this._generateLayerName(runs),
            runs: runs,
            x: x,
            y: y,
            fontSize: this.fontSize,
            fontFamily: this.fontFamily,
            fontWeight: this.fontWeight,
            fontStyle: this.fontStyle,
            textAlign: this.textAlign,
            color: this.app.foregroundColor || '#000000',
            docWidth: this.app.layerStack.width,
            docHeight: this.app.layerStack.height
        });

        this.app.history.saveState('Add Text');
        this.app.layerStack.addLayer(textLayer);
        this.app.history.finishState();

        this.app.eventBus?.emit('layer:added', { layer: textLayer });
    }

    /**
     * Generate a layer name from runs.
     */
    _generateLayerName(runs) {
        const text = runs.map(r => r.text).join('').substring(0, 20);
        return `Text: ${text}${runs.map(r => r.text).join('').length > 20 ? '...' : ''}`;
    }

    /**
     * Clean up the editor.
     */
    cleanup() {
        if (this.editorContainer) {
            this.editorContainer.remove();
            this.editorContainer = null;
        }
        this.editorElement = null;
        this.toolbar = null;
        this.isEditing = false;
        this.editingLayer = null;
        this._editorDefaultColor = null;
        this._preventCanvasFocus = false;
    }

    /**
     * Update tool property.
     */
    setProperty(id, value) {
        super.setProperty(id, value);

        if (this.isEditing && this.editorElement) {
            const scaledFontSize = this.fontSize * this.app.renderer.zoom;
            this.editorElement.style.fontSize = `${scaledFontSize}px`;
            this.editorElement.style.fontFamily = this.fontFamily;
        }
    }

    getProperties() {
        return [
            { id: 'fontSize', name: 'Size', type: 'range', min: 8, max: 200, step: 1, value: this.fontSize },
            { id: 'fontFamily', name: 'Font', type: 'select', options: [
                'Arial', 'Helvetica', 'Times New Roman', 'Georgia',
                'Courier New', 'Verdana', 'Impact', 'Comic Sans MS',
                'Trebuchet MS', 'Palatino', 'Garamond', 'Bookman'
            ], value: this.fontFamily },
            { id: 'fontWeight', name: 'Weight', type: 'select', options: ['normal', 'bold'], value: this.fontWeight },
            { id: 'fontStyle', name: 'Style', type: 'select', options: ['normal', 'italic'], value: this.fontStyle },
            { id: 'textAlign', name: 'Align', type: 'select', options: ['left', 'center', 'right'], value: this.textAlign }
        ];
    }

    getHint() {
        if (this.isEditing) {
            return 'Format with toolbar, Ctrl+Enter to confirm, Escape to cancel';
        }
        return 'Click to add text, click existing text to edit';
    }

    // API execution
    executeAction(action, params) {
        if (action === 'create' || action === 'draw' || action === 'write') {
            const text = params.text;
            if (!text) {
                return { success: false, error: 'No text provided' };
            }

            const x = params.x !== undefined ? params.x : 0;
            const y = params.y !== undefined ? params.y : 0;

            if (params.fontSize !== undefined) this.fontSize = params.fontSize;
            if (params.fontFamily) this.fontFamily = params.fontFamily;
            if (params.fontWeight) this.fontWeight = params.fontWeight;
            if (params.fontStyle) this.fontStyle = params.fontStyle;
            if (params.color) this.app.foregroundColor = params.color;
            if (params.textAlign) this.textAlign = params.textAlign;

            // Support both plain text and runs
            const runs = params.runs || [{ text }];
            this.createTextLayer(runs, x, y);
            return { success: true };
        }

        if (action === 'edit') {
            const layerId = params.layerId;
            const layer = this.app.layerStack.getLayerById(layerId);
            if (!layer || !layer.isText?.()) {
                return { success: false, error: 'Text layer not found' };
            }

            this.app.history.saveState('Edit Text');
            if (params.text !== undefined) layer.setText(params.text);
            if (params.runs !== undefined) layer.setRuns(params.runs);
            if (params.fontSize !== undefined) layer.setFontSize(params.fontSize);
            if (params.fontFamily) layer.setFontFamily(params.fontFamily);
            if (params.fontWeight) layer.setFontWeight(params.fontWeight);
            if (params.fontStyle) layer.setFontStyle(params.fontStyle);
            if (params.color) layer.setColor(params.color);
            if (params.textAlign) layer.setTextAlign(params.textAlign);
            if (params.x !== undefined && params.y !== undefined) {
                layer.setPosition(params.x, params.y);
            }
            this.app.history.finishState();
            this.app.renderer.requestRender();

            return { success: true };
        }

        return { success: false, error: `Unknown action: ${action}` };
    }
}
