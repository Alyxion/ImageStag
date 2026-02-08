/**
 * Page - Represents a single page within a document.
 *
 * Each page has its own LayerStack. All pages in a document share
 * the same dimensions. Used for multi-page documents (e.g., PDF import).
 */
import { LayerStack } from './LayerStack.js';

export class Page {
    /**
     * @param {Object} options
     * @param {string} [options.id] - Unique identifier
     * @param {string} [options.name] - Display name
     * @param {number} options.width - Page width (matches document width)
     * @param {number} options.height - Page height (matches document height)
     * @param {number} [options.duration] - Page duration in seconds (0 = no animation)
     * @param {number} [options.framerate] - Default framerate for animated export (GIF, WebP)
     * @param {Object} [options.eventBus] - Event bus for layer stack events
     */
    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();
        this.name = options.name || 'Page 1';
        this.width = options.width;
        this.height = options.height;
        this.duration = options.duration ?? 0.0;
        this.framerate = options.framerate ?? 24;
        this.eventBus = options.eventBus;
        this._layerStack = null;
    }

    /**
     * Get or create the layer stack for this page.
     * @returns {LayerStack}
     */
    get layerStack() {
        if (!this._layerStack) {
            this._layerStack = new LayerStack(this.width, this.height, this.eventBus);
        }
        return this._layerStack;
    }

    /**
     * Dispose of page resources (clear all layer canvases).
     */
    dispose() {
        if (this._layerStack) {
            for (const layer of this._layerStack.layers) {
                if (layer.canvas) {
                    layer.canvas.width = 0;
                    layer.canvas.height = 0;
                }
            }
            this._layerStack.layers = [];
        }
    }
}
