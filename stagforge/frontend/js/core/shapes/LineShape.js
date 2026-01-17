/**
 * LineShape - Line vector shape.
 */
import { VectorShape, registerShape } from '../VectorShape.js';

export class LineShape extends VectorShape {
    constructor(options = {}) {
        super(options);
        this.x1 = options.x1 ?? 0;
        this.y1 = options.y1 ?? 0;
        this.x2 = options.x2 ?? 100;
        this.y2 = options.y2 ?? 100;

        // Line-specific options
        this.lineCap = options.lineCap || 'round';  // butt, round, square
        this.arrowStart = options.arrowStart ?? false;
        this.arrowEnd = options.arrowEnd ?? false;
        this.arrowSize = options.arrowSize ?? 10;

        // Lines don't fill by default
        this.fill = false;
        this.stroke = true;
    }

    render(ctx) {
        ctx.save();
        this.applyStyles(ctx);
        ctx.lineCap = this.lineCap;

        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.stroke();

        // Draw arrowheads
        if (this.arrowStart) {
            this.drawArrow(ctx, this.x2, this.y2, this.x1, this.y1);
        }
        if (this.arrowEnd) {
            this.drawArrow(ctx, this.x1, this.y1, this.x2, this.y2);
        }

        ctx.restore();
    }

    drawArrow(ctx, fromX, fromY, toX, toY) {
        const angle = Math.atan2(toY - fromY, toX - fromX);
        const size = this.arrowSize;

        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(
            toX - size * Math.cos(angle - Math.PI / 6),
            toY - size * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
            toX - size * Math.cos(angle + Math.PI / 6),
            toY - size * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fillStyle = this.strokeColor;
        ctx.fill();
    }

    containsPoint(px, py) {
        // Distance from point to line segment
        const tolerance = Math.max(this.strokeWidth / 2, 5);
        return this.distanceToLine(px, py) <= tolerance;
    }

    distanceToLine(px, py) {
        const A = px - this.x1;
        const B = py - this.y1;
        const C = this.x2 - this.x1;
        const D = this.y2 - this.y1;

        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let param = -1;

        if (lenSq !== 0) {
            param = dot / lenSq;
        }

        let xx, yy;
        if (param < 0) {
            xx = this.x1;
            yy = this.y1;
        } else if (param > 1) {
            xx = this.x2;
            yy = this.y2;
        } else {
            xx = this.x1 + param * C;
            yy = this.y1 + param * D;
        }

        const dx = px - xx;
        const dy = py - yy;
        return Math.sqrt(dx * dx + dy * dy);
    }

    getBounds() {
        const minX = Math.min(this.x1, this.x2);
        const minY = Math.min(this.y1, this.y2);
        const maxX = Math.max(this.x1, this.x2);
        const maxY = Math.max(this.y1, this.y2);
        return {
            x: minX,
            y: minY,
            width: maxX - minX || 1,
            height: maxY - minY || 1
        };
    }

    getControlPoints() {
        return [
            { id: 'start', x: this.x1, y: this.y1, type: 'anchor' },
            { id: 'end', x: this.x2, y: this.y2, type: 'anchor' }
        ];
    }

    setControlPoint(id, px, py) {
        if (id === 'start') {
            this.x1 = px;
            this.y1 = py;
        } else if (id === 'end') {
            this.x2 = px;
            this.y2 = py;
        }
    }

    moveBy(dx, dy) {
        this.x1 += dx;
        this.y1 += dy;
        this.x2 += dx;
        this.y2 += dy;
    }

    toData() {
        return {
            ...super.toData(),
            x1: this.x1,
            y1: this.y1,
            x2: this.x2,
            y2: this.y2,
            lineCap: this.lineCap,
            arrowStart: this.arrowStart,
            arrowEnd: this.arrowEnd,
            arrowSize: this.arrowSize
        };
    }

    static fromData(data) {
        return new LineShape(data);
    }

    toSVGElement() {
        // Lines only stroke, no fill
        const linecap = this.lineCap || 'round';
        return `<line x1="${this.x1}" y1="${this.y1}" x2="${this.x2}" y2="${this.y2}" stroke="${this.strokeColor}" stroke-width="${this.strokeWidth}" stroke-linecap="${linecap}" opacity="${this.opacity}"/>`;
    }

    getProperties() {
        return [
            { id: 'stroke', name: 'Stroke', type: 'checkbox', value: this.stroke },
            { id: 'strokeColor', name: 'Stroke Color', type: 'color', value: this.strokeColor },
            { id: 'strokeWidth', name: 'Width', type: 'range', min: 1, max: 50, step: 1, value: this.strokeWidth },
            { id: 'lineCap', name: 'Line Cap', type: 'select', options: [
                { value: 'butt', label: 'Butt' },
                { value: 'round', label: 'Round' },
                { value: 'square', label: 'Square' }
            ], value: this.lineCap },
            { id: 'arrowStart', name: 'Arrow Start', type: 'checkbox', value: this.arrowStart },
            { id: 'arrowEnd', name: 'Arrow End', type: 'checkbox', value: this.arrowEnd },
            { id: 'arrowSize', name: 'Arrow Size', type: 'range', min: 5, max: 30, step: 1, value: this.arrowSize },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 0, max: 100, step: 1, value: Math.round(this.opacity * 100) }
        ];
    }

    setProperty(id, value) {
        switch (id) {
            case 'lineCap':
                this.lineCap = value;
                break;
            case 'arrowStart':
            case 'arrowEnd':
                this[id] = value;
                break;
            case 'arrowSize':
                this.arrowSize = Number(value);
                break;
            default:
                super.setProperty(id, value);
        }
    }
}

registerShape('line', LineShape);
