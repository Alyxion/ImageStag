/**
 * BaseLayer - Abstract base class for all layer types.
 *
 * Provides shared functionality for:
 * - Layer identity and properties (id, name, type, visible, locked, etc.)
 * - Transform operations (rotation, scale, mirror)
 * - Coordinate conversion (layerToDoc, docToLayer, etc.)
 * - Effects management
 * - Image caching for auto-save optimization
 * - Serialization helpers
 *
 * Subclasses:
 * - PixelLayer (type: 'raster') - Canvas-based raster layers
 * - SVGLayer (type: 'svg', abstract) - Base for SVG-based layers
 *   - StaticSVGLayer (type: 'svg') - Raw SVG content
 *   - TextLayer (type: 'text') - Text rendered as SVG
 * - LayerGroup (type: 'group') - Container for organizing layers
 */
import { LayerEffect, effectRegistry } from './LayerEffects.js';
import { DynamicFilter } from './DynamicFilter.js';
import { MAX_DIMENSION } from '../config/limits.js';
import { Frame } from './Frame.js';

export class BaseLayer {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {string} [options.id] - Unique identifier
     * @param {string} [options.name] - Display name
     * @param {string} [options.type] - Layer type
     * @param {number} [options.width] - Layer width
     * @param {number} [options.height] - Layer height
     * @param {number} [options.offsetX] - X offset from document origin
     * @param {number} [options.offsetY] - Y offset from document origin
     * @param {number} [options.rotation] - Rotation in degrees
     * @param {number} [options.scaleX] - Horizontal scale factor
     * @param {number} [options.scaleY] - Vertical scale factor
     * @param {number} [options.opacity] - Opacity 0.0-1.0
     * @param {string} [options.blendMode] - Blend mode
     * @param {boolean} [options.visible] - Visibility
     * @param {boolean} [options.locked] - Lock state
     * @param {string} [options.parentId] - Parent group ID
     * @param {Array} [options.effects] - Layer effects
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.name = options.name || 'Layer';
        this.type = options.type || 'base';

        // Dimensions (guard against NaN, clamp to MAX_DIMENSION)
        // Allow 0x0 for empty layers that will auto-fit to content
        this.width = Math.min(MAX_DIMENSION, Math.max(0, Math.ceil(options.width || 0)));
        this.height = Math.min(MAX_DIMENSION, Math.max(0, Math.ceil(options.height || 0)));

        // Offset from document origin (can be negative, guard against NaN)
        this.offsetX = Math.floor(options.offsetX || 0);
        this.offsetY = Math.floor(options.offsetY || 0);

        // Transform properties (applied around layer center)
        this.rotation = options.rotation || 0;  // Rotation in degrees
        this.scaleX = options.scaleX ?? 1.0;    // Horizontal scale factor
        this.scaleY = options.scaleY ?? 1.0;    // Vertical scale factor

        // Parent group ID (null = root level)
        this.parentId = options.parentId || null;

        // Layer properties
        this.opacity = options.opacity ?? 1.0;
        this.fillOpacity = options.fillOpacity ?? 1.0;
        this.blendMode = options.blendMode || 'normal';
        this.visible = options.visible ?? true;
        this.locked = options.locked ?? false;

        // Layer effects (non-destructive)
        this.effects = options.effects || [];

        // Dynamic filters (non-destructive, applied before effects)
        this.filters = (options.filters || []).map(f =>
            f instanceof DynamicFilter ? f : DynamicFilter.deserialize(f)
        );

        // Cache management
        this._effectCacheVersion = 0;
        this._filterCacheVersion = 0;
        this._cachedImageBlob = null;
        this._contentVersion = 0;

        // Change tracking (bumped on any visual change, polled by render consumers)
        this.changeCounter = options.changeCounter || 0;
        this.lastChangeTimestamp = options.lastChangeTimestamp || Date.now();

        // Multi-frame support
        this._frames = [this._createFrameData(options)];
        this.activeFrameIndex = 0;
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
     * Check if this is a pixel/raster layer.
     * @returns {boolean}
     */
    isRaster() {
        return false;
    }

    /**
     * Check if this is a dynamic (non-raster) layer.
     * @returns {boolean}
     */
    isDynamic() {
        return false;
    }

