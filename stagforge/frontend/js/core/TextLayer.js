/**
 * TextLayer - A layer that contains rich text with multiple styled runs.
 *
 * Supports multiple text runs, each with individual:
 * - fontSize, fontFamily, fontWeight, fontStyle, color
 *
 * Text remains editable until the layer is rasterized.
 */
import { Layer } from './Layer.js';
import { lanczosResample } from '../utils/lanczos.js';
import { MAX_DIMENSION } from '../config/limits.js';

/**
 * A single styled text run within a TextLayer.
 * @typedef {Object} TextRun
 * @property {string} text - The text content
 * @property {number} [fontSize] - Font size in pixels (inherits from layer default if not set)
 * @property {string} [fontFamily] - Font family (inherits from layer default if not set)
 * @property {string} [fontWeight] - Font weight: 'normal' or 'bold'
 * @property {string} [fontStyle] - Font style: 'normal' or 'italic'
 * @property {string} [color] - Text color (inherits from layer default if not set)
 */

export class TextLayer extends Layer {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {string} [options.id]
     * @param {string} [options.name]
     * @param {number} [options.opacity]
     * @param {string} [options.blendMode]
     * @param {boolean} [options.visible]
     * @param {boolean} [options.locked]
     * @param {string} [options.text] - Plain text content (converted to single run)
     * @param {TextRun[]} [options.runs] - Rich text runs (takes precedence over text)
     * @param {number} [options.x] - Position X in document space
     * @param {number} [options.y] - Position Y in document space
     * @param {number} [options.fontSize] - Default font size in pixels
     * @param {string} [options.fontFamily] - Default font family
     * @param {string} [options.fontWeight] - Default font weight (normal, bold)
     * @param {string} [options.fontStyle] - Default font style (normal, italic)
     * @param {string} [options.textAlign] - Text alignment (left, center, right)
     * @param {string} [options.color] - Default text color
     * @param {number} [options.lineHeight] - Line height multiplier
     */
    constructor(options = {}) {
        // Start with minimal size, will resize after measuring text
        const initialWidth = options.width || 100;
        const initialHeight = options.height || 50;

        super({
            ...options,
            width: initialWidth,
            height: initialHeight,
            offsetX: options.x ?? options.offsetX ?? 0,
            offsetY: options.y ?? options.offsetY ?? 0
        });

        // Mark as text layer
        this.type = 'text';

        // Default typography settings (used when runs don't specify)
        this.fontSize = options.fontSize ?? 24;
        this.fontFamily = options.fontFamily || 'Arial';
        this.fontWeight = options.fontWeight || 'normal';
        this.fontStyle = options.fontStyle || 'normal';
        this.textAlign = options.textAlign || 'left';
        this.color = options.color || '#000000';

        // Line height multiplier
        this.lineHeight = options.lineHeight ?? 1.2;

        // Padding around text
        this.padding = 4;

        // Left overhang for characters that extend past origin (set by measureText)
        this._leftOverhang = 0;

        // Render scale for crisp text (4x for high quality, independent of display DPR)
        this._renderScale = 4;

        // High-resolution canvas for text rendering
        this._hiResCanvas = document.createElement('canvas');
        this._hiResCtx = this._hiResCanvas.getContext('2d');

        // Rich text runs - array of styled text segments
        // Each run can have: text, fontSize, fontFamily, fontWeight, fontStyle, color
        if (options.runs && Array.isArray(options.runs)) {
            this.runs = options.runs.map(run => ({ ...run }));
        } else if (options.text) {
            // Convert plain text to single run
            this.runs = [{ text: options.text }];
        } else {
            this.runs = [];
        }

        // Selection state (for editing)
        this.isSelected = false;

        // Document dimensions for reference
        this._docWidth = options.docWidth || 800;
        this._docHeight = options.docHeight || 600;

        // Initial render and size calculation
        if (this.runs.length > 0) {
            this._updateBounds();
            this.render();
        }
    }

