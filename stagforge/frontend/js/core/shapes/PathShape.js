/**
 * PathShape - Bezier curve path vector shape.
 *
 * A path consists of PathPoints, each with optional bezier handles.
 */
import { VectorShape, registerShape } from '../VectorShape.js';

/**
 * A single point in a bezier path.
 */
export class PathPoint {
    constructor(x, y, options = {}) {
        this.x = x;
        this.y = y;

        // Bezier handles (relative to point position)
        // handleIn: control point coming into this anchor
        // handleOut: control point leaving this anchor
        this.handleIn = options.handleIn || null;   // { x, y } relative
        this.handleOut = options.handleOut || null; // { x, y } relative

        // Point type affects handle behavior:
        // 'corner': handles move independently
        // 'smooth': handles stay collinear but can have different lengths
        // 'symmetric': handles are mirror images
        this.type = options.type || 'corner';
    }

    /**
     * Get absolute position of the incoming handle.
     */
    getHandleInAbs() {
        if (!this.handleIn) return null;
        return { x: this.x + this.handleIn.x, y: this.y + this.handleIn.y };
    }

    /**
     * Get absolute position of the outgoing handle.
     */
    getHandleOutAbs() {
        if (!this.handleOut) return null;
        return { x: this.x + this.handleOut.x, y: this.y + this.handleOut.y };
    }

    /**
     * Set the incoming handle from absolute position.
     */
    setHandleInAbs(x, y, updatePaired = true) {
        this.handleIn = { x: x - this.x, y: y - this.y };

        if (updatePaired && this.type !== 'corner' && this.handleOut) {
            this.updatePairedHandle('in');
        }
    }

    /**
     * Set the outgoing handle from absolute position.
     */
    setHandleOutAbs(x, y, updatePaired = true) {
        this.handleOut = { x: x - this.x, y: y - this.y };

        if (updatePaired && this.type !== 'corner' && this.handleIn) {
            this.updatePairedHandle('out');
        }
    }

    /**
     * Update the paired handle based on point type.
     */
    updatePairedHandle(changed) {
        const source = changed === 'in' ? this.handleIn : this.handleOut;
        const target = changed === 'in' ? 'handleOut' : 'handleIn';

        if (!source) return;

        if (this.type === 'symmetric') {
            // Mirror the handle
            this[target] = { x: -source.x, y: -source.y };
        } else if (this.type === 'smooth') {
            // Keep collinear but preserve length
            const currentTarget = this[target];
            if (currentTarget) {
                const len = Math.sqrt(currentTarget.x ** 2 + currentTarget.y ** 2);
                const sourceLen = Math.sqrt(source.x ** 2 + source.y ** 2);
                if (sourceLen > 0) {
                    this[target] = {
                        x: -source.x * len / sourceLen,
                        y: -source.y * len / sourceLen
                    };
                }
            }
        }
    }

    toData() {
        return {
            x: this.x,
            y: this.y,
            handleIn: this.handleIn ? { ...this.handleIn } : null,
            handleOut: this.handleOut ? { ...this.handleOut } : null,
            type: this.type
        };
    }

    static fromData(data) {
        return new PathPoint(data.x, data.y, {
            handleIn: data.handleIn ? { ...data.handleIn } : null,
            handleOut: data.handleOut ? { ...data.handleOut } : null,
            type: data.type || 'corner'
        });
    }
}

export class PathShape extends VectorShape {
    constructor(options = {}) {
        super(options);
        this.points = (options.points || []).map(pt =>
            pt instanceof PathPoint ? pt : PathPoint.fromData(pt)
        );
        this.closed = options.closed ?? false;
    }

    render(ctx) {
        if (this.points.length < 2) return;

        ctx.save();
        this.applyStyles(ctx);

        ctx.beginPath();
        ctx.moveTo(this.points[0].x, this.points[0].y);

        for (let i = 1; i < this.points.length; i++) {
            this.drawSegment(ctx, this.points[i - 1], this.points[i]);
        }

        if (this.closed && this.points.length > 2) {
            this.drawSegment(ctx, this.points[this.points.length - 1], this.points[0]);
            ctx.closePath();
        }

        this.fillAndStroke(ctx);
        ctx.restore();
    }

