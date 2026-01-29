/**
 * SelectionMask utilities for fill operations.
 *
 * Provides functions to apply selection masks to canvases,
 * used by fill tools (gradient, bucket, pattern fill).
 *
 * All functions use the mask's alpha value (0-255) for smooth blending,
 * supporting soft/feathered selection edges.
 */

/**
 * Apply selection mask to a canvas using alpha blending.
 * Modifies the canvas in place. Uses mask alpha for smooth transitions.
 *
 * @param {HTMLCanvasElement} canvas - Canvas to mask
 * @param {SelectionManager} selectionManager - Selection manager with mask
 * @param {number} offsetX - Canvas offset in document coordinates (default 0)
 * @param {number} offsetY - Canvas offset in document coordinates (default 0)
 */
export function applySelectionMask(canvas, selectionManager, offsetX = 0, offsetY = 0) {
    if (!selectionManager?.hasSelection || !selectionManager.mask) {
        return; // No selection, nothing to mask
    }

    const ctx = canvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
            const docX = x + offsetX;
            const docY = y + offsetY;
            const maskAlpha = selectionManager.getMaskAt(docX, docY);

            const idx = (y * canvas.width + x) * 4;

            // Multiply canvas alpha by mask alpha (0-255 normalized)
            // This creates smooth transitions at feathered edges
            data[idx + 3] = Math.round(data[idx + 3] * maskAlpha / 255);
        }
    }

    ctx.putImageData(imageData, 0, 0);
}

/**
 * Create a clipping path from selection contours.
 * Use this for Canvas 2D clipping operations.
 *
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {SelectionManager} selectionManager - Selection manager
 * @param {number} offsetX - Offset for layer-local coordinates
 * @param {number} offsetY - Offset for layer-local coordinates
 * @returns {boolean} True if clip was applied, false if no selection
 */
export function clipToSelection(ctx, selectionManager, offsetX = 0, offsetY = 0) {
    if (!selectionManager?.hasSelection) {
        return false;
    }

    const outlines = selectionManager.getOutlinePolygons();
    if (!outlines || outlines.length === 0) {
        // Fall back to rectangular bounds
        const bounds = selectionManager.getBounds();
        if (bounds) {
            ctx.beginPath();
            ctx.rect(
                bounds.x - offsetX,
                bounds.y - offsetY,
                bounds.width,
                bounds.height
            );
            ctx.clip();
            return true;
        }
        return false;
    }

    ctx.beginPath();
    for (const outline of outlines) {
        if (outline.length < 3) continue;

        ctx.moveTo(outline[0][0] - offsetX, outline[0][1] - offsetY);
        for (let i = 1; i < outline.length; i++) {
            ctx.lineTo(outline[i][0] - offsetX, outline[i][1] - offsetY);
        }
        ctx.closePath();
    }
    ctx.clip('evenodd');
    return true;
}

/**
 * Fill a canvas region with a solid color, respecting selection mask.
 *
 * @param {CanvasRenderingContext2D} ctx - Canvas context to fill
 * @param {string} color - Fill color (hex)
 * @param {SelectionManager} selectionManager - Selection manager (optional)
 * @param {number} offsetX - Canvas offset in document coords
 * @param {number} offsetY - Canvas offset in document coords
 */
export function fillWithMask(ctx, color, selectionManager, offsetX = 0, offsetY = 0) {
    const canvas = ctx.canvas;

    if (!selectionManager?.hasSelection) {
        // No selection - fill entire canvas
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        return;
    }

    // Parse color
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);

    const bounds = selectionManager.getBounds();
    if (!bounds) return;

    // Get the region that overlaps with canvas
    const localLeft = Math.max(0, bounds.x - offsetX);
    const localTop = Math.max(0, bounds.y - offsetY);
    const localRight = Math.min(canvas.width, bounds.x + bounds.width - offsetX);
    const localBottom = Math.min(canvas.height, bounds.y + bounds.height - offsetY);

    if (localRight <= localLeft || localBottom <= localTop) {
        return; // No overlap
    }

    const width = localRight - localLeft;
    const height = localBottom - localTop;
    const imageData = ctx.getImageData(localLeft, localTop, width, height);
    const data = imageData.data;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const docX = localLeft + offsetX + x;
            const docY = localTop + offsetY + y;
            const maskValue = selectionManager.getMaskAt(docX, docY);

            if (maskValue > 0) {
                const idx = (y * width + x) * 4;
                const alpha = maskValue / 255;

                // Blend with existing pixel based on mask alpha
                data[idx] = Math.round(r * alpha + data[idx] * (1 - alpha));
                data[idx + 1] = Math.round(g * alpha + data[idx + 1] * (1 - alpha));
                data[idx + 2] = Math.round(b * alpha + data[idx + 2] * (1 - alpha));
                data[idx + 3] = Math.max(data[idx + 3], maskValue);
            }
        }
    }

    ctx.putImageData(imageData, localLeft, localTop);
}

/**
 * Draw a gradient to a canvas, respecting selection mask.
 *
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {CanvasGradient} gradient - The gradient to fill with
 * @param {number} opacity - Opacity 0-100
 * @param {SelectionManager} selectionManager - Selection manager (optional)
 * @param {number} offsetX - Canvas offset in document coords
 * @param {number} offsetY - Canvas offset in document coords
 */
export function fillGradientWithMask(ctx, gradient, opacity, selectionManager, offsetX = 0, offsetY = 0) {
    const canvas = ctx.canvas;

    // First draw the gradient to the full canvas
    ctx.save();
    ctx.globalAlpha = opacity / 100;
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalAlpha = 1.0;
    ctx.restore();

    // Then apply the selection mask
    if (selectionManager?.hasSelection) {
        applySelectionMask(canvas, selectionManager, offsetX, offsetY);
    }
}

export default {
    applySelectionMask,
    clipToSelection,
    fillWithMask,
    fillGradientWithMask
};
