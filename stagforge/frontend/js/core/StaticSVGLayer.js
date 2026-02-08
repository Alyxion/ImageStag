/**
 * StaticSVGLayer - A layer that stores and renders raw SVG content.
 *
 * SVG content is stored as a raw string and rendered identically in:
 * - JavaScript (Chrome's native SVG renderer via <img> element)
 * - Python (resvg via render_svg_string)
 *
 * This provides cross-platform parity for embedded SVG graphics.
 *
 * Extends SVGBaseLayer which provides:
 * - SVG transform envelope (rotation, scale, mirror)
 * - Zoom-aware rendering with high-res display canvas
 * - Pixel export in multiple formats
 */
import { SVGBaseLayer } from './SVGBaseLayer.js';
import { PixelLayer } from './PixelLayer.js';
import { LayerEffect, effectRegistry } from './LayerEffects.js';
import { MAX_DIMENSION } from '../config/limits.js';

export class StaticSVGLayer extends SVGBaseLayer {
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
        super({
            ...options,
            name: options.name || 'SVG Layer',
            type: 'svg'
        });

        // svgContent is now stored per-frame via getter/setter below.
        // _createFrameData(options) already captured options.svgContent into _frames[0].

        // Original SVG content before any rotation wrapper (for cumulative rotation)
        this._originalSvgContent = options._originalSvgContent || null;
        this._originalNaturalWidth = options._originalNaturalWidth || 0;
        this._originalNaturalHeight = options._originalNaturalHeight || 0;
        this._contentRotation = options._contentRotation || 0;

        // Natural dimensions from SVG viewBox (parsed on content change)
        this.naturalWidth = 0;
        this.naturalHeight = 0;

        // Store document dimensions for reference
        this._docWidth = options.width;
        this._docHeight = options.height;