    /**
     * Check if this is a text layer.
     * @returns {boolean}
     */
    isText() {
        return true;
    }

    /**
     * TextLayer is not a vector layer. Use isText() to check for text layers.
     * @returns {boolean}
     */
    isVector() {
        return false;
    }

    /**
     * Get plain text content (all runs concatenated).
     * @returns {string}
     */
    get text() {
        return this.runs.map(run => run.text).join('');
    }

    /**
     * Set plain text content (replaces all runs with single unstyled run).
     * @param {string} value
     */
    set text(value) {
        this.runs = [{ text: value }];
        this._updateBounds();
        this.render();
    }

    /**
     * Get the font string for a run.
     * @param {TextRun} run
     * @returns {string}
     */
    getFontString(run = {}) {
        const style = run.fontStyle ?? this.fontStyle;
        const weight = run.fontWeight ?? this.fontWeight;
        const size = run.fontSize ?? this.fontSize;
        const family = run.fontFamily ?? this.fontFamily;
        return `${style} ${weight} ${size}px ${family}`;
    }

    /**
     * Get effective font size for a run.
     * @param {TextRun} run
     * @returns {number}
     */
    getRunFontSize(run = {}) {
        return run.fontSize ?? this.fontSize;
    }

    /**
     * Get effective color for a run.
     * @param {TextRun} run
     * @returns {string}
     */
    getRunColor(run = {}) {
        return run.color ?? this.color;
    }

    /**
     * Parse runs into lines for rendering.
     * Handles newlines within runs and creates line-based structure.
     * @returns {Array<Array<{run: TextRun, text: string}>>}
     */
    _parseLines() {
        const lines = [[]];
        let currentLine = 0;

        for (const run of this.runs) {
            const parts = run.text.split('\n');
            for (let i = 0; i < parts.length; i++) {
                if (i > 0) {
                    // New line
                    currentLine++;
                    lines[currentLine] = [];
                }
                if (parts[i]) {
                    lines[currentLine].push({ run, text: parts[i] });
                }
            }
        }

        return lines;
    }

    /**
     * Measure the text and return dimensions.
     * Uses actualBoundingBox metrics to account for character overhang.
     * @returns {{width: number, height: number, lineHeights: number[], leftOverhang: number}}
     */
    measureText() {
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');

        const lines = this._parseLines();
        const lineHeights = [];
        let maxWidth = 0;
        let totalHeight = 0;
        let maxLeftOverhang = 0;
        let maxRightOverhang = 0;

        for (const lineRuns of lines) {
            let lineWidth = 0;
            let lineMaxFontSize = this.fontSize; // Default if line is empty
            let isFirstInLine = true;

            for (const { run, text } of lineRuns) {
                tempCtx.font = this.getFontString(run);
                const metrics = tempCtx.measureText(text);

                // Check for left overhang on first character of line
                if (isFirstInLine && metrics.actualBoundingBoxLeft !== undefined) {
                    maxLeftOverhang = Math.max(maxLeftOverhang, metrics.actualBoundingBoxLeft);
                }

                // Check for right overhang (text extending past advance width)
                if (metrics.actualBoundingBoxRight !== undefined) {
                    const rightOverhang = metrics.actualBoundingBoxRight - metrics.width;
                    if (rightOverhang > 0) {
                        maxRightOverhang = Math.max(maxRightOverhang, rightOverhang);
                    }
                }

                lineWidth += metrics.width;
                lineMaxFontSize = Math.max(lineMaxFontSize, this.getRunFontSize(run));
                isFirstInLine = false;
            }

            // If line is empty (just newline), use default font size
            if (lineRuns.length === 0) {
                lineMaxFontSize = this.fontSize;
            }

            const lineHeight = lineMaxFontSize * this.lineHeight;
            lineHeights.push(lineHeight);
            maxWidth = Math.max(maxWidth, lineWidth);
            totalHeight += lineHeight;
        }

        // Add extra padding for overhangs
        const extraLeft = Math.ceil(maxLeftOverhang);
        const extraRight = Math.ceil(maxRightOverhang);

        return {
            width: Math.ceil(maxWidth) + this.padding * 2 + extraLeft + extraRight,
            height: Math.ceil(totalHeight) + this.padding * 2,
            lineHeights,
            leftOverhang: extraLeft
        };
    }

