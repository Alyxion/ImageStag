/**
 * Renderer - Composites all layers to the display canvas.
 */
import { BlendModes } from './BlendModes.js';
import { effectRenderer } from './EffectRenderer.js';

// Expose effectRenderer for debugging/testing
window.effectRenderer = effectRenderer;

export class Renderer {
    /**
     * @param {HTMLCanvasElement} displayCanvas - The visible canvas element
     * @param {LayerStack} layerStack - The layer stack to render
     */
    constructor(displayCanvas, layerStack) {
        this.displayCanvas = displayCanvas;
        this.displayCtx = displayCanvas.getContext('2d');
        this.layerStack = layerStack;

        // Device pixel ratio for HiDPI displays
        this._dpr = window.devicePixelRatio || 1;

        // Logical display size (CSS pixels)
        this._displayWidth = displayCanvas.width;
        this._displayHeight = displayCanvas.height;

        // Working canvas for composition
        this.compositeCanvas = document.createElement('canvas');
        this.compositeCtx = this.compositeCanvas.getContext('2d', { willReadFrequently: true });

        // Preview layer for tool overlays
        this.previewCanvas = null;

        // Reference to app for tool overlays
        this.app = null;

        // Settings
        this.backgroundColor = '#FFFFFF';
        this.showTransparencyGrid = true;
        this.gridSize = 10;
        this.showLayerBounds = false;  // Only show in move tool

        // Viewport/zoom state
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;

        // Render loop
        this.needsRender = true;
        this.animationFrameId = null;
        this.onRenderCallback = null;  // Callback after render completes
        this.startRenderLoop();
    }

    /**
     * Get the logical display width (CSS pixels).
     * @returns {number}
     */
    get displayWidth() {
        return this._displayWidth;
    }

    /**
     * Get the logical display height (CSS pixels).
     * @returns {number}
     */
    get displayHeight() {
        return this._displayHeight;
    }

    /**
     * Resize the display canvas for HiDPI support.
     * @param {number} width - Logical width in CSS pixels
     * @param {number} height - Logical height in CSS pixels
     */
    resizeDisplay(width, height) {
        const dpr = this._dpr;
        this._displayWidth = width;
        this._displayHeight = height;

        // Set the canvas internal size (actual pixels)
        this.displayCanvas.width = Math.round(width * dpr);
        this.displayCanvas.height = Math.round(height * dpr);

        // Set the canvas CSS size (logical pixels)
        this.displayCanvas.style.width = width + 'px';
        this.displayCanvas.style.height = height + 'px';

        this.needsRender = true;
    }

    /**
     * Set a callback to be called after each render.
     * @param {Function} callback
     */
    setOnRender(callback) {
        this.onRenderCallback = callback;
    }

    /**
     * Set the app reference for tool overlay rendering.
     * @param {Object} app - The app context
     */
    setApp(app) {
        this.app = app;
    }

    /**
     * Resize the composite canvas (document size).
     * @param {number} width
     * @param {number} height
     */
    resize(width, height) {
        this.compositeCanvas.width = width;
        this.compositeCanvas.height = height;
        this.needsRender = true;
    }

    /**
     * Draw a canvas with layer transform applied.
     * @param {HTMLCanvasElement} canvas - Canvas to draw
     * @param {Object} layer - Layer with transform properties
     * @param {number} offsetX - X offset to draw at
     * @param {number} offsetY - Y offset to draw at
     * @private
     */
    _drawWithTransform(canvas, layer, offsetX, offsetY) {
        if (!layer.hasTransform || !layer.hasTransform()) {
            // No transform - draw directly
            this.compositeCtx.drawImage(canvas, offsetX, offsetY);
            return;
        }

        // Apply transform: rotate and scale around layer center
        const cx = offsetX + layer.width / 2;
        const cy = offsetY + layer.height / 2;
        const rotation = layer.rotation || 0;
        const scaleX = layer.scaleX ?? 1.0;
        const scaleY = layer.scaleY ?? 1.0;

        this.compositeCtx.save();
        this.compositeCtx.translate(cx, cy);
        this.compositeCtx.rotate((rotation * Math.PI) / 180);
        this.compositeCtx.scale(scaleX, scaleY);
        this.compositeCtx.translate(-cx, -cy);
        this.compositeCtx.drawImage(canvas, offsetX, offsetY);
        this.compositeCtx.restore();
    }

