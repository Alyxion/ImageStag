/**
 * VectorLayer - A layer that contains vector shapes instead of raster data.
 *
 * Vector shapes are stored as data objects and rendered to the canvas on demand.
 * Shapes remain editable until the layer is rasterized.
 *
 * Extends VectorizableLayer which provides:
 * - Internal canvas (no public ctx - shapes cannot be drawn on externally)
 * - Pixel export in multiple formats (RGBA8, RGB8, RGBA16, RGB16)
 * - SVG conversion capability
 */
import { VectorizableLayer } from './VectorizableLayer.js';
import { Layer } from './Layer.js';  // For rasterize()
import { createShape } from './VectorShape.js';
import { LayerEffect, effectRegistry } from './LayerEffects.js';

// Import shape types so they register themselves
import './shapes/RectShape.js';
import './shapes/EllipseShape.js';
import './shapes/LineShape.js';
import './shapes/PolygonShape.js';
import './shapes/PathShape.js';

export class VectorLayer extends VectorizableLayer {
    /** Serialization version for migration support */
    static VERSION = 2;

    /**
     * @param {Object} options
     * @param {string} [options.id]
     * @param {string} [options.name]
     * @param {number} options.width
     * @param {number} options.height
     * @param {number} [options.opacity]
     * @param {string} [options.blendMode]
     * @param {boolean} [options.visible]
     * @param {boolean} [options.locked]
     */
    constructor(options = {}) {
        super(options);

        // Mark as vector layer
        this.type = 'vector';

        // Parent group ID is inherited from Layer constructor via options.parentId

        // Array of VectorShape instances
        this.shapes = [];

        // Selection state
        this.selectedShapeIds = new Set();

        // Store original document dimensions for editing expansion
        // (layer starts at document size, then shrinks to fit content)
        this._docWidth = options.width;
        this._docHeight = options.height;
    }

    /**
     * Check if this is a group.
     * @returns {boolean}
     */
    isGroup() {
        return false;
    }

    /**
     * Add a shape to this layer.
     * When a shape is added (editing finishes), render via SVG with config settings.
     * @param {VectorShape} shape
     * @param {number} [index] - Insert at index, or append if not specified
     */
    addShape(shape, index = -1) {
        if (index >= 0 && index < this.shapes.length) {
            this.shapes.splice(index, 0, shape);
        } else {
            this.shapes.push(shape);
        }
        // Auto-fit layer to content bounds
        this.fitToContent();
        // Immediate Canvas 2D render so shape is visible right away
        this.renderPreview();
        // Then schedule high-quality SVG render
        this.render();
    }

    /**
     * Resize layer canvas to fit all shapes with minimal padding.
     * Updates offsetX/offsetY to position layer correctly in document space.
     */
    fitToContent() {
        const padding = 2;  // Small padding for anti-aliasing
        const bounds = this.getShapesBoundsInDocSpace(padding);

        if (!bounds || bounds.width <= 0 || bounds.height <= 0) {
            // No shapes or invalid bounds - use minimum size
            return;
        }

        const newWidth = Math.ceil(bounds.width);
        const newHeight = Math.ceil(bounds.height);
        const newOffsetX = Math.floor(bounds.x);
        const newOffsetY = Math.floor(bounds.y);

        // Only resize if dimensions actually changed
        if (this.width === newWidth && this.height === newHeight &&
            this.offsetX === newOffsetX && this.offsetY === newOffsetY) {
            return;
        }

        // Resize canvas (this clears the canvas content)
        this.width = newWidth;
        this.height = newHeight;
        this.canvas.width = newWidth;
        this.canvas.height = newHeight;

        // Update offset to position layer in document space
        this.offsetX = newOffsetX;
        this.offsetY = newOffsetY;

        // Re-render shapes after canvas resize (canvas was cleared by resize)
        this.renderPreview();

        console.debug(`[VectorLayer] fitToContent: ${newWidth}x${newHeight} at (${newOffsetX}, ${newOffsetY})`);
    }

