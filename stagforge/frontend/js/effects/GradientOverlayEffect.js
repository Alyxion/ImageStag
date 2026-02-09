/**
 * GradientOverlayEffect - Overlays a gradient on the layer content.
 *
 * Supports 5 gradient styles: linear, radial, angle, reflected, diamond.
 * Multi-stop gradients with separate Scale X/Y and Offset X/Y controls.
 * Opacity is controlled by the base class `opacity` field (0.0-1.0).
 */
import { LayerEffect } from './LayerEffect.js';

export class GradientOverlayEffect extends LayerEffect {
    static type = 'gradientOverlay';
    static displayName = 'Gradient Overlay';
    static VERSION = 2;

    constructor(options = {}) {
        super(options);
        this.gradient = options.gradient || [
            { position: 0.0, color: '#000000' },
            { position: 1.0, color: '#FFFFFF' }
        ];
        this.style = options.style || 'linear';
        this.angle = options.angle ?? 90;
        this.scaleX = options.scaleX ?? 100;
        this.scaleY = options.scaleY ?? 100;
        this.offsetX = options.offsetX ?? 0;
        this.offsetY = options.offsetY ?? 0;
        this.reverse = options.reverse ?? false;
        // Migrate legacy fillOpacity → base opacity
        if (options.fillOpacity != null && options.opacity == null) {
            this.opacity = options.fillOpacity;
        }
    }

    getExpansion() {
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    getParams() {
        return {
            gradient: this.gradient,
            style: this.style,
            angle: this.angle,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            reverse: this.reverse
        };
    }
}
