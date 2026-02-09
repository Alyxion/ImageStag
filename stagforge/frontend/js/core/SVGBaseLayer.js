/**
 * SVGBaseLayer - Abstract base class for all SVG-based layers.
 *
 * This class provides shared functionality for layers that represent their
 * content as SVG. The SVG is transformed via an envelope (rotation, scale,
 * mirror) before being rasterized for display.
 *
 * Two canvases are maintained:
 * - _canvas: Always at layer.width x layer.height for exports/compatibility
 * - _displayCanvas: At high resolution for zoom-aware display (used by Renderer)
 *
 * Subclasses:
 * - StaticSVGLayer (type: 'svg') - Raw SVG content storage
 * - TextLayer (type: 'text') - Text rendered as SVG for scalability
 *
 * Extends BaseLayer which provides:
 * - Transform operations (rotation, scale)
 * - Coordinate conversion (layerToDoc, docToLayer, etc.)
 * - Effects management
 * - Image caching
 */
import { BaseLayer } from './BaseLayer.js';
import { PixelLayer } from './PixelLayer.js';
import { LayerEffect, effectRegistry } from './LayerEffects.js';
import { MAX_DIMENSION } from '../config/limits.js';

export class SVGBaseLayer extends BaseLayer {
    /** Serialization version for migration support */
    static VERSION = 1;

    /** Maximum pixels for high-res display canvas (16 megapixels) */
    static MAX_DISPLAY_PIXELS = 16_000_000;

    /**
     * @param {Object} options
     * @param {string} [options.id] - Unique identifier
     * @param {string} [options.name] - Display name
     * @param {number} options.width - Layer width
     * @param {number} options.height - Layer height
     * @param {number} [options.offsetX] - X offset from document origin
     * @param {number} [options.offsetY] - Y offset from document origin
     * @param {number} [options.opacity] - Opacity 0.0-1.0
     * @param {string} [options.blendMode] - Blend mode
     * @param {boolean} [options.visible] - Visibility
     * @param {boolean} [options.locked] - Lock state
     */
    constructor(options = {}) {
        super({
            ...options,
            name: options.name || 'SVG Layer',
            type: options.type || 'svg'
        });

        // Ensure minimum dimensions of 1x1
        this.width = Math.min(MAX_DIMENSION, Math.max(1, Math.ceil(options.width || 1)));
        this.height = Math.min(MAX_DIMENSION, Math.max(1, Math.ceil(options.height || 1)));

        // SVG data storage
        this.svgData = '';           // The source SVG data
        this.renderedSvg = '';       // The transformed SVG (with rotation, scale, mirror)

        // Internal canvas for rendering (NOT publicly accessible)
        this._canvas = document.createElement('canvas');
        this._canvas.width = this.width;
        this._canvas.height = this.height;
        this._ctx = this._canvas.getContext('2d', { willReadFrequently: true });

        // Public ctx is null - external code cannot draw on SVG layers
        this.ctx = null;

        // For compatibility with code that accesses .canvas for compositing
        // This is read-only - writing to it has no effect on the layer content
        this.canvas = this._canvas;

        // Zoom-aware rendering state
        this._displayScale = 1.0;       // Current zoom level
        this._lastRenderedScale = 1.0;  // Scale at which we last rendered
        this._renderScale = 1.0;        // Actual render scale used (may be limited by memory)
        this._displayCanvas = null;     // High-res canvas for zoom display
        this._displayCtx = null;        // Context for display canvas

        // Render validity tracking
        this._renderValid = false;

        // Transform tracking - stores original SVG for cumulative transforms
        this._originalSvgData = null;      // Original SVG before any transforms
        this._originalWidth = null;        // Original width before transforms
        this._originalHeight = null;       // Original height before transforms
        this._contentRotation = 0;         // Cumulative rotation baked into content (0, 90, 180, 270)
        this._mirrorX = false;             // Horizontal mirror baked into content
        this._mirrorY = false;             // Vertical mirror baked into content
    }

    // ==================== Type Checks ====================

    /**
     * Check if this is an SVG layer.
     * @returns {boolean}
     */
    isSVG() {
        return true;
    }

    /**
     * Check if this is a dynamic (non-raster) layer.
     * @returns {boolean}
     */
    isDynamic() {
        return true;
    }

    // ==================== SVG Content Management ====================

