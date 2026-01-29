/**
 * SelectionManager - Global alpha mask-based selection system.
 *
 * All selection tools produce a unified alpha mask stored here.
 * Operations (copy, cut, delete, fill) use this mask.
 */
import { extractContours, initWasmContours } from '../utils/MarchingSquares.js';

export class SelectionManager {
    constructor(app) {
        this.app = app;

        // Initialize WASM contour extraction (async, non-blocking)
        initWasmContours().catch(e => {
            console.warn('[SelectionManager] WASM contours not available:', e.message);
        });

        // Alpha mask (document-sized)
        this.mask = null;
        this.width = 0;
        this.height = 0;

        // Cached bounds and outlines
        this._bounds = null;
        this._boundsValid = false;
        this._outlines = null;
        this._outlinesValid = false;

        // Previous selection for Reselect
        this._previousMask = null;
        this._previousWidth = 0;
        this._previousHeight = 0;

        // Marching ants animation
        this.antOffset = 0;
        this._animationId = null;

        // Preview canvas for marching ants
        this.previewCanvas = document.createElement('canvas');
        this.previewCtx = this.previewCanvas.getContext('2d');
    }

    /**
     * Check if there's an active selection.
     */
    get hasSelection() {
        return this.mask !== null && this._hasMaskPixels();
    }

    /**
     * Check if mask has any selected pixels.
     */
    _hasMaskPixels() {
        if (!this.mask) return false;
        for (let i = 0; i < this.mask.length; i++) {
            if (this.mask[i] > 0) return true;
        }
        return false;
    }

    /**
     * Resize mask to match document dimensions.
     */
    ensureSize(width, height) {
        if (this.width !== width || this.height !== height) {
            // If we have an existing mask, try to preserve it
            if (this.mask && this.width > 0 && this.height > 0) {
                const newMask = new Uint8Array(width * height);
                const copyWidth = Math.min(this.width, width);
                const copyHeight = Math.min(this.height, height);
                for (let y = 0; y < copyHeight; y++) {
                    for (let x = 0; x < copyWidth; x++) {
                        newMask[y * width + x] = this.mask[y * this.width + x];
                    }
                }
                this.mask = newMask;
            }
            this.width = width;
            this.height = height;
            this._invalidateCache();
        }
    }

    /**
     * Set selection from alpha mask.
     * @param {Uint8Array} mask - Alpha mask (0-255)
     * @param {number} width - Mask width
     * @param {number} height - Mask height
     */
    setMask(mask, width, height) {
        // Save previous for Reselect
        if (this.mask) {
            this._previousMask = this.mask;
            this._previousWidth = this.width;
            this._previousHeight = this.height;
        }

        this.mask = mask;
        this.width = width;
        this.height = height;
        this._invalidateCache();
        this._emitChanged();
    }

    /**
     * Set rectangular selection.
     */
    setRect(x, y, w, h) {
        const docWidth = this.app.layerStack?.width || this.width;
        const docHeight = this.app.layerStack?.height || this.height;

        this.ensureSize(docWidth, docHeight);

        // Save previous
        if (this.mask) {
            this._previousMask = this.mask.slice();
            this._previousWidth = this.width;
            this._previousHeight = this.height;
        }

        // Create new mask
        this.mask = new Uint8Array(docWidth * docHeight);

        // Clamp to document bounds
        const x1 = Math.max(0, Math.floor(x));
        const y1 = Math.max(0, Math.floor(y));
        const x2 = Math.min(docWidth, Math.ceil(x + w));
        const y2 = Math.min(docHeight, Math.ceil(y + h));

        // Fill rectangle
        for (let py = y1; py < y2; py++) {
            for (let px = x1; px < x2; px++) {
                this.mask[py * docWidth + px] = 255;
            }
        }

        this._invalidateCache();
        this._emitChanged();
    }

    /**
     * Set selection from polygon points.
     * @param {Array} points - Array of [x, y] points
     */
    setPolygon(points) {
        if (!points || points.length < 3) {
            this.clear();
            return;
        }

        const docWidth = this.app.layerStack?.width || this.width;
        const docHeight = this.app.layerStack?.height || this.height;

        this.ensureSize(docWidth, docHeight);

        // Save previous
        if (this.mask) {
            this._previousMask = this.mask.slice();
            this._previousWidth = this.width;
            this._previousHeight = this.height;
        }

        // Create new mask
        this.mask = new Uint8Array(docWidth * docHeight);

        // Get bounding box for efficiency
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const [px, py] of points) {
            minX = Math.min(minX, px);
            minY = Math.min(minY, py);
            maxX = Math.max(maxX, px);
            maxY = Math.max(maxY, py);
        }

