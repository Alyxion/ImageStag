/**
 * ColorOverlayEffect - Overlays a solid color on the layer content.
 */
import { LayerEffect } from './LayerEffect.js';

export class ColorOverlayEffect extends LayerEffect {
    static type = 'colorOverlay';
    static displayName = 'Color Overlay';
    static VERSION = 1;

    constructor(options = {}) {
        super(options);
        this.color = options.color || '#FF0000';
    }

    getExpansion() {
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    getParams() {
        return { color: this.color };
    }
}
