/**
 * NavigatorManager Mixin
 *
 * Handles the navigator panel: preview rendering and pan interactions.
 * Updates are managed by PreviewUpdateManager for consistent debouncing.
 *
 * Required component data:
 *   - showNavigator: Boolean
 *   - tabletNavPanelOpen: Boolean
 *   - currentUIMode: String
 *   - docWidth: Number
 *   - docHeight: Number
 *   - navigatorDragging: Boolean
 *
 * Required component refs:
 *   - navigatorCanvas: HTMLCanvasElement (desktop)
 *   - tabletNavigatorCanvas: HTMLCanvasElement (tablet)
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - markNavigatorDirty(): Marks navigator for debounced update (from PreviewUpdateManager)
 */
export const NavigatorManagerMixin = {
    methods: {
        /**
         * Throttled navigator update - DEPRECATED, use markNavigatorDirty() instead.
         * Kept for backwards compatibility, now delegates to PreviewUpdateManager.
         */
        throttledNavigatorUpdate() {
            // Delegate to the centralized debouncing system
            if (typeof this.markNavigatorDirty === 'function') {
                this.markNavigatorDirty();
            } else {
                // Fallback if PreviewUpdateManager not available
                this.updateNavigator();
            }
        },

        /**
         * Update the navigator panel with current document preview and viewport rectangle
         */
        updateNavigator() {
            const app = this.getState();
            const canvas = this.$refs.tabletNavigatorCanvas || this.$refs.navigatorCanvas;
            if (!app?.renderer || !app?.layerStack || !canvas) return;

            // In tablet mode, update if nav panel is open; in desktop mode check showNavigator
            if (this.currentUIMode === 'tablet') {
                if (!this.tabletNavPanelOpen) return;
            } else {
                if (!this.showNavigator) return;
            }

            const ctx = canvas.getContext('2d');
            const maxSize = 180;

            // Calculate scale to fit navigator
            const docWidth = app.renderer.compositeCanvas?.width || this.docWidth;
            const docHeight = app.renderer.compositeCanvas?.height || this.docHeight;
            const scale = Math.min(maxSize / docWidth, maxSize / docHeight);

            canvas.width = Math.ceil(docWidth * scale);
            canvas.height = Math.ceil(docHeight * scale);

            // Enable high-quality image smoothing for best preview quality
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            // Draw transparency pattern background
            ctx.fillStyle = '#444';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw checkerboard
            const gridSize = 8;
            ctx.fillStyle = '#555';
            for (let y = 0; y < canvas.height; y += gridSize) {
                for (let x = 0; x < canvas.width; x += gridSize) {
                    if ((Math.floor(x / gridSize) + Math.floor(y / gridSize)) % 2 === 0) {
                        ctx.fillRect(x, y, gridSize, gridSize);
                    }
                }
            }

            // Draw layers with proper offsets and high-quality scaling
            // Iterate last-to-first: index 0 is top, so we draw bottom layers first
            for (let i = app.layerStack.layers.length - 1; i >= 0; i--) {
                const layer = app.layerStack.layers[i];
                // Skip groups - they have no canvas
                if (layer.isGroup && layer.isGroup()) continue;
                // Use effective visibility (considers parent groups)
                if (!app.layerStack.isEffectivelyVisible(layer)) continue;
                ctx.globalAlpha = app.layerStack.getEffectiveOpacity(layer);

                // Use rasterizeToDocument for transformed layers
                if (layer.hasTransform && layer.hasTransform() && layer.rasterizeToDocument) {
                    const rasterized = layer.rasterizeToDocument();
                    if (rasterized.bounds.width > 0 && rasterized.bounds.height > 0) {
                        const drawX = rasterized.bounds.x * scale;
                        const drawY = rasterized.bounds.y * scale;
                        const drawW = rasterized.bounds.width * scale;
                        const drawH = rasterized.bounds.height * scale;
                        ctx.drawImage(rasterized.canvas, drawX, drawY, drawW, drawH);
                    }
                } else if (layer.canvas) {
                    // Simple path for non-transformed layers
                    const offsetX = (layer.offsetX ?? 0) * scale;
                    const offsetY = (layer.offsetY ?? 0) * scale;
                    const layerWidth = layer.width * scale;
                    const layerHeight = layer.height * scale;
                    ctx.drawImage(layer.canvas, offsetX, offsetY, layerWidth, layerHeight);
                }
            }
            ctx.globalAlpha = 1;

            // Calculate viewport rectangle
            const renderer = app.renderer;

            // The viewport in document coordinates (use logical display dimensions)
            const viewportLeft = -renderer.panX / renderer.zoom;
            const viewportTop = -renderer.panY / renderer.zoom;
            const viewportWidth = renderer.displayWidth / renderer.zoom;
            const viewportHeight = renderer.displayHeight / renderer.zoom;

            // Convert to navigator coordinates
            const viewX = viewportLeft * scale;
            const viewY = viewportTop * scale;
            const viewW = viewportWidth * scale;
            const viewH = viewportHeight * scale;

            // Draw viewport rectangle
            ctx.strokeStyle = '#ff3333';
            ctx.lineWidth = 2;
            ctx.strokeRect(
                Math.max(0, viewX),
                Math.max(0, viewY),
                Math.min(viewW, canvas.width - Math.max(0, viewX)),
                Math.min(viewH, canvas.height - Math.max(0, viewY))
            );

            // Draw full rectangle outline if partially visible
            ctx.strokeStyle = 'rgba(255, 100, 100, 0.5)';
            ctx.lineWidth = 1;
            ctx.strokeRect(viewX, viewY, viewW, viewH);
        },

        /**
         * Update tablet navigator — delegates to unified updateNavigator()
         */
        updateTabletNavigator() {
            this.updateNavigator();
        },

        /**
         * Handle mouse down on navigator canvas
         * @param {MouseEvent} e - The mouse event
         */
        navigatorMouseDown(e) {
            this.navigatorDragging = true;
            this.navigatorPan(e);
        },

        /**
         * Handle mouse move on navigator canvas
         * @param {MouseEvent} e - The mouse event
         */
        navigatorMouseMove(e) {
            if (this.navigatorDragging) {
                this.navigatorPan(e);
            }
        },

        /**
         * Handle mouse up on navigator canvas
         */
        navigatorMouseUp() {
            this.navigatorDragging = false;
        },

        /**
         * Handle touch start on navigator canvas
         * @param {TouchEvent} e - The touch event
         */
        navigatorTouchStart(e) {
            if (e.touches.length === 1) {
                this.navigatorDragging = true;
                this.navigatorPanTouch(e.touches[0]);
            }
        },

        /**
         * Handle touch move on navigator canvas
         * @param {TouchEvent} e - The touch event
         */
        navigatorTouchMove(e) {
            if (this.navigatorDragging && e.touches.length === 1) {
                this.navigatorPanTouch(e.touches[0]);
            }
        },

        /**
         * Pan the viewport based on touch position on navigator
         * @param {Touch} touch - The touch object
         */
        navigatorPanTouch(touch) {
            const app = this.getState();
            if (!app?.renderer) return;

            // Try tablet navigator first, then desktop navigator
            const canvas = this.$refs.tabletNavigatorCanvas || this.$refs.navigatorCanvas;
            if (!canvas) return;

            const rect = canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;

            const docWidth = app.renderer.compositeCanvas?.width || this.docWidth;
            const docHeight = app.renderer.compositeCanvas?.height || this.docHeight;

            // Use actual displayed size for accurate coordinate mapping
            const docX = x / (rect.width / docWidth);
            const docY = y / (rect.height / docHeight);

            // Use logical display dimensions for viewport calculations
            const viewWidth = app.renderer.displayWidth / app.renderer.zoom;
            const viewHeight = app.renderer.displayHeight / app.renderer.zoom;

            app.renderer.panX = -(docX - viewWidth / 2) * app.renderer.zoom;
            app.renderer.panY = -(docY - viewHeight / 2) * app.renderer.zoom;
            app.renderer.requestRender();
            this.updateNavigator();
        },

        /**
         * Pan the viewport based on mouse position on navigator
         * @param {MouseEvent} e - The mouse event
         */
        navigatorPan(e) {
            const app = this.getState();
            if (!app?.renderer) return;

            const canvas = this.$refs.tabletNavigatorCanvas || this.$refs.navigatorCanvas;
            if (!canvas) return;

            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const docWidth = app.renderer.compositeCanvas?.width || this.docWidth;
            const docHeight = app.renderer.compositeCanvas?.height || this.docHeight;

            // Convert click position to document coordinates using actual displayed size
            const docX = x / (rect.width / docWidth);
            const docY = y / (rect.height / docHeight);

            // Use logical display dimensions for viewport calculations
            const viewWidth = app.renderer.displayWidth / app.renderer.zoom;
            const viewHeight = app.renderer.displayHeight / app.renderer.zoom;

            // Set pan so the click position becomes the center of the viewport
            app.renderer.panX = -(docX - viewWidth / 2) * app.renderer.zoom;
            app.renderer.panY = -(docY - viewHeight / 2) * app.renderer.zoom;
            app.renderer.requestRender();
            this.updateNavigator();
        },
    },
};

export default NavigatorManagerMixin;