        // Parse initial content if provided
        if (this.svgContent) {
            // Sync with base class
            this.svgData = this.svgContent;
            this.parseViewBox();
            // Note: render() is NOT called in constructor to avoid unhandled promise rejections.
            // Caller MUST await layer.render() after construction for the layer to display content.
        }
    }

    // ==================== Type Checks ====================

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

    // ==================== Frame Data ====================

    /** @override */
    _createFrameData(options) {
        return {
            svgContent: options.svgContent || '',
            duration: options.duration || 100,
        };
    }

    /** @override */
    _createEmptyFrameData() {
        return { svgContent: '', duration: 100 };
    }

    /** @override */
    _cloneFrameData(frameData) {
        return {
            svgContent: frameData.svgContent,
            duration: frameData.duration,
        };
    }

    /** @override */
    _disposeFrameData(frameData) {
        // No-op: frame data is just strings
    }

    // ==================== Per-Frame SVG Content Accessors ====================

    /**
     * Get SVG content for a specific frame.
     * @param {number} [frameIndex=this.activeFrameIndex]
     * @returns {string}
     */
    getSvgContent(frameIndex = this.activeFrameIndex) {
        return this._frames[frameIndex].svgContent;
    }

    /**
     * Set SVG content for a specific frame.
     * @param {number} frameIndex
     * @param {string} content
     */
    setSvgContent(frameIndex, content) {
        this._frames[frameIndex].svgContent = content;
    }

    /**
     * Backward-compatible getter: reads active frame's svgContent.
     */
    get svgContent() {
        return this._frames[this.activeFrameIndex].svgContent;
    }

    /**
     * Backward-compatible setter: writes to active frame's svgContent.
     */
    set svgContent(v) {
        this._frames[this.activeFrameIndex].svgContent = v;
    }

    // ==================== SVG Content Methods ====================

    /**
     * Set SVG content and re-render.
     * @param {string} svgContent - Raw SVG string
     */
    setSVGContent(svgContent) {
        this.svgContent = svgContent;
        this.svgData = svgContent;
        // Reset rotation tracking when new content is set
        this._originalSvgContent = null;
        this._originalNaturalWidth = 0;
        this._originalNaturalHeight = 0;
        this._contentRotation = 0;
        this.parseViewBox();
        this.renderSvg();
        this.render();
    }

    /**
     * Update the SVG source data.
     * @param {string} [svgData] - Raw SVG string
     */
    updateSvgData(svgData) {
        if (svgData !== undefined) {
            this.svgContent = svgData;
            this.svgData = svgData;
            this.parseViewBox();
        }
        super.updateSvgData(svgData);
    }

    /**
     * Convert layer content to SVG string.
     * For StaticSVGLayer, this returns the stored svgContent with transforms applied.
     * @param {Object} [options] - Options (unused, for API compatibility)
     * @returns {string} SVG document string
     */
    toSVG(options = {}) {
        // If we have a rendered SVG with transforms, return that
        if (this.renderedSvg) {
            return this.renderedSvg;
        }
        return this.svgContent || '';
    }

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

        // Extract the inner content
        let innerContent = this.svgContent;

        // Remove XML declaration if present
        innerContent = innerContent.replace(/<\?xml[^?]*\?>\s*/gi, '');

        // Wrap in outer SVG with transforms
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
     * Render SVG content to the layer canvas.
     * Uses the SVG envelope with transforms for crisp rendering at any scale/rotation.
     *
     * @returns {Promise<void>}
     */
    async render() {
        if (!this.svgContent) {
            this._ctx.clearRect(0, 0, this.width, this.height);
            this.clearDisplayCanvas();
            return;
        }

        // Calculate render scale using 16MP limit
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
                img.onerror = () => reject(new Error('Failed to load SVG image'));
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

    // ==================== Content Rotation ====================

    /**
     * Rotate the SVG content by the specified degrees (90, 180, or 270).
     * This modifies svgContent by wrapping it with a rotation transform.
     *
     * @param {number} degrees - Rotation angle (90, 180, or 270)
     * @returns {Promise<void>}
     */
    async rotateContent(degrees) {
        if (![90, 180, 270].includes(degrees)) {
            console.error('[StaticSVGLayer] Invalid rotation angle:', degrees);
            return;
        }

        if (!this.svgContent) return;

        // Store original content on first rotation
        if (!this._originalSvgContent) {
            this._originalSvgContent = this.svgContent;
            this._originalNaturalWidth = this.naturalWidth || this.width;
            this._originalNaturalHeight = this.naturalHeight || this.height;
            this._contentRotation = 0;
        }

        // Update cumulative rotation
        this._contentRotation = (this._contentRotation + degrees) % 360;

        // If rotation is back to 0, restore original content
        if (this._contentRotation === 0) {
            this.svgContent = this._originalSvgContent;
            this.svgData = this._originalSvgContent;
            this.naturalWidth = this._originalNaturalWidth;
            this.naturalHeight = this._originalNaturalHeight;
            // Swap layer dimensions back if needed
            if (degrees === 90 || degrees === 270) {
                const oldW = this.width;
                this.width = this.height;
                this.height = oldW;
            }
            this._regenerateCanvas();
            await this.render();
            return;
        }

        // Extract inner content from ORIGINAL (unwrapped) SVG
        const innerContent = this._extractSVGContent(this._originalSvgContent);
        const origW = this._originalNaturalWidth;
        const origH = this._originalNaturalHeight;

        // Calculate new dimensions based on total rotation
        let newNatW, newNatH;
        if (this._contentRotation === 180) {
            newNatW = origW;
            newNatH = origH;
        } else {
            // 90 or 270: swap dimensions
            newNatW = origH;
            newNatH = origW;
        }

        // Build transform for the cumulative rotation
        let transform;
        if (this._contentRotation === 90) {
            transform = `translate(${origH}, 0) rotate(90)`;
        } else if (this._contentRotation === 180) {
            transform = `translate(${origW}, ${origH}) rotate(180)`;
        } else if (this._contentRotation === 270) {
            transform = `translate(0, ${origW}) rotate(270)`;
        }

        // Create new SVG with rotated content (always from original)
        this.svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${newNatW}" height="${newNatH}" viewBox="0 0 ${newNatW} ${newNatH}">
  <g transform="${transform}">
    <svg width="${origW}" height="${origH}" viewBox="0 0 ${origW} ${origH}">
      ${innerContent}
    </svg>
  </g>
</svg>`;
        this.svgData = this.svgContent;

        // Update natural dimensions
        this.naturalWidth = newNatW;
        this.naturalHeight = newNatH;

        // Update layer dimensions (swap for 90/270 from previous state)
        if (degrees === 90 || degrees === 270) {
            const oldW = this.width;
            this.width = this.height;
            this.height = oldW;
        }

        // Regenerate canvas at new size
        this._regenerateCanvas();

        // Re-render with new content
        await this.render();
    }

    /**
     * Rotate the SVG layer by the given degrees (90, 180, or 270).
     * This wraps rotateContent() and handles offset position calculation.
     *
     * @param {number} degrees - Rotation angle (90, 180, or 270)
     * @param {number} oldDocWidth - Document width before rotation
     * @param {number} oldDocHeight - Document height before rotation
     * @param {number} newDocWidth - Document width after rotation
     * @param {number} newDocHeight - Document height after rotation
     * @returns {Promise<void>}
     */
    async rotateCanvas(degrees, oldDocWidth, oldDocHeight, newDocWidth, newDocHeight) {
        if (![90, 180, 270].includes(degrees)) {
            console.error('[StaticSVGLayer] Invalid rotation angle:', degrees);
            return;
        }

        const oldWidth = this.width;
        const oldHeight = this.height;
        const oldOffsetX = this.offsetX || 0;
        const oldOffsetY = this.offsetY || 0;

        // Calculate new dimensions (rotateContent will swap layer.width/height)
        let newWidth, newHeight;
        if (degrees === 180) {
            newWidth = oldWidth;
            newHeight = oldHeight;
        } else {
            newWidth = oldHeight;
            newHeight = oldWidth;
        }

        // Calculate new offset based on rotation around document center
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

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

        // Rotate the SVG content
        await this.rotateContent(degrees);

        // Update offset position for the new document layout
        this.offsetX = Math.round(newCenterX - newWidth / 2);
        this.offsetY = Math.round(newCenterY - newHeight / 2);
    }

    /**
     * Mirror the SVG content horizontally or vertically.
     *
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @param {number} [docWidth] - Document width (for offset calculation)
     * @param {number} [docHeight] - Document height (for offset calculation)
     * @returns {Promise<void>}
     */
    async mirrorContent(direction, docWidth, docHeight) {
        if (!['horizontal', 'vertical'].includes(direction)) {
            console.error('[StaticSVGLayer] Invalid mirror direction:', direction);
            return;
        }

        if (!this.svgContent) return;

        // Update offset position if document dimensions provided
        if (docWidth !== undefined && docHeight !== undefined) {
            if (direction === 'horizontal') {
                this.offsetX = docWidth - this.offsetX - this.width;
            } else {
                this.offsetY = docHeight - this.offsetY - this.height;
            }
        }

        // Extract inner content
        const innerContent = this._extractSVGContent(this.svgContent);
        const w = this.naturalWidth || this.width;
        const h = this.naturalHeight || this.height;

        // Build mirror transform
        let transform;
        if (direction === 'horizontal') {
            transform = `translate(${w}, 0) scale(-1, 1)`;
        } else {
            transform = `translate(0, ${h}) scale(1, -1)`;
        }

        // Create new SVG with mirrored content
        this.svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <g transform="${transform}">
    <svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
      ${innerContent}
    </svg>
  </g>
</svg>`;
        this.svgData = this.svgContent;

        // Re-render with new content
        await this.render();
    }

    /**
     * Regenerate internal canvas at current layer dimensions.
     * @private
     */
    _regenerateCanvas() {
        if (this._canvas) {
            this._canvas.width = this.width;
            this._canvas.height = this.height;
        }
    }

    // ==================== Scaling ====================

    /**
     * Scale the layer by a factor.
     * IMPORTANT: SVG raw data is immutable - scaling only changes display dimensions.
     * @param {number} scaleX - Horizontal scale factor
     * @param {number} scaleY - Vertical scale factor
     * @param {Object} [options]
     */
    async scale(scaleX, scaleY, options = {}) {
        const newWidth = Math.min(MAX_DIMENSION, Math.max(1, Math.round(this.width * scaleX)));
        const newHeight = Math.min(MAX_DIMENSION, Math.max(1, Math.round(this.height * scaleY)));

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
     * @param {number} newWidth - Target width
     * @param {number} newHeight - Target height
     * @param {Object} [options]
     */
    async scaleTo(newWidth, newHeight, options = {}) {
        if (this.width === 0 || this.height === 0) return;

        const clampedWidth = Math.min(MAX_DIMENSION, Math.max(1, newWidth));
        const clampedHeight = Math.min(MAX_DIMENSION, Math.max(1, newHeight));

        const scaleX = clampedWidth / this.width;
        const scaleY = clampedHeight / this.height;

        await this.scale(scaleX, scaleY, options);
    }

    // ==================== Clone ====================

    /**
     * Clone this SVG layer.
     * @returns {StaticSVGLayer}
     */
    clone() {
        const cloned = new StaticSVGLayer({
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

        // Clone all frames (constructor created 1 frame already)
        cloned._frames = this._frames.map(f => this._cloneFrameData(f));
        cloned.activeFrameIndex = this.activeFrameIndex;

        // Copy rendered content
        cloned._ctx.drawImage(this.canvas, 0, 0);

        return cloned;
    }

    // ==================== Serialization ====================

    /**
     * Serialize for history/save.
     * @returns {Object}
     */
    serialize() {
        // Serialize all frames
        const frames = this._frames.map(frame => ({
            svgContent: frame.svgContent,
            duration: frame.duration,
        }));

        return {
            _version: StaticSVGLayer.VERSION,
            _type: 'StaticSVGLayer',
            type: 'svg',
            id: this.id,
            name: this.name,
            parentId: this.parentId,
            // Top-level svgContent for backward compat with v1 readers
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
            _docHeight: this._docHeight,
            // Content rotation tracking
            _originalSvgContent: this._originalSvgContent,
            _originalNaturalWidth: this._originalNaturalWidth,
            _originalNaturalHeight: this._originalNaturalHeight,
            _contentRotation: this._contentRotation,
            // Multi-frame data
            frames,
            activeFrameIndex: this.activeFrameIndex,
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

        // Ensure transform properties exist
        data.rotation = data.rotation ?? 0;
        data.scaleX = data.scaleX ?? 1.0;
        data.scaleY = data.scaleY ?? 1.0;

        return data;
    }

    /**
     * Restore from serialized data.
     * @param {Object} data
     * @returns {Promise<StaticSVGLayer>}
     */
    static async deserialize(data) {
        // Migrate to current version
        data = StaticSVGLayer.migrate(data);

        // Deserialize effects
        const effects = (data.effects || [])
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);

        const layer = new StaticSVGLayer({
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
            effects: effects,
            // Content rotation tracking
            _originalSvgContent: data._originalSvgContent,
            _originalNaturalWidth: data._originalNaturalWidth,
            _originalNaturalHeight: data._originalNaturalHeight,
            _contentRotation: data._contentRotation
        });

        // Restore multi-frame data if present
        if (data.frames && data.frames.length > 0) {
            layer._frames = data.frames.map(frameData => ({
                svgContent: frameData.svgContent || '',
                duration: frameData.duration || 100,
            }));
            layer.activeFrameIndex = data.activeFrameIndex ?? 0;
        }

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

// For backwards compatibility, also export as SVGLayer
export { StaticSVGLayer as SVGLayer };

// Register StaticSVGLayer with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('svg', StaticSVGLayer, ['SVGLayer', 'StaticSVGLayer']);
