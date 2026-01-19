/**
 * StrokeEffect - Adds an outline stroke around the layer content.
 */
import { LayerEffect } from './LayerEffect.js';

export class StrokeEffect extends LayerEffect {
    static type = 'stroke';
    static displayName = 'Stroke';
    static VERSION = 1;

    constructor(options = {}) {
        super(options);
        this.size = options.size ?? 3;
        this.position = options.position || 'outside'; // inside, outside, center
        this.color = options.color || '#000000';
        this.colorOpacity = options.colorOpacity ?? 1.0;
    }

    getExpansion() {
        if (this.position === 'outside') {
            return { left: this.size, top: this.size, right: this.size, bottom: this.size };
        } else if (this.position === 'center') {
            const half = Math.ceil(this.size / 2);
            return { left: half, top: half, right: half, bottom: half };
        }
        return { left: 0, top: 0, right: 0, bottom: 0 };
    }

    getParams() {
        return {
            size: this.size,
            position: this.position,
            color: this.color,
            colorOpacity: this.colorOpacity
        };
    }
}
