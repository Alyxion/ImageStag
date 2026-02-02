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

        // Create offscreen canvas for this layer
        // Canvas must be at least 1x1, even if logical size is 0x0
        this.canvas = document.createElement('canvas');
        this.canvas.width = Math.max(1, this.width);
        this.canvas.height = Math.max(1, this.height);
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
    }

    // ==================== Type Checks ====================

    /**
     * Check if this is a pixel/raster layer.
     * @returns {boolean}
     */
    isRaster() {
        return true;
    }

    // ==================== Bounds ====================

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
        // For transformed layers, skip auto-fit - the offset calculation is complex
        // and getting it wrong causes the content to jump to the wrong position.
        // The memory savings from auto-fit aren't worth the complexity for rotated layers.
        if (this.hasTransform()) {
            return false;
        }

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
            // Clamp dimensions to MAX_DIMENSION
            const newWidth = Math.min(MAX_DIMENSION, Math.ceil(width));
            const newHeight = Math.min(MAX_DIMENSION, Math.ceil(height));

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
        let newX = Math.floor(Math.min(this.offsetX, x));
        let newY = Math.floor(Math.min(this.offsetY, y));
        let newWidth = Math.ceil(Math.max(currentRight, newRight) - newX);
        let newHeight = Math.ceil(Math.max(currentBottom, newBottom) - newY);

        // Clamp dimensions to MAX_DIMENSION
        if (newWidth > MAX_DIMENSION) {
            // If expanding left, limit how far left we can go
            if (newX < this.offsetX) {
                newX = Math.max(newX, currentRight - MAX_DIMENSION);
            }
            newWidth = MAX_DIMENSION;
        }
        if (newHeight > MAX_DIMENSION) {
            // If expanding up, limit how far up we can go
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

        // Pick a reference point: the old content center
        const oldContentCenter = { x: oldWidth / 2, y: oldHeight / 2 };
        // Where does this point appear in document space?
        const oldDocPos = this.layerToDoc(oldContentCenter.x, oldContentCenter.y);

        // Calculate new layer-local bounds with padding to avoid frequent re-expansion
        const newMinX = Math.floor(Math.min(0, minX - expansionPadding));
        const newMinY = Math.floor(Math.min(0, minY - expansionPadding));
        const newMaxX = Math.ceil(Math.max(this.width, maxX + expansionPadding));
        const newMaxY = Math.ceil(Math.max(this.height, maxY + expansionPadding));

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

        const oldCanvas = this.canvas;
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
            // 90 or 270: swap dimensions
            newWidth = oldHeight;
            newHeight = oldWidth;
        }

        // Create new canvas
        const newCanvas = document.createElement('canvas');
        newCanvas.width = newWidth;
        newCanvas.height = newHeight;
        const newCtx = newCanvas.getContext('2d');

        // Rotate and draw
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
        newCtx.drawImage(oldCanvas, 0, 0);
        newCtx.restore();

        // Calculate new offset based on rotation around document center
        const centerX = oldDocWidth / 2;
        const centerY = oldDocHeight / 2;
        const layerCenterX = oldOffsetX + oldWidth / 2;
        const layerCenterY = oldOffsetY + oldHeight / 2;

        // Rotate layer center point around document center
        const dx = layerCenterX - centerX;
        const dy = layerCenterY - centerY;
        const rad = (degrees * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        const newCenterX = centerX + dx * cos - dy * sin;
        const newCenterY = centerY + dx * sin + dy * cos;

        // Adjust for new document center (if dimensions swapped)
        const newDocCenterX = newDocWidth / 2;
        const newDocCenterY = newDocHeight / 2;
        const adjustedCenterX = newCenterX - centerX + newDocCenterX;
        const adjustedCenterY = newCenterY - centerY + newDocCenterY;

        const newOffsetX = Math.round(adjustedCenterX - newWidth / 2);
        const newOffsetY = Math.round(adjustedCenterY - newHeight / 2);

        // Update layer
        this.canvas = newCanvas;
        this.ctx = newCtx;
        this.width = newWidth;
        this.height = newHeight;
        this.offsetX = newOffsetX;
        this.offsetY = newOffsetY;
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

        const oldCanvas = this.canvas;
        const width = this.width;
        const height = this.height;

        // Create new canvas with mirrored content
        const newCanvas = document.createElement('canvas');
        newCanvas.width = width;
        newCanvas.height = height;
        const newCtx = newCanvas.getContext('2d');

        // Apply mirror transform and draw
        newCtx.save();
        if (direction === 'horizontal') {
            newCtx.translate(width, 0);
            newCtx.scale(-1, 1);
        } else {
            newCtx.translate(0, height);
            newCtx.scale(1, -1);
        }
        newCtx.drawImage(oldCanvas, 0, 0);
        newCtx.restore();

        // Mirror the layer's offset position within the document
        if (direction === 'horizontal') {
            this.offsetX = docWidth - this.offsetX - width;
        } else {
            this.offsetY = docHeight - this.offsetY - height;
        }

        // Update layer
        this.canvas = newCanvas;
        this.ctx = newCtx;
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
        // For transformed layers, skip trim - the offset calculation is complex
        // and getting it wrong causes the content to jump to the wrong position.
        if (this.hasTransform()) {
            return;
        }

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
        if (this.width > 0 && this.height > 0) {
            cloned.ctx.drawImage(this.canvas, 0, 0);
        }
        return cloned;
    }

    // ==================== Serialization ====================

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
            _version: PixelLayer.VERSION,
            _type: 'PixelLayer',
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

// For backwards compatibility, also export as Layer
export { PixelLayer as Layer };

// Register PixelLayer with the LayerRegistry
import { layerRegistry } from './LayerRegistry.js';
layerRegistry.register('raster', PixelLayer, ['Layer', 'PixelLayer']);
