/**
 * PixelLayer - A canvas-based raster layer with drawable pixels.
 *
 * Each layer has:
 * - Its own canvas that can be larger than the document
 * - An offset (x, y) from the document origin
 * - Methods to expand when content is drawn outside bounds
 * - Optional layer effects (drop shadow, stroke, glow, etc.)
 *
 * Extends BaseLayer which provides:
 * - Transform operations (rotation, scale)
 * - Coordinate conversion (layerToDoc, docToLayer, etc.)
 * - Effects management
 * - Image caching
 */
import { BaseLayer } from './BaseLayer.js';
import { LayerEffect, effectRegistry } from './LayerEffects.js';
import { lanczosResample } from '../utils/lanczos.js';
import { MAX_DIMENSION } from '../config/limits.js';
import { PixelFrame } from './Frame.js';

export class PixelLayer extends BaseLayer {
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
        super({
            ...options,
            name: options.name || 'Layer',
            type: 'raster'
        });
        // Note: canvas/ctx are now accessed via the frame mechanism
        // (see _createFrameData and canvas/ctx getters below).
        // BaseLayer constructor calls _createFrameData which creates
        // the initial frame with a canvas.
    }

    // ==================== Type Checks ====================

    /**
     * Check if this is a pixel/raster layer.
     * @returns {boolean}
     */
    isRaster() {
        return true;
    }

    // ==================== Frame Data ====================

    /** @override */
    _createFrameData(options) {
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, this.width);
        canvas.height = Math.max(1, this.height);
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        return new PixelFrame({ canvas, ctx, duration: options.duration ?? 0.1, delay: options.delay ?? 0.0 });
    }

    /** @override */
    _createEmptyFrameData() {
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, this.width);
        canvas.height = Math.max(1, this.height);
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        return new PixelFrame({ canvas, ctx });
    }

    /** @override */
    _cloneFrameData(frameData) {
        return frameData.clone();
    }

    /** @override */
    _disposeFrameData(frameData) {
        frameData.dispose();
    }

    // ==================== Canvas/Ctx Accessors ====================

    /**
     * Get the canvas for a specific frame.
     * @param {number} [frameIndex] - Frame index (default: active frame)
     * @returns {HTMLCanvasElement}
     */
    getCanvas(frameIndex = this.activeFrameIndex) {
        return this._frames[frameIndex].canvas;
    }

    /**
     * Get the 2D context for a specific frame.
     * @param {number} [frameIndex] - Frame index (default: active frame)
     * @returns {CanvasRenderingContext2D}
     */
    getCtx(frameIndex = this.activeFrameIndex) {
        return this._frames[frameIndex].ctx;
    }

    /** Backward-compat getter for active frame's canvas. */
    get canvas() {
        return this._frames[this.activeFrameIndex].canvas;
    }

    /** Backward-compat setter for active frame's canvas. */
    set canvas(v) {
        this._frames[this.activeFrameIndex].canvas = v;
    }

    /** Backward-compat getter for active frame's context. */
    get ctx() {
        return this._frames[this.activeFrameIndex].ctx;
    }

    /** Backward-compat setter for active frame's context. */
    set ctx(v) {
        this._frames[this.activeFrameIndex].ctx = v;
    }

    // ==================== Bounds ====================

    /** @override */
    _getFrameContentBounds(frame) {
        if (this.width === 0 || this.height === 0) return null;

        const imageData = frame.ctx.getImageData(0, 0, this.width, this.height);
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
     * Get the bounds of actual content (non-transparent pixels).
     * Union of bounds across ALL frames.
     * Returns null if all frames are empty.
     * @returns {{x: number, y: number, width: number, height: number}|null}
     */
    getContentBounds() {
        if (this.width === 0 || this.height === 0) return null;

        let unionBounds = null;
        for (const frame of this._frames) {
            const bounds = this._getFrameContentBounds(frame);
            if (!bounds) continue;
            if (!unionBounds) {
                unionBounds = { ...bounds };
            } else {
                const right = Math.max(unionBounds.x + unionBounds.width, bounds.x + bounds.width);
                const bottom = Math.max(unionBounds.y + unionBounds.height, bounds.y + bounds.height);
                unionBounds.x = Math.min(unionBounds.x, bounds.x);
                unionBounds.y = Math.min(unionBounds.y, bounds.y);
                unionBounds.width = right - unionBounds.x;
                unionBounds.height = bottom - unionBounds.y;
            }
        }
        return unionBounds;
    }

    /**
     * Fit the layer bounds to the actual content (non-transparent pixels).
     * If the layer is empty (no content), it becomes a 0x0 layer.
     * @returns {boolean} True if bounds changed
     */
    fitToContent() {
        if (this.hasTransform()) {
            return false;
        }

        const bounds = this.getContentBounds();

        if (!bounds) {
            if (this.width === 0 && this.height === 0) {
                return false;
            }

            this.width = 0;
            this.height = 0;
            for (const frame of this._frames) {
                frame.canvas.width = 1;
                frame.canvas.height = 1;
                frame.ctx.clearRect(0, 0, 1, 1);
            }
            this.invalidateImageCache();
            return true;
        }

        const left = bounds.x - this.offsetX;
        const top = bounds.y - this.offsetY;
        const contentWidth = bounds.width;
        const contentHeight = bounds.height;

        if (left === 0 && top === 0 &&
            contentWidth === this.width && contentHeight === this.height) {
            return false;
        }

        // Fit ALL frames uniformly
        for (const frame of this._frames) {
            const imageData = frame.ctx.getImageData(left, top, contentWidth, contentHeight);
            frame.canvas.width = Math.max(1, contentWidth);
            frame.canvas.height = Math.max(1, contentHeight);
            frame.ctx.putImageData(imageData, 0, 0);
        }

        this.width = contentWidth;
        this.height = contentHeight;
        this.offsetX = bounds.x;
        this.offsetY = bounds.y;

        this.invalidateImageCache();
        return true;
    }

    /**
     * Expand the canvas to include the given bounds (in document coordinates).
     * Preserves existing content. Expands ALL frames uniformly.
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
            // Clamp dimensions to MAX_DIMENSION
            const newWidth = Math.min(MAX_DIMENSION, Math.ceil(width));
            const newHeight = Math.min(MAX_DIMENSION, Math.ceil(height));

            // Resize all frames
            for (const frame of this._frames) {
                frame.canvas.width = Math.max(1, newWidth);
                frame.canvas.height = Math.max(1, newHeight);
            }
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
        let newX = Math.floor(Math.min(this.offsetX, x));
        let newY = Math.floor(Math.min(this.offsetY, y));
        let newWidth = Math.ceil(Math.max(currentRight, newRight) - newX);
        let newHeight = Math.ceil(Math.max(currentBottom, newBottom) - newY);

        // Clamp dimensions to MAX_DIMENSION
        if (newWidth > MAX_DIMENSION) {
            if (newX < this.offsetX) {
                newX = Math.max(newX, currentRight - MAX_DIMENSION);
            }
            newWidth = MAX_DIMENSION;
        }
        if (newHeight > MAX_DIMENSION) {
            if (newY < this.offsetY) {
                newY = Math.max(newY, currentBottom - MAX_DIMENSION);
            }
            newHeight = MAX_DIMENSION;
        }

        // Check if expansion is needed
        if (newX >= this.offsetX && newY >= this.offsetY &&
            newWidth <= this.width && newHeight <= this.height) {
            return;  // No expansion needed
        }

        const dx = this.offsetX - newX;
        const dy = this.offsetY - newY;

        // Expand ALL frames uniformly
        for (const frame of this._frames) {
            const newCanvas = document.createElement('canvas');
            newCanvas.width = Math.max(1, newWidth);
            newCanvas.height = Math.max(1, newHeight);
            const newCtx = newCanvas.getContext('2d', { willReadFrequently: true });
            newCtx.drawImage(frame.canvas, dx, dy);
            frame.canvas = newCanvas;
            frame.ctx = newCtx;
        }

        this.width = newWidth;
        this.height = newHeight;
        this.offsetX = newX;
        this.offsetY = newY;
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

        // Check if point is already within bounds (with tolerance to avoid micro-expansions)
        // Tolerance should be generous to prevent repeated tiny expansions
        const tolerance = 5;
        if (minX >= -tolerance && minY >= -tolerance &&
            maxX <= this.width + tolerance && maxY <= this.height + tolerance) {
            return;  // No expansion needed (or close enough)
        }

        // Add padding to expansion to avoid frequent micro-expansions
        // This reduces cumulative rounding error from many small expansions
        // Use a larger padding to ensure we don't need to expand again soon
        const expansionPadding = Math.max(50, radius * 2);

        // Handle 0x0 layers
        if (this.width === 0 || this.height === 0) {
            const newWidth = (maxX - minX) + expansionPadding * 2;
            const newHeight = (maxY - minY) + expansionPadding * 2;

            // Resize all frames
            for (const frame of this._frames) {
                frame.canvas.width = Math.max(1, newWidth);
                frame.canvas.height = Math.max(1, newHeight);
            }
            this.width = newWidth;
            this.height = newHeight;

            this.offsetX = Math.round(docX - newWidth / 2);
            this.offsetY = Math.round(docY - newHeight / 2);
            this.invalidateImageCache();
            return;
        }

        // Remember old dimensions and where old content center maps to in document space
        const oldWidth = this.width;
        const oldHeight = this.height;

        const oldContentCenter = { x: oldWidth / 2, y: oldHeight / 2 };
        const oldDocPos = this.layerToDoc(oldContentCenter.x, oldContentCenter.y);

        const newMinX = Math.floor(Math.min(0, minX - expansionPadding));
        const newMinY = Math.floor(Math.min(0, minY - expansionPadding));
        const newMaxX = Math.ceil(Math.max(this.width, maxX + expansionPadding));
        const newMaxY = Math.ceil(Math.max(this.height, maxY + expansionPadding));

        const newWidth = newMaxX - newMinX;
        const newHeight = newMaxY - newMinY;

        const dx = -newMinX;
        const dy = -newMinY;

        // Expand ALL frames uniformly
        for (const frame of this._frames) {
            const newCanvas = document.createElement('canvas');
            newCanvas.width = Math.max(1, newWidth);
            newCanvas.height = Math.max(1, newHeight);
            const newCtx = newCanvas.getContext('2d', { willReadFrequently: true });
            newCtx.drawImage(frame.canvas, dx, dy);
            frame.canvas = newCanvas;
            frame.ctx = newCtx;
        }

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

    // ==================== Canvas Operations ====================

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
     */
    async rotateCanvas(degrees, oldDocWidth, oldDocHeight, newDocWidth, newDocHeight) {
        if (![90, 180, 270].includes(degrees)) {
            console.error('[PixelLayer] Invalid rotation angle:', degrees);
            return;
        }

        const oldWidth = this.width;
        const oldHeight = this.height;
        const oldOffsetX = this.offsetX || 0;
        const oldOffsetY = this.offsetY || 0;

        // Calculate new dimensions
        let newWidth, newHeight;
        if (degrees === 180) {
            newWidth = oldWidth;
            newHeight = oldHeight;
        } else {
            newWidth = oldHeight;
            newHeight = oldWidth;
        }

        // Rotate ALL frames
        for (const frame of this._frames) {
            const newCanvas = document.createElement('canvas');
            newCanvas.width = newWidth;
            newCanvas.height = newHeight;
            const newCtx = newCanvas.getContext('2d');

            newCtx.save();
            if (degrees === 90) {
                newCtx.translate(newWidth, 0);
                newCtx.rotate(Math.PI / 2);
            } else if (degrees === 180) {
                newCtx.translate(newWidth, newHeight);
                newCtx.rotate(Math.PI);
            } else if (degrees === 270) {
                newCtx.translate(0, newHeight);
                newCtx.rotate(-Math.PI / 2);
            }
            newCtx.drawImage(frame.canvas, 0, 0);
            newCtx.restore();

            frame.canvas = newCanvas;
            frame.ctx = newCtx;
        }

        // Calculate new offset based on rotation around document center
        const centerX = oldDocWidth / 2;
        const centerY = oldDocHeight / 2;
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

        const dx = layerCenterX - centerX;
        const dy = layerCenterY - centerY;
        const rad = (degrees * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        const newCenterX = centerX + dx * cos - dy * sin;
        const newCenterY = centerY + dx * sin + dy * cos;

        const newDocCenterX = newDocWidth / 2;
        const newDocCenterY = newDocHeight / 2;
        const adjustedCenterX = newCenterX - centerX + newDocCenterX;
        const adjustedCenterY = newCenterY - centerY + newDocCenterY;

        this.width = newWidth;
        this.height = newHeight;
        this.offsetX = Math.round(adjustedCenterX - newWidth / 2);
        this.offsetY = Math.round(adjustedCenterY - newHeight / 2);
        this.invalidateImageCache();
    }

    /**
     * Mirror the layer's canvas content horizontally or vertically.
     * This flips the pixel data and recalculates the layer position.
     *
     * @param {'horizontal' | 'vertical'} direction - Mirror direction
     * @param {number} docWidth - Document width
     * @param {number} docHeight - Document height
     * @returns {Promise<void>}
     */
    async mirrorContent(direction, docWidth, docHeight) {
        if (!['horizontal', 'vertical'].includes(direction)) {
            console.error('[PixelLayer] Invalid mirror direction:', direction);
            return;
        }

        const width = this.width;
        const height = this.height;

        // Mirror ALL frames
        for (const frame of this._frames) {
            const newCanvas = document.createElement('canvas');
            newCanvas.width = width;
            newCanvas.height = height;
            const newCtx = newCanvas.getContext('2d');

            newCtx.save();
            if (direction === 'horizontal') {
                newCtx.translate(width, 0);
                newCtx.scale(-1, 1);
            } else {
                newCtx.translate(0, height);
                newCtx.scale(1, -1);
            }
            newCtx.drawImage(frame.canvas, 0, 0);
            newCtx.restore();

            frame.canvas = newCanvas;
            frame.ctx = newCtx;
        }

        // Mirror the layer's offset position within the document
        if (direction === 'horizontal') {
            this.offsetX = docWidth - this.offsetX - width;
        } else {
            this.offsetY = docHeight - this.offsetY - height;
        }

        this.invalidateImageCache();
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
        ctx.translate(-cx, -cy);                           // Offset to layer top-left

        // Draw the layer - canvas interpolation handles anti-aliasing
        ctx.drawImage(this.canvas, 0, 0);

        // Reset transform
        ctx.setTransform(1, 0, 0, 1, 0, 0);

        return { canvas: outputCanvas, bounds: outputBounds, ctx };
    }

    /**
     * Render a thumbnail of this layer in document space.
     * The thumbnail shows the layer as it appears in the document.
     *
     * @param {number} maxWidth - Maximum thumbnail width
     * @param {number} maxHeight - Maximum thumbnail height
     * @param {Object} [docSize] - Document size for positioning context
     * @returns {{canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D}}
     */
    renderThumbnail(maxWidth, maxHeight, docSize = null) {
        const thumbCanvas = document.createElement('canvas');
        thumbCanvas.width = maxWidth;
        thumbCanvas.height = maxHeight;
        const ctx = thumbCanvas.getContext('2d');

        // Handle 0x0 layers
        if (this.width === 0 || this.height === 0) {
            return { canvas: thumbCanvas, ctx };
        }

        // Get the layer's document bounds
        const docBounds = this.getDocumentBounds();

        // Calculate the reference size (either document or layer bounds)
        const refWidth = docSize?.width || docBounds.width;
        const refHeight = docSize?.height || docBounds.height;

        if (refWidth === 0 || refHeight === 0) {
            return { canvas: thumbCanvas, ctx };
        }

        // Calculate scale to fit in thumbnail
        const scale = Math.min(maxWidth / refWidth, maxHeight / refHeight);

        // Calculate offset to center the content
        const offsetX = (maxWidth - refWidth * scale) / 2;
        const offsetY = (maxHeight - refHeight * scale) / 2;

        // For non-transformed layers, simple scaling
        if (!this.hasTransform()) {
            const drawX = offsetX + (this.offsetX - (docSize ? 0 : docBounds.x)) * scale;
            const drawY = offsetY + (this.offsetY - (docSize ? 0 : docBounds.y)) * scale;
            const drawW = this.width * scale;
            const drawH = this.height * scale;
            ctx.drawImage(this.canvas, drawX, drawY, drawW, drawH);
            return { canvas: thumbCanvas, ctx };
        }

        // For transformed layers, rasterize first then scale
        const rasterized = this.rasterizeToDocument();

        // Calculate position in thumbnail
        const drawX = offsetX + (rasterized.bounds.x - (docSize ? 0 : docBounds.x)) * scale;
        const drawY = offsetY + (rasterized.bounds.y - (docSize ? 0 : docBounds.y)) * scale;
        const drawW = rasterized.bounds.width * scale;
        const drawH = rasterized.bounds.height * scale;

        ctx.drawImage(rasterized.canvas, drawX, drawY, drawW, drawH);

        return { canvas: thumbCanvas, ctx };
    }

    // ==================== Pixel Data ====================

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

    // ==================== Scaling ====================

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
        if (this.width === 0 || this.height === 0) {
            return;
        }

        const newWidth = Math.max(1, Math.round(this.width * scaleX));
        const newHeight = Math.max(1, Math.round(this.height * scaleY));

        // Scale ALL frames
        for (const frame of this._frames) {
            const srcData = frame.ctx.getImageData(0, 0, this.width, this.height);
            const dstData = lanczosResample(srcData, newWidth, newHeight);
            frame.canvas.width = newWidth;
            frame.canvas.height = newHeight;
            frame.ctx.putImageData(dstData, 0, 0);
        }

        this.width = newWidth;
        this.height = newHeight;

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
        if (this.hasTransform()) {
            return;
        }

        const bounds = this.getContentBounds();
        if (!bounds) return;

        const left = bounds.x - this.offsetX - padding;
        const top = bounds.y - this.offsetY - padding;
        const width = bounds.width + padding * 2;
        const height = bounds.height + padding * 2;

        const cropX = Math.max(0, Math.floor(left));
        const cropY = Math.max(0, Math.floor(top));
        const cropWidth = Math.ceil(Math.min(width, this.width - cropX));
        const cropHeight = Math.ceil(Math.min(height, this.height - cropY));

        if (cropWidth <= 0 || cropHeight <= 0) return;

        // Trim ALL frames uniformly
        for (const frame of this._frames) {
            const imageData = frame.ctx.getImageData(cropX, cropY, cropWidth, cropHeight);
            frame.canvas.width = cropWidth;
            frame.canvas.height = cropHeight;
            frame.ctx.putImageData(imageData, 0, 0);
        }

        this.width = cropWidth;
        this.height = cropHeight;
        this.offsetX += cropX;
        this.offsetY += cropY;

        this.invalidateImageCache();
    }

    // ==================== Clone ====================

    /**
     * Clone this layer.
     * @returns {PixelLayer}
     */
    clone() {
        const cloned = new PixelLayer({
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

        // Clone all frames (constructor created 1 frame already)
        cloned._frames = this._frames.map(f => this._cloneFrameData(f));
        cloned.activeFrameIndex = this.activeFrameIndex;

        return cloned;
    }

    // ==================== SVG Export ====================

    /**
     * Convert this layer to an SVG element for document export.
     * Creates a <g> with sf:type="raster" and embeds the canvas as a PNG data URL.
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
        const g = createLayerGroup(xmlDoc, this.id, 'raster', this.name);

        // Add sf:properties element with all layer properties
        const properties = this.getBaseSerializeData();
        const propsEl = createPropertiesElement(xmlDoc, properties);
        g.appendChild(propsEl);

        // Add image element with PNG data URL
        if (this.width > 0 && this.height > 0) {
            const image = xmlDoc.createElementNS('http://www.w3.org/2000/svg', 'image');
            image.setAttribute('x', this.offsetX.toString());
            image.setAttribute('y', this.offsetY.toString());
            image.setAttribute('width', this.width.toString());
            image.setAttribute('height', this.height.toString());

            // Embed canvas as PNG data URL
            const dataUrl = this.canvas.toDataURL('image/png');
            image.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', dataUrl);
            // Also set href for modern browsers
            image.setAttribute('href', dataUrl);

            // Apply transforms if present
            if (this.hasTransform()) {
                const cx = this.offsetX + this.width / 2;
                const cy = this.offsetY + this.height / 2;
                const transform = `translate(${cx}, ${cy}) rotate(${this.rotation}) scale(${this.scaleX}, ${this.scaleY}) translate(${-cx}, ${-cy})`;
                image.setAttribute('transform', transform);
            }

            g.appendChild(image);
        }

        return g;
    }

    // ==================== Serialization ====================

    /**
     * Serialize for history/save.
     * @returns {Object}
     */
    serialize() {
        // Serialize all frames
        const frames = this._frames.map(frame => {
            const imageData = (this.width > 0 && this.height > 0)
                ? frame.canvas.toDataURL('image/png')
                : 'data:image/png;base64,';
            return { id: frame.id, imageData, duration: frame.duration, delay: frame.delay };
        });

        return {
            ...this.getBaseSerializeData(),
            // Active frame's imageData for backward compat with v1 readers
            imageData: frames[this.activeFrameIndex]?.imageData || 'data:image/png;base64,',
            frames,
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
     * @returns {Promise<PixelLayer>}
     */
    static async deserialize(data) {
        // Migrate to current version
        data = PixelLayer.migrate(data);

        // Deserialize effects
        const effects = (data.effects || [])
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);

        const layer = new PixelLayer({
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

        // Helper to load image data onto a canvas
        const loadImageData = async (canvas, ctx, dataUrl) => {
            if (!dataUrl || dataUrl === 'data:image/png;base64,') return;
            await new Promise((resolve) => {
                const img = new Image();
                img.onload = () => { ctx.drawImage(img, 0, 0); resolve(); };
                img.onerror = () => { resolve(); };
                img.src = dataUrl;
            });
        };

        if (data.frames && data.frames.length > 0) {
            // Deserialize multi-frame data
            layer._frames = [];
            for (const frameData of data.frames) {
                const canvas = document.createElement('canvas');
                canvas.width = Math.max(1, data.width);
                canvas.height = Math.max(1, data.height);
                const ctx = canvas.getContext('2d', { willReadFrequently: true });
                if (data.width > 0 && data.height > 0) {
                    await loadImageData(canvas, ctx, frameData.imageData);
                }
                layer._frames.push(new PixelFrame({
                    id: frameData.id,
                    canvas,
                    ctx,
                    duration: frameData.duration ?? 0.1,
                    delay: frameData.delay ?? 0.0,
                }));
            }
            layer.activeFrameIndex = data.activeFrameIndex ?? 0;
        } else {
            // Legacy single-frame (v1) — load into the existing first frame
            if (data.width > 0 && data.height > 0) {
                await loadImageData(layer.canvas, layer.ctx, data.imageData);
            }
        }

        return layer;
    }
}

// For backwards compatibility, also export as Layer
export { PixelLayer as Layer };

// Register PixelLayer with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('raster', PixelLayer, ['Layer', 'PixelLayer']);
