/**
 * VectorizableLayer - Base class for layers that can represent their content as SVG.
 *
 * Extends DynamicLayer with:
 * - Abstract toSVG() method - all subclasses must produce valid SVG
 * - Common SVG rendering logic (blob URL, render to canvas)
 * - SVG-based pixel rendering via Chrome's native renderer
 *
 * Subclasses:
 * - VectorLayer - editable vector shapes
 * - SVGLayer - raw SVG content
 */
import { DynamicLayer } from './DynamicLayer.js';

export class VectorizableLayer extends DynamicLayer {
    /** Serialization version for migration support */
    static VERSION = 1;

    constructor(options = {}) {
        super(options);
        this.type = 'vectorizable';
    }

    // ==================== Type Checks ====================

    /**
     * Check if this layer can produce SVG output.
     * @returns {boolean}
     */
    isVectorizable() {
        return true;
    }

    // Note: isVector() is NOT overridden here. It returns false from DynamicLayer.
    // VectorLayer overrides it to return true (editable vector shapes).
    // SVGLayer keeps it false (raw SVG content, not editable shapes).

    // ==================== SVG Methods ====================

    /**
     * Convert layer content to SVG string. Must be implemented by subclasses.
     * @param {Object} [options]
     * @param {number} [options.scale] - Scale factor for output
     * @param {boolean} [options.antialiasing] - Enable anti-aliasing
     * @param {{x: number, y: number, width: number, height: number}} [options.bounds] - Render only this area
     * @returns {string} SVG document string
     * @abstract
     */
    toSVG(options = {}) {
        throw new Error('VectorizableLayer.toSVG() must be implemented by subclass');
    }

    /**
     * Get SVG content as a Blob.
     * @param {Object} [options] - Options passed to toSVG()
     * @returns {Blob}
     */
    toSVGBlob(options = {}) {
        const svg = this.toSVG(options);
        return new Blob([svg], { type: 'image/svg+xml' });
    }

    /**
     * Get SVG content as a data URL.
     * @param {Object} [options] - Options passed to toSVG()
     * @returns {string}
     */
    toSVGDataURL(options = {}) {
        const svg = this.toSVG(options);
        return 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
    }

    // ==================== Rendering ====================

    /**
     * Render SVG content to internal canvas using Chrome's native SVG renderer.
     * @param {string} svgContent - SVG string to render
     * @param {Object} [options]
     * @param {number} [options.scale] - Supersample scale (1-4)
     * @returns {Promise<void>}
     */
    async renderSVGToCanvas(svgContent, options = {}) {
        const scale = options.scale || 1;

        if (!svgContent) {
            this._ctx.clearRect(0, 0, this.width, this.height);
            return;
        }

        // Create blob from SVG content
        const blob = new Blob([svgContent], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        try {
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = url;
            });

            // Clear and draw
            this._ctx.clearRect(0, 0, this.width, this.height);
            this._ctx.imageSmoothingEnabled = true;
            this._ctx.imageSmoothingQuality = 'high';

            if (scale === 1) {
                // Direct draw
                this._ctx.drawImage(img, 0, 0, this.width, this.height);
            } else {
                // Supersample: render at higher resolution then downscale
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = this.width * scale;
                tempCanvas.height = this.height * scale;
                const tempCtx = tempCanvas.getContext('2d');
                tempCtx.imageSmoothingEnabled = true;
                tempCtx.imageSmoothingQuality = 'high';
                tempCtx.drawImage(img, 0, 0, tempCanvas.width, tempCanvas.height);

                // Downscale to final size
                this._ctx.drawImage(tempCanvas, 0, 0, this.width, this.height);
            }

            this.invalidateImageCache();
            this.invalidateEffectCache();
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Default render implementation using toSVG().
     * Subclasses can override for more efficient rendering.
     * @returns {Promise<void>}
     */
    async render() {
        const svg = this.toSVG();
        await this.renderSVGToCanvas(svg);
    }

    // ==================== Export Methods ====================

    /**
     * Export as PNG blob.
     * @param {Object} [options]
     * @param {number} [options.scale] - Scale factor
     * @returns {Promise<Blob>}
     */
    async toPNGBlob(options = {}) {
        await this.ensureRendered();
        return new Promise((resolve) => {
            this._canvas.toBlob(resolve, 'image/png');
        });
    }

    /**
     * Export as PNG data URL.
     * @returns {Promise<string>}
     */
    async toPNGDataURL() {
        await this.ensureRendered();
        return this._canvas.toDataURL('image/png');
    }

    // ==================== Utility ====================

    /**
     * Create an SVG document wrapper with proper headers.
     * @param {string} content - SVG element content (without <svg> wrapper)
     * @param {Object} [options]
     * @param {number} [options.width] - SVG width (defaults to layer width)
     * @param {number} [options.height] - SVG height (defaults to layer height)
     * @param {string} [options.viewBox] - Custom viewBox
     * @param {boolean} [options.antialiasing] - Enable anti-aliasing
     * @returns {string}
     */
    wrapSVG(content, options = {}) {
        const width = options.width || this.width;
        const height = options.height || this.height;
        const viewBox = options.viewBox || `0 0 ${width} ${height}`;
        const shapeRendering = options.antialiasing ? '' : ' shape-rendering="crispEdges"';

        return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="${width}" height="${height}"
     viewBox="${viewBox}"${shapeRendering}>
${content}
</svg>`;
    }
}

export default VectorizableLayer;
