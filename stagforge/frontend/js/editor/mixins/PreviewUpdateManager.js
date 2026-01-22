/**
 * PreviewUpdateManager Mixin
 *
 * Manages debounced updates for layer thumbnails and navigator preview.
 * Provides consistent, race-condition-free updates with configurable timing.
 *
 * Key features:
 * - Single timer for all preview updates (no race conditions)
 * - Dirty tracking: only redraws changed layers
 * - Configurable refresh interval
 * - 5 changes in 1 second = same render cost as 1 change
 *
 * Required component data:
 *   - previewUpdateInterval: Number (ms, default 250)
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateNavigator(): Renders navigator preview
 */
export const PreviewUpdateManagerMixin = {
    data() {
        return {
            // Configurable refresh interval in milliseconds
            // Lower = more responsive, higher = better performance
            previewUpdateInterval: 250,

            // Internal state (not reactive to avoid overhead)
            _previewUpdatePending: false,
            _previewUpdateTimer: null,
            _dirtyLayers: new Set(),
            _navigatorDirty: false,
            _lastPreviewUpdate: 0,
        };
    },

    methods: {
        /**
         * Mark a layer as dirty (needs thumbnail update).
         * Call this when a layer's content changes.
         * @param {string|null} layerId - Layer ID, or null/undefined to mark all layers
         */
        markLayerDirty(layerId = null) {
            if (layerId) {
                this._dirtyLayers.add(layerId);
            } else {
                // Mark all layers dirty
                const app = this.getState();
                if (app?.layerStack) {
                    for (const layer of app.layerStack.layers) {
                        this._dirtyLayers.add(layer.id);
                    }
                }
            }
            this._schedulePreviewUpdate();
        },

        /**
         * Mark navigator as needing update.
         * Call this when viewport changes or layers are modified.
         */
        markNavigatorDirty() {
            this._navigatorDirty = true;
            this._schedulePreviewUpdate();
        },

        /**
         * Mark both thumbnails and navigator as dirty.
         * Convenience method for layer content changes.
         * @param {string|null} layerId - Layer ID, or null for all
         */
        markPreviewsDirty(layerId = null) {
            this.markLayerDirty(layerId);
            this.markNavigatorDirty();
        },

        /**
         * Schedule a preview update.
         * Uses debouncing: multiple calls within the interval = single update.
         * @private
         */
        _schedulePreviewUpdate() {
            // Already scheduled - nothing to do
            if (this._previewUpdatePending) {
                return;
            }

            const now = Date.now();
            const timeSinceLastUpdate = now - this._lastPreviewUpdate;

            if (timeSinceLastUpdate >= this.previewUpdateInterval) {
                // Enough time has passed - update immediately
                this._executePreviewUpdate();
            } else {
                // Schedule for later
                this._previewUpdatePending = true;
                const delay = this.previewUpdateInterval - timeSinceLastUpdate;

                // Clear any existing timer (shouldn't happen, but be safe)
                if (this._previewUpdateTimer) {
                    clearTimeout(this._previewUpdateTimer);
                }

                this._previewUpdateTimer = setTimeout(() => {
                    this._previewUpdateTimer = null;
                    this._executePreviewUpdate();
                }, delay);
            }
        },

        /**
         * Execute the actual preview update.
         * Updates only dirty thumbnails and navigator if needed.
         * @private
         */
        _executePreviewUpdate() {
            this._previewUpdatePending = false;
            this._lastPreviewUpdate = Date.now();

            // Update dirty layer thumbnails
            if (this._dirtyLayers.size > 0) {
                this._updateDirtyThumbnails();
                this._dirtyLayers.clear();
            }

            // Update navigator if dirty
            if (this._navigatorDirty) {
                this._navigatorDirty = false;
                // Use the existing updateNavigator method
                if (typeof this.updateNavigator === 'function') {
                    this.updateNavigator();
                }
            }
        },

        /**
         * Update only the thumbnails for dirty layers.
         * @private
         */
        _updateDirtyThumbnails() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const thumbSize = 40;

            for (const layerId of this._dirtyLayers) {
                const layer = app.layerStack.getLayerById(layerId);
                if (!layer) continue;

                const refKey = 'layerThumb_' + layer.id;
                const thumbCanvas = this.$refs[refKey];
                if (!thumbCanvas || !thumbCanvas[0]) continue;

                const canvas = thumbCanvas[0];
                const ctx = canvas.getContext('2d');

                // Draw transparency grid background
                const gridSize = 5;
                for (let y = 0; y < thumbSize; y += gridSize) {
                    for (let x = 0; x < thumbSize; x += gridSize) {
                        const isLight = ((x / gridSize) + (y / gridSize)) % 2 === 0;
                        ctx.fillStyle = isLight ? '#ffffff' : '#cccccc';
                        ctx.fillRect(x, y, gridSize, gridSize);
                    }
                }

                // Calculate scaling to fit layer in thumbnail
                const layerWidth = layer.width || layer.canvas?.width || thumbSize;
                const layerHeight = layer.height || layer.canvas?.height || thumbSize;
                const scale = Math.min(thumbSize / layerWidth, thumbSize / layerHeight);
                const scaledWidth = layerWidth * scale;
                const scaledHeight = layerHeight * scale;
                const offsetX = (thumbSize - scaledWidth) / 2;
                const offsetY = (thumbSize - scaledHeight) / 2;

                // Draw layer content
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                if (layer.canvas) {
                    ctx.drawImage(layer.canvas, offsetX, offsetY, scaledWidth, scaledHeight);
                }
            }
        },

        /**
         * Force immediate update of all thumbnails.
         * Use sparingly - prefer markLayerDirty() for normal operations.
         */
        forceUpdateAllThumbnails() {
            const app = this.getState();
            if (app?.layerStack) {
                for (const layer of app.layerStack.layers) {
                    this._dirtyLayers.add(layer.id);
                }
            }
            this._updateDirtyThumbnails();
            this._dirtyLayers.clear();
        },

        /**
         * Force immediate update of navigator.
         * Use sparingly - prefer markNavigatorDirty() for normal operations.
         */
        forceUpdateNavigator() {
            this._navigatorDirty = false;
            if (typeof this.updateNavigator === 'function') {
                this.updateNavigator();
            }
        },

        /**
         * Set the preview update interval.
         * @param {number} ms - Interval in milliseconds (min: 50, max: 5000)
         */
        setPreviewUpdateInterval(ms) {
            this.previewUpdateInterval = Math.max(50, Math.min(5000, ms));
        },

        /**
         * Clean up timers on unmount.
         */
        _cleanupPreviewUpdateManager() {
            if (this._previewUpdateTimer) {
                clearTimeout(this._previewUpdateTimer);
                this._previewUpdateTimer = null;
            }
            this._dirtyLayers.clear();
        },
    },

    beforeUnmount() {
        this._cleanupPreviewUpdateManager();
    },
};

export default PreviewUpdateManagerMixin;
