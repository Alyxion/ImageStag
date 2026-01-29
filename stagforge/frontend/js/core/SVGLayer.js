/**
 * SVGLayer - A layer that stores and renders raw SVG content.
 *
 * SVG content is stored as a raw string and rendered identically in:
 * - JavaScript (Chrome's native SVG renderer via <img> element)
 * - Python (resvg via render_svg_string)
 *
 * This provides cross-platform parity for embedded SVG graphics.
 *
 * Extends VectorizableLayer which provides:
 * - Internal canvas (no public ctx - SVG content cannot be drawn on externally)
 * - Pixel export in multiple formats (RGBA8, RGB8, RGBA16, RGB16)
 * - SVG conversion capability
 */
import { VectorizableLayer } from './VectorizableLayer.js';
import { Layer } from './Layer.js';  // For prototype extension at bottom
import { LayerEffect, effectRegistry } from './LayerEffects.js';

export class SVGLayer extends VectorizableLayer {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {string} [options.id]
     * @param {string} [options.name]
     * @param {number} options.width - Output width
     * @param {number} options.height - Output height
     * @param {string} [options.svgContent] - Raw SVG string
     * @param {number} [options.opacity]
     * @param {string} [options.blendMode]
     * @param {boolean} [options.visible]
     * @param {boolean} [options.locked]
     */
    constructor(options = {}) {
        super(options);

        // Mark as SVG layer
        this.type = 'svg';

        // Note: VectorizableLayer sets up zoom-aware rendering state:
        // - _displayScale, _lastRenderedScale, _renderScale
        // - _displayCanvas, _displayCtx
        // - setDisplayScale(), getDisplayCanvas(), getRenderScale(), calculateRenderScale()

        // Note: VectorizableLayer (via DynamicLayer) already sets up:
        // - this._ctx for internal rendering
        // - this.ctx = null (SVG layers are read-only, external code cannot draw on them)

        // Raw SVG content string
        this.svgContent = options.svgContent || '';

        // Note: rotation, scaleX, scaleY are inherited from DynamicLayer

        // Natural dimensions from SVG viewBox (parsed on content change)
        this.naturalWidth = 0;
        this.naturalHeight = 0;

        // Store document dimensions for reference
        this._docWidth = options.width;
        this._docHeight = options.height;

        // Parse and render initial content if provided
        if (this.svgContent) {
            this.parseViewBox();
            // Start async render (caller should await layer.render() if synchronous completion is needed)
            this.render();
        }
    }

    /**
     * Check if this is a group.
     * @returns {boolean}
     */
    isGroup() {
        return false;
    }

    /**
     * Check if this is a vector layer.
     * @returns {boolean}
     */
    isVector() {
        return false;
    }

    /**
     * Check if this is an SVG layer.
     * @returns {boolean}
     */
    isSVG() {
        return true;
    }

    // Note: setDisplayScale(), getDisplayCanvas(), getRenderScale() inherited from VectorizableLayer

    // ==================== SVG Methods ====================

    /**
     * Convert layer content to SVG string.
     * For SVGLayer, this simply returns the stored svgContent.
     * @param {Object} [options] - Options (unused, for API compatibility)
     * @returns {string} SVG document string
     */
    toSVG(options = {}) {
        return this.svgContent || '';
    }

    /**
     * Set SVG content and re-render.
     * @param {string} svgContent - Raw SVG string
     */
    setSVGContent(svgContent) {
        this.svgContent = svgContent;
        this.parseViewBox();
        this.render();
    }

    // Note: setRotation() is inherited from DynamicLayer

