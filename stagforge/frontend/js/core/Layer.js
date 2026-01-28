import { LayerEffect, effectRegistry } from './LayerEffects.js';
import { lanczosResample } from '../utils/lanczos.js';

/**
 * Layer - Represents a single layer with its own offscreen canvas.
 *
 * Each layer has:
 * - Its own canvas that can be larger than the document
 * - An offset (x, y) from the document origin
 * - Methods to expand when content is drawn outside bounds
 * - Optional layer effects (drop shadow, stroke, glow, etc.)
 */
export class Layer {
    /** Serialization version for migration support */
    static VERSION = 1;

    /**
     * @param {Object} options
     * @param {string} [options.id] - Unique identifier
     * @param {string} [options.name] - Display name
     * @param {number} options.width - Initial canvas width (usually document width)
     * @param {number} options.height - Initial canvas height (usually document height)
     * @param {number} [options.offsetX] - X offset from document origin
     * @param {number} [options.offsetY] - Y offset from document origin
     * @param {number} [options.opacity] - Opacity 0.0-1.0
     * @param {string} [options.blendMode] - Blend mode
     * @param {boolean} [options.visible] - Visibility
     * @param {boolean} [options.locked] - Lock state
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.name = options.name || 'Layer';
        this.type = 'raster';
        // Ensure integer dimensions for canvas operations (guard against NaN)
        // Allow 0x0 for empty layers that will auto-fit to content
        this.width = Math.max(0, Math.ceil(options.width || 0));
        this.height = Math.max(0, Math.ceil(options.height || 0));

        // Offset from document origin (can be negative, guard against NaN)
        this.offsetX = Math.floor(options.offsetX || 0);
        this.offsetY = Math.floor(options.offsetY || 0);

        // Transform properties (applied around layer center)
        this.rotation = options.rotation || 0;  // Rotation in degrees
        this.scaleX = options.scaleX ?? 1.0;    // Horizontal scale factor
        this.scaleY = options.scaleY ?? 1.0;    // Vertical scale factor

        // Parent group ID (null = root level)
        this.parentId = options.parentId || null;

        // Create offscreen canvas for this layer
        // Canvas must be at least 1x1, even if logical size is 0x0
        this.canvas = document.createElement('canvas');
        this.canvas.width = Math.max(1, this.width);
        this.canvas.height = Math.max(1, this.height);
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });

        // Layer properties
        this.opacity = options.opacity ?? 1.0;
        this.blendMode = options.blendMode || 'normal';
        this.visible = options.visible ?? true;
        this.locked = options.locked ?? false;

        // Layer effects (non-destructive)
        this.effects = options.effects || [];

        // Effect cache invalidation counter
        this._effectCacheVersion = 0;

        // Image cache for efficient saving (WebP blob)
        // Cache is invalidated when layer content changes
        this._cachedImageBlob = null;
        this._contentVersion = 0;  // Increments on any content change
    }

    /**
     * Invalidate the image cache (call after modifying layer pixels).
     * This should be called by any operation that changes the canvas content.
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
        this._effectCacheVersion++;
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
     * @param {Object} params - Parameters to update
     * @returns {boolean} True if effect was found and updated
     */
    updateEffect(effectId, params) {
        const effect = this.getEffect(effectId);
        if (!effect) return false;

        Object.assign(effect, params);
        this._effectCacheVersion++;
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
        this._effectCacheVersion++;
    }