    /**
     * Update the SVG source data.
     * This stores the original SVG and rebuilds the transformed version.
     * Subclasses should call this after generating their SVG content.
     * @param {string} [svgData] - Raw SVG string (optional)
     */
    updateSvgData(svgData) {
        const newSvgData = svgData || '';

        // Store as the original (untransformed) SVG
        this._originalSvgData = newSvgData;
        const dims = this._parseSVGDimensions(newSvgData);
        this._originalWidth = dims.width;
        this._originalHeight = dims.height;

        // Reset transforms when content changes
        this._contentRotation = 0;
        this._mirrorX = false;
        this._mirrorY = false;

        // Also reset BaseLayer transform properties
        this.rotation = 0;
        this.scaleX = 1;
        this.scaleY = 1;

        // Rebuild the transformed SVG
        this.svgData = newSvgData;
        this.renderSvg();
        this.invalidateRender();
    }

    /**
     * Regenerate renderedSvg from original SVG with all baked transforms.
     * Transforms are applied in order: rotation, then mirroring.
     *
     * This method bakes ALL transforms (rotation + mirroring) into the SVG content,
     * matching StaticSVGLayer's approach. The BaseLayer transform properties
     * (this.rotation, this.scaleX, this.scaleY) remain at identity values.
     */
    renderSvg() {
        if (!this._originalSvgData && !this.svgData) {
            this.renderedSvg = '';
            return;
        }

        // Use original if available, otherwise use svgData
        const sourceSvg = this._originalSvgData || this.svgData;
        if (!sourceSvg) {
            this.renderedSvg = '';
            return;
        }

        // If no transforms, use source directly
        if (this._contentRotation === 0 && !this._mirrorX && !this._mirrorY) {
            this.renderedSvg = sourceSvg;
            this.svgData = sourceSvg;
            return;
        }

        // Get original dimensions
        const origW = this._originalWidth || this.width;
        const origH = this._originalHeight || this.height;

        // Extract inner content from original SVG
        const innerContent = this._extractSVGContent(sourceSvg);

        // Calculate dimensions after rotation
        let rotatedW, rotatedH;
        if (this._contentRotation === 90 || this._contentRotation === 270) {
            rotatedW = origH;
            rotatedH = origW;
        } else {
            rotatedW = origW;
            rotatedH = origH;
        }

        // Build combined transform string
        // Order: inner transforms applied first (right to left in SVG)
        // We want: rotate first, then mirror
        // So in SVG: mirror transform wraps rotation transform
        const transforms = [];

        // Step 1: Build rotation transform (applied to original content)
        let rotationTransform = '';
        if (this._contentRotation === 90) {
            rotationTransform = `translate(${origH}, 0) rotate(90)`;
        } else if (this._contentRotation === 180) {
            rotationTransform = `translate(${origW}, ${origH}) rotate(180)`;
        } else if (this._contentRotation === 270) {
            rotationTransform = `translate(0, ${origW}) rotate(270)`;
        }

        // Step 2: Build mirror transform (applied after rotation)
        let mirrorTransform = '';
        if (this._mirrorX && this._mirrorY) {
            mirrorTransform = `translate(${rotatedW}, ${rotatedH}) scale(-1, -1)`;
        } else if (this._mirrorX) {
            mirrorTransform = `translate(${rotatedW}, 0) scale(-1, 1)`;
        } else if (this._mirrorY) {
            mirrorTransform = `translate(0, ${rotatedH}) scale(1, -1)`;
        }

        // Build nested SVG structure
        // Inner: rotation applied to original content
        // Outer: mirror applied to rotated result
        let transformedContent;
        if (rotationTransform && mirrorTransform) {
            // Both rotation and mirror
            transformedContent = `
  <g transform="${mirrorTransform}">
    <g transform="${rotationTransform}">
      <svg width="${origW}" height="${origH}" viewBox="0 0 ${origW} ${origH}">
        ${innerContent}
      </svg>
    </g>
  </g>`;
        } else if (rotationTransform) {
            // Only rotation
            transformedContent = `
  <g transform="${rotationTransform}">
    <svg width="${origW}" height="${origH}" viewBox="0 0 ${origW} ${origH}">
      ${innerContent}
    </svg>
  </g>`;
        } else if (mirrorTransform) {
            // Only mirror (no rotation, so use original dimensions)
            transformedContent = `
  <g transform="${mirrorTransform}">
    <svg width="${origW}" height="${origH}" viewBox="0 0 ${origW} ${origH}">
      ${innerContent}
    </svg>
  </g>`;
        } else {
            transformedContent = innerContent;
        }

        // Final dimensions (after all transforms)
        const finalW = rotatedW;
        const finalH = rotatedH;

        // Create the transformed SVG
        this.renderedSvg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${finalW}" height="${finalH}" viewBox="0 0 ${finalW} ${finalH}">${transformedContent}
</svg>`;

        // Also update svgData to match
        this.svgData = this.renderedSvg;

        // Invalidate rasterized cache
        this._displayCanvas = null;
        this._displayCtx = null;
    }

    /**
     * Get the SVG content for export/display.
     * @param {Object} [options] - Options (unused, for API compatibility)
     * @returns {string} SVG document string
     */
    toSVG(options = {}) {
        return this.renderedSvg || this.svgData || '';
    }

    // ==================== Rendering ====================

    /**
     * Render SVG content to the layer canvas.
     * Uses the transformed SVG for crisp rendering at any scale/rotation.
     * @returns {Promise<void>}
     */
    async render() {
        if (!this.svgData && !this.renderedSvg) {
            this._ctx.clearRect(0, 0, this.width, this.height);
            this.clearDisplayCanvas();
            this._renderValid = true;
            return;
        }

        // Ensure renderedSvg is up to date
        if (!this.renderedSvg) {
            this.renderSvg();
        }

        const svgToRender = this.renderedSvg || this.svgData;

        // Calculate render scale using 16MP limit
        const displayScale = this._displayScale || 1.0;
        const renderScale = this.calculateRenderScale(displayScale);

        // Track what scale we rendered at
        this._lastRenderedScale = displayScale;
        this._renderScale = renderScale;

        // Create blob from SVG
        const blob = new Blob([svgToRender], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        try {
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = () => reject(new Error('Failed to load SVG image'));
                img.src = url;
            });

            // Create/resize display canvas
            const { ctx: displayCtx, width: hiresWidth, height: hiresHeight } = this.ensureDisplayCanvas(renderScale);

            // Draw to high-res display canvas
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

            // Mark render as valid
            this._renderValid = true;

            // Invalidate caches
            this.invalidateImageCache();
            this.invalidateEffectCache();
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Ensure render cache is valid, re-rendering if needed.
     * @returns {Promise<void>}
     */
    async ensureRendered() {
        if (!this._renderValid) {
            await this.render();
        }
    }

    /**
     * Invalidate render cache (call when source content changes).
     */
    invalidateRender() {
        this._renderValid = false;
        this.invalidateImageCache();
        this.invalidateEffectCache();
    }

    // ==================== Zoom-Aware Rendering ====================

    /**
     * Calculate optimal render scale for zoom-aware rendering.
     * Limits resolution to MAX_DISPLAY_PIXELS to prevent memory issues.
     * @param {number} displayScale - Desired display scale (zoom level)
     * @returns {number} Actual render scale to use
     */
    calculateRenderScale(displayScale) {
        const basePixels = this.width * this.height;
        if (basePixels === 0) return 1;

        const maxScale = Math.sqrt(SVGBaseLayer.MAX_DISPLAY_PIXELS / basePixels);
        return Math.max(1, Math.min(Math.floor(displayScale), Math.floor(maxScale)));
    }

    /**
     * Set the display scale for zoom-aware rendering.
     * When zoom increases, layers should re-render at higher resolution.
     * @param {number} scale - Display scale (e.g., 2.0 for 200% zoom)
     */
    setDisplayScale(scale) {
        const newScale = Math.max(1, scale);
        this._displayScale = newScale;

        // Re-render if scale changed significantly (>20% increase or <50% decrease)
        const scaleRatio = newScale / this._lastRenderedScale;
        if (scaleRatio > 1.2 || scaleRatio < 0.5) {
            this.render();
        }
    }

    /**
     * Get the high-resolution display canvas for zoom-aware rendering.
     * @returns {HTMLCanvasElement}
     */
    getDisplayCanvas() {
        return this._displayCanvas || this._canvas;
    }

    /**
     * Get the scale factor of the display canvas relative to layer dimensions.
     * @returns {number}
     */
    getRenderScale() {
        return this._renderScale;
    }

    /**
     * Create or resize the display canvas for high-resolution rendering.
     * @param {number} renderScale - Scale factor for the display canvas
     * @returns {{ canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D, width: number, height: number }}
     */
    ensureDisplayCanvas(renderScale) {
        const hiresWidth = Math.round(this.width * renderScale);
        const hiresHeight = Math.round(this.height * renderScale);

        if (!this._displayCanvas) {
            this._displayCanvas = document.createElement('canvas');
            this._displayCtx = this._displayCanvas.getContext('2d');
        }

        if (this._displayCanvas.width !== hiresWidth || this._displayCanvas.height !== hiresHeight) {
            this._displayCanvas.width = hiresWidth;
            this._displayCanvas.height = hiresHeight;
        }

        return {
            canvas: this._displayCanvas,
            ctx: this._displayCtx,
            width: hiresWidth,
            height: hiresHeight
        };
    }

    /**
     * Clear the display canvas.
     */
    clearDisplayCanvas() {
        if (this._displayCtx && this._displayCanvas) {
            this._displayCtx.clearRect(0, 0, this._displayCanvas.width, this._displayCanvas.height);
        }
    }

    // ==================== Pixel Access ====================

    /**
     * Get raw RGBA8 pixel data.
     * @returns {Promise<Uint8ClampedArray>}
     */
    async getPixelsRGBA8() {
        await this.ensureRendered();
        const imageData = this._ctx.getImageData(0, 0, this.width, this.height);
        return imageData.data;
    }

    /**
     * Get ImageData for the layer.
     * @returns {Promise<ImageData>}
     */
    async getImageData() {
        await this.ensureRendered();
        return this._ctx.getImageData(0, 0, this.width, this.height);
    }

    /**
     * Get pixels in specified format.
     * @param {'rgba8'|'rgb8'|'rgba16'|'rgb16'} format
     * @returns {Promise<Uint8ClampedArray|Uint8Array|Uint16Array>}
     */
    async getPixels(format = 'rgba8') {
        const rgba = await this.getPixelsRGBA8();

        switch (format) {
            case 'rgba8':
                return rgba;
            case 'rgb8': {
                const rgb = new Uint8Array((rgba.length / 4) * 3);
                for (let i = 0, j = 0; i < rgba.length; i += 4, j += 3) {
                    rgb[j] = rgba[i];
                    rgb[j + 1] = rgba[i + 1];
                    rgb[j + 2] = rgba[i + 2];
                }
                return rgb;
            }
            case 'rgba16': {
                const rgba16 = new Uint16Array(rgba.length);
                for (let i = 0; i < rgba.length; i++) {
                    rgba16[i] = (rgba[i] << 8) | rgba[i];
                }
                return rgba16;
            }
            case 'rgb16': {
                const rgb16 = new Uint16Array((rgba.length / 4) * 3);
                for (let i = 0, j = 0; i < rgba.length; i += 4, j += 3) {
                    rgb16[j] = (rgba[i] << 8) | rgba[i];
                    rgb16[j + 1] = (rgba[i + 1] << 8) | rgba[i + 1];
                    rgb16[j + 2] = (rgba[i + 2] << 8) | rgba[i + 2];
                }
                return rgb16;
            }
            default:
                throw new Error(`Unknown pixel format: ${format}`);
        }
    }

    // ==================== Content Bounds ====================

    /**
     * Get the bounds of actual content (non-transparent pixels).
     * Returns null if layer is empty.
     * @returns {Promise<{x: number, y: number, width: number, height: number}|null>}
     */
    async getContentBounds() {
        await this.ensureRendered();
        const imageData = this._ctx.getImageData(0, 0, this.width, this.height);
        const data = imageData.data;

        let minX = this.width, minY = this.height;
        let maxX = -1, maxY = -1;

        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const alpha = data[(y * this.width + x) * 4 + 3];
                if (alpha > 0) {
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        if (maxX < 0) return null;

        return {
            x: this.offsetX + minX,
            y: this.offsetY + minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }

    // ==================== Transforms ====================

    /**
     * Regenerate the canvas at current dimensions.
     * Called after dimension changes from rotation.
     * @private
     */
    _regenerateCanvas() {
        this._canvas.width = this.width;
        this._canvas.height = this.height;
        this._displayCanvas = null;
        this._displayCtx = null;
    }

    /**
     * Rotate the SVG layer by the given degrees (90, 180, or 270).
     * This bakes rotation into the SVG content, matching StaticSVGLayer behavior.
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
            console.error('[SVGBaseLayer] Invalid rotation angle:', degrees);
            return;
        }

        // Store original if not already stored
        if (!this._originalSvgData) {
            this._originalSvgData = this.svgData;
            this._originalWidth = this.width;
            this._originalHeight = this.height;
        }

        const oldWidth = this.width;
        const oldHeight = this.height;
        const oldOffsetX = this.offsetX || 0;
        const oldOffsetY = this.offsetY || 0;

        // Update cumulative content rotation
        this._contentRotation = (this._contentRotation + degrees) % 360;

        // Calculate new dimensions (swap for 90/270)
        let newWidth, newHeight;
        if (degrees === 90 || degrees === 270) {
            newWidth = oldHeight;
            newHeight = oldWidth;
        } else {
            newWidth = oldWidth;
            newHeight = oldHeight;
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

        // Update layer dimensions
        this.width = newWidth;
        this.height = newHeight;

        // Update offset position
        this.offsetX = Math.round(newCenterX - newWidth / 2);
        this.offsetY = Math.round(newCenterY - newHeight / 2);

        // Regenerate canvas at new size
        this._regenerateCanvas();

        // Rebuild SVG with new rotation baked in
        this.renderSvg();
        await this.render();

        this.invalidateImageCache();
        this.invalidateEffectCache();
    }

    /**
     * Mirror the SVG content horizontally or vertically.
     * This bakes mirroring into the SVG content, matching StaticSVGLayer behavior.
     *
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @param {number} docWidth - Document width
     * @param {number} docHeight - Document height
     * @returns {Promise<void>}
     */
    async mirrorContent(direction, docWidth, docHeight) {
        if (!['horizontal', 'vertical'].includes(direction)) {
            console.error('[SVGBaseLayer] Invalid mirror direction:', direction);
            return;
        }

        // Store original if not already stored
        if (!this._originalSvgData) {
            this._originalSvgData = this.svgData;
            this._originalWidth = this.width;
            this._originalHeight = this.height;
        }

        // Toggle mirror flags
        if (direction === 'horizontal') {
            this._mirrorX = !this._mirrorX;
            // Mirror offset position within document
            this.offsetX = docWidth - this.offsetX - this.width;
        } else {
            this._mirrorY = !this._mirrorY;
            // Mirror offset position within document
            this.offsetY = docHeight - this.offsetY - this.height;
        }

        // Rebuild SVG with mirroring baked in
        this.renderSvg();
        await this.render();

        this.invalidateImageCache();
        this.invalidateEffectCache();
    }

    // ==================== Resize ====================

    /**
     * Resize internal canvas.
     * @param {number} newWidth
     * @param {number} newHeight
     */
    resize(newWidth, newHeight) {
        this.width = Math.min(MAX_DIMENSION, Math.max(1, Math.ceil(newWidth)));
        this.height = Math.min(MAX_DIMENSION, Math.max(1, Math.ceil(newHeight)));
        this._canvas.width = this.width;
        this._canvas.height = this.height;
        this.invalidateRender();
    }

    /**
     * Scale to specific dimensions.
     * IMPORTANT: SVG data is preserved - scaling only changes display dimensions.
     * @param {number} newWidth - Target width
     * @param {number} newHeight - Target height
     * @param {Object} [options]
     */
    async scaleTo(newWidth, newHeight, options = {}) {
        if (this.width === 0 || this.height === 0) return;

        const clampedWidth = Math.min(MAX_DIMENSION, Math.max(1, newWidth));
        const clampedHeight = Math.min(MAX_DIMENSION, Math.max(1, newHeight));

        this.width = clampedWidth;
        this.height = clampedHeight;
        this._canvas.width = clampedWidth;
        this._canvas.height = clampedHeight;

        // Re-render SVG at new size
        this.renderSvg();
        await this.render();

        this.invalidateImageCache();
        this.invalidateEffectCache();
    }

    /**
     * Scale the layer by a factor.
     * @param {number} scaleX - Horizontal scale factor
     * @param {number} scaleY - Vertical scale factor
     * @param {Object} [options]
     */
    async scale(scaleX, scaleY, options = {}) {
        const newWidth = Math.round(this.width * scaleX);
        const newHeight = Math.round(this.height * scaleY);
        await this.scaleTo(newWidth, newHeight, options);
    }

    // ==================== Rasterization ====================

    /**
     * Rasterize this layer to document coordinate space.
     * @param {Object} [clipBounds] - Optional bounds to clip to
     * @returns {{canvas: HTMLCanvasElement, bounds: {x, y, width, height}, ctx: CanvasRenderingContext2D}}
     */
    rasterizeToDocument(clipBounds = null) {
        // Get the layer's document-space bounds
        const layerDocBounds = this.getDocumentBounds();

        // Determine output bounds (intersection with clipBounds if provided)
        let outputBounds;
        if (clipBounds) {
            const left = Math.max(layerDocBounds.x, clipBounds.x);
            const top = Math.max(layerDocBounds.y, clipBounds.y);
            const right = Math.min(layerDocBounds.x + layerDocBounds.width, clipBounds.x + clipBounds.width);
            const bottom = Math.min(layerDocBounds.y + layerDocBounds.height, clipBounds.y + clipBounds.height);

            if (right <= left || bottom <= top) {
                const emptyCanvas = document.createElement('canvas');
                emptyCanvas.width = 1;
                emptyCanvas.height = 1;
                return {
                    canvas: emptyCanvas,
                    bounds: { x: 0, y: 0, width: 0, height: 0 },
                    ctx: emptyCanvas.getContext('2d')
                };
            }

            outputBounds = {
                x: left,
                y: top,
                width: right - left,
                height: bottom - top
            };
        } else {
            outputBounds = layerDocBounds;
        }

        // Handle empty layer
        if (this.width === 0 || this.height === 0 || outputBounds.width === 0 || outputBounds.height === 0) {
            const emptyCanvas = document.createElement('canvas');
            emptyCanvas.width = 1;
            emptyCanvas.height = 1;
            return {
                canvas: emptyCanvas,
                bounds: outputBounds,
                ctx: emptyCanvas.getContext('2d')
            };
        }

        // Create output canvas at the output bounds size
        const outputCanvas = document.createElement('canvas');
        outputCanvas.width = outputBounds.width;
        outputCanvas.height = outputBounds.height;
        const ctx = outputCanvas.getContext('2d');

        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // All transforms (rotation, mirroring) are baked into the SVG content
        // So we just need a simple offset copy
        const srcX = outputBounds.x - this.offsetX;
        const srcY = outputBounds.y - this.offsetY;
        ctx.drawImage(
            this.canvas,
            srcX, srcY, outputBounds.width, outputBounds.height,
            0, 0, outputBounds.width, outputBounds.height
        );

        return { canvas: outputCanvas, bounds: outputBounds, ctx };
    }

    /**
     * Create a rasterized (pixel) copy of this layer.
     * Applies all transforms (rotation, scale, mirror) to produce an axis-aligned
     * pixel layer with no transforms (rotation=0, scaleX=1, scaleY=1).
     * @returns {PixelLayer}
     */
    rasterize() {
        // Ensure content is rendered
        this.render();

        // Get the axis-aligned bounding box in document space
        const docBounds = this.getDocumentBounds();

        // Handle empty layers
        if (docBounds.width === 0 || docBounds.height === 0) {
            const rasterLayer = new PixelLayer({
                width: 1,
                height: 1,
                name: this.name,
                opacity: this.opacity,
                blendMode: this.blendMode,
                visible: this.visible,
                locked: this.locked,
                effects: this.effects,
            });
            rasterLayer.offsetX = this.offsetX;
            rasterLayer.offsetY = this.offsetY;
            return rasterLayer;
        }

        // Create output canvas at document bounds size
        const outputCanvas = document.createElement('canvas');
        outputCanvas.width = docBounds.width;
        outputCanvas.height = docBounds.height;
        const ctx = outputCanvas.getContext('2d');

        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // If no transform, simple copy
        if (!this.hasTransform()) {
            // Just offset copy
            const srcX = docBounds.x - this.offsetX;
            const srcY = docBounds.y - this.offsetY;
            ctx.drawImage(this.canvas, srcX, srcY, docBounds.width, docBounds.height,
                          0, 0, docBounds.width, docBounds.height);
        } else {
            // Apply transform to render "baked" version
            ctx.save();

            // Translate so output canvas origin is at docBounds position
            ctx.translate(-docBounds.x, -docBounds.y);

            // Apply transform around layer center (same as Renderer._drawWithTransform)
            const cx = this.offsetX + this.width / 2;
            const cy = this.offsetY + this.height / 2;
            const rotation = this.rotation || 0;
            const scaleX = this.scaleX ?? 1.0;
            const scaleY = this.scaleY ?? 1.0;

            ctx.translate(cx, cy);
            ctx.rotate((rotation * Math.PI) / 180);
            ctx.scale(scaleX, scaleY);
            ctx.translate(-cx, -cy);

            // Draw the layer canvas at its offset position
            ctx.drawImage(this.canvas, this.offsetX, this.offsetY);

            ctx.restore();
        }

        // Create PixelLayer with the baked result
        // No rotation/scale - all transforms have been applied to the pixels
        const rasterLayer = new PixelLayer({
            width: docBounds.width,
            height: docBounds.height,
            name: this.name,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            effects: this.effects,
        });

        // Position at the document bounds origin (axis-aligned)
        rasterLayer.offsetX = docBounds.x;
        rasterLayer.offsetY = docBounds.y;

        // Copy the rendered content
        rasterLayer.ctx.drawImage(outputCanvas, 0, 0);

        return rasterLayer;
    }

    /**
     * Render a thumbnail of this layer.
     * @param {number} maxWidth
     * @param {number} maxHeight
     * @param {Object} [docSize]
     * @returns {{canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D}}
     */
    renderThumbnail(maxWidth, maxHeight, docSize = null) {
        const thumbCanvas = document.createElement('canvas');
        thumbCanvas.width = maxWidth;
        thumbCanvas.height = maxHeight;
        const ctx = thumbCanvas.getContext('2d');

        if (this.width === 0 || this.height === 0) {
            return { canvas: thumbCanvas, ctx };
        }

        const docBounds = this.getDocumentBounds();
        const refWidth = docSize?.width || docBounds.width;
        const refHeight = docSize?.height || docBounds.height;

        if (refWidth === 0 || refHeight === 0) {
            return { canvas: thumbCanvas, ctx };
        }

        const scale = Math.min(maxWidth / refWidth, maxHeight / refHeight);
        const offsetX = (maxWidth - refWidth * scale) / 2;
        const offsetY = (maxHeight - refHeight * scale) / 2;

        const drawW = this.width * scale;
        const drawH = this.height * scale;

        // All transforms (rotation, mirroring) are baked into the SVG content
        // So we just need a simple draw at the offset position
        const drawX = offsetX + (this.offsetX - (docSize ? 0 : docBounds.x)) * scale;
        const drawY = offsetY + (this.offsetY - (docSize ? 0 : docBounds.y)) * scale;
        ctx.drawImage(this.canvas, drawX, drawY, drawW, drawH);

        return { canvas: thumbCanvas, ctx };
    }

    // ==================== Export Methods ====================

    /**
     * Get SVG content as a Blob.
     * @param {Object} [options] - Options passed to toSVG()
     * @returns {Blob}
     */
    toSVGBlob(options = {}) {
        const svg = this.toSVG(options);
        return new Blob([svg], { type: 'image/svg+xml' });
    }

    /**
     * Get SVG content as a data URL.
     * @param {Object} [options] - Options passed to toSVG()
     * @returns {string}
     */
    toSVGDataURL(options = {}) {
        const svg = this.toSVG(options);
        return 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
    }

    /**
     * Export as PNG blob.
     * @param {Object} [options]
     * @returns {Promise<Blob>}
     */
    async toPNGBlob(options = {}) {
        await this.ensureRendered();
        return new Promise((resolve) => {
            this._canvas.toBlob(resolve, 'image/png');
        });
    }

    /**
     * Export as PNG data URL.
     * @returns {Promise<string>}
     */
    async toPNGDataURL() {
        await this.ensureRendered();
        return this._canvas.toDataURL('image/png');
    }

    // ==================== Utility Methods ====================

    /**
     * Extract the inner content from an SVG string.
     * @param {string} svgString - Full SVG string
     * @returns {string} Inner content
     * @protected
     */
    _extractSVGContent(svgString) {
        const openTagMatch = svgString.match(/<svg[^>]*>/i);
        if (!openTagMatch) return svgString;

        const startIdx = openTagMatch.index + openTagMatch[0].length;
        const endIdx = svgString.lastIndexOf('</svg>');
        if (endIdx <= startIdx) return svgString;

        return svgString.substring(startIdx, endIdx);
    }

    /**
     * Parse dimensions from SVG string.
     * @param {string} svgString
     * @returns {{width: number, height: number}}
     * @protected
     */
    _parseSVGDimensions(svgString) {
        // Try viewBox first
        const viewBoxMatch = svgString.match(/viewBox\s*=\s*["']([^"']+)["']/i);
        if (viewBoxMatch) {
            const parts = viewBoxMatch[1].trim().split(/[\s,]+/);
            if (parts.length >= 4) {
                return {
                    width: parseFloat(parts[2]) || this.width,
                    height: parseFloat(parts[3]) || this.height
                };
            }
        }

        // Fall back to width/height attributes
        const widthMatch = svgString.match(/\bwidth\s*=\s*["']([^"']+)["']/i);
        const heightMatch = svgString.match(/\bheight\s*=\s*["']([^"']+)["']/i);

        return {
            width: widthMatch ? (parseFloat(widthMatch[1]) || this.width) : this.width,
            height: heightMatch ? (parseFloat(heightMatch[1]) || this.height) : this.height
        };
    }

    /**
     * Create an SVG document wrapper with proper headers.
     * @param {string} content - SVG element content
     * @param {Object} [options]
     * @returns {string}
     */
    wrapSVG(content, options = {}) {
        const width = options.width || this.width;
        const height = options.height || this.height;
        const viewBox = options.viewBox || `0 0 ${width} ${height}`;
        const shapeRendering = options.antialiasing ? '' : ' shape-rendering="crispEdges"';

        return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="${width}" height="${height}"
     viewBox="${viewBox}"${shapeRendering}>
${content}
</svg>`;
    }