    /**
     * Parse viewBox from SVG to get natural dimensions.
     * Falls back to width/height attributes if no viewBox.
     */
    parseViewBox() {
        if (!this.svgContent) {
            this.naturalWidth = 0;
            this.naturalHeight = 0;
            return;
        }

        // Try to parse viewBox first
        const viewBoxMatch = this.svgContent.match(/viewBox\s*=\s*["']([^"']+)["']/i);
        if (viewBoxMatch) {
            const parts = viewBoxMatch[1].trim().split(/[\s,]+/);
            if (parts.length >= 4) {
                this.naturalWidth = parseFloat(parts[2]) || 0;
                this.naturalHeight = parseFloat(parts[3]) || 0;
                return;
            }
        }

        // Fall back to width/height attributes
        const widthMatch = this.svgContent.match(/\bwidth\s*=\s*["']([^"']+)["']/i);
        const heightMatch = this.svgContent.match(/\bheight\s*=\s*["']([^"']+)["']/i);

        if (widthMatch && heightMatch) {
            // Handle units (mm, px, etc.) - extract numeric value
            this.naturalWidth = parseFloat(widthMatch[1]) || 0;
            this.naturalHeight = parseFloat(heightMatch[1]) || 0;
        }
    }

    /**
     * Generate an SVG string with the inner content wrapped in an envelope
     * that applies scaling and rotation transforms.
     *
     * The inner SVG is never modified — transforms are applied via the envelope.
     * This ensures crisp vector-quality rendering at any scale and rotation.
     *
     * @param {number} [supersample=1] - Supersample factor for higher resolution rendering
     * @returns {string} SVG string ready for rendering
     */
    renderToSVG(supersample = 1) {
        if (!this.svgContent) return '';

        // Apply supersample to output dimensions
        const targetW = this.width * supersample;
        const targetH = this.height * supersample;
        const natW = this.naturalWidth || this.width;
        const natH = this.naturalHeight || this.height;
        const rot = this.rotation || 0;

        // Calculate bounding box of rotated content
        const radians = (rot * Math.PI) / 180;
        const cos = Math.abs(Math.cos(radians));
        const sin = Math.abs(Math.sin(radians));
        const rotatedW = natW * cos + natH * sin;
        const rotatedH = natW * sin + natH * cos;

        // Scale to fit rotated content within target dimensions
        const scale = Math.min(targetW / rotatedW, targetH / rotatedH);

        // Build viewBox for the inner SVG (use natural dimensions)
        const innerViewBox = `0 0 ${natW} ${natH}`;

        // Extract the inner content (everything inside the root <svg> tag)
        // We'll embed it in a nested <svg> with proper viewBox
        let innerContent = this.svgContent;

        // Remove XML declaration if present
        innerContent = innerContent.replace(/<\?xml[^?]*\?>\s*/gi, '');

        // Wrap in outer SVG with transforms
        // Transform order: translate to center → rotate → scale → translate content to center
        const cx = targetW / 2;
        const cy = targetH / 2;

        return `<svg xmlns="http://www.w3.org/2000/svg" width="${targetW}" height="${targetH}">
            <g transform="translate(${cx}, ${cy}) rotate(${rot}) scale(${scale}) translate(${-natW / 2}, ${-natH / 2})">
                <svg width="${natW}" height="${natH}" viewBox="${innerViewBox}" preserveAspectRatio="none">
                    ${this._extractSVGContent(innerContent)}
                </svg>
            </g>
        </svg>`;
    }

    /**
     * Extract the inner content from an SVG string (content inside <svg>...</svg>).
     * @param {string} svgString - Full SVG string
     * @returns {string} Inner content
     * @private
     */
    _extractSVGContent(svgString) {
        // Match opening <svg ...> tag and extract everything after it until </svg>
        const openTagMatch = svgString.match(/<svg[^>]*>/i);
        if (!openTagMatch) return svgString;

        const startIdx = openTagMatch.index + openTagMatch[0].length;
        const endIdx = svgString.lastIndexOf('</svg>');
        if (endIdx <= startIdx) return svgString;

        return svgString.substring(startIdx, endIdx);
    }

