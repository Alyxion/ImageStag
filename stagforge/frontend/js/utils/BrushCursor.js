/**
 * BrushCursor - Shared cursor overlay for size-based tools.
 *
 * Displays a circle showing the brush/tool size at the cursor position.
 * Used by Brush, Eraser, Blur, Sharpen, Smudge, Dodge, Burn, Sponge, CloneStamp, etc.
 */
export class BrushCursor {
    /**
     * @param {Object} options
     * @param {string} [options.color='#FFFFFF'] - Cursor circle color
     * @param {string} [options.secondaryColor='#000000'] - Secondary color for contrast
     * @param {boolean} [options.showCrosshair=false] - Show crosshair at center
     */
    constructor(options = {}) {
        this.color = options.color || '#FFFFFF';
        this.secondaryColor = options.secondaryColor || '#000000';
        this.showCrosshair = options.showCrosshair || false;

        // Current state
        this.x = 0;
        this.y = 0;
        this.size = 10;
        this.visible = true;
    }

    /**
     * Update cursor position and size.
     * @param {number} x - Document X coordinate
     * @param {number} y - Document Y coordinate
     * @param {number} size - Brush/tool diameter
     */
    update(x, y, size) {
        this.x = x;
        this.y = y;
        this.size = size;
    }

    /**
     * Draw the cursor overlay.
     * Called by Renderer after compositing layers.
     *
     * @param {CanvasRenderingContext2D} ctx - The display canvas context
     * @param {Function} docToScreen - Function to convert doc coords to screen coords
     * @param {number} zoom - Current zoom level
     */
    draw(ctx, docToScreen, zoom) {
        if (!this.visible) return;

        const screen = docToScreen(this.x, this.y);
        const x = screen.x;
        const y = screen.y;
        const radius = (this.size / 2) * zoom;

        ctx.save();

        // Draw outer circle (dark for contrast)
        ctx.strokeStyle = this.secondaryColor;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.stroke();

        // Draw inner circle (light)
        ctx.strokeStyle = this.color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.stroke();

        // Optional crosshair at center
        if (this.showCrosshair) {
            const crossSize = Math.min(6, radius * 0.5);
            ctx.strokeStyle = this.color;
            ctx.lineWidth = 1;
            ctx.beginPath();
            // Horizontal
            ctx.moveTo(x - crossSize, y);
            ctx.lineTo(x + crossSize, y);
            // Vertical
            ctx.moveTo(x, y - crossSize);
            ctx.lineTo(x, y + crossSize);
            ctx.stroke();
        }

        ctx.restore();
    }

    /**
     * Set cursor visibility.
     * @param {boolean} visible
     */
    setVisible(visible) {
        this.visible = visible;
    }
}
