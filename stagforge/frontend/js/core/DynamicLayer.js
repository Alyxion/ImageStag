/**
 * DynamicLayer - Base class for layers that generate content programmatically.
 *
 * Unlike raster Layer which has a directly drawable canvas, DynamicLayer:
 * - Has NO public ctx (cannot be drawn on externally)
 * - Generates pixel content on demand via render()
 * - Can export pixels in various formats (RGBA8, RGBA16, RGB8, RGB16)
 * - Uses an internal canvas for caching rendered content
 *
 * Subclasses must implement:
 * - render() - Generate content to internal canvas
 * - clone() - Create a copy of this layer
 * - serialize() - Convert to JSON for saving
 * - static deserialize() - Create from JSON
 */
import { LayerEffect, effectRegistry } from './LayerEffects.js';

export class DynamicLayer {
    /** Serialization version for migration support */
    static VERSION = 1;

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
        this.id = options.id || crypto.randomUUID();
        this.name = options.name || 'Dynamic Layer';
        this.type = 'dynamic';

        // Dimensions (guard against NaN)
        this.width = Math.max(1, Math.ceil(options.width || 1));
        this.height = Math.max(1, Math.ceil(options.height || 1));

        // Offset from document origin
        this.offsetX = Math.floor(options.offsetX || 0);
        this.offsetY = Math.floor(options.offsetY || 0);

        // Transform properties (applied around layer center)
        this.rotation = options.rotation || 0;  // Rotation in degrees
        this.scaleX = options.scaleX ?? 1.0;    // Horizontal scale factor
        this.scaleY = options.scaleY ?? 1.0;    // Vertical scale factor

        // Parent group ID (null = root level)
        this.parentId = options.parentId || null;

        // Internal canvas for rendering (NOT publicly accessible)
        this._canvas = document.createElement('canvas');
        this._canvas.width = this.width;
        this._canvas.height = this.height;
        this._ctx = this._canvas.getContext('2d', { willReadFrequently: true });

        // Public ctx is null - external code cannot draw on dynamic layers
        this.ctx = null;

        // For compatibility with code that accesses .canvas for compositing
        // This is read-only - writing to it has no effect on the layer content
        this.canvas = this._canvas;

        // Layer properties
        this.opacity = options.opacity ?? 1.0;
        this.blendMode = options.blendMode || 'normal';
        this.visible = options.visible ?? true;
        this.locked = options.locked ?? false;

        // Layer effects (non-destructive)
        this.effects = options.effects || [];

        // Cache management
        this._effectCacheVersion = 0;
        this._cachedImageBlob = null;
        this._contentVersion = 0;
        this._renderValid = false;
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

    /**
     * Check if this is a text layer.
     * @returns {boolean}
     */
    isText() {
        return false;
    }

    /**
     * Check if this is an SVG layer.
     * @returns {boolean}
     */
    isSVG() {
        return false;
    }

    /**
     * Check if this is a dynamic (non-raster) layer.
     * @returns {boolean}
     */
    isDynamic() {
        return true;
    }

    // ==================== Rendering ====================

    /**
     * Render content to internal canvas. Must be implemented by subclasses.
     * @returns {Promise<void>}
     * @abstract
     */
    async render() {
        throw new Error('DynamicLayer.render() must be implemented by subclass');
    }

