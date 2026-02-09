/**
 * OuterGlowEffect - Creates a colored glow around the layer content.
 */
import { LayerEffect } from './LayerEffect.js';

export class OuterGlowEffect extends LayerEffect {
    static type = 'outerGlow';
    static displayName = 'Outer Glow';
    static VERSION = 1;

    constructor(options = {}) {
        if (options.opacity == null) { options.opacity = options.colorOpacity ?? 0.75; }
        super(options);
        this.blur = options.blur ?? 10;
        this.spread = options.spread ?? 0;
        this.color = options.color || '#FFFF00';
    }

    getExpansion() {
        const expand = Math.ceil(this.blur * 3) + this.spread;
        return { left: expand, top: expand, right: expand, bottom: expand };
    }

    getParams() {
        return {
            blur: this.blur,
            spread: this.spread,
            color: this.color
        };
    }
}