    /**
     * Update layer bounds to match text content.
     */
    _updateBounds() {
        if (this.runs.length === 0 || this.text === '') {
            this.width = 100;
            this.height = this.fontSize + this.padding * 2;
            this._leftOverhang = 0;
            this._resizeCanvases(this.width, this.height);
            return;
        }

        const { width, height, leftOverhang } = this.measureText();
        this._leftOverhang = leftOverhang;

        // Clamp dimensions to MAX_DIMENSION to prevent memory issues
        const clampedWidth = Math.min(MAX_DIMENSION, width);
        const clampedHeight = Math.min(MAX_DIMENSION, height);

        // Resize canvases if needed
        if (this.width !== clampedWidth || this.height !== clampedHeight) {
            this.width = clampedWidth;
            this.height = clampedHeight;
            this._resizeCanvases(clampedWidth, clampedHeight);
        }
    }

    /**
     * Resize both the output canvas and high-res rendering canvas.
     */
    _resizeCanvases(width, height) {
        const scale = this._renderScale;

        // Clamp dimensions to MAX_DIMENSION
        const clampedWidth = Math.min(MAX_DIMENSION, width);
        const clampedHeight = Math.min(MAX_DIMENSION, height);

        // Output canvas at logical size
        this.canvas.width = clampedWidth;
        this.canvas.height = clampedHeight;

        // High-res canvas for crisp text rendering (4x)
        // Also clamp hi-res to MAX_DIMENSION to prevent memory issues
        this._hiResCanvas.width = Math.min(MAX_DIMENSION, Math.ceil(clampedWidth * scale));
        this._hiResCanvas.height = Math.min(MAX_DIMENSION, Math.ceil(clampedHeight * scale));
    }

    /**
     * Set plain text content (replaces all runs).
     * @param {string} text
     */
    setText(text) {
        this.runs = [{ text }];
        this._updateBounds();
        this.render();
    }

    /**
     * Set rich text runs.
     * @param {TextRun[]} runs
     */
    setRuns(runs) {
        this.runs = runs.map(run => ({ ...run }));
        this._updateBounds();
        this.render();
    }

    /**
     * Add a styled text run.
     * @param {TextRun} run
     */
    addRun(run) {
        this.runs.push({ ...run });
        this._updateBounds();
        this.render();
    }

    /**
     * Set text position in document space.
     * @param {number} x
     * @param {number} y
     */
    setPosition(x, y) {
        this.offsetX = x;
        this.offsetY = y;
    }

    /**
     * Get text position in document space.
     * @returns {{x: number, y: number}}
     */
    getPosition() {
        return { x: this.offsetX, y: this.offsetY };
    }

    /**
     * Set default font size (affects runs without explicit fontSize).
     * @param {number} size
     */
    setFontSize(size) {
        this.fontSize = size;
        this._updateBounds();
        this.render();
    }

    /**
     * Set default font family.
     * @param {string} family
     */
    setFontFamily(family) {
        this.fontFamily = family;
        this._updateBounds();
        this.render();
    }

    /**
     * Set default font weight.
     * @param {string} weight
     */
    setFontWeight(weight) {
        this.fontWeight = weight;
        this._updateBounds();
        this.render();
    }

    /**
     * Set default font style.
     * @param {string} style
     */
    setFontStyle(style) {
        this.fontStyle = style;
        this._updateBounds();
        this.render();
    }

    /**
     * Set default text color.
     * @param {string} color
     */
    setColor(color) {
        this.color = color;
        this.render();
    }

    /**
     * Set text alignment.
     * @param {string} align
     */
    setTextAlign(align) {
        this.textAlign = align;
        this.render();
    }