    /**
     * Ensure render cache is valid, re-rendering if needed.
     * @returns {Promise<void>}
     */
    async ensureRendered() {
        if (!this._renderValid) {
            await this.render();
            this._renderValid = true;
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

    // ==================== Pixel Access ====================

    /**
     * Get raw RGBA8 pixel data (Uint8ClampedArray).
     * @returns {Promise<Uint8ClampedArray>}
     */
    async getPixelsRGBA8() {
        await this.ensureRendered();
        const imageData = this._ctx.getImageData(0, 0, this.width, this.height);
        return imageData.data;
    }

    /**
     * Get RGB8 pixel data (no alpha).
     * @returns {Promise<Uint8Array>}
     */
    async getPixelsRGB8() {
        const rgba = await this.getPixelsRGBA8();
        const rgb = new Uint8Array((rgba.length / 4) * 3);
        for (let i = 0, j = 0; i < rgba.length; i += 4, j += 3) {
            rgb[j] = rgba[i];
            rgb[j + 1] = rgba[i + 1];
            rgb[j + 2] = rgba[i + 2];
        }
        return rgb;
    }

    /**
     * Get RGBA16 pixel data (Uint16Array, values 0-65535).
     * @returns {Promise<Uint16Array>}
     */
    async getPixelsRGBA16() {
        const rgba8 = await this.getPixelsRGBA8();
        const rgba16 = new Uint16Array(rgba8.length);
        for (let i = 0; i < rgba8.length; i++) {
            // Scale 0-255 to 0-65535
            rgba16[i] = (rgba8[i] << 8) | rgba8[i];
        }
        return rgba16;
    }

    /**
     * Get RGB16 pixel data (no alpha, Uint16Array).
     * @returns {Promise<Uint16Array>}
     */
    async getPixelsRGB16() {
        const rgba8 = await this.getPixelsRGBA8();
        const rgb16 = new Uint16Array((rgba8.length / 4) * 3);
        for (let i = 0, j = 0; i < rgba8.length; i += 4, j += 3) {
            rgb16[j] = (rgba8[i] << 8) | rgba8[i];
            rgb16[j + 1] = (rgba8[i + 1] << 8) | rgba8[i + 1];
            rgb16[j + 2] = (rgba8[i + 2] << 8) | rgba8[i + 2];
        }
        return rgb16;
    }

    /**
     * Get pixels in specified format.
     * @param {'rgba8'|'rgb8'|'rgba16'|'rgb16'} format
     * @returns {Promise<Uint8ClampedArray|Uint8Array|Uint16Array>}
     */
    async getPixels(format = 'rgba8') {
        switch (format) {
            case 'rgba8': return this.getPixelsRGBA8();
            case 'rgb8': return this.getPixelsRGB8();
            case 'rgba16': return this.getPixelsRGBA16();
            case 'rgb16': return this.getPixelsRGB16();
            default: throw new Error(`Unknown pixel format: ${format}`);
        }
    }

    /**
     * Get ImageData for the layer.
     * @returns {Promise<ImageData>}
     */
    async getImageData() {
        await this.ensureRendered();
        return this._ctx.getImageData(0, 0, this.width, this.height);
    }

    // ==================== Bounds ====================

    /**
     * Get the bounds of this layer in document coordinates.
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

    /**
     * Get the visual bounds including effect expansion.
     * @returns {{x: number, y: number, width: number, height: number}}
     */
    getVisualBounds() {
        const base = this.getBounds();

        if (!this.hasEffects()) {
            return base;
        }

        let left = 0, top = 0, right = 0, bottom = 0;
        for (const effect of this.effects) {
            if (!effect.enabled) continue;
            const exp = effect.getExpansion();
            left = Math.max(left, exp.left);
            top = Math.max(top, exp.top);
            right = Math.max(right, exp.right);
            bottom = Math.max(bottom, exp.bottom);
        }

        return {
            x: base.x - left,
            y: base.y - top,
            width: base.width + left + right,
            height: base.height + top + bottom
        };
    }

    // ==================== Effects ====================

    /**
     * Add an effect to this layer.
     * @param {LayerEffect} effect
     * @param {number} [index]
     */
    addEffect(effect, index = -1) {
        if (index < 0 || index >= this.effects.length) {
            this.effects.push(effect);
        } else {
            this.effects.splice(index, 0, effect);
        }
        this._effectCacheVersion++;
    }

    /**
     * Remove an effect by ID.
     * @param {string} effectId
     * @returns {boolean}
     */
    removeEffect(effectId) {
        const index = this.effects.findIndex(e => e.id === effectId);
        if (index >= 0) {
            this.effects.splice(index, 1);
            this._effectCacheVersion++;
            return true;
        }
        return false;
    }

    /**
     * Get an effect by ID.
     * @param {string} effectId
     * @returns {LayerEffect|null}
     */
    getEffect(effectId) {
        return this.effects.find(e => e.id === effectId) || null;
    }

    /**
     * Update effect parameters.
     * @param {string} effectId
     * @param {Object} params
     * @returns {boolean}
     */
    updateEffect(effectId, params) {
        const effect = this.getEffect(effectId);
        if (!effect) return false;
        Object.assign(effect, params);
        this._effectCacheVersion++;
        return true;
    }

    /**
     * Check if layer has any enabled effects.
     * @returns {boolean}
     */
    hasEffects() {
        return this.effects.some(e => e.enabled);
    }

    /**
     * Invalidate effect cache.
     */
    invalidateEffectCache() {
        this._effectCacheVersion++;
    }

    // ==================== Image Cache ====================

    /**
     * Invalidate the image cache.
     */
    invalidateImageCache() {
        this._cachedImageBlob = null;
        this._contentVersion++;
    }

    /**
     * Get cached WebP blob if available.
     * @returns {Blob|null}
     */
    getCachedImageBlob() {
        return this._cachedImageBlob;
    }

    /**
     * Set cached WebP blob after encoding.
     * @param {Blob} blob
     */
    setCachedImageBlob(blob) {
        this._cachedImageBlob = blob;
    }

    /**
     * Check if image cache is valid.
     * @returns {boolean}
     */
    hasValidImageCache() {
        return this._cachedImageBlob !== null;
    }

    // ==================== Transform Methods ====================

    /**
     * Get the center point of the layer in document coordinates.
     * This is the pivot point for rotation and scaling.
     * @returns {{x: number, y: number}}
     */
    getCenter() {
        return {
            x: this.offsetX + this.width / 2,
            y: this.offsetY + this.height / 2
        };
    }

    /**
     * Check if this layer has any transform (rotation or non-unit scale).
     * @returns {boolean}
     */
    hasTransform() {
        return this.rotation !== 0 || this.scaleX !== 1.0 || this.scaleY !== 1.0;
    }

    /**
     * Convert document coordinates to layer canvas coordinates.
     * @param {number} docX
     * @param {number} docY
     * @returns {{x: number, y: number}}
     */
    docToCanvas(docX, docY) {
        if (!this.hasTransform()) {
            return {
                x: docX - this.offsetX,
                y: docY - this.offsetY
            };
        }
        return this.docToLayer(docX, docY);
    }

    /**
     * Convert layer canvas coordinates to document coordinates.
     * @param {number} canvasX
     * @param {number} canvasY
     * @returns {{x: number, y: number}}
     */
    canvasToDoc(canvasX, canvasY) {
        if (!this.hasTransform()) {
            return {
                x: canvasX + this.offsetX,
                y: canvasY + this.offsetY
            };
        }
        return this.layerToDoc(canvasX, canvasY);
    }

    /**
     * Transform a point from layer local coordinates to document coordinates.
     * @param {number} lx - X in layer local space (0 to width)
     * @param {number} ly - Y in layer local space (0 to height)
     * @returns {{x: number, y: number}} Point in document space
     */
    layerToDoc(lx, ly) {
        if (!this.hasTransform()) {
            return {
                x: lx + this.offsetX,
                y: ly + this.offsetY
            };
        }

        const cx = this.width / 2;
        const cy = this.height / 2;
        let x = lx - cx;
        let y = ly - cy;

        x *= this.scaleX;
        y *= this.scaleY;

        const radians = (this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);
        const rx = x * cos - y * sin;
        const ry = x * sin + y * cos;

        const docCenterX = this.offsetX + cx;
        const docCenterY = this.offsetY + cy;

        return {
            x: rx + docCenterX,
            y: ry + docCenterY
        };
    }

    /**
     * Transform a point from document coordinates to layer local coordinates.
     * @param {number} docX - X in document space
     * @param {number} docY - Y in document space
     * @returns {{x: number, y: number}} Point in layer local space
     */
    docToLayer(docX, docY) {
        if (!this.hasTransform()) {
            return {
                x: docX - this.offsetX,
                y: docY - this.offsetY
            };
        }

        const cx = this.width / 2;
        const cy = this.height / 2;
        const docCenterX = this.offsetX + cx;
        const docCenterY = this.offsetY + cy;
        let x = docX - docCenterX;
        let y = docY - docCenterY;

        const radians = (-this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);
        const rx = x * cos - y * sin;
        const ry = x * sin + y * cos;

        x = rx / this.scaleX;
        y = ry / this.scaleY;

        return {
            x: x + cx,
            y: y + cy
        };
    }

    /**
     * Get the 2D transform matrix components [a, b, c, d, e, f].
     * @returns {number[]} [a, b, c, d, e, f] matrix components
     */
    getTransformMatrix() {
        if (!this.hasTransform()) {
            return [1, 0, 0, 1, 0, 0];
        }

        const cx = this.offsetX + this.width / 2;
        const cy = this.offsetY + this.height / 2;
        const radians = (this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);

        const a = cos * this.scaleX;
        const b = sin * this.scaleX;
        const c = -sin * this.scaleY;
        const d = cos * this.scaleY;
        const e = cx - cx * cos * this.scaleX + cy * sin * this.scaleY;
        const f = cy - cx * sin * this.scaleX - cy * cos * this.scaleY;

        return [a, b, c, d, e, f];
    }

    /**
     * Set rotation angle in degrees.
     * @param {number} degrees - Rotation angle
     */
    setRotation(degrees) {
        this.rotation = degrees;
        this.invalidateEffectCache();
    }

    /**
     * Set scale factors.
     * @param {number} sx - Horizontal scale factor
     * @param {number} sy - Vertical scale factor (defaults to sx for uniform scale)
     */
    setScale(sx, sy = sx) {
        this.scaleX = sx;
        this.scaleY = sy;
        this.invalidateEffectCache();
    }

    /**
     * Reset transforms to identity (no rotation, unit scale).
     */
    resetTransform() {
        this.rotation = 0;
        this.scaleX = 1.0;
        this.scaleY = 1.0;
        this.invalidateEffectCache();
    }

    // ==================== Document Coordinate Methods ====================

    /**
     * Get the axis-aligned bounding box of this layer in document coordinates.
     * Accounts for rotation and scale transforms.
     * @returns {{x: number, y: number, width: number, height: number}}
     */
    getDocumentBounds() {
        // Handle 0x0 layers
        if (this.width === 0 || this.height === 0) {
            return { x: this.offsetX, y: this.offsetY, width: 0, height: 0 };
        }

        // Fast path for non-transformed layers
        if (!this.hasTransform()) {
            return {
                x: this.offsetX,
                y: this.offsetY,
                width: this.width,
                height: this.height
            };
        }

        // Transform all 4 corners and find enclosing rectangle
        const corners = [
            this.layerToDoc(0, 0),
            this.layerToDoc(this.width, 0),
            this.layerToDoc(this.width, this.height),
            this.layerToDoc(0, this.height)
        ];

        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        for (const corner of corners) {
            minX = Math.min(minX, corner.x);
            minY = Math.min(minY, corner.y);
            maxX = Math.max(maxX, corner.x);
            maxY = Math.max(maxY, corner.y);
        }

        return {
            x: Math.floor(minX),
            y: Math.floor(minY),
            width: Math.ceil(maxX) - Math.floor(minX),
            height: Math.ceil(maxY) - Math.floor(minY)
        };
    }

    /**
     * Rasterize this layer to document coordinate space.
     * Returns a canvas containing the layer as it appears in the document,
     * with all transforms (rotation, scale) applied.
     *
     * @param {Object} [clipBounds] - Optional bounds to clip to (document coords)
     * @param {number} clipBounds.x
     * @param {number} clipBounds.y
     * @param {number} clipBounds.width
     * @param {number} clipBounds.height
     * @returns {{canvas: HTMLCanvasElement, bounds: {x, y, width, height}, ctx: CanvasRenderingContext2D}}
     */
    rasterizeToDocument(clipBounds = null) {
        // Get the layer's document-space bounds
        const layerDocBounds = this.getDocumentBounds();

        // Determine output bounds (intersection with clipBounds if provided)
        let outputBounds;
        if (clipBounds) {
            // Intersect with clip bounds
            const left = Math.max(layerDocBounds.x, clipBounds.x);
            const top = Math.max(layerDocBounds.y, clipBounds.y);
            const right = Math.min(layerDocBounds.x + layerDocBounds.width, clipBounds.x + clipBounds.width);
            const bottom = Math.min(layerDocBounds.y + layerDocBounds.height, clipBounds.y + clipBounds.height);

            if (right <= left || bottom <= top) {
                // No intersection - return empty canvas
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

        // Enable high-quality interpolation
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // Fast path for non-transformed layers
        if (!this.hasTransform()) {
            // Simple offset - just copy the relevant portion
            const srcX = outputBounds.x - this.offsetX;
            const srcY = outputBounds.y - this.offsetY;
            ctx.drawImage(
                this.canvas,
                srcX, srcY, outputBounds.width, outputBounds.height,
                0, 0, outputBounds.width, outputBounds.height
            );
            return { canvas: outputCanvas, bounds: outputBounds, ctx };
        }

        // For transformed layers, use canvas transforms with high-quality interpolation
        // The transform is: translate to center -> scale -> rotate -> translate to doc position
        const cx = this.width / 2;   // Layer center in layer coords
        const cy = this.height / 2;
        const docCx = this.offsetX + cx;  // Layer center in document coords
        const docCy = this.offsetY + cy;

        // Build the transform:
        // 1. Offset output canvas origin to outputBounds position
        // 2. Translate to layer's document center
        // 3. Rotate
        // 4. Scale
        // 5. Translate back by layer center (in layer coords)

        ctx.translate(-outputBounds.x, -outputBounds.y);  // Map to output canvas
        ctx.translate(docCx, docCy);                       // Move to rotation center
        ctx.rotate(this.rotation * Math.PI / 180);         // Apply rotation
        ctx.scale(this.scaleX, this.scaleY);               // Apply scale
        ctx.translate(-cx, -cy);                           // Move back to layer origin

        // Draw the layer content
        ctx.drawImage(this.canvas, 0, 0);

        return { canvas: outputCanvas, bounds: outputBounds, ctx };
    }

    // ==================== Abstract Methods ====================

    /**
     * Clone this layer. Must be implemented by subclasses.
     * @returns {DynamicLayer}
     * @abstract
     */
    clone() {
        throw new Error('DynamicLayer.clone() must be implemented by subclass');
    }

    /**
     * Serialize to JSON. Must be implemented by subclasses.
     * @returns {Object}
     * @abstract
     */
    serialize() {
        throw new Error('DynamicLayer.serialize() must be implemented by subclass');
    }

    /**
     * Get base serialization data (common to all dynamic layers).
     * @returns {Object}
     */
    getBaseSerializeData() {
        return {
            _version: this.constructor.VERSION,
            _type: this.constructor.name,
            type: this.type,
            id: this.id,
            name: this.name,
            width: this.width,
            height: this.height,
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            rotation: this.rotation,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            parentId: this.parentId,
            effects: this.effects.map(e => e.serialize()),
        };
    }

    /**
     * Apply base deserialization data to this layer.
     * @param {Object} data
     */
    applyBaseDeserializeData(data) {
        if (data.id) this.id = data.id;
        if (data.name) this.name = data.name;
        if (data.opacity !== undefined) this.opacity = data.opacity;
        if (data.blendMode) this.blendMode = data.blendMode;
        if (data.visible !== undefined) this.visible = data.visible;
        if (data.locked !== undefined) this.locked = data.locked;
        if (data.parentId !== undefined) this.parentId = data.parentId;
        if (data.offsetX !== undefined) this.offsetX = data.offsetX;
        if (data.offsetY !== undefined) this.offsetY = data.offsetY;

        // Transform properties
        this.rotation = data.rotation ?? 0;
        this.scaleX = data.scaleX ?? 1.0;
        this.scaleY = data.scaleY ?? 1.0;

        // Deserialize effects
        if (data.effects && Array.isArray(data.effects)) {
            this.effects = data.effects.map(effectData => {
                const EffectClass = effectRegistry[effectData._type] || LayerEffect;
                return EffectClass.deserialize(effectData);
            }).filter(e => e);
        }
    }

    /**
     * Resize internal canvas.
     * @param {number} newWidth
     * @param {number} newHeight
     */
    resize(newWidth, newHeight) {
        this.width = Math.max(1, Math.ceil(newWidth));
        this.height = Math.max(1, Math.ceil(newHeight));
        this._canvas.width = this.width;
        this._canvas.height = this.height;
        this.invalidateRender();
    }
}

export default DynamicLayer;
