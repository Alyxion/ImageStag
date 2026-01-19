/**
 * DropShadowEffect - Creates a shadow behind the layer content.
 */
import { LayerEffect } from './LayerEffect.js';

export class DropShadowEffect extends LayerEffect {
    static type = 'dropShadow';
    static displayName = 'Drop Shadow';
    static VERSION = 1;

    constructor(options = {}) {
        super(options);
        this.offsetX = options.offsetX ?? 4;
        this.offsetY = options.offsetY ?? 4;
        this.blur = options.blur ?? 5;
        this.spread = options.spread ?? 0;
        this.color = options.color || '#000000';
        this.colorOpacity = options.colorOpacity ?? 0.75;
    }

    getExpansion() {
        const expand = Math.ceil(this.blur * 3) + Math.abs(this.spread);
        return {
            left: Math.max(0, expand - this.offsetX),
            top: Math.max(0, expand - this.offsetY),
            right: Math.max(0, expand + this.offsetX),
            bottom: Math.max(0, expand + this.offsetY)
        };
    }

    getParams() {
        return {
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            blur: this.blur,
            spread: this.spread,
            color: this.color,
            colorOpacity: this.colorOpacity
        };
    }
}