    /**
     * Draw a bezier segment between two path points.
     */
    drawSegment(ctx, from, to) {
        const hOut = from.getHandleOutAbs();
        const hIn = to.getHandleInAbs();

        if (hOut && hIn) {
            // Full cubic bezier
            ctx.bezierCurveTo(hOut.x, hOut.y, hIn.x, hIn.y, to.x, to.y);
        } else if (hOut) {
            // Quadratic with outgoing handle only
            ctx.quadraticCurveTo(hOut.x, hOut.y, to.x, to.y);
        } else if (hIn) {
            // Quadratic with incoming handle only
            ctx.quadraticCurveTo(hIn.x, hIn.y, to.x, to.y);
        } else {
            // Straight line
            ctx.lineTo(to.x, to.y);
        }
    }

    containsPoint(px, py) {
        // Check distance to path segments
        const tolerance = Math.max(this.strokeWidth / 2, 5);

        for (let i = 0; i < this.points.length - 1; i++) {
            if (this.distanceToSegment(px, py, i) <= tolerance) {
                return true;
            }
        }

        if (this.closed && this.points.length > 2) {
            if (this.distanceToSegment(px, py, this.points.length - 1, true) <= tolerance) {
                return true;
            }
        }

        return false;
    }

    /**
     * Approximate distance to a bezier segment.
     */
    distanceToSegment(px, py, segmentIndex, wrap = false) {
        const from = this.points[segmentIndex];
        const to = wrap ? this.points[0] : this.points[segmentIndex + 1];

        // Sample the bezier at several points and find minimum distance
        let minDist = Infinity;
        const samples = 20;

        for (let t = 0; t <= samples; t++) {
            const pt = this.getPointOnSegment(from, to, t / samples);
            const dist = Math.sqrt((px - pt.x) ** 2 + (py - pt.y) ** 2);
            minDist = Math.min(minDist, dist);
        }

        return minDist;
    }

    /**
     * Get point on segment at parameter t (0-1).
     */
    getPointOnSegment(from, to, t) {
        const hOut = from.getHandleOutAbs();
        const hIn = to.getHandleInAbs();

        if (hOut && hIn) {
            // Cubic bezier
            return this.cubicBezier(from.x, from.y, hOut.x, hOut.y, hIn.x, hIn.y, to.x, to.y, t);
        } else if (hOut) {
            // Quadratic
            return this.quadraticBezier(from.x, from.y, hOut.x, hOut.y, to.x, to.y, t);
        } else if (hIn) {
            // Quadratic
            return this.quadraticBezier(from.x, from.y, hIn.x, hIn.y, to.x, to.y, t);
        } else {
            // Linear
            return {
                x: from.x + (to.x - from.x) * t,
                y: from.y + (to.y - from.y) * t
            };
        }
    }

    cubicBezier(x0, y0, x1, y1, x2, y2, x3, y3, t) {
        const mt = 1 - t;
        const mt2 = mt * mt;
        const mt3 = mt2 * mt;
        const t2 = t * t;
        const t3 = t2 * t;

        return {
            x: mt3 * x0 + 3 * mt2 * t * x1 + 3 * mt * t2 * x2 + t3 * x3,
            y: mt3 * y0 + 3 * mt2 * t * y1 + 3 * mt * t2 * y2 + t3 * y3
        };
    }

    quadraticBezier(x0, y0, x1, y1, x2, y2, t) {
        const mt = 1 - t;
        const mt2 = mt * mt;
        const t2 = t * t;

        return {
            x: mt2 * x0 + 2 * mt * t * x1 + t2 * x2,
            y: mt2 * y0 + 2 * mt * t * y1 + t2 * y2
        };
    }