    /**
     * Get bounds of all shapes in document coordinate space.
     * Unlike getShapesBounds(), this doesn't clamp to layer bounds.
     * @param {number} [padding=0]
     * @returns {{ x: number, y: number, width: number, height: number } | null}
     */
    getShapesBoundsInDocSpace(padding = 0) {
        if (this.shapes.length === 0) return null;

        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        for (const shape of this.shapes) {
            const bounds = shape.getBounds();
            if (!bounds) continue;

            // Account for stroke width
            const strokePadding = (shape.stroke ? shape.strokeWidth / 2 : 0);

            minX = Math.min(minX, bounds.x - strokePadding);
            minY = Math.min(minY, bounds.y - strokePadding);
            maxX = Math.max(maxX, bounds.x + bounds.width + strokePadding);
            maxY = Math.max(maxY, bounds.y + bounds.height + strokePadding);
        }

        if (minX === Infinity) return null;

        // Add padding (don't clamp to layer bounds - shapes define the bounds)
        minX = Math.floor(minX - padding);
        minY = Math.floor(minY - padding);
        maxX = Math.ceil(maxX + padding);
        maxY = Math.ceil(maxY + padding);

        return {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY
        };
    }

    /**
     * Remove a shape by ID.
     * @param {string} shapeId
     * @returns {VectorShape|null} The removed shape
     */
    removeShape(shapeId) {
        const index = this.shapes.findIndex(s => s.id === shapeId);
        if (index >= 0) {
            const [removed] = this.shapes.splice(index, 1);
            this.selectedShapeIds.delete(shapeId);
            // Auto-fit layer to remaining content
            this.fitToContent();
            // Immediate Canvas 2D render so removal is visible right away
            this.renderPreview();
            // Then schedule high-quality SVG render
            this.render();
            return removed;
        }
        return null;
    }

    /**
     * Get shape by ID.
     * @param {string} shapeId
     * @returns {VectorShape|null}
     */
    getShapeById(shapeId) {
        return this.shapes.find(s => s.id === shapeId) || null;
    }

    /**
     * Get shape at position (for hit testing).
     * Checks in reverse order (top shapes first).
     * @param {number} x
     * @param {number} y
     * @returns {VectorShape|null}
     */
    getShapeAt(x, y) {
        for (let i = this.shapes.length - 1; i >= 0; i--) {
            if (this.shapes[i].containsPoint(x, y)) {
                return this.shapes[i];
            }
        }
        return null;
    }

    /**
     * Get control point at position across all selected shapes.
     * @param {number} x
     * @param {number} y
     * @param {number} [tolerance]
     * @returns {{ shape: VectorShape, control: Object }|null}
     */
    getControlPointAt(x, y, tolerance = 8) {
        for (const shapeId of this.selectedShapeIds) {
            const shape = this.getShapeById(shapeId);
            if (shape) {
                const control = shape.getControlPointAt(x, y, tolerance);
                if (control) {
                    return { shape, control };
                }
            }
        }
        return null;
    }

    /**
     * Select a shape.
     * Selection changes don't re-render the layer - they only affect overlay display.
     * @param {string} shapeId
     * @param {boolean} [addToSelection] - Add to existing selection
     */
    selectShape(shapeId, addToSelection = false) {
        if (!addToSelection) {
            // Clear without triggering render
            for (const id of this.selectedShapeIds) {
                const s = this.getShapeById(id);
                if (s) s.selected = false;
            }
            this.selectedShapeIds.clear();
        }

        const shape = this.getShapeById(shapeId);
        if (shape) {
            shape.selected = true;
            this.selectedShapeIds.add(shapeId);
        }
        // Note: caller should request renderer update for overlay
    }

    /**
     * Deselect a shape.
     * @param {string} shapeId
     */
    deselectShape(shapeId) {
        const shape = this.getShapeById(shapeId);
        if (shape) {
            shape.selected = false;
            this.selectedShapeIds.delete(shapeId);
        }
        // Note: caller should request renderer update for overlay
    }

    /**
     * Clear all selection.
     */
    clearSelection() {
        for (const shapeId of this.selectedShapeIds) {
            const shape = this.getShapeById(shapeId);
            if (shape) {
                shape.selected = false;
            }
        }
        this.selectedShapeIds.clear();
        // Note: caller should request renderer update for overlay
    }