        // Clamp to document
        minX = Math.max(0, Math.floor(minX));
        minY = Math.max(0, Math.floor(minY));
        maxX = Math.min(docWidth, Math.ceil(maxX));
        maxY = Math.min(docHeight, Math.ceil(maxY));

        // Fill using point-in-polygon test
        for (let y = minY; y < maxY; y++) {
            for (let x = minX; x < maxX; x++) {
                if (this._pointInPolygon(x + 0.5, y + 0.5, points)) {
                    this.mask[y * docWidth + x] = 255;
                }
            }
        }

        this._invalidateCache();
        this._emitChanged();
    }

    /**
     * Point-in-polygon test using ray casting.
     */
    _pointInPolygon(x, y, points) {
        let inside = false;
        const n = points.length;

        for (let i = 0, j = n - 1; i < n; j = i++) {
            const xi = points[i][0], yi = points[i][1];
            const xj = points[j][0], yj = points[j][1];

            if (((yi > y) !== (yj > y)) &&
                (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }

        return inside;
    }

    /**
     * Clear selection.
     */
    clear() {
        // Save previous for Reselect
        if (this.mask && this._hasMaskPixels()) {
            this._previousMask = this.mask;
            this._previousWidth = this.width;
            this._previousHeight = this.height;
        }

        this.mask = null;
        this._invalidateCache();
        this.app.eventBus?.emit('selection:cleared', {});
        this.app.eventBus?.emit('selection:changed', { hasSelection: false, bounds: null });

        // Clear preview
        if (this.app.renderer) {
            this.app.renderer.clearPreviewLayer();
        }
    }

    /**
     * Restore previous selection (Reselect).
     */
    reselect() {
        if (this._previousMask) {
            this.mask = this._previousMask;
            this.width = this._previousWidth;
            this.height = this._previousHeight;
            this._previousMask = null;
            this._invalidateCache();
            this._emitChanged();
        }
    }

    /**
     * Select all.
     */
    selectAll() {
        const docWidth = this.app.layerStack?.width || 800;
        const docHeight = this.app.layerStack?.height || 600;

        this.ensureSize(docWidth, docHeight);

        // Save previous
        if (this.mask) {
            this._previousMask = this.mask.slice();
            this._previousWidth = this.width;
            this._previousHeight = this.height;
        }

        this.mask = new Uint8Array(docWidth * docHeight);
        this.mask.fill(255);

        this._invalidateCache();
        this._emitChanged();
    }

    /**
     * Invert selection.
     */
    invert() {
        if (!this.mask) {
            // No selection = select all
            this.selectAll();
            return;
        }

        // Save previous
        this._previousMask = this.mask.slice();
        this._previousWidth = this.width;
        this._previousHeight = this.height;

        for (let i = 0; i < this.mask.length; i++) {
            this.mask[i] = 255 - this.mask[i];
        }

        this._invalidateCache();
        this._emitChanged();
    }

    /**
     * Get mask value at document coordinates.
     */
    getMaskAt(x, y) {
        if (!this.mask) return 0;
        const ix = Math.floor(x);
        const iy = Math.floor(y);
        if (ix < 0 || ix >= this.width || iy < 0 || iy >= this.height) return 0;
        return this.mask[iy * this.width + ix];
    }

    /**
     * Check if point is selected.
     */
    isSelected(x, y) {
        return this.getMaskAt(x, y) > 0;
    }

    /**
     * Get bounding box of selection.
     */
    getBounds() {
        if (!this.mask) return null;

        if (this._boundsValid) {
            return this._bounds;
        }

        let minX = this.width, minY = this.height, maxX = 0, maxY = 0;
        let found = false;

        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (this.mask[y * this.width + x] > 0) {
                    found = true;
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        if (!found) {
            this._bounds = null;
        } else {
            this._bounds = {
                x: minX,
                y: minY,
                width: maxX - minX + 1,
                height: maxY - minY + 1
            };
        }

        this._boundsValid = true;
        return this._bounds;
    }

    /**
     * Get outline polygons for marching ants rendering.
     */
    getOutlinePolygons() {
        if (!this.mask) return [];

        if (this._outlinesValid) {
            return this._outlines;
        }

        this._outlines = extractContours(this.mask, this.width, this.height);
        this._outlinesValid = true;
        return this._outlines;
    }

    /**
     * Invalidate cached bounds and outlines.
     */
    _invalidateCache() {
        this._boundsValid = false;
        this._outlinesValid = false;
        this._bounds = null;
        this._outlines = null;
    }

    /**
     * Emit selection changed event.
     */
    _emitChanged() {
        this.app.eventBus?.emit('selection:changed', {
            hasSelection: this.hasSelection,
            bounds: this.getBounds()
        });
    }

    /**
     * Start marching ants animation.
     */
    startAnimation() {
        if (this._animationId) return;

        const animate = () => {
            this.antOffset = (this.antOffset + 0.5) % 8;
            if (this.hasSelection) {
                this.renderMarchingAnts();
            }
            this._animationId = requestAnimationFrame(animate);
        };
        animate();
    }

    /**
     * Stop marching ants animation.
     */
    stopAnimation() {
        if (this._animationId) {
            cancelAnimationFrame(this._animationId);
            this._animationId = null;
        }
    }

    /**
     * Render marching ants to preview layer.
     */
    renderMarchingAnts() {
        if (!this.hasSelection || !this.app.renderer) return;

        try {
            const docWidth = this.app.layerStack?.width || this.width;
            const docHeight = this.app.layerStack?.height || this.height;

            // Resize preview canvas if needed
            if (this.previewCanvas.width !== docWidth || this.previewCanvas.height !== docHeight) {
                this.previewCanvas.width = docWidth;
                this.previewCanvas.height = docHeight;
            }

            this.previewCtx.clearRect(0, 0, docWidth, docHeight);

            const outlines = this.getOutlinePolygons();
            if (!outlines || outlines.length === 0) return;

            this.previewCtx.lineWidth = 1;
            this.previewCtx.setLineDash([4, 4]);

            // Draw black stroke
            this.previewCtx.strokeStyle = '#000000';
            this.previewCtx.lineDashOffset = -this.antOffset;
            for (const outline of outlines) {
                this._drawOutline(this.previewCtx, outline);
            }

            // Draw white stroke offset
            this.previewCtx.strokeStyle = '#FFFFFF';
            this.previewCtx.lineDashOffset = -this.antOffset + 4;
            for (const outline of outlines) {
                this._drawOutline(this.previewCtx, outline);
            }

            this.previewCtx.setLineDash([]);

            this.app.renderer.setPreviewLayer(this.previewCanvas);
        } catch (e) {
            console.error('[SelectionManager] Error rendering marching ants:', e);
        }
    }

    /**
     * Draw a single outline polygon.
     */
    _drawOutline(ctx, points) {
        if (!points || !Array.isArray(points) || points.length < 2) return;

        ctx.beginPath();
        const p0 = points[0];
        if (!p0 || typeof p0[0] !== 'number' || typeof p0[1] !== 'number') return;

        ctx.moveTo(p0[0] + 0.5, p0[1] + 0.5);
        for (let i = 1; i < points.length; i++) {
            const p = points[i];
            if (p && typeof p[0] === 'number' && typeof p[1] === 'number') {
                ctx.lineTo(p[0] + 0.5, p[1] + 0.5);
            }
        }
        ctx.closePath();
        ctx.stroke();
    }

    /**
     * Apply selection mask to layer - returns masked image data.
     * Uses layer.rasterizeToDocument() to handle all transforms (rotation, scale).
     * @param {Layer} layer - The layer to extract from
     * @returns {Object} { canvas, imageData, bounds } or null
     */
    extractFromLayer(layer) {
        const bounds = this.getBounds();
        if (!bounds) return null;

        // Use the layer's rasterizeToDocument method which handles all transforms
        const rasterized = layer.rasterizeToDocument(bounds);

        if (rasterized.bounds.width === 0 || rasterized.bounds.height === 0) {
            return null; // No overlap with layer
        }

        // Create output canvas at selection bounds size
        const extractCanvas = document.createElement('canvas');
        extractCanvas.width = bounds.width;
        extractCanvas.height = bounds.height;
        const extractCtx = extractCanvas.getContext('2d', { willReadFrequently: true });

        // Draw the rasterized layer content at the correct position
        // The rasterized bounds may be smaller than selection bounds if layer doesn't cover all of selection
        const drawX = rasterized.bounds.x - bounds.x;
        const drawY = rasterized.bounds.y - bounds.y;
        extractCtx.drawImage(rasterized.canvas, drawX, drawY);

        // Apply selection mask
        const imageData = extractCtx.getImageData(0, 0, bounds.width, bounds.height);
        for (let y = 0; y < bounds.height; y++) {
            for (let x = 0; x < bounds.width; x++) {
                const docX = bounds.x + x;
                const docY = bounds.y + y;
                const maskValue = this.getMaskAt(docX, docY);
                if (maskValue === 0) {
                    const idx = (y * bounds.width + x) * 4;
                    imageData.data[idx + 3] = 0; // Clear alpha
                }
            }
        }
        extractCtx.putImageData(imageData, 0, 0);

        return {
            canvas: extractCanvas,
            imageData: imageData,
            bounds: bounds
        };
    }

    /**
     * Delete selected pixels from layer.
     * Handles rotated/scaled layers by using proper coordinate transforms.
     */
    deleteFromLayer(layer) {
        const bounds = this.getBounds();
        if (!bounds) return false;

        // For transformed layers, we need to iterate over layer pixels
        // and check if they fall within the selection in document space
        const hasTransform = layer.layerToDoc && (layer.rotation !== 0 || layer.scaleX !== 1 || layer.scaleY !== 1);

        if (hasTransform) {
            return this._deleteFromTransformedLayer(layer, bounds);
        }

        // Simple case: no rotation/scale, just offset
        return this._deleteFromSimpleLayer(layer, bounds);
    }

    /**
     * Delete from a layer with rotation/scale transforms.
     * Iterates over layer pixels and checks if they map to selected document coords.
     */
    _deleteFromTransformedLayer(layer, bounds) {
        // Get entire layer image data
        const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);
        let modified = false;

        // For each pixel in the layer, check if it maps to a selected document pixel
        for (let ly = 0; ly < layer.height; ly++) {
            for (let lx = 0; lx < layer.width; lx++) {
                // Convert layer coords to document coords
                const docCoords = layer.layerToDoc(lx, ly);
                const docX = Math.floor(docCoords.x);
                const docY = Math.floor(docCoords.y);

                // Check if this document pixel is selected
                const maskValue = this.getMaskAt(docX, docY);
                if (maskValue > 0) {
                    // Clear this layer pixel
                    const idx = (ly * layer.width + lx) * 4;
                    imageData.data[idx] = 0;
                    imageData.data[idx + 1] = 0;
                    imageData.data[idx + 2] = 0;
                    imageData.data[idx + 3] = 0;
                    modified = true;
                }
            }
        }

        if (modified) {
            layer.ctx.putImageData(imageData, 0, 0);
        }

        return modified;
    }

    /**
     * Delete from a simple layer (no rotation/scale).
     */
    _deleteFromSimpleLayer(layer, bounds) {
        const offsetX = layer.offsetX || 0;
        const offsetY = layer.offsetY || 0;

        // Calculate layer-local bounds
        const localLeft = bounds.x - offsetX;
        const localTop = bounds.y - offsetY;
        const localRight = bounds.x + bounds.width - offsetX;
        const localBottom = bounds.y + bounds.height - offsetY;

        // Clamp to layer bounds
        const left = Math.max(0, localLeft);
        const top = Math.max(0, localTop);
        const right = Math.min(layer.width, localRight);
        const bottom = Math.min(layer.height, localBottom);

        if (right <= left || bottom <= top) {
            return false; // No overlap
        }

        const width = right - left;
        const height = bottom - top;

        // Get image data
        const imageData = layer.ctx.getImageData(left, top, width, height);

        // Clear selected pixels
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const docX = left + offsetX + x;
                const docY = top + offsetY + y;
                const maskValue = this.getMaskAt(docX, docY);
                if (maskValue > 0) {
                    const idx = (y * width + x) * 4;
                    imageData.data[idx] = 0;
                    imageData.data[idx + 1] = 0;
                    imageData.data[idx + 2] = 0;
                    imageData.data[idx + 3] = 0;
                }
            }
        }

        layer.ctx.putImageData(imageData, left, top);
        return true;
    }
}