    getBounds() {
        if (this.points.length === 0) return { x: 0, y: 0, width: 0, height: 0 };

        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        // Sample all segments
        for (let i = 0; i < this.points.length - 1; i++) {
            for (let t = 0; t <= 1; t += 0.1) {
                const pt = this.getPointOnSegment(this.points[i], this.points[i + 1], t);
                minX = Math.min(minX, pt.x);
                minY = Math.min(minY, pt.y);
                maxX = Math.max(maxX, pt.x);
                maxY = Math.max(maxY, pt.y);
            }
        }

        if (this.closed && this.points.length > 2) {
            for (let t = 0; t <= 1; t += 0.1) {
                const pt = this.getPointOnSegment(this.points[this.points.length - 1], this.points[0], t);
                minX = Math.min(minX, pt.x);
                minY = Math.min(minY, pt.y);
                maxX = Math.max(maxX, pt.x);
                maxY = Math.max(maxY, pt.y);
            }
        }

        return {
            x: minX,
            y: minY,
            width: maxX - minX || 1,
            height: maxY - minY || 1
        };
    }

    getControlPoints() {
        const controls = [];

        this.points.forEach((pt, idx) => {
            // Anchor point
            controls.push({
                id: `pt-${idx}`,
                x: pt.x,
                y: pt.y,
                type: 'anchor',
                pointIndex: idx,
                pointType: pt.type
            });

            // Handle in
            if (pt.handleIn) {
                const hIn = pt.getHandleInAbs();
                controls.push({
                    id: `pt-${idx}-hin`,
                    x: hIn.x,
                    y: hIn.y,
                    type: 'handle',
                    pointIndex: idx,
                    handleType: 'in',
                    anchorX: pt.x,
                    anchorY: pt.y
                });
            }

            // Handle out
            if (pt.handleOut) {
                const hOut = pt.getHandleOutAbs();
                controls.push({
                    id: `pt-${idx}-hout`,
                    x: hOut.x,
                    y: hOut.y,
                    type: 'handle',
                    pointIndex: idx,
                    handleType: 'out',
                    anchorX: pt.x,
                    anchorY: pt.y
                });
            }
        });

        return controls;
    }

    setControlPoint(id, px, py) {
        const anchorMatch = id.match(/^pt-(\d+)$/);
        if (anchorMatch) {
            const idx = parseInt(anchorMatch[1], 10);
            if (idx >= 0 && idx < this.points.length) {
                const pt = this.points[idx];
                const dx = px - pt.x;
                const dy = py - pt.y;
                pt.x = px;
                pt.y = py;
                // Handles move with anchor (they're relative)
            }
            return;
        }

        const handleMatch = id.match(/^pt-(\d+)-(hin|hout)$/);
        if (handleMatch) {
            const idx = parseInt(handleMatch[1], 10);
            const handleType = handleMatch[2];
            if (idx >= 0 && idx < this.points.length) {
                const pt = this.points[idx];
                if (handleType === 'hin') {
                    pt.setHandleInAbs(px, py);
                } else {
                    pt.setHandleOutAbs(px, py);
                }
            }
        }
    }

    moveBy(dx, dy) {
        for (const pt of this.points) {
            pt.x += dx;
            pt.y += dy;
        }
    }

    scale(scaleX, scaleY, cx, cy) {
        const bounds = this.getBounds();
        cx = cx ?? (bounds.x + bounds.width / 2);
        cy = cy ?? (bounds.y + bounds.height / 2);

        for (const pt of this.points) {
            // Scale anchor point relative to center
            pt.x = cx + (pt.x - cx) * scaleX;
            pt.y = cy + (pt.y - cy) * scaleY;

            // Scale handles (they are RELATIVE to anchor, so just multiply)
            if (pt.handleIn) {
                pt.handleIn.x *= scaleX;
                pt.handleIn.y *= scaleY;
            }
            if (pt.handleOut) {
                pt.handleOut.x *= scaleX;
                pt.handleOut.y *= scaleY;
            }
        }
    }

    /**
     * Add a point at the end of the path.
     */
    addPoint(x, y, options = {}) {
        const pt = new PathPoint(x, y, options);
        this.points.push(pt);
        return pt;
    }