    // ==================== SVG Export ====================

    /**
     * Convert this layer to an SVG element for document export.
     * Creates a <g> with sf:type and embeds the ORIGINAL SVG content with proper transforms.
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
        const g = createLayerGroup(xmlDoc, this.id, this.type, this.name);

        // Add sf:properties element with all layer properties
        // NOTE: svgData is NOT stored here - it's embedded in the visual SVG below
        // and extracted on import by "debaking" (removing the transform envelope)
        const properties = {
            ...this.serializeBase(),
            naturalWidth: this.naturalWidth || this.width,
            naturalHeight: this.naturalHeight || this.height
        };
        const propsEl = createPropertiesElement(xmlDoc, properties);
        g.appendChild(propsEl);

        // Embed the ORIGINAL SVG content with explicit transform
        const svgContent = this.svgData || '';
        if (svgContent) {
            const natW = this.naturalWidth || this.width;
            const natH = this.naturalHeight || this.height;

            // Calculate total scale: size scaling * layer scale (for mirroring)
            const sizeScaleX = this.width / natW;
            const sizeScaleY = this.height / natH;
            const totalScaleX = sizeScaleX * (this.scaleX || 1);
            const totalScaleY = sizeScaleY * (this.scaleY || 1);

            // Center point in document space
            const cx = this.offsetX + this.width / 2;
            const cy = this.offsetY + this.height / 2;

            // Build transform: translate to center, rotate, scale, translate back
            const contentGroup = xmlDoc.createElementNS('http://www.w3.org/2000/svg', 'g');
            const rotation = this.rotation || 0;

            // Transform sequence:
            // 1. Move origin to layer center
            // 2. Rotate
            // 3. Scale (includes size + mirror)
            // 4. Move back so SVG content is centered
            contentGroup.setAttribute('transform',
                `translate(${cx}, ${cy}) rotate(${rotation}) scale(${totalScaleX}, ${totalScaleY}) translate(${-natW / 2}, ${-natH / 2})`);

            // Parse and import the original SVG content
            const parser = new DOMParser();
            const svgDoc = parser.parseFromString(svgContent, 'image/svg+xml');
            const svgRoot = svgDoc.documentElement;

            if (svgRoot && svgRoot.tagName === 'svg') {
                const importedSvg = xmlDoc.importNode(svgRoot, true);
                // Set explicit width/height to natural dimensions so scale transform works
                importedSvg.setAttribute('width', natW.toString());
                importedSvg.setAttribute('height', natH.toString());
                contentGroup.appendChild(importedSvg);
            }

            g.appendChild(contentGroup);
        }

        return g;
    }

    // ==================== Abstract Methods ====================

    /**
     * Clone this layer.
     * @returns {SVGBaseLayer}
     * @abstract
     */
    clone() {
        throw new Error('SVGBaseLayer.clone() must be implemented by subclass');
    }

