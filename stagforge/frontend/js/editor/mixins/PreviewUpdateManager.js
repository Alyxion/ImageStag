/**
 * PreviewUpdateManager Mixin
 *
 * Polls layer render versions at a fixed interval to detect changes
 * and update thumbnails/navigator. Fully decoupled from data mutations —
 * no caller needs to invoke markPreviewsDirty().
 *
 * Key features:
 * - Poll-based: checks changeCounter on each layer every 250ms
 * - Coalesces rapid changes: 100 brush stamps = 1 thumbnail update
 * - No coupling: data mutations only bump version counters
 * - Configurable refresh interval
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
            _lastSeenVersions: new Map(),   // layerId → changeCounter
            _lastStructureVersion: -1,
            _pollTimer: null,
            _dirtyLayers: new Set(),        // Retained for _updateDirtyThumbnails
        };
    },

    methods: {
        /**
         * Start polling for layer version changes.
         * Call when a document is activated.
         */
        startPreviewPolling() {
            if (this._pollTimer) return;
            this._pollTimer = setInterval(() => this._checkForUpdates(), this.previewUpdateInterval);
        },

        /**
         * Stop polling.
         * Call when a document is deactivated or component unmounts.
         */
        stopPreviewPolling() {
            if (this._pollTimer) {
                clearInterval(this._pollTimer);
                this._pollTimer = null;
            }
        },

        /**
         * Check all layers for version changes and update dirty previews.
         * @private
         */
        _checkForUpdates() {
            const app = this.getState();
            const layerStack = app?.layerStack;
            if (!layerStack) return;

            let navigatorDirty = false;
            const dirtyLayerIds = [];

            // Check structure version
            const structVersion = layerStack._structureVersion || 0;
            if (structVersion !== this._lastStructureVersion) {
                this._lastStructureVersion = structVersion;
                navigatorDirty = true;
            }

            // Check each layer's render version
            const allLayers = layerStack.layers;
            for (let i = 0; i < allLayers.length; i++) {
                const layer = allLayers[i];
                const lastSeen = this._lastSeenVersions.get(layer.id) ?? -1;
                const current = layer.changeCounter || 0;
                if (current !== lastSeen) {
                    dirtyLayerIds.push(layer.id);
                    this._lastSeenVersions.set(layer.id, current);
                    navigatorDirty = true;
                }
            }

            // Clean up stale entries on structure changes
            if (structVersion !== this._lastStructureVersion || dirtyLayerIds.length > 0) {
                const currentIds = new Set(allLayers.map(l => l.id));
                for (const id of this._lastSeenVersions.keys()) {
                    if (!currentIds.has(id)) this._lastSeenVersions.delete(id);
                }
            }

            // Update dirty thumbnails
            if (dirtyLayerIds.length > 0) {
                for (const id of dirtyLayerIds) this._dirtyLayers.add(id);
                this._updateDirtyThumbnails();
                this._dirtyLayers.clear();
            }

            // Update navigator
            if (navigatorDirty) {
                if (typeof this.updateNavigator === 'function') {
                    this.updateNavigator();
                }
            }
        },

        /**
         * No-op stub for backward compatibility.
         * Callers that previously pushed dirty flags can still call this safely.
         * @param {string|null} layerId - Ignored
         */
        markLayerDirty(layerId = null) {
            // No-op: polling detects changes via changeCounter
        },

        /**
         * No-op stub for backward compatibility.
         */
        markNavigatorDirty() {
            // No-op: polling detects changes via changeCounter/_structureVersion
        },

        /**
         * No-op stub for backward compatibility.
         * @param {string|null} layerId - Ignored
         */
        markPreviewsDirty(layerId = null) {
            // No-op: polling detects changes via changeCounter/_structureVersion
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

                // Draw layer content using renderThumbnail (handles transforms)
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';

                if (layer.renderThumbnail) {
                    // Use renderThumbnail which handles rotation/scale transforms
                    const thumb = layer.renderThumbnail(thumbSize, thumbSize);
                    ctx.drawImage(thumb.canvas, 0, 0);
                } else if (layer.canvas) {
                    // Fallback for layers without renderThumbnail (groups, etc.)
                    const layerWidth = layer.width || layer.canvas?.width || thumbSize;
                    const layerHeight = layer.height || layer.canvas?.height || thumbSize;
                    const scale = Math.min(thumbSize / layerWidth, thumbSize / layerHeight);
                    const scaledWidth = layerWidth * scale;
                    const scaledHeight = layerHeight * scale;
                    const offsetX = (thumbSize - scaledWidth) / 2;
                    const offsetY = (thumbSize - scaledHeight) / 2;
                    ctx.drawImage(layer.canvas, offsetX, offsetY, scaledWidth, scaledHeight);
                }
            }
        },

        /**
         * Force immediate update of all thumbnails.
         * Use sparingly - prefer version-based polling for normal operations.
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
         * Use sparingly - prefer version-based polling for normal operations.
         */
        forceUpdateNavigator() {
            if (typeof this.updateNavigator === 'function') {
                this.updateNavigator();
            }
        },

        /**
         * Set the preview update interval.
         * Restarts polling if active.
         * @param {number} ms - Interval in milliseconds (min: 50, max: 5000)
         */
        setPreviewUpdateInterval(ms) {
            this.previewUpdateInterval = Math.max(50, Math.min(5000, ms));
            if (this._pollTimer) {
                this.stopPreviewPolling();
                this.startPreviewPolling();
            }
        },

        /**
         * Clean up timers on unmount.
         */
        _cleanupPreviewUpdateManager() {
            this.stopPreviewPolling();
            this._dirtyLayers.clear();
            this._lastSeenVersions.clear();
        },
    },

    beforeUnmount() {
        this._cleanupPreviewUpdateManager();
    },
};

export default PreviewUpdateManagerMixin;
