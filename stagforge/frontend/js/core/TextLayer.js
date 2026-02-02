/**
 * TextLayer - A layer that contains rich text rendered as SVG.
 *
 * Supports multiple text runs, each with individual:
 * - fontSize, fontFamily, fontWeight, fontStyle, color
 *
 * Text is rendered as SVG for scalability in exports. The SVG is generated
 * from the text runs and rendered to canvas for display.
 *
 * Text remains editable until the layer is rasterized.
 *
 * Extends SVGBaseLayer which provides:
 * - SVG transform envelope (rotation, scale, mirror)
 * - Zoom-aware rendering with high-res display canvas
 * - Cross-platform rendering parity
 */
import { SVGBaseLayer } from './SVGBaseLayer.js';
import { PixelLayer } from './PixelLayer.js';
import { LayerEffect, effectRegistry } from './LayerEffects.js';
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

/**
 * Escape XML special characters.
 * @param {string} text
 * @returns {string}
 */
function escapeXml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

export class TextLayer extends SVGBaseLayer {
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
            name: options.name || 'Text',
            type: 'text',
            width: initialWidth,
            height: initialHeight,
            offsetX: options.x ?? options.offsetX ?? 0,
            offsetY: options.y ?? options.offsetY ?? 0
        });

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

        // Rich text runs - array of styled text segments
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
            this.updateSvgData();
        }
    }

    // ==================== Type Checks ====================

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

    // ==================== Text Content ====================

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
        this.updateSvgData();
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
     * @returns {Array<Array<{run: TextRun, text: string}>>}
     */
    _parseLines() {
        const lines = [[]];
        let currentLine = 0;

        for (const run of this.runs) {
            const parts = run.text.split('\n');
            for (let i = 0; i < parts.length; i++) {
                if (i > 0) {
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
            let lineMaxFontSize = this.fontSize;
            let isFirstInLine = true;

            for (const { run, text } of lineRuns) {
                tempCtx.font = this.getFontString(run);
                const metrics = tempCtx.measureText(text);

                if (isFirstInLine && metrics.actualBoundingBoxLeft !== undefined) {
                    maxLeftOverhang = Math.max(maxLeftOverhang, metrics.actualBoundingBoxLeft);
                }

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

            if (lineRuns.length === 0) {
                lineMaxFontSize = this.fontSize;
            }

            const lineHeight = lineMaxFontSize * this.lineHeight;
            lineHeights.push(lineHeight);
            maxWidth = Math.max(maxWidth, lineWidth);
            totalHeight += lineHeight;
        }

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

        const clampedWidth = Math.min(MAX_DIMENSION, width);
        const clampedHeight = Math.min(MAX_DIMENSION, height);

        if (this.width !== clampedWidth || this.height !== clampedHeight) {
            this.width = clampedWidth;
            this.height = clampedHeight;
            this._resizeCanvases(clampedWidth, clampedHeight);
        }
    }

    /**
     * Resize both the output canvas and internal canvas.
     */
    _resizeCanvases(width, height) {
        const clampedWidth = Math.min(MAX_DIMENSION, width);
        const clampedHeight = Math.min(MAX_DIMENSION, height);

        this._canvas.width = clampedWidth;
        this._canvas.height = clampedHeight;
    }

    // ==================== SVG Generation ====================

    /**
     * Generate SVG from text properties.
     * This is called internally when text properties change.
     */
    updateSvgData() {
        if (this.runs.length === 0 || this.text === '') {
            this.svgData = '';
            this.renderedSvg = '';
            return;
        }

        const lines = this._parseLines();
        const { lineHeights } = this.measureText();

        const svgLines = [];
        let y = this.padding;

        for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
            const lineRuns = lines[lineIdx];
            const lineHeight = lineHeights[lineIdx];

            // Calculate line width for alignment
            let lineWidth = 0;
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');
            for (const { run, text } of lineRuns) {
                tempCtx.font = this.getFontString(run);
                lineWidth += tempCtx.measureText(text).width;
            }

            // Calculate starting X based on alignment
            const leftOffset = this.padding + (this._leftOverhang || 0);
            let x = leftOffset;
            if (this.textAlign === 'center') {
                x = (this.width - lineWidth) / 2;
            } else if (this.textAlign === 'right') {
                x = this.width - this.padding - lineWidth;
            }

            // Calculate baseline position (y is top of line, we need baseline)
            // For SVG, dominant-baseline="text-before-edge" positions at top
            const baselineY = y + lineHeight * 0.85; // Approximate baseline

            // Generate SVG tspans for each run in the line
            for (const { run, text } of lineRuns) {
                const fontSize = this.getRunFontSize(run);
                const fontFamily = run.fontFamily ?? this.fontFamily;
                const fontWeight = run.fontWeight ?? this.fontWeight;
                const fontStyle = run.fontStyle ?? this.fontStyle;
                const color = this.getRunColor(run);

                const textAttrs = [
                    `x="${x}"`,
                    `y="${baselineY}"`,
                    `font-family="${escapeXml(fontFamily)}"`,
                    `font-size="${fontSize}"`,
                    `font-weight="${fontWeight}"`,
                    `font-style="${fontStyle}"`,
                    `fill="${escapeXml(color)}"`
                ];

                // Handle text decorations
                const decorations = [];
                if (run.underline) decorations.push('underline');
                if (run.strikethrough) decorations.push('line-through');
                if (decorations.length > 0) {
                    textAttrs.push(`text-decoration="${decorations.join(' ')}"`);
                }

                // Handle letter spacing
                if (run.letterSpacing) {
                    textAttrs.push(`letter-spacing="${run.letterSpacing}"`);
                }

                svgLines.push(`<text ${textAttrs.join(' ')}>${escapeXml(text)}</text>`);

                // Update x position for next run
                tempCtx.font = this.getFontString(run);
                x += tempCtx.measureText(text).width;
            }

            y += lineHeight;
        }

        // Build complete SVG
        this.svgData = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
${svgLines.join('\n')}
</svg>`;

        // Apply transform envelope
        this.renderSvg();
    }

    /**
     * Convert layer content to SVG string.
     * @param {Object} [options]
     * @returns {string} SVG document string
     */
    toSVG(options = {}) {
        if (this.renderedSvg) {
            return this.renderedSvg;
        }
        return this.svgData || '';
    }

    // ==================== Text Modification Methods ====================

    /**
     * Set plain text content (replaces all runs).
     * @param {string} text
     */
    setText(text) {
        this.runs = [{ text }];
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    /**
     * Set rich text runs.
     * @param {TextRun[]} runs
     */
    setRuns(runs) {
        this.runs = runs.map(run => ({ ...run }));
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    /**
     * Add a styled text run.
     * @param {TextRun} run
     */
    addRun(run) {
        this.runs.push({ ...run });
        this._updateBounds();
        this.updateSvgData();
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
     * Set default font size.
     * @param {number} size
     */
    setFontSize(size) {
        this.fontSize = size;
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    /**
     * Set default font family.
     * @param {string} family
     */
    setFontFamily(family) {
        this.fontFamily = family;
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    /**
     * Set default font weight.
     * @param {string} weight
     */
    setFontWeight(weight) {
        this.fontWeight = weight;
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    /**
     * Set default font style.
     * @param {string} style
     */
    setFontStyle(style) {
        this.fontStyle = style;
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    /**
     * Set default text color.
     * @param {string} color
     */
    setColor(color) {
        this.color = color;
        this.updateSvgData();
        this.render();
    }

    /**
     * Set text alignment.
     * @param {string} align
     */
    setTextAlign(align) {
        this.textAlign = align;
        this.updateSvgData();
        this.render();
    }

    /**
     * Apply formatting to all runs.
     * @param {Object} formatting
     */
    applyFormattingToAll(formatting) {
        for (const run of this.runs) {
            Object.assign(run, formatting);
        }
        this._updateBounds();
        this.updateSvgData();
        this.render();
    }

    // ==================== Selection and Interaction ====================

    /**
     * Check if a point is within the text layer.
     * @param {number} x
     * @param {number} y
     * @returns {boolean}
     */
    containsPoint(x, y) {
        // Use getDocumentBounds() for proper hit testing in document coordinates
        const bounds = this.getDocumentBounds();
        return x >= bounds.x && x <= bounds.x + bounds.width &&
               y >= bounds.y && y <= bounds.y + bounds.height;
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

    // ==================== Rendering ====================

    /**
     * Render the text layer.
     * First renders the SVG, then optionally draws selection indicators.
     * @returns {Promise<void>}
     */
    async render() {
        // Use base class SVG rendering
        await super.render();

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
        this._ctx.strokeStyle = '#0078d4';
        this._ctx.lineWidth = 2;
        this._ctx.setLineDash([4, 4]);
        this._ctx.strokeRect(1, 1, this.width - 2, this.height - 2);
        this._ctx.setLineDash([]);

        // Corner handles
        const handleSize = 8;
        const corners = [
            { x: 0, y: 0 },
            { x: this.width - handleSize, y: 0 },
            { x: 0, y: this.height - handleSize },
            { x: this.width - handleSize, y: this.height - handleSize }
        ];

        this._ctx.fillStyle = 'white';
        this._ctx.strokeStyle = '#0078d4';
        this._ctx.lineWidth = 1;

        for (const corner of corners) {
            this._ctx.fillRect(corner.x, corner.y, handleSize, handleSize);
            this._ctx.strokeRect(corner.x, corner.y, handleSize, handleSize);
        }
    }

    // ==================== Rasterization ====================

    /**
     * Rasterize the text layer to a regular bitmap layer.
     * @returns {PixelLayer}
     */
    rasterize() {
        // Make sure canvas is up to date (without selection)
        const wasSelected = this.isSelected;
        this.isSelected = false;
        this.render();

        const rasterLayer = new PixelLayer({
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

        rasterLayer.ctx.drawImage(this.canvas, 0, 0);

        // Restore selection state
        this.isSelected = wasSelected;
        if (wasSelected) this.render();

        return rasterLayer;
    }

    // ==================== SVG Export ====================

    /**
     * Convert this layer to an SVG element for document export.
     * Creates a <g> with sf:type="text" and includes all text properties.
     *
     * @param {Document} xmlDoc - XML document for creating elements
     * @returns {Promise<Element>} SVG group element
     */
    async toSVGElement(xmlDoc) {
        const {
            STAGFORGE_NAMESPACE,
            STAGFORGE_PREFIX,
            createLayerGroup,
            createPropertiesElement
        } = await import('./svgExportUtils.js');

        // Create layer group with sf:type and sf:name
        const g = createLayerGroup(xmlDoc, this.id, 'text', this.name);

        // Add sf:properties element with all layer properties including text-specific ones
        const properties = {
            ...this.serializeBase(),
            // Text-specific properties
            runs: this.runs,
            fontSize: this.fontSize,
            fontFamily: this.fontFamily,
            fontWeight: this.fontWeight,
            fontStyle: this.fontStyle,
            textAlign: this.textAlign,
            color: this.color,
            lineHeight: this.lineHeight,
            // Position aliases
            x: this.offsetX,
            y: this.offsetY
        };
        const propsEl = createPropertiesElement(xmlDoc, properties);
        g.appendChild(propsEl);

        // Add the rendered SVG content
        const svgContent = this.renderedSvg || this.svgData || '';
        if (svgContent) {
            // Create a container group for positioning
            const contentGroup = xmlDoc.createElementNS('http://www.w3.org/2000/svg', 'g');
            contentGroup.setAttribute('transform', `translate(${this.offsetX}, ${this.offsetY})`);

            // Parse the SVG content and import it
            const parser = new DOMParser();
            const svgDoc = parser.parseFromString(svgContent, 'image/svg+xml');
            const svgRoot = svgDoc.documentElement;

            if (svgRoot && svgRoot.tagName === 'svg') {
                const importedSvg = xmlDoc.importNode(svgRoot, true);
                contentGroup.appendChild(importedSvg);
            }

            g.appendChild(contentGroup);
        }

        return g;
    }

    // ==================== Clone ====================

    /**
     * Clone this text layer.
     * @returns {TextLayer}
     */
    clone() {
        const cloned = new TextLayer({
            width: this.width,
            height: this.height,
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            rotation: this.rotation,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            parentId: this.parentId,
            name: `${this.name} (copy)`,
            runs: this.runs.map(run => ({ ...run })),
            fontSize: this.fontSize,
            fontFamily: this.fontFamily,
            fontWeight: this.fontWeight,
            fontStyle: this.fontStyle,
            textAlign: this.textAlign,
            color: this.color,
            lineHeight: this.lineHeight,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            effects: this.effects.map(e => e.clone())
        });

        return cloned;
    }

    // ==================== Serialization ====================

    /**
     * Serialize the text layer for saving.
     * @returns {Object}
     */
    serialize() {
        return {
            _version: TextLayer.VERSION,
            _type: 'TextLayer',
            // All shared SVGBaseLayer properties
            ...this.serializeBase(),
            // Use 'x' and 'y' for backward compatibility
            x: this.offsetX,
            y: this.offsetY,
            // TextLayer-specific properties
            runs: this.runs.map(run => ({ ...run })),
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
     * @param {Object} data
     * @returns {Object}
     */
    static migrate(data) {
        if (data._version === undefined) {
            data._version = 0;
        }

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

        // Ensure transform properties exist
        data.rotation = data.rotation ?? 0;
        data.scaleX = data.scaleX ?? 1.0;
        data.scaleY = data.scaleY ?? 1.0;

        return data;
    }

    /**
     * Create a TextLayer from serialized data.
     * @param {Object} data
     * @returns {Promise<TextLayer>}
     */
    static async deserialize(data) {
        data = TextLayer.migrate(data);

        // Deserialize effects
        const effects = (data.effects || [])
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);

        const layer = new TextLayer({
            ...data,
            offsetX: data.x ?? data.offsetX,
            offsetY: data.y ?? data.offsetY,
            effects: effects
        });

        // Restore all shared SVGBaseLayer properties including transform state
        layer.restoreBase(data);

        // Ensure SVG is generated and rendered
        await layer.render();

        return layer;
    }

    // ==================== HTML Conversion ====================

    /**
     * Convert HTML from contenteditable to runs.
     * @param {string} html
     * @param {Object} [defaultStyle]
     * @returns {TextRun[]}
     */
    static htmlToRuns(html, defaultStyle = {}) {
        const container = document.createElement('div');
        container.innerHTML = html;

        const runs = [];

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

                if (inlineStyle.fontSize) {
                    style.fontSize = parseInt(inlineStyle.fontSize);
                }
                if (inlineStyle.fontFamily) {
                    style.fontFamily = inlineStyle.fontFamily.replace(/['"]/g, '');
                }
                if (inlineStyle.fontWeight) {
                    style.fontWeight = inlineStyle.fontWeight;
                } else if (node.tagName === 'B' || node.tagName === 'STRONG') {
                    style.fontWeight = 'bold';
                }
                if (inlineStyle.fontStyle) {
                    style.fontStyle = inlineStyle.fontStyle;
                } else if (node.tagName === 'I' || node.tagName === 'EM') {
                    style.fontStyle = 'italic';
                }
                if (inlineStyle.color) {
                    style.color = inlineStyle.color;
                }

                if (node.tagName === 'BR') {
                    runs.push({ text: '\n' });
                    return;
                }

                if ((node.tagName === 'DIV' || node.tagName === 'P') && runs.length > 0) {
                    const lastRun = runs[runs.length - 1];
                    if (lastRun && !lastRun.text.endsWith('\n')) {
                        runs.push({ text: '\n' });
                    }
                }

                for (const child of node.childNodes) {
                    processNode(child, style);
                }
            }
        }

        processNode(container);

        // Merge adjacent runs with same style
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
     * @param {Object} defaults
     * @returns {string}
     */
    static runsToHtml(runs, defaults = {}) {
        let html = '';

        for (const run of runs) {
            let text = run.text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            text = text.replace(/\n/g, '<br>');

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
}

// Register TextLayer with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('text', TextLayer, ['TextLayer']);