    /**
     * Insert a point at the specified index.
     */
    insertPoint(index, x, y, options = {}) {
        const pt = new PathPoint(x, y, options);
        this.points.splice(index, 0, pt);
        return pt;
    }

    /**
     * Remove a point by index.
     */
    removePoint(index) {
        if (this.points.length > 2 && index >= 0 && index < this.points.length) {
            this.points.splice(index, 1);
        }
    }

    /**
     * Convert a corner point to smooth (add handles).
     */
    makeSmooth(pointIndex) {
        const pt = this.points[pointIndex];
        if (!pt) return;

        pt.type = 'smooth';

        // Calculate handles based on neighboring points
        const prev = this.points[pointIndex - 1] || (this.closed ? this.points[this.points.length - 1] : null);
        const next = this.points[pointIndex + 1] || (this.closed ? this.points[0] : null);

        if (prev && next) {
            const dx = next.x - prev.x;
            const dy = next.y - prev.y;
            const len = Math.sqrt(dx * dx + dy * dy) / 4;

            if (len > 0) {
                const nx = dx / Math.sqrt(dx * dx + dy * dy);
                const ny = dy / Math.sqrt(dx * dx + dy * dy);

                pt.handleIn = { x: -nx * len, y: -ny * len };
                pt.handleOut = { x: nx * len, y: ny * len };
            }
        }
    }

    /**
     * Convert a smooth point to corner (remove handles).
     */
    makeCorner(pointIndex) {
        const pt = this.points[pointIndex];
        if (!pt) return;

        pt.type = 'corner';
        pt.handleIn = null;
        pt.handleOut = null;
    }

    toData() {
        return {
            ...super.toData(),
            points: this.points.map(pt => pt.toData()),
            closed: this.closed
        };
    }

    static fromData(data) {
        return new PathShape({
            ...data,
            points: data.points.map(pt => PathPoint.fromData(pt))
        });
    }

    /**
     * Generate SVG path 'd' attribute.
     */
    toSVGPathD() {
        if (this.points.length < 2) return '';

        const parts = [`M ${this.points[0].x} ${this.points[0].y}`];

        for (let i = 1; i < this.points.length; i++) {
            const from = this.points[i - 1];
            const to = this.points[i];
            const hOut = from.getHandleOutAbs();
            const hIn = to.getHandleInAbs();

            if (hOut && hIn) {
                // Cubic bezier
                parts.push(`C ${hOut.x} ${hOut.y} ${hIn.x} ${hIn.y} ${to.x} ${to.y}`);
            } else if (hOut) {
                // Quadratic with control point from outgoing handle
                parts.push(`Q ${hOut.x} ${hOut.y} ${to.x} ${to.y}`);
            } else if (hIn) {
                // Quadratic with control point from incoming handle
                parts.push(`Q ${hIn.x} ${hIn.y} ${to.x} ${to.y}`);
            } else {
                // Line
                parts.push(`L ${to.x} ${to.y}`);
            }
        }

        // Close path if needed
        if (this.closed && this.points.length > 2) {
            const from = this.points[this.points.length - 1];
            const to = this.points[0];
            const hOut = from.getHandleOutAbs();
            const hIn = to.getHandleInAbs();

            if (hOut && hIn) {
                parts.push(`C ${hOut.x} ${hOut.y} ${hIn.x} ${hIn.y} ${to.x} ${to.y}`);
            } else if (hOut) {
                parts.push(`Q ${hOut.x} ${hOut.y} ${to.x} ${to.y}`);
            } else if (hIn) {
                parts.push(`Q ${hIn.x} ${hIn.y} ${to.x} ${to.y}`);
            }
            parts.push('Z');
        }

        return parts.join(' ');
    }

    toSVGElement() {
        const d = this.toSVGPathD();
        if (!d) return '';
        const style = this.getSVGStyleAttrs();
        return `<path d="${d}" ${style}/>`;
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

registerShape('path', PathShape);
