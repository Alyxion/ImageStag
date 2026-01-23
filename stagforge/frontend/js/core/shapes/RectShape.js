/**
 * RectShape - Rectangle vector shape.
 */
import { VectorShape, registerShape } from '../VectorShape.js';

export class RectShape extends VectorShape {
    constructor(options = {}) {
        super(options);
        this.x = options.x ?? 0;
        this.y = options.y ?? 0;
        this.width = options.width ?? 100;
        this.height = options.height ?? 100;
        this.cornerRadius = options.cornerRadius ?? 0;
    }

    render(ctx) {
        ctx.save();
        this.applyStyles(ctx);

        ctx.beginPath();
        if (this.cornerRadius > 0) {
            this.drawRoundedRect(ctx);
        } else {
            ctx.rect(this.x, this.y, this.width, this.height);
        }

        this.fillAndStroke(ctx);
        ctx.restore();
    }

    drawRoundedRect(ctx) {
        const r = Math.min(this.cornerRadius, this.width / 2, this.height / 2);
        const x = this.x, y = this.y, w = this.width, h = this.height;

        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    containsPoint(px, py) {
        return px >= this.x && px <= this.x + this.width &&
               py >= this.y && py <= this.y + this.height;
    }

    getBounds() {
        return {
            x: this.x,
            y: this.y,
            width: this.width,
            height: this.height
        };
    }

    getControlPoints() {
        const x = this.x, y = this.y, w = this.width, h = this.height;
        return [
            { id: 'tl', x: x, y: y, type: 'corner' },
            { id: 'tr', x: x + w, y: y, type: 'corner' },
            { id: 'br', x: x + w, y: y + h, type: 'corner' },
            { id: 'bl', x: x, y: y + h, type: 'corner' },
            { id: 't', x: x + w / 2, y: y, type: 'edge' },
            { id: 'r', x: x + w, y: y + h / 2, type: 'edge' },
            { id: 'b', x: x + w / 2, y: y + h, type: 'edge' },
            { id: 'l', x: x, y: y + h / 2, type: 'edge' }
        ];
    }

    setControlPoint(id, px, py) {
        switch (id) {
            case 'tl':
                this.width += this.x - px;
                this.height += this.y - py;
                this.x = px;
                this.y = py;
                break;
            case 'tr':
                this.width = px - this.x;
                this.height += this.y - py;
                this.y = py;
                break;
            case 'br':
                this.width = px - this.x;
                this.height = py - this.y;
                break;
            case 'bl':
                this.width += this.x - px;
                this.x = px;
                this.height = py - this.y;
                break;
            case 't':
                this.height += this.y - py;
                this.y = py;
                break;
            case 'r':
                this.width = px - this.x;
                break;
            case 'b':
                this.height = py - this.y;
                break;
            case 'l':
                this.width += this.x - px;
                this.x = px;
                break;
        }
        // Normalize if width/height became negative
        if (this.width < 0) {
            this.x += this.width;
            this.width = -this.width;
        }
        if (this.height < 0) {
            this.y += this.height;
            this.height = -this.height;
        }
    }

    moveBy(dx, dy) {
        this.x += dx;
        this.y += dy;
    }

    scale(scaleX, scaleY, cx, cy) {
        const bounds = this.getBounds();
        cx = cx ?? (bounds.x + bounds.width / 2);
        cy = cy ?? (bounds.y + bounds.height / 2);

        // Scale position relative to center
        this.x = cx + (this.x - cx) * scaleX;
        this.y = cy + (this.y - cy) * scaleY;

        // Scale dimensions
        this.width *= Math.abs(scaleX);
        this.height *= Math.abs(scaleY);

        // Scale corner radius proportionally
        this.cornerRadius *= Math.min(Math.abs(scaleX), Math.abs(scaleY));
    }

    toData() {
        return {
            ...super.toData(),
            x: this.x,
            y: this.y,
            width: this.width,
            height: this.height,
            cornerRadius: this.cornerRadius
        };
    }

    static fromData(data) {
        return new RectShape(data);
    }

    toSVGElement() {
        const style = this.getSVGStyleAttrs();
        if (this.cornerRadius > 0) {
            const r = Math.min(this.cornerRadius, this.width / 2, this.height / 2);
            return `<rect x="${this.x}" y="${this.y}" width="${this.width}" height="${this.height}" rx="${r}" ry="${r}" ${style}/>`;
        }
        return `<rect x="${this.x}" y="${this.y}" width="${this.width}" height="${this.height}" ${style}/>`;
    }

    getProperties() {
        return [
            ...super.getProperties(),
            { id: 'cornerRadius', name: 'Corner Radius', type: 'range', min: 0, max: 100, step: 1, value: this.cornerRadius }
        ];
    }

    setProperty(id, value) {
        if (id === 'cornerRadius') {
            this.cornerRadius = Number(value);
        } else {
            super.setProperty(id, value);
        }
    }
}

registerShape('rect', RectShape);