    // ==================== Serialization ====================

    /**
     * Serialize all shared SVGBaseLayer properties.
     * Subclasses should call this and merge with their own properties.
     * @returns {Object}
     */
    serializeBase() {
        return {
            ...this.getBaseSerializeData(),
            // SVGBaseLayer transform state
            _originalSvgData: this._originalSvgData,
            _originalWidth: this._originalWidth,
            _originalHeight: this._originalHeight,
            _contentRotation: this._contentRotation || 0,
            _mirrorX: this._mirrorX || false,
            _mirrorY: this._mirrorY || false
        };
    }

    /**
     * Restore all shared SVGBaseLayer properties from serialized data.
     * Subclasses should call this in their deserialize() method.
     * @param {Object} data - Serialized data
     */
    restoreBase(data) {
        // BaseLayer properties are set via constructor, but transform state needs explicit restore
        if (data._originalSvgData !== undefined) {
            this._originalSvgData = data._originalSvgData;
        }
        if (data._originalWidth !== undefined) {
            this._originalWidth = data._originalWidth;
        }
        if (data._originalHeight !== undefined) {
            this._originalHeight = data._originalHeight;
        }
        if (data._contentRotation !== undefined) {
            this._contentRotation = data._contentRotation;
        }
        if (data._mirrorX !== undefined) {
            this._mirrorX = data._mirrorX;
        }
        if (data._mirrorY !== undefined) {
            this._mirrorY = data._mirrorY;
        }

        // If there are transforms, rebuild the SVG
        if (this._contentRotation || this._mirrorX || this._mirrorY) {
            this._regenerateCanvas();
            this.renderSvg();
        }
    }

    /**
     * Serialize for history/save.
     * @returns {Object}
     * @abstract
     */
    serialize() {
        throw new Error('SVGBaseLayer.serialize() must be implemented by subclass');
    }
}

export default SVGBaseLayer;