    // ==================== Frame Data (Subclass Overrides) ====================

    /**
     * Create frame data for a new frame. Subclasses override to include
     * type-specific data (canvas, svgContent, runs, etc.).
     * @param {Object} options
     * @returns {Object} Frame data object
     * @protected
     */
    _createFrameData(options) {
        return new Frame({ duration: options.duration ?? 0.1, delay: options.delay ?? 0.0 });
    }

    /**
     * Create empty frame data (for addFrame without cloning).
     * @returns {Object}
     * @protected
     */
    _createEmptyFrameData() {
        return new Frame({});
    }

    /**
     * Clone frame data (deep copy).
     * @param {Frame} frameData
     * @returns {Frame}
     * @protected
     */
    _cloneFrameData(frameData) {
        return frameData.clone();
    }

    /**
     * Dispose of frame data resources.
     * @param {Frame} frameData
     * @protected
     */
    _disposeFrameData(frameData) {
        frameData.dispose();
    }

    // ==================== Per-Frame Operations (Subclass Overrides) ====================

    /**
     * Get content bounds for a specific frame.
     * @param {Object} frame - Frame data
     * @returns {{x: number, y: number, width: number, height: number}|null}
     * @protected
     */
    _getFrameContentBounds(frame) {
        return null;
    }

    /**
     * Expand a single frame to include new bounds.
     * @param {Object} frame - Frame data
     * @param {Object} newBounds - {x, y, width, height}
     * @param {Object} oldBounds - {x, y, width, height}
     * @protected
     */
    _expandFrameToInclude(frame, newBounds, oldBounds) {
        // Base: no-op
    }

    /**
     * Rotate a single frame's content.
     * @param {Object} frame - Frame data
     * @param {number} degrees
     * @param {number} oldW - Old document width
     * @param {number} oldH - Old document height
     * @param {number} newW - New document width
     * @param {number} newH - New document height
     * @protected
     */
    _rotateFrameCanvas(frame, degrees, oldW, oldH, newW, newH) {
        // Base: no-op
    }

    /**
     * Mirror a single frame's content.
     * @param {Object} frame - Frame data
     * @param {'horizontal'|'vertical'} direction
     * @param {number} docW
     * @param {number} docH
     * @protected
     */
    _mirrorFrameContent(frame, direction, docW, docH) {
        // Base: no-op
    }

    /**
     * Scale a single frame.
     * @param {Object} frame - Frame data
     * @param {number} scaleX
     * @param {number} scaleY
     * @protected
     */
    _scaleFrame(frame, scaleX, scaleY) {
        // Base: no-op
    }

    /**
     * Fit a single frame to a region (crop).
     * @param {Object} frame - Frame data
     * @param {number} cropX
     * @param {number} cropY
     * @param {number} cropW
     * @param {number} cropH
     * @protected
     */
    _fitFrameToRegion(frame, cropX, cropY, cropW, cropH) {
        // Base: no-op
    }

    // ==================== Frame Management ====================

    /**
     * Get the number of frames.
     * @returns {number}
     */
    get frameCount() {
        return this._frames.length;
    }

    /**
     * Get frame data at index.
     * @param {number} index
     * @returns {Object|null}
     */
    getFrame(index) {
        return this._frames[index] || null;
    }

    /**
     * Get the active frame data.
     * @returns {Object}
     */
    get activeFrame() {
        return this._frames[this.activeFrameIndex];
    }

    /**
     * Add a new frame.
     * @param {Object} [options]
     * @param {boolean} [options.clone=false] - Clone active frame instead of creating empty
     * @param {number} [options.insertIndex] - Where to insert (default: after active frame)
     * @returns {number} Index of the new frame
     */
    addFrame(options = {}) {
        const frame = options.clone
            ? this._cloneFrameData(this._frames[this.activeFrameIndex])
            : this._createEmptyFrameData();
        const insertIndex = options.insertIndex ?? (this.activeFrameIndex + 1);
        this._frames.splice(insertIndex, 0, frame);
        this.activeFrameIndex = insertIndex;
        this.markChanged();
        return insertIndex;
    }

