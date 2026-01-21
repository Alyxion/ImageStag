/**
 * ZoomManager Mixin
 *
 * Handles zoom controls: zoom in, zoom out, fit to window,
 * zoom percent input, and related view operations.
 *
 * Required component data:
 *   - zoom: Number
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateNavigator(): Refreshes the navigator panel
 */
export const ZoomManagerMixin = {
    methods: {
        /**
         * Zoom in by 25% at the center of the viewport
         */
        zoomIn() {
            const app = this.getState();
            if (!app?.renderer) return;
            // Use logical display dimensions for center point
            const centerX = app.renderer.displayWidth / 2;
            const centerY = app.renderer.displayHeight / 2;
            app.renderer.zoomAt(1.25, centerX, centerY);
            this.zoom = app.renderer.zoom;
            this.updateNavigator();
        },

        /**
         * Zoom out by 20% at the center of the viewport
         */
        zoomOut() {
            const app = this.getState();
            if (!app?.renderer) return;
            // Use logical display dimensions for center point
            const centerX = app.renderer.displayWidth / 2;
            const centerY = app.renderer.displayHeight / 2;
            app.renderer.zoomAt(0.8, centerX, centerY);
            this.zoom = app.renderer.zoom;
            this.updateNavigator();
        },

        /**
         * Fit the document to the window (fit entire document in view)
         */
        fitToWindow() {
            const app = this.getState();
            if (!app?.renderer) return;

            // Get document dimensions
            const docWidth = app.canvasWidth || app.layerStack?.width || 800;
            const docHeight = app.canvasHeight || app.layerStack?.height || 600;

            // Get display dimensions
            const displayWidth = app.renderer.displayWidth;
            const displayHeight = app.renderer.displayHeight;

            // Add padding (5% on each side)
            const padding = 0.9;

            // Calculate zoom to fit both dimensions
            const zoomX = (displayWidth * padding) / docWidth;
            const zoomY = (displayHeight * padding) / docHeight;
            const newZoom = Math.min(zoomX, zoomY);

            // Clamp zoom
            app.renderer.zoom = Math.max(0.1, Math.min(10, newZoom));

            // Center the document
            app.renderer.panX = (displayWidth - docWidth * app.renderer.zoom) / 2;
            app.renderer.panY = (displayHeight - docHeight * app.renderer.zoom) / 2;

            app.renderer.requestRender();
            this.zoom = app.renderer.zoom;
            this.updateNavigator();
        },

        /**
         * Set zoom to a specific percentage
         * @param {number} percent - Zoom percentage (e.g., 100 for 100%)
         */
        setZoomPercent(percent) {
            const app = this.getState();
            if (!app?.renderer) return;

            // Validate and clamp
            let zoom = parseFloat(percent);
            if (isNaN(zoom)) zoom = 100;
            zoom = Math.max(1, Math.min(6400, zoom));

            // Zoom at center of viewport
            const centerX = app.renderer.displayWidth / 2;
            const centerY = app.renderer.displayHeight / 2;

            // Calculate zoom factor relative to current zoom
            const factor = (zoom / 100) / app.renderer.zoom;
            app.renderer.zoomAt(factor, centerX, centerY);

            this.zoom = app.renderer.zoom;
            this.updateNavigator();
        },

        /**
         * Fit document to view (alias for fitToWindow)
         */
        fitToView() {
            this.fitToWindow();
        },

        /**
         * Set zoom to actual size (100%)
         */
        zoomActual() {
            this.setZoomPercent(100);
        },

        /**
         * Set zoom to 50%
         */
        zoomHalf() {
            this.setZoomPercent(50);
        },

        /**
         * Set zoom to 200%
         */
        zoomDouble() {
            this.setZoomPercent(200);
        },
    },
};

export default ZoomManagerMixin;