    /**
     * Get all selected shapes.
     * @returns {VectorShape[]}
     */
    getSelectedShapes() {
        return this.shapes.filter(s => this.selectedShapeIds.has(s.id));
    }

    /**
     * Move a shape in z-order.
     * @param {string} shapeId
     * @param {'up'|'down'|'top'|'bottom'} direction
     */
    moveShapeInOrder(shapeId, direction) {
        const index = this.shapes.findIndex(s => s.id === shapeId);
        if (index < 0) return;

        const [shape] = this.shapes.splice(index, 1);

        switch (direction) {
            case 'up':
                this.shapes.splice(Math.min(index + 1, this.shapes.length), 0, shape);
                break;
            case 'down':
                this.shapes.splice(Math.max(index - 1, 0), 0, shape);
                break;
            case 'top':
                this.shapes.push(shape);
                break;
            case 'bottom':
                this.shapes.unshift(shape);
                break;
        }

        this.render();
    }

    /**
     * Render all shapes via SVG (default) or Canvas 2D preview.
     * Only uses Canvas 2D when explicitly in editing mode (dragging).
     */
    render() {
        if (this._isEditing) {
            // During active editing (dragging), use fast Canvas 2D
            this.renderPreview();
        } else {
            // Always use SVG for final output
            // Debounce to avoid multiple concurrent renders
            if (this._svgRenderTimeout) {
                clearTimeout(this._svgRenderTimeout);
            }
            this._svgRenderTimeout = setTimeout(() => {
                this._svgRenderTimeout = null;
                this.renderFinal().catch(err => {
                    console.warn('SVG render failed:', err);
                });
            }, 10);  // Small delay to batch rapid render calls
        }
    }

    /**
     * Start editing mode - uses fast Canvas 2D preview.
     * Expands canvas to document size to allow free movement.
     * Call this before drag operations or interactive editing.
     */
    startEditing() {
        this._isEditing = true;

        // Expand canvas to document dimensions to allow shapes to move freely
        // Without this, shapes would be clipped to the auto-fitted bounds
        if (this._docWidth && this._docHeight) {
            // Save current fit state
            this._preEditWidth = this.width;
            this._preEditHeight = this.height;
            this._preEditOffsetX = this.offsetX;
            this._preEditOffsetY = this.offsetY;

            // Expand to document size at origin
            this.width = this._docWidth;
            this.height = this._docHeight;
            this.canvas.width = this._docWidth;
            this.canvas.height = this._docHeight;
            this.offsetX = 0;
            this.offsetY = 0;
        }
    }

    /**
     * End editing mode - resizes layer to fit content and renders via SVG.
     * Call this when drag/edit operation completes.
     */
    endEditing() {
        this._isEditing = false;
        // Clear saved state
        delete this._preEditWidth;
        delete this._preEditHeight;
        delete this._preEditOffsetX;
        delete this._preEditOffsetY;
        // Re-fit layer to content (shapes may have moved)
        this.fitToContent();
        // Do immediate Canvas 2D render so layer isn't blank while async SVG renders
        // (fitToContent resizes canvas which clears it, and SVG render is async)
        this.renderPreview();
        // Then schedule high-quality SVG render
        this.render();
    }

    /**
     * Fast Canvas 2D preview render.
     * Used during active editing for responsiveness.
     * Note: Selection handles are drawn by the Renderer as an overlay.
     */
    renderPreview() {
        this._ctx.clearRect(0, 0, this.width, this.height);

        // Translate so shapes (in document coordinates) render correctly
        // within the layer canvas (which is positioned at offsetX, offsetY)
        this._ctx.save();
        this._ctx.translate(-this.offsetX, -this.offsetY);

        for (const shape of this.shapes) {
            shape.render(this._ctx);
        }

        this._ctx.restore();
    }

    /**
     * Get combined bounding box of all shapes in document space.
     * Returns the actual bounds of shapes including stroke, without clamping.
     * @param {number} [padding=0] - Extra padding around bounds
     * @returns {{ x: number, y: number, width: number, height: number } | null}
     */
    getShapesBounds(padding = 0) {
        // Delegate to getShapesBoundsInDocSpace - shapes are in document coordinates
        return this.getShapesBoundsInDocSpace(padding);
    }