    /**
     * Render SVG content to the layer canvas.
     * Uses the SVG envelope with transforms for crisp rendering at any scale/rotation.
     * When display scale is high (zoomed in), renders at higher resolution for crispness.
     *
     * Two canvases are maintained:
     * - _canvas (via _ctx): Always at layer.width x layer.height for exports/compatibility
     * - _displayCanvas: At high resolution for zoom-aware display (used by Renderer)
     *
     * @returns {Promise<void>}
     */
    async render() {
        if (!this.svgContent) {
            this._ctx.clearRect(0, 0, this.width, this.height);
            this.clearDisplayCanvas();
            return;
        }

        // Calculate render scale using 16MP limit from base class
        const displayScale = this._displayScale || 1.0;
        const renderScale = this.calculateRenderScale(displayScale);

        // Track what scale we rendered at
        this._lastRenderedScale = displayScale;
        this._renderScale = renderScale;

        // Generate transformed SVG at render scale
        const transformedSVG = this.renderToSVG(renderScale);

        // Create blob from transformed SVG
        const blob = new Blob([transformedSVG], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        try {
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = url;
            });

            // Create/resize display canvas using base class helper
            const { ctx: displayCtx, width: hiresWidth, height: hiresHeight } = this.ensureDisplayCanvas(renderScale);

            // Draw to high-res display canvas (NO downscaling - keep full resolution)
            this._displayCtx.clearRect(0, 0, hiresWidth, hiresHeight);
            this._displayCtx.imageSmoothingEnabled = false;
            this._displayCtx.drawImage(img, 0, 0, hiresWidth, hiresHeight);

            // Also render to the regular canvas at 1x for exports/compatibility
            this._ctx.clearRect(0, 0, this.width, this.height);
            if (renderScale > 1) {
                // Downscale from high-res to 1x for the regular canvas
                this._ctx.imageSmoothingEnabled = true;
                this._ctx.imageSmoothingQuality = 'high';
                this._ctx.drawImage(this._displayCanvas, 0, 0, this.width, this.height);
            } else {
                // 1:1 rendering - draw directly
                this._ctx.imageSmoothingEnabled = false;
                this._ctx.drawImage(img, 0, 0);
            }

            // Invalidate caches
            this.invalidateImageCache();
            this.invalidateEffectCache();
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Scale the layer by a factor around an optional center point.
     * IMPORTANT: SVG raw data is immutable - scaling only changes display dimensions.
     * @param {number} scaleX - Horizontal scale factor
     * @param {number} scaleY - Vertical scale factor
     * @param {Object} [options]
     * @param {number} [options.centerX] - Center X in document coords (unused)
     * @param {number} [options.centerY] - Center Y in document coords (unused)
     */
    async scale(scaleX, scaleY, options = {}) {
        // NEVER modify svgContent - only change render dimensions
        const newWidth = Math.max(1, Math.round(this.width * scaleX));
        const newHeight = Math.max(1, Math.round(this.height * scaleY));

        // Resize canvas
        this.width = newWidth;
        this.height = newHeight;
        this._canvas.width = newWidth;
        this._canvas.height = newHeight;

        // Re-render SVG at new size
        await this.render();

        this.invalidateImageCache();
        this.invalidateEffectCache();
    }

    /**
     * Scale to specific dimensions.
     * IMPORTANT: SVG raw data is immutable - scaling only changes display dimensions.
     * @param {number} newWidth - Target width
     * @param {number} newHeight - Target height
     * @param {Object} [options]
     */
    async scaleTo(newWidth, newHeight, options = {}) {
        if (this.width === 0 || this.height === 0) return;

        const scaleX = newWidth / this.width;
        const scaleY = newHeight / this.height;

        await this.scale(scaleX, scaleY, options);
    }

    /**
     * Get raw RGBA pixel data after SVG rendering.
     * Used for parity testing with Python.
     * @returns {Promise<Uint8ClampedArray>}
     */
    async getPixels() {
        await this.render();
        const imageData = this._ctx.getImageData(0, 0, this.width, this.height);
        return imageData.data;
    }

    /**
     * Clone this SVG layer.
     * @returns {SVGLayer}
     */
    clone() {
        const cloned = new SVGLayer({
            width: this.width,
            height: this.height,
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            rotation: this.rotation,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            parentId: this.parentId,
            name: `${this.name} (copy)`,
            svgContent: this.svgContent,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            effects: this.effects.map(e => e.clone())
        });

        // Copy rendered content (use _ctx since ctx is null)
        cloned._ctx.drawImage(this.canvas, 0, 0);

        return cloned;
    }

    /**
     * Create a rasterized (pixel) copy of this layer.
     * @returns {Layer}
     */
    rasterize() {
        this.render();
        const rasterLayer = new Layer({
            width: this.width,
            height: this.height,
            name: this.name,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
        });
        rasterLayer.offsetX = this.offsetX;
        rasterLayer.offsetY = this.offsetY;
        rasterLayer.ctx.drawImage(this.canvas, 0, 0);
        return rasterLayer;
    }

    /**
     * Serialize for history/save.
     * @returns {Object}
     */
    serialize() {
        return {
            _version: SVGLayer.VERSION,
            _type: 'SVGLayer',
            type: 'svg',
            id: this.id,
            name: this.name,
            parentId: this.parentId,
            svgContent: this.svgContent,
            rotation: this.rotation,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            naturalWidth: this.naturalWidth,
            naturalHeight: this.naturalHeight,
            width: this.width,
            height: this.height,
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            effects: this.effects.map(e => e.serialize()),
            _docWidth: this._docWidth,
            _docHeight: this._docHeight
        };
    }

    /**
     * Migrate serialized data from older versions.
     * @param {Object} data - Serialized SVG layer data
     * @returns {Object} - Migrated data at current version
     */
    static migrate(data) {
        // Handle pre-versioned data
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Ensure all fields exist
        if (data._version < 1) {
            data.svgContent = data.svgContent || '';
            data.naturalWidth = data.naturalWidth ?? 0;
            data.naturalHeight = data.naturalHeight ?? 0;
            data.offsetX = data.offsetX ?? 0;
            data.offsetY = data.offsetY ?? 0;
            data.parentId = data.parentId ?? null;
            data.effects = data.effects || [];
            data._docWidth = data._docWidth ?? data.width;
            data._docHeight = data._docHeight ?? data.height;
            data._version = 1;
        }

        // Ensure transform properties exist (added after v1)
        data.rotation = data.rotation ?? 0;
        data.scaleX = data.scaleX ?? 1.0;
        data.scaleY = data.scaleY ?? 1.0;

        return data;
    }

    /**
     * Restore from serialized data.
     * @param {Object} data
     * @returns {Promise<SVGLayer>}
     */
    static async deserialize(data) {
        // Migrate to current version
        data = SVGLayer.migrate(data);

        // Deserialize effects
        const effects = (data.effects || [])
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);

        const layer = new SVGLayer({
            id: data.id,
            name: data.name,
            parentId: data.parentId,
            width: data.width,
            height: data.height,
            svgContent: data.svgContent,
            rotation: data.rotation,
            scaleX: data.scaleX,
            scaleY: data.scaleY,
            opacity: data.opacity,
            blendMode: data.blendMode,
            visible: data.visible,
            locked: data.locked,
            effects: effects
        });

        // Restore offset position
        layer.offsetX = data.offsetX ?? 0;
        layer.offsetY = data.offsetY ?? 0;

        // Restore document dimensions
        layer._docWidth = data._docWidth ?? data.width;
        layer._docHeight = data._docHeight ?? data.height;

        // Restore natural dimensions
        layer.naturalWidth = data.naturalWidth ?? 0;
        layer.naturalHeight = data.naturalHeight ?? 0;

        // Render SVG content
        await layer.render();

        return layer;
    }
}

// Add helper to regular Layer to check SVG type
Layer.prototype.isSVG = function() {
    return false;
};