    /**
     * Render all layers to the display canvas.
     */
    render() {
        const { width, height } = this.compositeCanvas;
        const dpr = this._dpr;

        // Clear composite canvas
        this.compositeCtx.clearRect(0, 0, width, height);

        // Draw transparency grid if enabled
        if (this.showTransparencyGrid) {
            this.drawTransparencyGrid();
        } else {
            this.compositeCtx.fillStyle = this.backgroundColor;
            this.compositeCtx.fillRect(0, 0, width, height);
        }

        // Composite all visible layers (bottom to top)
        // With index 0 = top, we iterate from last to first
        // Photoshop-style effect compositing:
        // 1. Draw behind effects (shadow/glow) - these blend with layers BELOW
        // 2. Draw layer content + stroke - unaffected by shadows
        for (let i = this.layerStack.layers.length - 1; i >= 0; i--) {
            const layer = this.layerStack.layers[i];
            // Skip groups - they have no canvas and don't render
            if (layer.isGroup && layer.isGroup()) continue;

            // Use effective visibility (considers parent group visibility)
            if (!this.layerStack.isEffectivelyVisible(layer)) continue;

            // Get effective opacity (multiplied through parent chain if not passthrough)
            const effectiveOpacity = this.layerStack.getEffectiveOpacity(layer);

            // Check if layer has effects
            if (layer.hasEffects && layer.hasEffects()) {
                // Get rendered layer with separate canvases for proper compositing
                const rendered = effectRenderer.getRenderedLayer(layer);
                if (rendered) {
                    // STEP 1: Draw behind effects (shadow, outer glow)
                    // These should blend with what's already been drawn (layers below)
                    // Each behind effect can have its own blend mode
                    if (rendered.behindEffects && rendered.behindEffects.length > 0) {
                        for (let j = 0; j < rendered.behindEffects.length; j++) {
                            const effect = rendered.behindEffects[j];
                            this.compositeCtx.globalAlpha = effectiveOpacity * effect.opacity;
                            this.compositeCtx.globalCompositeOperation = BlendModes.toCompositeOperation(effect.blendMode);
                            this._drawWithTransform(rendered.behindCanvas, layer, rendered.offsetX, rendered.offsetY);
                        }
                    } else if (rendered.behindCanvas) {
                        // Fallback: draw behind canvas with layer's blend mode if no effect list
                        this.compositeCtx.globalAlpha = effectiveOpacity;
                        this.compositeCtx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
                        this._drawWithTransform(rendered.behindCanvas, layer, rendered.offsetX, rendered.offsetY);
                    }

                    // STEP 2: Draw content + stroke (clean, unaffected by shadows)
                    // This uses the layer's blend mode
                    this.compositeCtx.globalAlpha = effectiveOpacity;
                    this.compositeCtx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
                    this._drawWithTransform(rendered.contentCanvas, layer, rendered.offsetX, rendered.offsetY);
                } else {
                    // Fallback to original if rendering failed
                    this.compositeCtx.globalAlpha = effectiveOpacity;
                    this.compositeCtx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
                    const offsetX = layer.offsetX ?? 0;
                    const offsetY = layer.offsetY ?? 0;
                    this._drawWithTransform(layer.canvas, layer, offsetX, offsetY);
                }
            } else {
                // No effects - draw layer with transform
                this.compositeCtx.globalAlpha = effectiveOpacity;
                this.compositeCtx.globalCompositeOperation = BlendModes.toCompositeOperation(layer.blendMode);
                const offsetX = layer.offsetX ?? 0;
                const offsetY = layer.offsetY ?? 0;
                this._drawWithTransform(layer.canvas, layer, offsetX, offsetY);
            }
        }

        // Draw preview layer if set
        if (this.previewCanvas) {
            this.compositeCtx.globalAlpha = 1.0;
            this.compositeCtx.globalCompositeOperation = 'source-over';
            this.compositeCtx.drawImage(this.previewCanvas, 0, 0);
        }

        // Reset composite settings
        this.compositeCtx.globalAlpha = 1.0;
        this.compositeCtx.globalCompositeOperation = 'source-over';

        // Draw vector layer selection handles as overlay (not stored on layer canvas)
        this.drawVectorSelectionHandles();

        // Get logical display size (use stored values or fallback to canvas size / dpr)
        const displayWidth = this._displayWidth || (this.displayCanvas.width / dpr);
        const displayHeight = this._displayHeight || (this.displayCanvas.height / dpr);

        // Draw to display canvas with DPR scaling and zoom/pan transform
        this.displayCtx.save();

        // Scale for HiDPI
        this.displayCtx.scale(dpr, dpr);

        // Fill background at logical size
        this.displayCtx.fillStyle = '#2d2d2d';
        this.displayCtx.fillRect(0, 0, displayWidth, displayHeight);

        // Apply zoom/pan transform
        this.displayCtx.translate(this.panX, this.panY);
        this.displayCtx.scale(this.zoom, this.zoom);

        // Always enable high-quality image smoothing for best rendering
        this.displayCtx.imageSmoothingEnabled = true;
        this.displayCtx.imageSmoothingQuality = 'high';

        this.displayCtx.drawImage(this.compositeCanvas, 0, 0);
        this.displayCtx.restore();

        // Draw overlays with DPR scaling (border, bounding boxes, tool overlays)
        this.displayCtx.save();
        this.displayCtx.scale(dpr, dpr);

        // Draw canvas border
        this.displayCtx.strokeStyle = '#666666';
        this.displayCtx.lineWidth = 1;
        this.displayCtx.strokeRect(
            this.panX - 0.5,
            this.panY - 0.5,
            width * this.zoom + 1,
            height * this.zoom + 1
        );

        // Draw bounding boxes for layers that extend outside the main canvas
        this.drawLayerBoundingBoxes(width, height);

        // Draw tool overlays (e.g., clone stamp source indicator)
        this.drawToolOverlay();

        this.displayCtx.restore();
    }

