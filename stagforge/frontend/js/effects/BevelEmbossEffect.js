/**
 * BevelEmbossEffect - Creates beveled/embossed 3D-like edges on the layer.
 */
import { LayerEffect } from './LayerEffect.js';

export class BevelEmbossEffect extends LayerEffect {
    static type = 'bevelEmboss';
    static displayName = 'Bevel & Emboss';
    static VERSION = 1;

    constructor(options = {}) {
        super(options);
        this.style = options.style || 'innerBevel'; // innerBevel, outerBevel, emboss, pillowEmboss
        this.depth = options.depth ?? 3;
        this.direction = options.direction || 'up'; // up, down
        this.size = options.size ?? 5;
        this.soften = options.soften ?? 0;
        this.angle = options.angle ?? 120;
        this.altitude = options.altitude ?? 30;
        this.highlightColor = options.highlightColor || '#FFFFFF';
        this.highlightOpacity = options.highlightOpacity ?? 0.75;
        this.shadowColor = options.shadowColor || '#000000';
        this.shadowOpacity = options.shadowOpacity ?? 0.75;
    }

    getExpansion() {
        if (this.style === 'outerBevel') {
            const expand = Math.ceil(this.size);
            return { left: expand, top: expand, right: expand, bottom: expand };
        }
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    getParams() {
        return {
            style: this.style,
            depth: this.depth,
            direction: this.direction,
            size: this.size,
            soften: this.soften,
            angle: this.angle,
            altitude: this.altitude,
            highlightColor: this.highlightColor,
            highlightOpacity: this.highlightOpacity,
            shadowColor: this.shadowColor,
            shadowOpacity: this.shadowOpacity
        };
    }
}