    /**
     * Remove a frame by index.
     * @param {number} index
     * @returns {boolean}
     */
    removeFrame(index) {
        if (this._frames.length <= 1) return false;
        if (index < 0 || index >= this._frames.length) return false;

        this._disposeFrameData(this._frames[index]);
        this._frames.splice(index, 1);

        if (this.activeFrameIndex >= this._frames.length) {
            this.activeFrameIndex = this._frames.length - 1;
        }
        this.markChanged();
        return true;
    }

    /**
     * Duplicate a frame at the given index.
     * @param {number} index
     * @returns {number} Index of the new frame
     */
    duplicateFrame(index) {
        if (index < 0 || index >= this._frames.length) return -1;

        const frame = this._cloneFrameData(this._frames[index]);
        this._frames.splice(index + 1, 0, frame);
        this.activeFrameIndex = index + 1;
        this.markChanged();
        return index + 1;
    }

    /**
     * Set the active frame index.
     * @param {number} index
     */
    setActiveFrame(index) {
        if (index < 0 || index >= this._frames.length) return;
        if (index === this.activeFrameIndex) return;
        this.activeFrameIndex = index;
        this.markChanged();
    }

    /**
     * Get frame duration in milliseconds.
     * @param {number} index
     * @returns {number}
     */
    getFrameDuration(index) {
        return this._frames[index]?.duration || 100;
    }

    /**
     * Set frame duration in milliseconds.
     * @param {number} index
     * @param {number} ms
     */
    setFrameDuration(index, ms) {
        if (this._frames[index]) {
            this._frames[index].duration = ms;
        }
    }

    // ==================== Image Cache ====================

    /**
     * Invalidate the image cache (call after modifying layer pixels).
     * This should be called by any operation that changes the canvas content.
     */
    invalidateImageCache() {
        this._cachedImageBlob = null;
        this._contentVersion++;
        this.markChanged();
    }

    /**
     * Mark this layer as changed (updates change tracking).
     * Called automatically by invalidateImageCache(), but can be called
     * directly for non-pixel changes (e.g., property updates).
     */
    markChanged() {
        this.changeCounter++;
        this.lastChangeTimestamp = Date.now();
    }