    /**
     * Apply formatting to all runs.
     * @param {Object} formatting - Properties to apply
     */
    applyFormattingToAll(formatting) {
        for (const run of this.runs) {
            Object.assign(run, formatting);
        }
        this._updateBounds();
        this.render();
    }

    /**
     * Check if a point (in document coordinates) is within the text layer.
     * @param {number} x
     * @param {number} y
     * @returns {boolean}
     */
    containsPoint(x, y) {
        const bounds = this.getBounds();
        return x >= bounds.x && x <= bounds.x + bounds.width &&
               y >= bounds.y && y <= bounds.y + bounds.height;
    }

    /**
     * Get the bounding box in document coordinates.
     * @returns {{x: number, y: number, width: number, height: number}}
     */
    getBounds() {
        return {
            x: this.offsetX,
            y: this.offsetY,
            width: this.width,
            height: this.height
        };
    }

    /**
     * Render the text to the canvas using high-resolution rendering for crisp text.
     * Uses 4x rendering with Lanczos downscaling for maximum quality.
     */
    render() {
        const scale = this._renderScale;
        const hiCtx = this._hiResCtx;

        // Clear canvases
        this.ctx.clearRect(0, 0, this.width, this.height);
        hiCtx.clearRect(0, 0, this._hiResCanvas.width, this._hiResCanvas.height);

        if (this.runs.length === 0) return;

        // Render text at 4x resolution
        hiCtx.save();
        hiCtx.scale(scale, scale);

        const lines = this._parseLines();
        const { lineHeights } = this.measureText();

        hiCtx.textBaseline = 'top';

        let y = this.padding;

        for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
            const lineRuns = lines[lineIdx];
            const lineHeight = lineHeights[lineIdx];

            // Calculate line width for alignment
            let lineWidth = 0;
            for (const { run, text } of lineRuns) {
                hiCtx.font = this.getFontString(run);
                lineWidth += hiCtx.measureText(text).width;
            }

            // Calculate starting X based on alignment (account for left overhang)
            const leftOffset = this.padding + (this._leftOverhang || 0);
            let x = leftOffset;
            if (this.textAlign === 'center') {
                x = (this.width - lineWidth) / 2;
            } else if (this.textAlign === 'right') {
                x = this.width - this.padding - lineWidth;
            }

            // Render each run in the line
            for (const { run, text } of lineRuns) {
                hiCtx.font = this.getFontString(run);
                hiCtx.fillStyle = this.getRunColor(run);

                // Vertical alignment within line (center smaller fonts)
                const runFontSize = this.getRunFontSize(run);
                const runLineHeight = runFontSize * this.lineHeight;
                const yOffset = (lineHeight - runLineHeight) / 2;

                hiCtx.fillText(text, x, y + yOffset);
                x += hiCtx.measureText(text).width;
            }

            y += lineHeight;
        }

        hiCtx.restore();

        // Lanczos downscale from 4x to 1x
        const hiResData = hiCtx.getImageData(0, 0, this._hiResCanvas.width, this._hiResCanvas.height);
        const downscaled = lanczosResample(hiResData, this.width, this.height, 3);
        this.ctx.putImageData(downscaled, 0, 0);