    /**
     * Generate SVG document from all shapes.
     * This is the canonical representation for cross-platform parity.
     * @param {Object} [options]
     * @param {number} [options.scale=1] - Scale factor for supersampling
     * @param {boolean} [options.antialiasing=false] - Use geometricPrecision (true) or crispEdges (false)
     * @param {{ x: number, y: number, width: number, height: number }} [options.bounds] - Render only this area
     * @returns {string} SVG document string
     */
    toSVG(options = {}) {
        const scale = options.scale || 1;
        const antialiasing = options.antialiasing ?? false;
        const bounds = options.bounds || { x: 0, y: 0, width: this.width, height: this.height };

        const elements = this.shapes
            .map(shape => shape.toSVGElement())
            .filter(el => el);  // Remove empty elements

        // shape-rendering options:
        // - crispEdges: Disables AA, gives exact cross-platform parity
        // - geometricPrecision: High-quality AA, but 1-4% diff between Chrome/resvg
        const shapeRendering = antialiasing ? 'geometricPrecision' : 'crispEdges';

        // For supersampling: scale width/height but keep viewBox at logical size
        const renderWidth = bounds.width * scale;
        const renderHeight = bounds.height * scale;

        return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${renderWidth}" height="${renderHeight}" viewBox="${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}" shape-rendering="${shapeRendering}">
  ${elements.join('\n  ')}
</svg>`;
    }

    /**
     * Render layer via SVG for pixel-accurate output.
     * This matches Python's resvg rendering for cross-platform parity.
     * With auto-fit, the layer canvas is already sized to content bounds.
     * @param {Object} [options]
     * @param {number} [options.supersample=1] - Supersampling level (render at Nx, downscale)
     * @param {boolean} [options.antialiasing=false] - Use geometricPrecision (true) or crispEdges (false)
     * @returns {Promise<void>}
     */
    async renderViaSVG(options = {}) {
        if (this.shapes.length === 0) {
            this._ctx.clearRect(0, 0, this.width, this.height);
            return;
        }

        const supersample = Math.max(1, options.supersample || 1);
        const antialiasing = options.antialiasing ?? false;

        // Get bounds in document space for SVG viewBox
        const padding = 2;
        const docBounds = this.getShapesBoundsInDocSpace(padding);

        if (!docBounds || docBounds.width <= 0 || docBounds.height <= 0) {
            this._ctx.clearRect(0, 0, this.width, this.height);
            return;
        }

        // SVG viewBox uses document coordinates (shapes are in document space)
        const svg = this.toSVG({ scale: supersample, antialiasing, bounds: docBounds });
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        try {
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = url;
            });

            // Clear the entire canvas first
            this._ctx.clearRect(0, 0, this.width, this.height);

            // Target dimensions = layer canvas size (already auto-fitted)
            const targetWidth = this.width;
            const targetHeight = this.height;

            // Position in layer canvas: account for difference between
            // actual bounds and layer offset (due to padding/rounding)
            const drawX = docBounds.x - this.offsetX;
            const drawY = docBounds.y - this.offsetY;

            if (supersample > 1) {
                // Multi-step downscaling for quality
                let currentImg = img;
                let currentWidth = img.naturalWidth;
                let currentHeight = img.naturalHeight;

                const tempCanvas = document.createElement('canvas');
                const tempCtx = tempCanvas.getContext('2d');

                // Downscale in 2x steps
                while (currentWidth > targetWidth * 2 || currentHeight > targetHeight * 2) {
                    const nextWidth = Math.max(targetWidth, Math.floor(currentWidth / 2));
                    const nextHeight = Math.max(targetHeight, Math.floor(currentHeight / 2));

                    tempCanvas.width = nextWidth;
                    tempCanvas.height = nextHeight;
                    tempCtx.imageSmoothingEnabled = true;
                    tempCtx.imageSmoothingQuality = 'high';
                    tempCtx.drawImage(currentImg, 0, 0, nextWidth, nextHeight);

                    currentImg = tempCanvas;
                    currentWidth = nextWidth;
                    currentHeight = nextHeight;
                }

                // Final step - draw at correct position in layer canvas
                this._ctx.imageSmoothingEnabled = true;
                this._ctx.imageSmoothingQuality = 'high';
                this._ctx.drawImage(currentImg, 0, 0, currentWidth, currentHeight,
                                   drawX, drawY, targetWidth, targetHeight);
            } else {
                // 1:1 rendering - draw at correct position
                this._ctx.imageSmoothingEnabled = false;
                this._ctx.drawImage(img, drawX, drawY);
            }
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Render using current config settings.
     * Called automatically when editing finishes.
     * @returns {Promise<void>}
     */
    async renderFinal() {
        // Get config from UIConfig if available, otherwise use defaults
        let useSVG = true;
        let supersample = 3;
        let antialiasing = false;

        try {
            // Dynamic import to avoid circular dependencies
            const { UIConfig } = await import('../config/UIConfig.js');
            useSVG = UIConfig.get('rendering.vectorSVGRendering') ?? true;
            supersample = UIConfig.get('rendering.vectorSupersampleLevel') ?? 3;
            antialiasing = UIConfig.get('rendering.vectorAntialiasing') ?? false;
        } catch (e) {
            console.warn('[VectorLayer.renderFinal] UIConfig not available, using defaults:', e);
        }

        if (useSVG) {
            await this.renderViaSVG({ supersample, antialiasing });
        } else {
            // Fallback: use Canvas 2D directly (same as renderPreview)
            this.renderPreview();
        }
        // Note: Selection handles are drawn by the Renderer as an overlay,
        // not on the layer canvas (so they don't appear in navigator/export)
    }

    /**
     * Draw selection handles for selected shapes to a given context.
     * Called by Renderer to draw handles as an overlay.
     * Shapes are stored in document coordinates, so no translation needed.
     * @param {CanvasRenderingContext2D} ctx - The context to draw to (in document space)
     */
    drawSelectionHandles(ctx) {
        // Shapes are in document coordinates, composite context is in document coordinates.
        // No translation needed - just draw at shape positions.
        for (const shapeId of this.selectedShapeIds) {
            const shape = this.getShapeById(shapeId);
            if (shape) {
                shape.renderSelection(ctx);
            }
        }
    }

    /**
     * Get raw RGBA pixel data after SVG rendering.
     * Used for parity testing with Python.
     * @returns {Promise<Uint8ClampedArray>}
     */
    async getPixelsViaSVG() {
        await this.renderViaSVG();
        const imageData = this._ctx.getImageData(0, 0, this.width, this.height);
        return imageData.data;
    }

    /**
     * Create a rasterized (pixel) copy of this layer.
     * @returns {Layer}
     */
    rasterize() {
        // Make sure canvas is up to date
        this.render();

        // Create a new bitmap layer
        const rasterLayer = new Layer({
            width: this.width,
            height: this.height,
            name: this.name,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible,
            locked: this.locked
        });

        // Copy the rendered content
        rasterLayer.ctx.drawImage(this.canvas, 0, 0);

        return rasterLayer;
    }

    /**
     * Clone this vector layer.
     * @returns {VectorLayer}
     */
    clone() {
        const cloned = new VectorLayer({
            width: this.width,
            height: this.height,
            parentId: this.parentId,
            name: `${this.name} (copy)`,
            opacity: this.opacity,
            blendMode: this.blendMode,
            visible: this.visible
        });

        // Clone all shapes
        cloned.shapes = this.shapes.map(s => s.clone());

        cloned.render();
        return cloned;
    }

    /**
     * Serialize for history/save.
     * @returns {Object}
     */
    serialize() {
        return {
            _version: VectorLayer.VERSION,
            _type: 'VectorLayer',
            type: 'vector',
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
            shapes: this.shapes.map(s => s.toData()),
            effects: this.effects.map(e => e.serialize()),
            _docWidth: this._docWidth,
            _docHeight: this._docHeight
        };
    }

    /**
     * Migrate serialized data from older versions.
     * @param {Object} data - Serialized vector layer data
     * @returns {Object} - Migrated data at current version
     */
    static migrate(data) {
        // Handle pre-versioned data
        if (data._version === undefined) {
            data._version = 0;
        }

        // v0 -> v1: Ensure shapes array exists
        if (data._version < 1) {
            data.shapes = data.shapes || [];
            data._version = 1;
        }

        // v1 -> v2: Add offsetX, offsetY, effects, _docWidth, _docHeight, parentId
        if (data._version < 2) {
            data.offsetX = data.offsetX ?? 0;
            data.offsetY = data.offsetY ?? 0;
            data.effects = data.effects || [];
            data._docWidth = data._docWidth ?? data.width;
            data._docHeight = data._docHeight ?? data.height;
            data.parentId = data.parentId ?? null;
            data._version = 2;
        }

        // Future migrations:
        // if (data._version < 3) { ... data._version = 3; }

        return data;
    }

    /**
     * Restore from serialized data.
     * @param {Object} data
     * @returns {VectorLayer}
     */
    static deserialize(data) {
        // Migrate to current version
        data = VectorLayer.migrate(data);

        // Deserialize effects
        const effects = (data.effects || [])
            .map(e => LayerEffect.deserialize(e))
            .filter(e => e !== null);

        const layer = new VectorLayer({
            id: data.id,
            name: data.name,
            parentId: data.parentId,
            width: data.width,
            height: data.height,
            opacity: data.opacity,
            blendMode: data.blendMode,
            visible: data.visible,
            locked: data.locked,
            effects: effects
        });

        // Restore offset position
        layer.offsetX = data.offsetX ?? 0;
        layer.offsetY = data.offsetY ?? 0;

        // Restore document dimensions for editing expansion
        layer._docWidth = data._docWidth ?? data.width;
        layer._docHeight = data._docHeight ?? data.height;

        // Restore shapes
        layer.shapes = (data.shapes || []).map(shapeData => createShape(shapeData));

        // Fit canvas to content bounds and render
        layer.fitToContent();
        // renderPreview() for immediate visibility (sync)
        layer.renderPreview();
        // render() schedules high-quality async SVG render
        layer.render();

        return layer;
    }

    /**
     * Check if this is a vector layer.
     * @returns {boolean}
     */
    isVector() {
        return true;
    }

    /**
     * Scale the layer by a factor around an optional center point.
     * Scales all shapes' coordinates, then re-fits to content.
     * @param {number} scaleX - Horizontal scale factor
     * @param {number} scaleY - Vertical scale factor
     * @param {Object} [options]
     * @param {number} [options.centerX] - Center X in document coords
     * @param {number} [options.centerY] - Center Y in document coords
     */
    async scale(scaleX, scaleY, options = {}) {
        if (this.shapes.length === 0) return;

        const bounds = this.getShapesBoundsInDocSpace();
        if (!bounds) return;

        const centerX = options.centerX ?? (bounds.x + bounds.width / 2);
        const centerY = options.centerY ?? (bounds.y + bounds.height / 2);

        // Scale all shapes
        for (const shape of this.shapes) {
            shape.scale(scaleX, scaleY, centerX, centerY);
        }

        // Re-fit layer to new content bounds
        this.fitToContent();

        // Render (fast preview first, then high-quality SVG)
        this.renderPreview();
        await this.renderFinal();

        this.invalidateImageCache();
    }

    /**
     * Scale to specific dimensions.
     * @param {number} newWidth - Target width
     * @param {number} newHeight - Target height
     * @param {Object} [options]
     * @param {number} [options.centerX] - Center X in document coords
     * @param {number} [options.centerY] - Center Y in document coords
     */
    async scaleTo(newWidth, newHeight, options = {}) {
        const bounds = this.getShapesBoundsInDocSpace();
        if (!bounds || bounds.width === 0 || bounds.height === 0) return;

        const scaleX = newWidth / bounds.width;
        const scaleY = newHeight / bounds.height;

        await this.scale(scaleX, scaleY, options);
    }
}

// Add helper to regular Layer to check type
Layer.prototype.isVector = function() {
    return false;
};
