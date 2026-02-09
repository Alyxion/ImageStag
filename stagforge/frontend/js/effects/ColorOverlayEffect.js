/**
 * ColorOverlayEffect - Overlays a solid color on the layer content.
 *
 * Opacity is controlled by the base class `opacity` field (0.0-1.0).
 */
import { LayerEffect } from './LayerEffect.js';

export class ColorOverlayEffect extends LayerEffect {
    static type = 'colorOverlay';
    static displayName = 'Color Overlay';
    static VERSION = 2;

    constructor(options = {}) {
        super(options);
        this.color = options.color || '#FF0000';
        // Migrate legacy colorOpacity → base opacity
        if (options.colorOpacity != null && options.opacity == null) {
            this.opacity = options.colorOpacity;
        }
    }

    getExpansion() {
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    getParams() {
        return { color: this.color };
    }
}