        // Draw selection box if selected
        if (this.isSelected) {
            this.renderSelection();
        }
    }

    /**
     * Render selection handles around the text.
     */
    renderSelection() {
        // Selection rectangle (inside canvas bounds)
        this.ctx.strokeStyle = '#0078d4';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([4, 4]);
        this.ctx.strokeRect(1, 1, this.width - 2, this.height - 2);
        this.ctx.setLineDash([]);

        // Corner handles
        const handleSize = 8;
        const corners = [
            { x: 0, y: 0 },
            { x: this.width - handleSize, y: 0 },
            { x: 0, y: this.height - handleSize },
            { x: this.width - handleSize, y: this.height - handleSize }
        ];

        this.ctx.fillStyle = 'white';
        this.ctx.strokeStyle = '#0078d4';
        this.ctx.lineWidth = 1;

        for (const corner of corners) {
            this.ctx.fillRect(corner.x, corner.y, handleSize, handleSize);
            this.ctx.strokeRect(corner.x, corner.y, handleSize, handleSize);
        }
    }

    /**
     * Select this text layer for editing.
     */
    select() {
        this.isSelected = true;
        this.render();
    }

    /**
     * Deselect this text layer.
     */
    deselect() {
        this.isSelected = false;
        this.render();
    }

    /**
     * Convert document coordinates to layer-local coordinates.
     * @param {number} docX
     * @param {number} docY
     * @returns {{x: number, y: number}}
     */
    docToCanvas(docX, docY) {
        return {
            x: docX - this.offsetX,
            y: docY - this.offsetY
        };
    }

    /**
     * Convert layer-local coordinates to document coordinates.
     * @param {number} canvasX
     * @param {number} canvasY
     * @returns {{x: number, y: number}}
     */
    canvasToDoc(canvasX, canvasY) {
        return {
            x: canvasX + this.offsetX,
            y: canvasY + this.offsetY
        };
    }

    /**
     * Rotate the text layer by the given degrees (90, 180, or 270).
     * Text layers use transform-based rotation - the text content is never modified.
     * The render() method handles applying the rotation transform during rendering.
     *
     * @param {number} degrees - Rotation angle (90, 180, or 270)
     * @param {number} oldDocWidth - Document width before rotation
     * @param {number} oldDocHeight - Document height before rotation
     * @param {number} newDocWidth - Document width after rotation (unused, kept for API consistency)
     * @param {number} newDocHeight - Document height after rotation (unused, kept for API consistency)
     * @returns {Promise<void>}
     */
    async rotateCanvas(degrees, oldDocWidth, oldDocHeight, newDocWidth, newDocHeight) {
        if (![90, 180, 270].includes(degrees)) {
            console.error('[TextLayer] Invalid rotation angle:', degrees);
            return;
        }

        const oldOffsetX = this.offsetX || 0;
        const oldOffsetY = this.offsetY || 0;
        const oldWidth = this.width;
        const oldHeight = this.height;

        // Calculate the layer center in old document coordinates
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

        // Rotate the center point using exact 90-degree formulas
        let newCenterX, newCenterY;
        if (degrees === 90) {
            newCenterX = oldDocHeight - layerCenterY;
            newCenterY = layerCenterX;
        } else if (degrees === 180) {
            newCenterX = oldDocWidth - layerCenterX;
            newCenterY = oldDocHeight - layerCenterY;
        } else if (degrees === 270) {
            newCenterX = layerCenterY;
            newCenterY = oldDocWidth - layerCenterX;
        } else {
            newCenterX = layerCenterX;
            newCenterY = layerCenterY;
        }

        // For text layers, rotation is purely transform-based.
        // Update the rotation property - render() handles the rest.
        this.rotation = ((this.rotation || 0) + degrees) % 360;

        // Calculate new offset from center (layer dimensions stay the same)
        this.offsetX = Math.round(newCenterX - oldWidth / 2);
        this.offsetY = Math.round(newCenterY - oldHeight / 2);

        // Re-render text with updated rotation transform
        this.render?.();
    }

    /**
     * Mirror the text layer using negative scaling.
     * Text layers use transform-based mirroring - the text content is never modified.
     *
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @param {number} docWidth - Document width
     * @param {number} docHeight - Document height
     * @returns {Promise<void>}
     */
    async mirrorContent(direction, docWidth, docHeight) {
        if (!['horizontal', 'vertical'].includes(direction)) {
            console.error('[TextLayer] Invalid mirror direction:', direction);
            return;
        }

        // Use negative scale to mirror
        if (direction === 'horizontal') {
            this.scaleX = -(this.scaleX || 1);
            // Mirror offset position
            this.offsetX = docWidth - this.offsetX - this.width;
        } else {
            this.scaleY = -(this.scaleY || 1);
            // Mirror offset position
            this.offsetY = docHeight - this.offsetY - this.height;
        }

        // Re-render with new scale
        this.render?.();
    }

    /**
     * Rasterize the text layer to a regular bitmap layer.
     * @returns {Layer} A new raster Layer with the text rendered
     */
    rasterize() {
        // Make sure canvas is up to date (without selection)
        const wasSelected = this.isSelected;
        this.isSelected = false;
        this.render();

        // Create a new bitmap layer with same bounds
        const rasterLayer = new Layer({
            width: this.width,
            height: this.height,
            name: this.name,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            offsetX: this.offsetX,
            offsetY: this.offsetY
        });

        // Copy the rendered content
        rasterLayer.ctx.drawImage(this.canvas, 0, 0);

        // Restore selection state
        this.isSelected = wasSelected;
        if (wasSelected) this.render();

        return rasterLayer;
    }

    /**
     * Serialize the text layer for saving.
     * @returns {Object}
     */
    serialize() {
        return {
            _version: TextLayer.VERSION,
            _type: 'TextLayer',
            type: 'text',
            id: this.id,
            name: this.name,
            x: this.offsetX,
            y: this.offsetY,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            // Rich text data
            runs: this.runs.map(run => ({ ...run })),
            // Default styles
            fontSize: this.fontSize,
            fontFamily: this.fontFamily,
            fontWeight: this.fontWeight,
            fontStyle: this.fontStyle,
            textAlign: this.textAlign,
            color: this.color,
            lineHeight: this.lineHeight
        };
    }

    /**
     * Migrate serialized data from older versions.
     * @param {Object} data - Serialized text layer data
     * @returns {Object} - Migrated data at current version
     */
    static migrate(data) {
        // Handle pre-versioned data
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Ensure default styles exist
        if (data._version < 1) {
            data.fontSize = data.fontSize || 24;
            data.fontFamily = data.fontFamily || 'Arial';
            data.fontWeight = data.fontWeight || 'normal';
            data.fontStyle = data.fontStyle || 'normal';
            data.textAlign = data.textAlign || 'left';
            data.color = data.color || '#000000';
            data.lineHeight = data.lineHeight || 1.2;
            data._version = 1;
        }

        // Future migrations:
        // if (data._version < 2) { ... data._version = 2; }

        return data;
    }

    /**
     * Create a TextLayer from serialized data.
     * @param {Object} data
     * @returns {TextLayer}
     */
    static deserialize(data) {
        // Migrate to current version
        data = TextLayer.migrate(data);

        return new TextLayer({
            ...data,
            offsetX: data.x,
            offsetY: data.y
        });
    }

    /**
     * Convert HTML from contenteditable to runs.
     * Parses inline styles for font-size, font-family, font-weight, font-style, color.
     * @param {string} html
     * @param {Object} [defaultStyle] - Default styles to use when not specified in HTML
     * @returns {TextRun[]}
     */
    static htmlToRuns(html, defaultStyle = {}) {
        const container = document.createElement('div');
        container.innerHTML = html;

        const runs = [];

        // Start with default styles as the base inherited style
        const baseStyle = {
            color: defaultStyle.color || null,
            fontSize: defaultStyle.fontSize || null,
            fontFamily: defaultStyle.fontFamily || null,
            fontWeight: defaultStyle.fontWeight || null,
            fontStyle: defaultStyle.fontStyle || null
        };

        function processNode(node, inheritedStyle = baseStyle) {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent;
                if (text) {
                    const run = { text };
                    // Apply inherited styles (only non-null values)
                    if (inheritedStyle.fontSize) run.fontSize = inheritedStyle.fontSize;
                    if (inheritedStyle.fontFamily) run.fontFamily = inheritedStyle.fontFamily;
                    if (inheritedStyle.fontWeight && inheritedStyle.fontWeight !== 'normal') {
                        run.fontWeight = inheritedStyle.fontWeight;
                    }
                    if (inheritedStyle.fontStyle && inheritedStyle.fontStyle !== 'normal') {
                        run.fontStyle = inheritedStyle.fontStyle;
                    }
                    if (inheritedStyle.color) run.color = inheritedStyle.color;
                    runs.push(run);
                }
                return;
            }

            if (node.nodeType === Node.ELEMENT_NODE) {
                const style = { ...inheritedStyle };
                const inlineStyle = node.style;

                // Parse inline styles
                if (inlineStyle.fontSize) {
                    style.fontSize = parseInt(inlineStyle.fontSize);
                }
                if (inlineStyle.fontFamily) {
                    style.fontFamily = inlineStyle.fontFamily.replace(/['"]/g, '');
                }
                // Handle bold - from style or tag
                if (inlineStyle.fontWeight) {
                    style.fontWeight = inlineStyle.fontWeight;
                } else if (node.tagName === 'B' || node.tagName === 'STRONG') {
                    style.fontWeight = 'bold';
                }
                // Handle italic - from style or tag
                if (inlineStyle.fontStyle) {
                    style.fontStyle = inlineStyle.fontStyle;
                } else if (node.tagName === 'I' || node.tagName === 'EM') {
                    style.fontStyle = 'italic';
                }
                if (inlineStyle.color) {
                    style.color = inlineStyle.color;
                }

                // Handle BR as newline
                if (node.tagName === 'BR') {
                    runs.push({ text: '\n' });
                    return;
                }

                // Handle DIV/P as newline (if not first element)
                if ((node.tagName === 'DIV' || node.tagName === 'P') && runs.length > 0) {
                    // Add newline before block element content
                    const lastRun = runs[runs.length - 1];
                    if (lastRun && !lastRun.text.endsWith('\n')) {
                        runs.push({ text: '\n' });
                    }
                }

                // Process children
                for (const child of node.childNodes) {
                    processNode(child, style);
                }
            }
        }

        processNode(container);

        // Clean up: merge adjacent runs with same style, remove trailing newlines
        const mergedRuns = [];
        for (const run of runs) {
            const last = mergedRuns[mergedRuns.length - 1];
            if (last &&
                last.fontSize === run.fontSize &&
                last.fontFamily === run.fontFamily &&
                last.fontWeight === run.fontWeight &&
                last.fontStyle === run.fontStyle &&
                last.color === run.color) {
                last.text += run.text;
            } else {
                mergedRuns.push(run);
            }
        }

        return mergedRuns;
    }

    /**
     * Convert runs to HTML for contenteditable.
     * @param {TextRun[]} runs
     * @param {Object} defaults - Default styles
     * @returns {string}
     */
    static runsToHtml(runs, defaults = {}) {
        let html = '';

        for (const run of runs) {
            let text = run.text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

            // Handle newlines
            text = text.replace(/\n/g, '<br>');

            // Build inline style
            const styles = [];
            if (run.fontSize && run.fontSize !== defaults.fontSize) {
                styles.push(`font-size: ${run.fontSize}px`);
            }
            if (run.fontFamily && run.fontFamily !== defaults.fontFamily) {
                styles.push(`font-family: ${run.fontFamily}`);
            }
            if (run.fontWeight && run.fontWeight !== defaults.fontWeight) {
                styles.push(`font-weight: ${run.fontWeight}`);
            }
            if (run.fontStyle && run.fontStyle !== defaults.fontStyle) {
                styles.push(`font-style: ${run.fontStyle}`);
            }
            if (run.color && run.color !== defaults.color) {
                styles.push(`color: ${run.color}`);
            }

            if (styles.length > 0) {
                html += `<span style="${styles.join('; ')}">${text}</span>`;
            } else {
                html += text;
            }
        }

        return html;
    }

    /**
     * Check if this is an SVG layer.
     * @returns {boolean}
     */
    isSVG() {
        return false;
    }
}

// Register TextLayer with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('text', TextLayer, ['TextLayer']);
