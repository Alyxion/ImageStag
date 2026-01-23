/**
 * PolygonShape - Multi-point polygon vector shape.
 */
import { VectorShape, registerShape } from '../VectorShape.js';

export class PolygonShape extends VectorShape {
    constructor(options = {}) {
        super(options);
        // Array of [x, y] points
        this.points = options.points || [[0, 0], [100, 0], [50, 100]];
        this.closed = options.closed ?? true;
    }

    render(ctx) {
        if (this.points.length < 2) return;

        ctx.save();
        this.applyStyles(ctx);

        ctx.beginPath();
        ctx.moveTo(this.points[0][0], this.points[0][1]);

        for (let i = 1; i < this.points.length; i++) {
            ctx.lineTo(this.points[i][0], this.points[i][1]);
        }

        if (this.closed) {
            ctx.closePath();
        }

        this.fillAndStroke(ctx);
        ctx.restore();
    }

    containsPoint(px, py) {
        if (!this.closed) {
            // For open polygons, check distance to edges
            for (let i = 0; i < this.points.length - 1; i++) {
                if (this.distanceToSegment(px, py, this.points[i], this.points[i + 1]) <= 5) {
                    return true;
                }
            }
            return false;
        }

        // Ray casting algorithm for closed polygons
        let inside = false;
        for (let i = 0, j = this.points.length - 1; i < this.points.length; j = i++) {
            const xi = this.points[i][0], yi = this.points[i][1];
            const xj = this.points[j][0], yj = this.points[j][1];

            if (((yi > py) !== (yj > py)) &&
                (px < (xj - xi) * (py - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }
        return inside;
    }

    distanceToSegment(px, py, p1, p2) {
        const A = px - p1[0];
        const B = py - p1[1];
        const C = p2[0] - p1[0];
        const D = p2[1] - p1[1];

        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let param = lenSq !== 0 ? dot / lenSq : -1;

        let xx, yy;
        if (param < 0) {
            xx = p1[0]; yy = p1[1];
        } else if (param > 1) {
            xx = p2[0]; yy = p2[1];
        } else {
            xx = p1[0] + param * C;
            yy = p1[1] + param * D;
        }

        return Math.sqrt((px - xx) ** 2 + (py - yy) ** 2);
    }

    getBounds() {
        if (this.points.length === 0) return { x: 0, y: 0, width: 0, height: 0 };

        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        for (const [x, y] of this.points) {
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        }

        return {
            x: minX,
            y: minY,
            width: maxX - minX || 1,
            height: maxY - minY || 1
        };
    }

    getControlPoints() {
        return this.points.map((pt, idx) => ({
            id: `pt-${idx}`,
            x: pt[0],
            y: pt[1],
            type: 'anchor',
            pointIndex: idx
        }));
    }

    setControlPoint(id, px, py) {
        const match = id.match(/^pt-(\d+)$/);
        if (match) {
            const idx = parseInt(match[1], 10);
            if (idx >= 0 && idx < this.points.length) {
                this.points[idx] = [px, py];
            }
        }
    }

    moveBy(dx, dy) {
        for (const pt of this.points) {
            pt[0] += dx;
            pt[1] += dy;
        }
    }

    scale(scaleX, scaleY, cx, cy) {
        const bounds = this.getBounds();
        cx = cx ?? (bounds.x + bounds.width / 2);
        cy = cy ?? (bounds.y + bounds.height / 2);

        // Scale all points relative to center
        for (const pt of this.points) {
            pt[0] = cx + (pt[0] - cx) * scaleX;
            pt[1] = cy + (pt[1] - cy) * scaleY;
        }
    }

    /**
     * Add a point at the specified index.
     */
    addPoint(x, y, index = -1) {
        const pt = [x, y];
        if (index < 0 || index >= this.points.length) {
            this.points.push(pt);
        } else {
            this.points.splice(index, 0, pt);
        }
    }

    /**
     * Remove a point by index.
     */
    removePoint(index) {
        if (this.points.length > 2 && index >= 0 && index < this.points.length) {
            this.points.splice(index, 1);
        }
    }

    toData() {
        return {
            ...super.toData(),
            points: this.points.map(pt => [...pt]),  // Deep copy
            closed: this.closed
        };
    }

    static fromData(data) {
        return new PolygonShape({
            ...data,
            points: data.points.map(pt => [...pt])  // Deep copy
        });
    }

    toSVGElement() {
        if (this.points.length < 2) return '';
        const style = this.getSVGStyleAttrs();
        const pointsStr = this.points.map(pt => `${pt[0]},${pt[1]}`).join(' ');
        if (this.closed) {
            return `<polygon points="${pointsStr}" ${style}/>`;
        } else {
            return `<polyline points="${pointsStr}" ${style}/>`;
        }
    }

    getProperties() {
        return [
            ...super.getProperties(),
            { id: 'closed', name: 'Closed', type: 'checkbox', value: this.closed }
        ];
    }

    setProperty(id, value) {
        if (id === 'closed') {
            this.closed = value;
        } else {
            super.setProperty(id, value);
        }
    }
}

registerShape('polygon', PolygonShape);
