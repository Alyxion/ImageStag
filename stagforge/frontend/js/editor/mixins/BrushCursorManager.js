/**
 * BrushCursorManager Mixin
 *
 * Handles brush preset thumbnails and cursor overlay rendering.
 *
 * Required component data:
 *   - brushPresetThumbnails: Object
 *   - brushPresetThumbnailsGenerated: Boolean
 *   - showBrushPresetMenu: Boolean
 *   - canvasCursor: String
 *   - showCursorOverlay: Boolean
 *   - cursorOverlaySize: Number
 *   - cursorOverlayX: Number
 *   - cursorOverlayY: Number
 *   - mouseOverCanvas: Boolean
 *   - toolProperties: Array
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateToolProperty(): Update a tool property
 */
export const BrushCursorManagerMixin = {
    methods: {
        /**
         * Generate thumbnails for all brush presets
         */
        generateBrushPresetThumbnails() {
            if (this.brushPresetThumbnailsGenerated) return;

            // Preset definitions (must match BrushPresets.js)
            const presets = [
                { id: 'hard-round-sm', size: 5, hardness: 100, opacity: 100, flow: 100 },
                { id: 'hard-round-md', size: 20, hardness: 100, opacity: 100, flow: 100 },
                { id: 'hard-round-lg', size: 50, hardness: 100, opacity: 100, flow: 100 },
                { id: 'soft-round-sm', size: 10, hardness: 0, opacity: 100, flow: 100 },
                { id: 'soft-round-md', size: 30, hardness: 0, opacity: 100, flow: 100 },
                { id: 'soft-round-lg', size: 60, hardness: 0, opacity: 100, flow: 100 },
                { id: 'airbrush', size: 40, hardness: 0, opacity: 50, flow: 30 },
                { id: 'pencil', size: 2, hardness: 100, opacity: 100, flow: 100 },
                { id: 'marker', size: 15, hardness: 80, opacity: 80, flow: 100 },
                { id: 'chalk', size: 25, hardness: 50, opacity: 70, flow: 60 },
            ];

            const newThumbnails = { ...this.brushPresetThumbnails };
            for (const preset of presets) {
                try {
                    newThumbnails[preset.id] = this.generatePresetThumbnail(preset);
                } catch (e) {
                    console.error('Error generating thumbnail for', preset.id, e);
                }
            }

            // Replace with new object to trigger Vue reactivity
            this.brushPresetThumbnails = newThumbnails;
            this.brushPresetThumbnailsGenerated = true;
        },

        /**
         * Generate a single preset thumbnail
         * @param {Object} preset - Preset configuration
         * @returns {string} Base64 data URL
         */
        generatePresetThumbnail(preset) {
            // Use 2x resolution for crisp rendering
            const width = 64;
            const height = 32;
            const scale = 2;

            const canvas = document.createElement('canvas');
            canvas.width = width * scale;
            canvas.height = height * scale;
            const ctx = canvas.getContext('2d');
            ctx.scale(scale, scale);

            // Enable high-quality rendering
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            // Dark background with subtle gradient
            const bgGrad = ctx.createLinearGradient(0, 0, width, height);
            bgGrad.addColorStop(0, '#1a1a1a');
            bgGrad.addColorStop(1, '#242424');
            ctx.fillStyle = bgGrad;
            ctx.fillRect(0, 0, width, height);

            // Calculate stroke width - scale down large brushes
            const maxStrokeWidth = 10;
            const minStrokeWidth = 1;
            const strokeWidth = Math.max(minStrokeWidth, Math.min(maxStrokeWidth, preset.size * 0.2));

            // Set up stroke style
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.lineWidth = strokeWidth;

            // Calculate alpha from opacity and flow
            const alpha = (preset.opacity / 100) * (preset.flow / 100);

            // Draw bezier curve using native canvas bezierCurveTo for smooth anti-aliased strokes
            ctx.beginPath();
            ctx.moveTo(6, height * 0.65);
            ctx.bezierCurveTo(
                width * 0.3, height * 0.15,   // control point 1
                width * 0.7, height * 0.85,   // control point 2
                width - 6, height * 0.35      // end point
            );

            // Apply hardness via blur/shadow or gradient stroke
            const hardness = preset.hardness / 100;

            if (hardness < 0.5) {
                // Soft brush - use shadow blur for soft edges
                const blur = (1 - hardness) * strokeWidth * 0.8;
                ctx.shadowColor = `rgba(255, 255, 255, ${alpha * 0.7})`;
                ctx.shadowBlur = blur;
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.5})`;
                ctx.stroke();

                // Draw core stroke
                ctx.shadowBlur = blur * 0.3;
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.8})`;
                ctx.lineWidth = strokeWidth * 0.6;
                ctx.stroke();
            } else {
                // Hard brush - solid stroke
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
                ctx.stroke();
            }

            // Reset shadow
            ctx.shadowBlur = 0;
            ctx.shadowColor = 'transparent';

            return canvas.toDataURL('image/png');
        },

        /**
         * Toggle brush preset menu visibility
         * @param {Event} event - Click event
         */
        toggleBrushPresetMenu(event) {
            if (event) {
                event.stopPropagation();
                event.preventDefault();
            }
            if (!this.brushPresetThumbnailsGenerated) {
                this.generateBrushPresetThumbnails();
            }
            this.showBrushPresetMenu = !this.showBrushPresetMenu;
        },

        /**
         * Select a brush preset
         * @param {string} presetId - Preset identifier
         */
        selectBrushPreset(presetId) {
            this.updateToolProperty('preset', presetId);
            this.showBrushPresetMenu = false;
        },

        /**
         * Update the brush cursor based on current tool
         */
        updateBrushCursor() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;

            if (!tool) {
                this.canvasCursor = 'default';
                this.showCursorOverlay = false;
                return;
            }

            // Tools that should show a size-based circular cursor overlay
            const toolCursor = tool.constructor.cursor;
            const hasSize = typeof tool.size === 'number';

            // If the tool has its own drawOverlay(), it renders its own cursor
            // on the display canvas via Renderer.drawToolOverlay(). Don't show
            // the HTML overlay too — that would create a duplicate cursor.
            const toolDrawsOwnOverlay = typeof tool.drawOverlay === 'function';

            if (toolCursor === 'none' && hasSize && !toolDrawsOwnOverlay) {
                const size = tool.size || 20;
                const zoom = app?.renderer?.zoom || 1;
                const scaledSize = Math.max(4, size * zoom);

                // Always use overlay cursor
                this.canvasCursor = 'none';
                this.cursorOverlaySize = Math.ceil(scaledSize) + 4;
                this.drawCursorOverlay(scaledSize);

                // Only show overlay if mouse is over canvas
                this.showCursorOverlay = this.mouseOverCanvas;
            } else if (toolCursor === 'none') {
                // Tool draws its own overlay cursor — hide CSS cursor but no HTML overlay
                this.canvasCursor = 'none';
                this.showCursorOverlay = false;
            } else {
                // Use the tool's default cursor
                this.showCursorOverlay = false;
                this.canvasCursor = toolCursor || 'crosshair';
            }
        },

        /**
         * Draw the brush cursor on the overlay canvas
         * @param {number} scaledSize - Scaled brush size
         */
        drawCursorOverlay(scaledSize) {
            this.$nextTick(() => {
                const canvas = this.$refs.cursorOverlay;
                if (!canvas) return;

                const canvasSize = Math.ceil(scaledSize) + 4;
                canvas.width = canvasSize;
                canvas.height = canvasSize;

                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvasSize, canvasSize);

                const center = canvasSize / 2;
                const radius = scaledSize / 2;

                // Draw outer circle (dark outline)
                ctx.beginPath();
                ctx.arc(center, center, radius, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)';
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Draw inner circle (light outline)
                ctx.beginPath();
                ctx.arc(center, center, radius - 1, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.lineWidth = 1;
                ctx.stroke();

                // Draw center crosshair
                const crossSize = Math.min(8, scaledSize / 4);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(center - crossSize, center);
                ctx.lineTo(center + crossSize, center);
                ctx.moveTo(center, center - crossSize);
                ctx.lineTo(center, center + crossSize);
                ctx.stroke();

                ctx.strokeStyle = 'rgba(0, 0, 0, 0.9)';
                ctx.lineWidth = 0.5;
                ctx.stroke();
            });
        },

        /**
         * Update cursor overlay position
         * @param {number} clientX - Client X coordinate
         * @param {number} clientY - Client Y coordinate
         */
        updateCursorOverlayPosition(clientX, clientY) {
            const canvas = this.$refs.mainCanvas;
            if (!canvas) return;

            const rect = canvas.getBoundingClientRect();
            this.cursorOverlayX = clientX - rect.left;
            this.cursorOverlayY = clientY - rect.top;
        },

        /**
         * Get the display label for a preset
         * @param {string} presetId - Preset identifier
         * @returns {string} Display label
         */
        getPresetLabel(presetId) {
            const preset = this.toolProperties.find(p => p.id === 'preset');
            if (preset) {
                const opt = preset.options.find(o => o.value === presetId);
                return opt ? opt.label : presetId;
            }
            return presetId;
        },
    },
};

export default BrushCursorManagerMixin;
