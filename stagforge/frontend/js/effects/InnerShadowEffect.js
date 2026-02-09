/**
 * InnerShadowEffect - Creates a shadow inside the layer content edges.
 */
import { LayerEffect } from './LayerEffect.js';

export class InnerShadowEffect extends LayerEffect {
    static type = 'innerShadow';
    static displayName = 'Inner Shadow';
    static VERSION = 1;

    constructor(options = {}) {
        if (options.opacity == null) { options.opacity = options.colorOpacity ?? 0.75; }
        super(options);
        this.offsetX = options.offsetX ?? 2;
        this.offsetY = options.offsetY ?? 2;
        this.blur = options.blur ?? 5;
        this.choke = options.choke ?? 0;
        this.color = options.color || '#000000';
    }

    getExpansion() {
        return { left: 0, top: 0, right: 0, bottom: 0 }; // Inner effects don't expand
    }

    getParams() {
        return {
            offsetX: this.offsetX,
            offsetY: this.offsetY,
            blur: this.blur,
            choke: this.choke,
            color: this.color
        };
    }
}