    /**
     * Draw the current tool's overlay if it has one.
     */
    drawToolOverlay() {
        if (!this.app || !this.app.toolManager) return;

        const currentTool = this.app.toolManager.currentTool;
        if (!currentTool || !currentTool.drawOverlay) return;

        // Create a docToScreen function for the tool to use
        const docToScreen = (docX, docY) => this.canvasToScreen(docX, docY);

        currentTool.drawOverlay(this.displayCtx, docToScreen);
    }

    /**
     * Draw selection handles for vector layers.
     * These are drawn on the composite canvas (not stored on layer canvas)
     * so they don't appear in the navigator or exports.
     */
    drawVectorSelectionHandles() {
        // Iterate bottom to top (last to first with index 0 = top)
        for (let i = this.layerStack.layers.length - 1; i >= 0; i--) {
            const layer = this.layerStack.layers[i];
            // Skip groups
            if (layer.isGroup && layer.isGroup()) continue;
            // Use effective visibility
            if (!this.layerStack.isEffectivelyVisible(layer)) continue;
            // Check if this is a vector layer with selections
            // Shapes are in document coordinates, composite context is in document coordinates
            if (layer.isVector && layer.isVector() && layer.selectedShapeIds?.size > 0) {
                layer.drawSelectionHandles(this.compositeCtx);
            }
        }
    }

