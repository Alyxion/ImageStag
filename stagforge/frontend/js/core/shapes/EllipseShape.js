/**
 * EllipseShape - Ellipse/circle vector shape.
 */
import { VectorShape, registerShape } from '../VectorShape.js';

export class EllipseShape extends VectorShape {
    constructor(options = {}) {
        super(options);
        // Center point and radii
        this.cx = options.cx ?? 0;
        this.cy = options.cy ?? 0;
        this.rx = options.rx ?? 50;  // X radius
        this.ry = options.ry ?? 50;  // Y radius
    }

    render(ctx) {
        ctx.save();
        this.applyStyles(ctx);

        ctx.beginPath();
        ctx.ellipse(this.cx, this.cy, Math.abs(this.rx), Math.abs(this.ry), 0, 0, Math.PI * 2);

        this.fillAndStroke(ctx);
        ctx.restore();
    }

    containsPoint(px, py) {
        // Point in ellipse check
        const dx = (px - this.cx) / this.rx;
        const dy = (py - this.cy) / this.ry;
        return dx * dx + dy * dy <= 1;
    }

    getBounds() {
        const rx = Math.abs(this.rx);
        const ry = Math.abs(this.ry);
        return {
            x: this.cx - rx,
            y: this.cy - ry,
            width: rx * 2,
            height: ry * 2
        };
    }

    getControlPoints() {
        const rx = Math.abs(this.rx);
        const ry = Math.abs(this.ry);
        return [
            { id: 't', x: this.cx, y: this.cy - ry, type: 'edge' },
            { id: 'r', x: this.cx + rx, y: this.cy, type: 'edge' },
            { id: 'b', x: this.cx, y: this.cy + ry, type: 'edge' },
            { id: 'l', x: this.cx - rx, y: this.cy, type: 'edge' },
            { id: 'tl', x: this.cx - rx, y: this.cy - ry, type: 'corner' },
            { id: 'tr', x: this.cx + rx, y: this.cy - ry, type: 'corner' },
            { id: 'br', x: this.cx + rx, y: this.cy + ry, type: 'corner' },
            { id: 'bl', x: this.cx - rx, y: this.cy + ry, type: 'corner' }
        ];
    }

    setControlPoint(id, px, py) {
        // Get current bounding box
        const bounds = this.getBounds();
        let left = bounds.x;
        let top = bounds.y;
        let right = bounds.x + bounds.width;
        let bottom = bounds.y + bounds.height;

        // Update the appropriate edge(s) based on control point
        switch (id) {
            case 't':
                top = py;
                break;
            case 'b':
                bottom = py;
                break;
            case 'l':
                left = px;
                break;
            case 'r':
                right = px;
                break;
            case 'tl':
                top = py;
                left = px;
                break;
            case 'tr':
                top = py;
                right = px;
                break;
            case 'bl':
                bottom = py;
                left = px;
                break;
            case 'br':
                bottom = py;
                right = px;
                break;
        }

        // Calculate new dimensions (allow negative for flipping)
        const newWidth = right - left;
        const newHeight = bottom - top;

        // Update center and radii (radii are always positive)
        this.cx = left + newWidth / 2;
        this.cy = top + newHeight / 2;
        this.rx = Math.abs(newWidth / 2);
        this.ry = Math.abs(newHeight / 2);
    }

    moveBy(dx, dy) {
        this.cx += dx;
        this.cy += dy;
    }

    toData() {
        return {
            ...super.toData(),
            cx: this.cx,
            cy: this.cy,
            rx: this.rx,
            ry: this.ry
        };
    }

    static fromData(data) {
        return new EllipseShape(data);
    }

    toSVGElement() {
        const style = this.getSVGStyleAttrs();
        return `<ellipse cx="${this.cx}" cy="${this.cy}" rx="${Math.abs(this.rx)}" ry="${Math.abs(this.ry)}" ${style}/>`;
    }
}

registerShape('ellipse', EllipseShape);
