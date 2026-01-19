/**
 * InnerGlowEffect - Creates a colored glow inside the layer content edges.
 */
import { LayerEffect } from './LayerEffect.js';

export class InnerGlowEffect extends LayerEffect {
    static type = 'innerGlow';
    static displayName = 'Inner Glow';
    static VERSION = 1;

    constructor(options = {}) {
        super(options);
        this.blur = options.blur ?? 10;
        this.choke = options.choke ?? 0;
        this.color = options.color || '#FFFF00';
        this.colorOpacity = options.colorOpacity ?? 0.75;
        this.source = options.source || 'edge'; // 'edge' or 'center'
    }

    getExpansion() {
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    getParams() {
        return {
            blur: this.blur,
            choke: this.choke,
            color: this.color,
            colorOpacity: this.colorOpacity,
            source: this.source
        };
    }
}