    /**
     * Draw bounding boxes for layers that extend outside the document bounds.
     * Only shown when move tool is active (showLayerBounds = true).
     * Handles layer transforms (rotation, scale) when drawing the bounding box.
     * @param {number} docWidth - Document width
     * @param {number} docHeight - Document height
     */
    drawLayerBoundingBoxes(docWidth, docHeight) {
        // Only show bounding boxes when explicitly enabled (e.g., move tool active)
        if (!this.showLayerBounds) return;

        const activeLayer = this.layerStack.getActiveLayer();
        if (!activeLayer) return;

        const offsetX = activeLayer.offsetX ?? 0;
        const offsetY = activeLayer.offsetY ?? 0;

        this.displayCtx.save();
        this.displayCtx.translate(this.panX, this.panY);
        this.displayCtx.scale(this.zoom, this.zoom);

        // Check if layer has transform
        const hasTransform = activeLayer.hasTransform && activeLayer.hasTransform();

        if (hasTransform) {
            // Apply layer transform to draw rotated/scaled bounding box
            const cx = offsetX + activeLayer.width / 2;
            const cy = offsetY + activeLayer.height / 2;
            const rotation = activeLayer.rotation || 0;
            const scaleX = activeLayer.scaleX ?? 1.0;
            const scaleY = activeLayer.scaleY ?? 1.0;

            this.displayCtx.save();
            this.displayCtx.translate(cx, cy);
            this.displayCtx.rotate((rotation * Math.PI) / 180);
            this.displayCtx.scale(scaleX, scaleY);
            this.displayCtx.translate(-cx, -cy);

            // Draw subtle dashed bounding box
            this.displayCtx.strokeStyle = '#888888';
            this.displayCtx.lineWidth = 1 / (this.zoom * Math.max(scaleX, scaleY));
            this.displayCtx.setLineDash([4 / (this.zoom * Math.max(scaleX, scaleY)), 4 / (this.zoom * Math.max(scaleX, scaleY))]);
            this.displayCtx.strokeRect(offsetX, offsetY, activeLayer.width, activeLayer.height);

            // Draw small corner handles
            this.displayCtx.setLineDash([]);
            this.displayCtx.fillStyle = '#888888';
            const handleSize = 4 / (this.zoom * Math.max(scaleX, scaleY));
            const corners = [
                { x: offsetX, y: offsetY },
                { x: offsetX + activeLayer.width, y: offsetY },
                { x: offsetX + activeLayer.width, y: offsetY + activeLayer.height },
                { x: offsetX, y: offsetY + activeLayer.height }
            ];
            for (const corner of corners) {
                this.displayCtx.fillRect(
                    corner.x - handleSize / 2,
                    corner.y - handleSize / 2,
                    handleSize,
                    handleSize
                );
            }

            this.displayCtx.restore();
        } else {
            // No transform - draw simple bounding box
            const layerRight = offsetX + activeLayer.width;
            const layerBottom = offsetY + activeLayer.height;

            // Draw subtle dashed bounding box around layer bounds (gray color)
            this.displayCtx.strokeStyle = '#888888';
            this.displayCtx.lineWidth = 1 / this.zoom;
            this.displayCtx.setLineDash([4 / this.zoom, 4 / this.zoom]);
            this.displayCtx.strokeRect(offsetX, offsetY, activeLayer.width, activeLayer.height);

            // Draw small corner handles
            this.displayCtx.setLineDash([]);
            this.displayCtx.fillStyle = '#888888';
            const handleSize = 4 / this.zoom;
            const corners = [
                { x: offsetX, y: offsetY },
                { x: layerRight, y: offsetY },
                { x: layerRight, y: layerBottom },
                { x: offsetX, y: layerBottom }
            ];
            for (const corner of corners) {
                this.displayCtx.fillRect(
                    corner.x - handleSize / 2,
                    corner.y - handleSize / 2,
                    handleSize,
                    handleSize
                );
            }
        }

        this.displayCtx.restore();
    }

