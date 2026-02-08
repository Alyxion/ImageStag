/**
 * Frame classes for multi-frame layer support.
 *
 * Each layer type has a corresponding frame type:
 * - Frame: Base class with id, duration (seconds), delay (seconds) (used by BaseLayer, LayerGroup)
 * - PixelFrame: Canvas-based frame (used by PixelLayer)
 * - SVGFrame: SVG content frame (used by StaticSVGLayer)
 * - TextFrame: Rich text runs frame (used by TextLayer)
 */

export class Frame {
    /**
     * @param {Object} [options]
     * @param {string} [options.id] - Unique identifier
     * @param {number} [options.duration] - Frame duration in seconds
     * @param {number} [options.delay] - Delay before frame in seconds
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.duration = options.duration ?? 0.1;
        this.delay = options.delay ?? 0.0;
    }

    /**
     * Clone this frame (deep copy).
     * @returns {Frame}
     */
    clone() {
        return new Frame({ duration: this.duration, delay: this.delay });
    }

    /**
     * Dispose of frame resources.
     */
    dispose() {
        // No-op for base frame
    }
}

export class PixelFrame extends Frame {
    /**
     * @param {Object} [options]
     * @param {string} [options.id]
     * @param {number} [options.duration]
     * @param {number} [options.delay]
     * @param {HTMLCanvasElement} [options.canvas]
     * @param {CanvasRenderingContext2D} [options.ctx]
     */
    constructor(options = {}) {
        super(options);
        this.canvas = options.canvas || document.createElement('canvas');
        this.ctx = options.ctx || this.canvas.getContext('2d', { willReadFrequently: true });
    }

    /** @override */
    clone() {
        const canvas = document.createElement('canvas');
        canvas.width = this.canvas.width;
        canvas.height = this.canvas.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(this.canvas, 0, 0);
        return new PixelFrame({ canvas, ctx, duration: this.duration, delay: this.delay });
    }

    /** @override */
    dispose() {
        this.canvas.width = 0;
        this.canvas.height = 0;
    }
}

export class SVGFrame extends Frame {
    /**
     * @param {Object} [options]
     * @param {string} [options.id]
     * @param {number} [options.duration]
     * @param {number} [options.delay]
     * @param {string} [options.svgContent]
     */
    constructor(options = {}) {
        super(options);
        this.svgContent = options.svgContent || '';
    }

    /** @override */
    clone() {
        return new SVGFrame({ svgContent: this.svgContent, duration: this.duration, delay: this.delay });
    }
}

export class TextFrame extends Frame {
    /**
     * @param {Object} [options]
     * @param {string} [options.id]
     * @param {number} [options.duration]
     * @param {number} [options.delay]
     * @param {Array} [options.runs]
     */
    constructor(options = {}) {
        super(options);
        this.runs = options.runs ? options.runs.map(r => ({ ...r })) : [];
    }

    /** @override */
    clone() {
        return new TextFrame({
            runs: this.runs.map(r => ({ ...r })),
            duration: this.duration,
            delay: this.delay,
        });
    }
}