    /**
     * Lightweight version bump for painting tools.
     * Signals a visual change without updating timestamp.
     */
    touch() {
        this.changeCounter++;
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
     * @param {Blob} blob - WebP blob
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

    // ==================== Effects ====================

    /**
     * Add an effect to this layer.
     * @param {LayerEffect} effect - Effect to add
     * @param {number} [index] - Position to insert at (default: end)
     */
    addEffect(effect, index = -1) {
        if (index < 0 || index >= this.effects.length) {
            this.effects.push(effect);
        } else {
            this.effects.splice(index, 0, effect);
        }
        this.invalidateEffectCache();
    }

    /**
     * Remove an effect by ID.
     * @param {string} effectId
     * @returns {boolean} True if effect was found and removed
     */
    removeEffect(effectId) {
        const index = this.effects.findIndex(e => e.id === effectId);
        if (index >= 0) {
            this.effects.splice(index, 1);
            this.invalidateEffectCache();
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
     * @param {Object} params - Parameters to update
     * @returns {boolean} True if effect was found and updated
     */
    updateEffect(effectId, params) {
        const effect = this.getEffect(effectId);
        if (!effect) return false;

        Object.assign(effect, params);
        this.invalidateEffectCache();
        return true;
    }

    /**
     * Move an effect to a new position in the stack.
     * @param {string} effectId
     * @param {number} newIndex
     */
    moveEffect(effectId, newIndex) {
        const index = this.effects.findIndex(e => e.id === effectId);
        if (index < 0) return;

        const [effect] = this.effects.splice(index, 1);
        this.effects.splice(Math.max(0, Math.min(newIndex, this.effects.length)), 0, effect);
        this.invalidateEffectCache();
    }

    /**
     * Check if layer has any enabled effects.
     * @returns {boolean}
     */
    hasEffects() {
        return this.effects.some(e => e.enabled);
    }

    /**
     * Invalidate effect cache (call after modifying layer content).
     */
    invalidateEffectCache() {
        this._effectCacheVersion++;
        this.markChanged();
    }

    // ==================== Dynamic Filters ====================

    /**
     * Add a dynamic filter to this layer.
     * @param {DynamicFilter} filter - Filter to add
     * @param {number} [index] - Position to insert at (default: end)
     */
    addFilter(filter, index = -1) {
        if (index < 0 || index >= this.filters.length) {
            this.filters.push(filter);
        } else {
            this.filters.splice(index, 0, filter);
        }
        this.invalidateFilterCache();
    }

    /**
     * Remove a dynamic filter by ID.
     * @param {string} filterId - The filter's unique ID
     * @returns {boolean} True if filter was found and removed
     */
    removeFilter(filterId) {
        const index = this.filters.findIndex(f => f.id === filterId);
        if (index >= 0) {
            this.filters.splice(index, 1);
            this.invalidateFilterCache();
            return true;
        }
        return false;
    }

    /**
     * Get a dynamic filter by ID.
     * @param {string} filterId
     * @returns {DynamicFilter|null}
     */
    getFilter(filterId) {
        return this.filters.find(f => f.id === filterId) || null;
    }

    /**
     * Update dynamic filter parameters.
     * @param {string} filterId
     * @param {Object} params - Parameters to update
     * @returns {boolean} True if filter was found and updated
     */
    updateFilter(filterId, params) {
        const filter = this.getFilter(filterId);
        if (!filter) return false;
        Object.assign(filter.params, params);
        this.invalidateFilterCache();
        return true;
    }

    /**
     * Move a dynamic filter to a new position in the stack.
     * @param {string} filterId
     * @param {number} newIndex
     */
    moveFilter(filterId, newIndex) {
        const index = this.filters.findIndex(f => f.id === filterId);
        if (index < 0) return;
        const [filter] = this.filters.splice(index, 1);
        this.filters.splice(Math.max(0, Math.min(newIndex, this.filters.length)), 0, filter);
        this.invalidateFilterCache();
    }

    /**
     * Check if layer has any enabled dynamic filters.
     * @returns {boolean}
     */
    hasFilters() {
        return this.filters.some(f => f.enabled);
    }

    /**
     * Invalidate filter cache (call after modifying filter params).
     */
    invalidateFilterCache() {
        this._filterCacheVersion++;
        this.invalidateEffectCache(); // Effects depend on filtered output
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
     * Get the visual bounds including effect expansion.
     * @returns {{x: number, y: number, width: number, height: number}}
     */
    getVisualBounds() {
        const base = this.getBounds();

        if (!this.hasEffects()) {
            return base;
        }

        // Calculate total expansion from all effects
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

    /**
     * Get the axis-aligned bounding box of this layer in document coordinates.
     * For transformed layers, this calculates the enclosing rectangle of the
     * rotated/scaled layer bounds.
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
     * For simple offset-only layers (no rotation/scale), this is equivalent
     * to subtracting the offset.
     * @param {number} docX - X in document space
     * @param {number} docY - Y in document space
     * @returns {{x: number, y: number}}
     */
    docToCanvas(docX, docY) {
        // Fast path for no transform
        if (!this.hasTransform()) {
            return {
                x: docX - this.offsetX,
                y: docY - this.offsetY
            };
        }

        // Full transform: inverse of layerToDoc
        return this.docToLayer(docX, docY);
    }

    /**
     * Convert layer canvas coordinates to document coordinates.
     * For simple offset-only layers (no rotation/scale), this is equivalent
     * to adding the offset.
     * @param {number} canvasX - X in canvas space
     * @param {number} canvasY - Y in canvas space
     * @returns {{x: number, y: number}}
     */
    canvasToDoc(canvasX, canvasY) {
        // Fast path for no transform
        if (!this.hasTransform()) {
            return {
                x: canvasX + this.offsetX,
                y: canvasY + this.offsetY
            };
        }

        // Full transform
        return this.layerToDoc(canvasX, canvasY);
    }

    /**
     * Transform a point from layer local coordinates to document coordinates.
     * Applies: translate to center → scale → rotate → translate to doc position
     * @param {number} lx - X in layer local space (0 to width)
     * @param {number} ly - Y in layer local space (0 to height)
     * @returns {{x: number, y: number}} Point in document space
     */
    layerToDoc(lx, ly) {
        // Fast path for no transform
        if (!this.hasTransform()) {
            return {
                x: lx + this.offsetX,
                y: ly + this.offsetY
            };
        }

        // Step 1: Translate to layer center (origin at center for rotation/scale)
        const cx = this.width / 2;
        const cy = this.height / 2;
        let x = lx - cx;
        let y = ly - cy;

        // Step 2: Apply scale
        x *= this.scaleX;
        y *= this.scaleY;

        // Step 3: Apply rotation
        const radians = (this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);
        const rx = x * cos - y * sin;
        const ry = x * sin + y * cos;

        // Step 4: Translate to document position (offset + center)
        const docCenterX = this.offsetX + cx;
        const docCenterY = this.offsetY + cy;

        return {
            x: rx + docCenterX,
            y: ry + docCenterY
        };
    }

    /**
     * Transform a point from document coordinates to layer local coordinates.
     * This is the inverse of layerToDoc.
     * @param {number} docX - X in document space
     * @param {number} docY - Y in document space
     * @returns {{x: number, y: number}} Point in layer local space
     */
    docToLayer(docX, docY) {
        // Fast path for no transform
        if (!this.hasTransform()) {
            return {
                x: docX - this.offsetX,
                y: docY - this.offsetY
            };
        }

        // Step 1: Translate from document to layer center
        const cx = this.width / 2;
        const cy = this.height / 2;
        const docCenterX = this.offsetX + cx;
        const docCenterY = this.offsetY + cy;
        let x = docX - docCenterX;
        let y = docY - docCenterY;

        // Step 2: Apply inverse rotation
        const radians = (-this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);
        const rx = x * cos - y * sin;
        const ry = x * sin + y * cos;

        // Step 3: Apply inverse scale
        x = rx / this.scaleX;
        y = ry / this.scaleY;

        // Step 4: Translate back from center to local coords
        return {
            x: x + cx,
            y: y + cy
        };
    }

    /**
     * Get the transform matrix for this layer (CSS transform style).
     * Can be used to apply the layer transform to a DOM element.
     * @returns {string} CSS transform string
     */
    getTransformCSS() {
        if (!this.hasTransform()) {
            return 'none';
        }

        const cx = this.offsetX + this.width / 2;
        const cy = this.offsetY + this.height / 2;

        // Transform around center: translate to center, rotate, scale, translate back
        return `translate(${cx}px, ${cy}px) rotate(${this.rotation}deg) scale(${this.scaleX}, ${this.scaleY}) translate(${-cx}px, ${-cy}px)`;
    }

    /**
     * Get the 2D transform matrix components [a, b, c, d, e, f].
     * Suitable for canvas setTransform(a, b, c, d, e, f).
     * @returns {number[]} [a, b, c, d, e, f] matrix components
     */
    getTransformMatrix() {
        if (!this.hasTransform()) {
            return [1, 0, 0, 1, 0, 0];  // Identity matrix
        }

        const cx = this.offsetX + this.width / 2;
        const cy = this.offsetY + this.height / 2;
        const radians = (this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);

        // Combined matrix: T(cx,cy) * R(angle) * S(sx,sy) * T(-cx,-cy)
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

    /**
     * Move the layer by the given delta.
     * This changes the offset, not the pixel data.
     * @param {number} dx - X movement
     * @param {number} dy - Y movement
     */
    move(dx, dy) {
        this.offsetX += dx;
        this.offsetY += dy;
    }

    // ==================== Abstract Methods ====================
    // Subclasses must implement these methods

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
     * @abstract
     */
    rasterizeToDocument(clipBounds = null) {
        throw new Error('BaseLayer.rasterizeToDocument() must be implemented by subclass');
    }

    /**
     * Clone this layer.
     * @returns {BaseLayer}
     * @abstract
     */
    clone() {
        throw new Error('BaseLayer.clone() must be implemented by subclass');
    }

    /**
     * Serialize for history/save.
     * @returns {Object}
     * @abstract
     */
    serialize() {
        throw new Error('BaseLayer.serialize() must be implemented by subclass');
    }

    /**
     * Render a thumbnail of this layer in document space.
     * The thumbnail shows the layer as it appears in the document.
     *
     * @param {number} maxWidth - Maximum thumbnail width
     * @param {number} maxHeight - Maximum thumbnail height
     * @param {Object} [docSize] - Document size for positioning context
     * @returns {{canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D}}
     * @abstract
     */
    renderThumbnail(maxWidth, maxHeight, docSize = null) {
        throw new Error('BaseLayer.renderThumbnail() must be implemented by subclass');
    }

    /**
     * Rotate the layer's canvas content by the given degrees (90, 180, or 270).
     * This rotates the pixel data and recalculates the layer position based on
     * rotation around the document center.
     *
     * @param {number} degrees - Rotation angle (90, 180, or 270)
     * @param {number} oldDocWidth - Document width before rotation
     * @param {number} oldDocHeight - Document height before rotation
     * @param {number} newDocWidth - Document width after rotation
     * @param {number} newDocHeight - Document height after rotation
     * @returns {Promise<void>}
     * @abstract
     */
    async rotateCanvas(degrees, oldDocWidth, oldDocHeight, newDocWidth, newDocHeight) {
        throw new Error('BaseLayer.rotateCanvas() must be implemented by subclass');
    }

    /**
     * Mirror the layer's canvas content horizontally or vertically.
     * This flips the pixel data and recalculates the layer position.
     *
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @param {number} docWidth - Document width
     * @param {number} docHeight - Document height
     * @returns {Promise<void>}
     * @abstract
     */
    async mirrorContent(direction, docWidth, docHeight) {
        throw new Error('BaseLayer.mirrorContent() must be implemented by subclass');
    }

    /**
     * Convert this layer to an SVG element for document export.
     * The element will be a <g> with sf:* attributes containing all layer properties
     * and the visual content (image for raster, nested SVG for vector, etc.).
     *
     * @param {Document} xmlDoc - XML document for creating elements
     * @returns {Promise<Element>} SVG group element representing this layer
     * @abstract
     */
    async toSVGElement(xmlDoc) {
        throw new Error('BaseLayer.toSVGElement() must be implemented by subclass');
    }

    // ==================== Serialization Helpers ====================

    /**
     * Get base serialization data (common to all layer types).
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
            fillOpacity: this.fillOpacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            parentId: this.parentId,
            effects: this.effects.map(e => e.serialize()),
            filters: this.filters.filter(f => f.name !== '__preview__').map(f => typeof f.serialize === 'function' ? f.serialize() : { ...f }),
            frames: this._frames.map(f => ({ id: f.id, duration: f.duration, delay: f.delay })),
            activeFrameIndex: this.activeFrameIndex,
            changeCounter: this.changeCounter,
            lastChangeTimestamp: this.lastChangeTimestamp,
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
        if (data.fillOpacity !== undefined) this.fillOpacity = data.fillOpacity;
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

        // Frame index (frames themselves are restored by subclass)
        this.activeFrameIndex = data.activeFrameIndex ?? 0;

        // Change tracking
        this.changeCounter = data.changeCounter ?? 0;
        this.lastChangeTimestamp = data.lastChangeTimestamp ?? Date.now();

        // Deserialize effects
        if (data.effects && Array.isArray(data.effects)) {
            this.effects = data.effects.map(effectData => {
                const EffectClass = effectRegistry[effectData._type] || LayerEffect;
                return EffectClass.deserialize(effectData);
            }).filter(e => e);
        }

        // Deserialize dynamic filters
        if (data.filters && Array.isArray(data.filters)) {
            this.filters = data.filters.map(filterData => DynamicFilter.deserialize(filterData));
        }
    }

    /**
     * Migrate serialized data from older versions.
     * @param {Object} data - Serialized layer data
     * @returns {Object} - Migrated data at current version
     */
    static migrate(data) {
        // Handle pre-versioned data
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Ensure offsetX/offsetY and parentId exist
        if (data._version < 1) {
            data.offsetX = data.offsetX ?? 0;
            data.offsetY = data.offsetY ?? 0;
            data.parentId = data.parentId ?? null;
            data._version = 1;
        }

        // Ensure transform properties exist (added after v1)
        data.rotation = data.rotation ?? 0;
        data.scaleX = data.scaleX ?? 1.0;
        data.scaleY = data.scaleY ?? 1.0;

        return data;
    }
}

export default BaseLayer;
