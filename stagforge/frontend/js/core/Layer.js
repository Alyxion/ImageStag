import { LayerEffect, effectRegistry } from './LayerEffects.js';

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
        this.width = options.width;
        this.height = options.height;

        // Offset from document origin (can be negative)
        this.offsetX = options.offsetX ?? 0;
        this.offsetY = options.offsetY ?? 0;

        // Parent group ID (null = root level)
        this.parentId = options.parentId || null;

        // Create offscreen canvas for this layer
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.width;
        this.canvas.height = this.height;
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
     * Expand the canvas to include the given bounds (in document coordinates).
     * Preserves existing content.
     * @param {number} x - Left edge in document coords
     * @param {number} y - Top edge in document coords
     * @param {number} width - Width to include
     * @param {number} height - Height to include
     */
    expandToInclude(x, y, width, height) {
        const currentRight = this.offsetX + this.width;
        const currentBottom = this.offsetY + this.height;
        const newRight = x + width;
        const newBottom = y + height;

        // Calculate new bounds
        const newX = Math.min(this.offsetX, x);
        const newY = Math.min(this.offsetY, y);
        const newWidth = Math.max(currentRight, newRight) - newX;
        const newHeight = Math.max(currentBottom, newBottom) - newY;

        // Check if expansion is needed
        if (newX >= this.offsetX && newY >= this.offsetY &&
            newWidth <= this.width && newHeight <= this.height) {
            return;  // No expansion needed
        }

        // Create new canvas with expanded size
        const newCanvas = document.createElement('canvas');
        newCanvas.width = newWidth;
        newCanvas.height = newHeight;
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
     * Convert document coordinates to layer canvas coordinates.
     * @param {number} docX - X in document space
     * @param {number} docY - Y in document space
     * @returns {{x: number, y: number}}
     */
    docToCanvas(docX, docY) {
        return {
            x: docX - this.offsetX,
            y: docY - this.offsetY
        };
    }

    /**
     * Convert layer canvas coordinates to document coordinates.
     * @param {number} canvasX - X in canvas space
     * @param {number} canvasY - Y in canvas space
     * @returns {{x: number, y: number}}
     */
    canvasToDoc(canvasX, canvasY) {
        return {
            x: canvasX + this.offsetX,
            y: canvasY + this.offsetY
        };
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
            parentId: this.parentId,
            name: `${this.name} (copy)`,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            effects: this.effects.map(e => e.clone())
        });
        cloned.ctx.drawImage(this.canvas, 0, 0);
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
     * @param {string} color - CSS color string
     */
    fill(color) {
        this.ctx.fillStyle = color;
        this.ctx.fillRect(0, 0, this.width, this.height);
        this.invalidateImageCache();
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

        // Ensure we don't go below zero
        const cropX = Math.max(0, left);
        const cropY = Math.max(0, top);
        const cropWidth = Math.min(width, this.width - cropX);
        const cropHeight = Math.min(height, this.height - cropY);

        if (cropWidth <= 0 || cropHeight <= 0) return;

        // Get the content
        const imageData = this.ctx.getImageData(cropX, cropY, cropWidth, cropHeight);

        // Resize canvas
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
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked,
            imageData: this.canvas.toDataURL('image/png'),
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
            opacity: data.opacity,
            blendMode: data.blendMode,
            visible: data.visible,
            locked: data.locked,
            effects: effects
        });

        // Load image data from data URL
        await new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                layer.ctx.drawImage(img, 0, 0);
                resolve();
            };
            img.src = data.imageData;
        });

        return layer;
    }
}
