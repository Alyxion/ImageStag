/**
 * NavigatorManager Mixin
 *
 * Handles the navigator panel: preview rendering, pan interactions,
 * and throttled updates during drawing operations.
 *
 * Required component data:
 *   - showNavigator: Boolean
 *   - tabletNavPanelOpen: Boolean
 *   - currentUIMode: String
 *   - docWidth: Number
 *   - docHeight: Number
 *   - navigatorDragging: Boolean
 *   - lastNavigatorUpdate: Number
 *   - navigatorUpdatePending: Boolean
 *
 * Required component refs:
 *   - navigatorCanvas: HTMLCanvasElement (desktop)
 *   - tabletNavigatorCanvas: HTMLCanvasElement (tablet)
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 */
export const NavigatorManagerMixin = {
    methods: {
        /**
         * Throttled navigator update - updates at most every 100ms during continuous operations.
         * This provides live feedback without overwhelming the browser.
         */
        throttledNavigatorUpdate() {
            const now = Date.now();
            const minInterval = 100; // Update at most every 100ms during drawing

            if (now - this.lastNavigatorUpdate > minInterval) {
                this.updateNavigator();
                this.lastNavigatorUpdate = now;
                this.navigatorUpdatePending = false;
            } else if (!this.navigatorUpdatePending) {
                this.navigatorUpdatePending = true;
                setTimeout(() => {
                    if (this.navigatorUpdatePending) {
                        this.updateNavigator();
                        this.lastNavigatorUpdate = Date.now();
                        this.navigatorUpdatePending = false;
                    }
                }, minInterval - (now - this.lastNavigatorUpdate));
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
            for (const layer of app.layerStack.layers) {
                // Skip groups - they have no canvas
                if (layer.isGroup && layer.isGroup()) continue;
                // Use effective visibility (considers parent groups)
                if (!app.layerStack.isEffectivelyVisible(layer)) continue;
                ctx.globalAlpha = app.layerStack.getEffectiveOpacity(layer);
                const offsetX = (layer.offsetX ?? 0) * scale;
                const offsetY = (layer.offsetY ?? 0) * scale;
                const layerWidth = layer.width * scale;
                const layerHeight = layer.height * scale;
                if (layer.canvas) {
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
         * Update tablet navigator (separate implementation)
         */
        updateTabletNavigator() {
            const app = this.getState();
            if (!app?.renderer || !app?.layerStack) return;

            const canvas = this.$refs.tabletNavigatorCanvas;
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const maxSize = 240;

            // Calculate scale to fit navigator
            const docWidth = app.renderer.compositeCanvas?.width || this.docWidth;
            const docHeight = app.renderer.compositeCanvas?.height || this.docHeight;
            const scale = Math.min(maxSize / docWidth, maxSize / docHeight);

            canvas.width = Math.round(docWidth * scale);
            canvas.height = Math.round(docHeight * scale);

            // Draw document preview
            ctx.drawImage(app.renderer.compositeCanvas, 0, 0, canvas.width, canvas.height);

            // Draw viewport rectangle using logical display dimensions
            const viewLeft = -app.renderer.panX / app.renderer.zoom;
            const viewTop = -app.renderer.panY / app.renderer.zoom;
            const viewWidth = app.renderer.displayWidth / app.renderer.zoom;
            const viewHeight = app.renderer.displayHeight / app.renderer.zoom;

            ctx.strokeStyle = '#ff3333';
            ctx.lineWidth = 2;
            ctx.strokeRect(
                viewLeft * scale,
                viewTop * scale,
                viewWidth * scale,
                viewHeight * scale
            );
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
            const maxSize = 200;
            const scale = Math.min(maxSize / docWidth, maxSize / docHeight);

            const docX = x / scale;
            const docY = y / scale;

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
            if (!app?.renderer || !this.$refs.navigatorCanvas) return;

            const canvas = this.$refs.navigatorCanvas;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const docWidth = app.renderer.compositeCanvas?.width || this.docWidth;
            const docHeight = app.renderer.compositeCanvas?.height || this.docHeight;
            const maxSize = 180;
            const scale = Math.min(maxSize / docWidth, maxSize / docHeight);

            // Convert click position to document coordinates
            const docX = x / scale;
            const docY = y / scale;

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