    /**
     * Draw transparency checkerboard pattern.
     */
    drawTransparencyGrid() {
        const { width, height } = this.compositeCanvas;
        const size = this.gridSize;
        const colors = ['#CCCCCC', '#FFFFFF'];

        for (let y = 0; y < height; y += size) {
            for (let x = 0; x < width; x += size) {
                const colorIndex = ((Math.floor(x / size) + Math.floor(y / size)) % 2);
                this.compositeCtx.fillStyle = colors[colorIndex];
                this.compositeCtx.fillRect(x, y, size, size);
            }
        }
    }

    /**
     * Start the render loop.
     */
    startRenderLoop() {
        const loop = () => {
            if (this.needsRender) {
                this.render();
                this.needsRender = false;
                // Call render callback if set
                if (this.onRenderCallback) {
                    this.onRenderCallback();
                }
            }
            this.animationFrameId = requestAnimationFrame(loop);
        };
        loop();
    }

    /**
     * Stop the render loop.
     */
    stopRenderLoop() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    /**
     * Request a render on the next frame.
     */
    requestRender() {
        this.needsRender = true;
    }

    /**
     * Set preview canvas for tool overlays.
     * @param {HTMLCanvasElement} canvas
     */
    setPreviewLayer(canvas) {
        this.previewCanvas = canvas;
        this.requestRender();
    }

    /**
     * Clear preview layer.
     */
    clearPreviewLayer() {
        this.previewCanvas = null;
        this.requestRender();
    }

    /**
     * Clear any tool overlay by requesting a re-render.
     * (Tool overlays are drawn fresh each frame, so we just need to re-render)
     */
    clearOverlay() {
        this.requestRender();
    }

    /**
     * Convert screen coordinates to canvas coordinates.
     * @param {number} screenX
     * @param {number} screenY
     * @returns {{x: number, y: number}}
     */
    screenToCanvas(screenX, screenY) {
        return {
            x: (screenX - this.panX) / this.zoom,
            y: (screenY - this.panY) / this.zoom
        };
    }

    /**
     * Convert canvas coordinates to screen coordinates.
     * @param {number} canvasX
     * @param {number} canvasY
     * @returns {{x: number, y: number}}
     */
    canvasToScreen(canvasX, canvasY) {
        return {
            x: canvasX * this.zoom + this.panX,
            y: canvasY * this.zoom + this.panY
        };
    }

    /**
     * Zoom in/out centered on a point.
     * @param {number} factor - Zoom factor (>1 to zoom in, <1 to zoom out)
     * @param {number} centerX - Screen X to zoom around
     * @param {number} centerY - Screen Y to zoom around
     */
    zoomAt(factor, centerX, centerY) {
        const canvas = this.screenToCanvas(centerX, centerY);
        this.zoom *= factor;
        this.zoom = Math.max(0.1, Math.min(10, this.zoom));
        const newScreen = this.canvasToScreen(canvas.x, canvas.y);
        this.panX += centerX - newScreen.x;
        this.panY += centerY - newScreen.y;
        this.requestRender();
    }

    /**
     * Pan the viewport.
     * @param {number} dx
     * @param {number} dy
     */
    pan(dx, dy) {
        this.panX += dx;
        this.panY += dy;
        this.requestRender();
    }

    /**
     * Center the canvas in the viewport.
     */
    centerCanvas() {
        const { width, height } = this.compositeCanvas;
        // Use logical display dimensions for centering
        this.panX = (this._displayWidth - width * this.zoom) / 2;
        this.panY = (this._displayHeight - height * this.zoom) / 2;
        this.requestRender();
    }

    /**
     * Fit the canvas to the viewport.
     */
    fitToViewport() {
        const { width, height } = this.compositeCanvas;
        // Use logical display dimensions for fitting
        const scaleX = (this._displayWidth - 40) / width;
        const scaleY = (this._displayHeight - 40) / height;
        this.zoom = Math.min(scaleX, scaleY, 1);
        this.centerCanvas();
    }
}