    /**
     * Check if layer has any enabled effects.
     * @returns {boolean}
     */
    hasEffects() {
        return this.effects.some(e => e.enabled);
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
     * Invalidate effect cache (call after modifying layer content).
     */
    invalidateEffectCache() {
        this._effectCacheVersion++;
    }

    /**
     * Check if this layer is a vector layer.
     * @returns {boolean}
     */
    isVector() {
        return false;
    }

    /**
     * Check if this is a group.
     * @returns {boolean}
     */
    isGroup() {
        return false;
    }

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
     * @returns {{x: number, y: number, width: number, height: number}|null}
     */
    getContentBounds() {
        // Handle 0x0 layers
        if (this.width === 0 || this.height === 0) {
            return null;  // Empty layer
        }

        const imageData = this.ctx.getImageData(0, 0, this.width, this.height);
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

        if (maxX < 0) return null;  // Empty layer

        return {
            x: this.offsetX + minX,
            y: this.offsetY + minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }

    /**
     * Fit the layer bounds to the actual content (non-transparent pixels).
     * If the layer is empty (no content), it becomes a 0x0 layer.
     * @returns {boolean} True if bounds changed
     */
    fitToContent() {
        const bounds = this.getContentBounds();

        if (!bounds) {
            // Empty layer - set to 0x0
            if (this.width === 0 && this.height === 0) {
                return false;  // Already 0x0
            }

            this.width = 0;
            this.height = 0;
            // Canvas must be at least 1x1
            this.canvas.width = 1;
            this.canvas.height = 1;
            this.ctx.clearRect(0, 0, 1, 1);
            this.invalidateImageCache();
            return true;
        }

        // Calculate canvas coordinates of the content bounds
        const left = bounds.x - this.offsetX;
        const top = bounds.y - this.offsetY;
        const contentWidth = bounds.width;
        const contentHeight = bounds.height;

        // Check if already fitted
        if (left === 0 && top === 0 &&
            contentWidth === this.width && contentHeight === this.height) {
            return false;  // Already fitted
        }

        // Extract the content pixels
        const imageData = this.ctx.getImageData(left, top, contentWidth, contentHeight);

        // Resize canvas (at least 1x1 for canvas API)
        this.canvas.width = Math.max(1, contentWidth);
        this.canvas.height = Math.max(1, contentHeight);
        this.width = contentWidth;
        this.height = contentHeight;

        // Update offset to maintain document position
        this.offsetX = bounds.x;
        this.offsetY = bounds.y;

        // Put the content back
        this.ctx.putImageData(imageData, 0, 0);

        this.invalidateImageCache();
        return true;
    }

    /**
     * Expand the canvas to include the given bounds (in document coordinates).
     * Preserves existing content.
     * @param {number} x - Left edge in document coords
     * @param {number} y - Top edge in document coords
     * @param {number} width - Width to include
     * @param {number} height - Height to include
     */
    expandToInclude(x, y, width, height) {
        // Handle 0x0 layers - just set to the new bounds
        if (this.width === 0 || this.height === 0) {
            const newX = Math.floor(x);
            const newY = Math.floor(y);
            const newWidth = Math.ceil(width);
            const newHeight = Math.ceil(height);

            // Create canvas with new size
            this.canvas.width = Math.max(1, newWidth);
            this.canvas.height = Math.max(1, newHeight);
            this.width = newWidth;
            this.height = newHeight;
            this.offsetX = newX;
            this.offsetY = newY;
            this.invalidateImageCache();
            return;
        }

        const currentRight = this.offsetX + this.width;
        const currentBottom = this.offsetY + this.height;
        const newRight = x + width;
        const newBottom = y + height;

        // Calculate new bounds (ensure integer dimensions for canvas)
        const newX = Math.floor(Math.min(this.offsetX, x));
        const newY = Math.floor(Math.min(this.offsetY, y));
        const newWidth = Math.ceil(Math.max(currentRight, newRight) - newX);
        const newHeight = Math.ceil(Math.max(currentBottom, newBottom) - newY);

        // Check if expansion is needed
        if (newX >= this.offsetX && newY >= this.offsetY &&
            newWidth <= this.width && newHeight <= this.height) {
            return;  // No expansion needed
        }

        // Create new canvas with expanded size
        const newCanvas = document.createElement('canvas');
        newCanvas.width = Math.max(1, newWidth);
        newCanvas.height = Math.max(1, newHeight);
        const newCtx = newCanvas.getContext('2d', { willReadFrequently: true });

        // Copy existing content to new position
        const dx = this.offsetX - newX;
        const dy = this.offsetY - newY;
        newCtx.drawImage(this.canvas, dx, dy);

        // Replace canvas
        this.canvas = newCanvas;
        this.ctx = newCtx;
        this.width = newWidth;
        this.height = newHeight;
        this.offsetX = newX;
        this.offsetY = newY;

        // Invalidate cache since canvas was replaced
        this.invalidateImageCache();
    }

    /**
     * Expand layer to include a point in document coordinates, handling transforms.
     * For non-transformed layers, this delegates to expandToInclude.
     * For transformed layers, this works in layer-local space and preserves the
     * document-space center position (rotation pivot).
     *
     * @param {number} docX - X coordinate in document space
     * @param {number} docY - Y coordinate in document space
     * @param {number} radius - Radius around the point to include
     */
    expandToIncludeDocPoint(docX, docY, radius) {
        // For non-transformed layers, use the simple method
        if (!this.hasTransform()) {
            this.expandToInclude(docX - radius, docY - radius, radius * 2, radius * 2);
            return;
        }

        // For transformed layers, work in layer-local space
        // Convert document point to layer-local coordinates
        const local = this.docToLayer(docX, docY);
        const lx = local.x;
        const ly = local.y;

        // Calculate the layer-local bounds needed to include the brush
        const minX = Math.floor(lx - radius);
        const minY = Math.floor(ly - radius);
        const maxX = Math.ceil(lx + radius);
        const maxY = Math.ceil(ly + radius);

        // Check if point is already within bounds
        if (minX >= 0 && minY >= 0 && maxX <= this.width && maxY <= this.height) {
            return;  // No expansion needed
        }

        // Handle 0x0 layers
        if (this.width === 0 || this.height === 0) {
            const newWidth = maxX - minX;
            const newHeight = maxY - minY;

            this.canvas.width = Math.max(1, newWidth);
            this.canvas.height = Math.max(1, newHeight);
            this.width = newWidth;
            this.height = newHeight;

            // For a new layer, center it at the document point
            // The center of the new canvas should map to (docX, docY)
            // center = offsetX + width/2, so offsetX = docX - width/2
            this.offsetX = Math.round(docX - newWidth / 2);
            this.offsetY = Math.round(docY - newHeight / 2);
            this.invalidateImageCache();
            return;
        }

        // Remember old dimensions and where old content center maps to in document space
        const oldWidth = this.width;
        const oldHeight = this.height;
        const oldOffsetX = this.offsetX;
        const oldOffsetY = this.offsetY;

        // Pick a reference point: the old content center
        const oldContentCenter = { x: oldWidth / 2, y: oldHeight / 2 };
        // Where does this point appear in document space?
        const oldDocPos = this.layerToDoc(oldContentCenter.x, oldContentCenter.y);

        // Calculate new layer-local bounds
        const newMinX = Math.floor(Math.min(0, minX));
        const newMinY = Math.floor(Math.min(0, minY));
        const newMaxX = Math.ceil(Math.max(this.width, maxX));
        const newMaxY = Math.ceil(Math.max(this.height, maxY));

        const newWidth = newMaxX - newMinX;
        const newHeight = newMaxY - newMinY;

        // Create new canvas with expanded size
        const newCanvas = document.createElement('canvas');
        newCanvas.width = Math.max(1, newWidth);
        newCanvas.height = Math.max(1, newHeight);
        const newCtx = newCanvas.getContext('2d', { willReadFrequently: true });

        // Copy existing content to new position
        // Old content at (0,0) moves to (-newMinX, -newMinY) in new canvas
        const dx = -newMinX;
        const dy = -newMinY;
        newCtx.drawImage(this.canvas, dx, dy);

        // Replace canvas
        this.canvas = newCanvas;
        this.ctx = newCtx;
        this.width = newWidth;
        this.height = newHeight;

        // Calculate new offset so that old content stays in same document position
        //
        // After expansion, the old content center is now at canvas position:
        const newContentCenterX = oldContentCenter.x + dx;
        const newContentCenterY = oldContentCenter.y + dy;

        // The new canvas center
        const newCenterX = newWidth / 2;
        const newCenterY = newHeight / 2;

        // The offset from new canvas center to where old content center now sits
        let deltaX = newContentCenterX - newCenterX;
        let deltaY = newContentCenterY - newCenterY;

        // Apply scale
        deltaX *= this.scaleX;
        deltaY *= this.scaleY;

        // Apply rotation to this delta
        const radians = (this.rotation * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);
        const rotatedDeltaX = deltaX * cos - deltaY * sin;
        const rotatedDeltaY = deltaX * sin + deltaY * cos;

        // The new offset should place the layer such that:
        // oldDocPos = newOffset + newCenter + rotatedDelta
        // Therefore: newOffset = oldDocPos - newCenter - rotatedDelta
        this.offsetX = Math.round(oldDocPos.x - newCenterX - rotatedDeltaX);
        this.offsetY = Math.round(oldDocPos.y - newCenterY - rotatedDeltaY);

        this.invalidateImageCache();
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
     * Get raw ImageData for transfer to backend.
     * @returns {ImageData}
     */
    getImageData() {
        return this.ctx.getImageData(0, 0, this.width, this.height);
    }

    /**
     * Set ImageData (from backend filter result).
     * @param {ImageData} imageData
     */
    setImageData(imageData) {
        this.ctx.putImageData(imageData, 0, 0);
        this.invalidateImageCache();
    }

    /**
     * Clone this layer.
     * @returns {Layer}
     */
    clone() {
        const cloned = new Layer({
            width: this.width,
            height: this.height,
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            rotation: this.rotation,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            parentId: this.parentId,
            name: `${this.name} (copy)`,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            effects: this.effects.map(e => e.clone())
        });
        if (this.width > 0 && this.height > 0) {
            cloned.ctx.drawImage(this.canvas, 0, 0);
        }
        return cloned;
    }

    /**
     * Clear layer content.
     */
    clear() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.invalidateImageCache();
    }

    /**
     * Fill layer with a color.
     * If the layer is 0x0, this does nothing. Use fillArea() for specific bounds.
     * @param {string} color - CSS color string
     */
    fill(color) {
        if (this.width === 0 || this.height === 0) return;
        this.ctx.fillStyle = color;
        this.ctx.fillRect(0, 0, this.width, this.height);
        this.invalidateImageCache();
    }

    /**
     * Fill a specific area with a color (in document coordinates).
     * Expands the layer if needed to include the filled area.
     * @param {string} color - CSS color string
     * @param {number} x - X in document coords
     * @param {number} y - Y in document coords
     * @param {number} width - Width
     * @param {number} height - Height
     */
    fillArea(color, x, y, width, height) {
        // Expand layer to include the fill area
        this.expandToInclude(x, y, width, height);

        // Convert to canvas coordinates
        const canvasX = x - this.offsetX;
        const canvasY = y - this.offsetY;

        this.ctx.fillStyle = color;
        this.ctx.fillRect(canvasX, canvasY, width, height);
        this.invalidateImageCache();
    }

    /**
     * Scale the layer by a factor around an optional center point.
     * Uses Lanczos-3 resampling for high-quality scaling.
     * @param {number} scaleX - Horizontal scale factor
     * @param {number} scaleY - Vertical scale factor
     * @param {Object} [options]
     * @param {number} [options.centerX] - Center X in document coords (unused for pixel layers)
     * @param {number} [options.centerY] - Center Y in document coords (unused for pixel layers)
     */
    async scale(scaleX, scaleY, options = {}) {
        // Handle 0x0 layers
        if (this.width === 0 || this.height === 0) {
            return;
        }

        const newWidth = Math.max(1, Math.round(this.width * scaleX));
        const newHeight = Math.max(1, Math.round(this.height * scaleY));

        // Get current content
        const srcData = this.ctx.getImageData(0, 0, this.width, this.height);

        // Resample using Lanczos-3
        const dstData = lanczosResample(srcData, newWidth, newHeight);

        // Resize canvas and apply
        this.canvas.width = newWidth;
        this.canvas.height = newHeight;
        this.width = newWidth;
        this.height = newHeight;
        this.ctx.putImageData(dstData, 0, 0);

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

        const scaleX = newWidth / this.width;
        const scaleY = newHeight / this.height;

        await this.scale(scaleX, scaleY, options);
    }

    /**
     * Trim the canvas to the content bounds, removing empty space.
     * @param {number} [padding=0] - Extra padding to keep around content
     */
    trimToContent(padding = 0) {
        const bounds = this.getContentBounds();
        if (!bounds) return;  // Empty layer

        // Convert back to canvas coordinates
        const left = bounds.x - this.offsetX - padding;
        const top = bounds.y - this.offsetY - padding;
        const width = bounds.width + padding * 2;
        const height = bounds.height + padding * 2;

        // Ensure we don't go below zero and use integers
        const cropX = Math.max(0, Math.floor(left));
        const cropY = Math.max(0, Math.floor(top));
        const cropWidth = Math.ceil(Math.min(width, this.width - cropX));
        const cropHeight = Math.ceil(Math.min(height, this.height - cropY));

        if (cropWidth <= 0 || cropHeight <= 0) return;

        // Get the content
        const imageData = this.ctx.getImageData(cropX, cropY, cropWidth, cropHeight);

        // Resize canvas (integers required)
        this.canvas.width = cropWidth;
        this.canvas.height = cropHeight;
        this.width = cropWidth;
        this.height = cropHeight;

        // Update offset
        this.offsetX += cropX;
        this.offsetY += cropY;

        // Put the content back
        this.ctx.putImageData(imageData, 0, 0);

        // Invalidate cache since canvas was resized and content changed
        this.invalidateImageCache();
    }

    /**
     * Serialize for history/save.
     * @returns {Object}
     */
    serialize() {
        // For 0x0 layers, use an empty data URL
        const imageData = (this.width > 0 && this.height > 0)
            ? this.canvas.toDataURL('image/png')
            : 'data:image/png;base64,';

        return {
            _version: Layer.VERSION,
            _type: 'Layer',
            type: 'raster',
            id: this.id,
            name: this.name,
            parentId: this.parentId,
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
            imageData: imageData,
            effects: this.effects.map(e => e.serialize())
        };
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

        // Future migrations:
        // if (data._version < 2) { ... data._version = 2; }

        return data;
    }

    /**
     * Restore from serialized data.
     * @param {Object} data
     * @returns {Promise<Layer>}
     */
    static async deserialize(data) {
        // Migrate to current version
        data = Layer.migrate(data);

        // Deserialize effects
        const effects = (data.effects || [])
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);

        const layer = new Layer({
            id: data.id,
            name: data.name,
            parentId: data.parentId,
            width: data.width,
            height: data.height,
            offsetX: data.offsetX ?? 0,
            offsetY: data.offsetY ?? 0,
            rotation: data.rotation ?? 0,
            scaleX: data.scaleX ?? 1.0,
            scaleY: data.scaleY ?? 1.0,
            opacity: data.opacity,
            blendMode: data.blendMode,
            visible: data.visible,
            locked: data.locked,
            effects: effects
        });

        // Load image data from data URL (skip for empty layers)
        if (data.width > 0 && data.height > 0 && data.imageData && data.imageData !== 'data:image/png;base64,') {
            await new Promise((resolve) => {
                const img = new Image();
                img.onload = () => {
                    layer.ctx.drawImage(img, 0, 0);
                    resolve();
                };
                img.onerror = () => {
                    // Handle empty/invalid image data gracefully
                    resolve();
                };
                img.src = data.imageData;
            });
        }

        return layer;
    }
}
