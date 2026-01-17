/**
 * VectorShape - Base class for all vector shapes.
 *
 * Shapes are stored as data objects and rendered to canvas on demand.
 * Each shape type registers itself for serialization/deserialization.
 */

// Shape registry for type -> class mapping
export const ShapeRegistry = {};

/**
 * Register a shape class with its type identifier.
 */
export function registerShape(type, ShapeClass) {
    ShapeRegistry[type] = ShapeClass;
    ShapeClass.shapeType = type;
}

/**
 * Create a shape from serialized data.
 */
export function createShape(data) {
    const ShapeClass = ShapeRegistry[data.type];
    if (!ShapeClass) {
        throw new Error(`Unknown shape type: ${data.type}`);
    }
    return ShapeClass.fromData(data);
}

/**
 * Base class for all vector shapes.
 */
export class VectorShape {
    static shapeType = 'shape';

    constructor(options = {}) {
        this.id = options.id || crypto.randomUUID();

        // Visual properties
        this.fillColor = options.fillColor || '#000000';
        this.strokeColor = options.strokeColor || '#000000';
        this.strokeWidth = options.strokeWidth ?? 2;
        this.fill = options.fill ?? true;
        this.stroke = options.stroke ?? true;
        this.opacity = options.opacity ?? 1.0;

        // Selection state (not serialized)
        this.selected = false;
    }

    /**
     * Render the shape to a canvas context.
     * Must be overridden by subclasses.
     */
    render(ctx) {
        throw new Error('render() must be implemented by subclass');
    }

    /**
     * Render selection handles when shape is selected.
     */
    renderSelection(ctx) {
        const bounds = this.getBounds();
        if (!bounds) return;

        ctx.save();

        // Selection rectangle
        ctx.strokeStyle = '#0078d4';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(bounds.x - 2, bounds.y - 2, bounds.width + 4, bounds.height + 4);
        ctx.setLineDash([]);

        // Control points
        const controls = this.getControlPoints();
        for (const ctrl of controls) {
            ctx.fillStyle = ctrl.type === 'handle' ? '#ffffff' : '#0078d4';
            ctx.strokeStyle = '#0078d4';
            ctx.lineWidth = 1;

            const size = ctrl.type === 'handle' ? 6 : 8;

            ctx.beginPath();
            if (ctrl.type === 'handle') {
                // Bezier handles are circles
                ctx.arc(ctrl.x, ctrl.y, size / 2, 0, Math.PI * 2);
            } else {
                // Anchor points are squares
                ctx.rect(ctrl.x - size / 2, ctrl.y - size / 2, size, size);
            }
            ctx.fill();
            ctx.stroke();

            // Draw line from anchor to handle
            if (ctrl.type === 'handle' && ctrl.anchorX !== undefined) {
                ctx.beginPath();
                ctx.strokeStyle = '#0078d4';
                ctx.lineWidth = 1;
                ctx.moveTo(ctrl.anchorX, ctrl.anchorY);
                ctx.lineTo(ctrl.x, ctrl.y);
                ctx.stroke();
            }
        }

        ctx.restore();
    }

    /**
     * Check if a point is inside the shape.
     * Must be overridden by subclasses.
     */
    containsPoint(x, y) {
        throw new Error('containsPoint() must be implemented by subclass');
    }

    /**
     * Get bounding box of the shape.
     * Must be overridden by subclasses.
     * @returns {{ x: number, y: number, width: number, height: number }}
     */
    getBounds() {
        throw new Error('getBounds() must be implemented by subclass');
    }

    /**
     * Get control points for editing.
     * Returns array of { id, x, y, type: 'anchor'|'handle'|'corner', ... }
     */
    getControlPoints() {
        return [];
    }

    /**
     * Find control point at position.
     * @returns Control point object or null
     */
    getControlPointAt(x, y, tolerance = 8) {
        const controls = this.getControlPoints();
        for (const ctrl of controls) {
            const dx = x - ctrl.x;
            const dy = y - ctrl.y;
            if (Math.sqrt(dx * dx + dy * dy) <= tolerance) {
                return ctrl;
            }
        }
        return null;
    }

    /**
     * Move a control point to a new position.
     * @param {string} id - Control point ID
     * @param {number} x - New X position
     * @param {number} y - New Y position
     */
    setControlPoint(id, x, y) {
        // Override in subclasses
    }

    /**
     * Move the entire shape by delta.
     */
    moveBy(dx, dy) {
        // Override in subclasses
    }

    /**
     * Clone the shape.
     */
    clone() {
        const data = this.toData();
        data.id = crypto.randomUUID();
        return createShape(data);
    }

    /**
     * Serialize shape to plain object for storage.
     */
    toData() {
        return {
            type: this.constructor.shapeType,
            id: this.id,
            fillColor: this.fillColor,
            strokeColor: this.strokeColor,
            strokeWidth: this.strokeWidth,
            fill: this.fill,
            stroke: this.stroke,
            opacity: this.opacity
        };
    }

    /**
     * Create shape from serialized data.
     * Must be overridden by subclasses.
     */
    static fromData(data) {
        throw new Error('fromData() must be implemented by subclass');
    }

    /**
     * Get properties for the UI property panel.
     */
    getProperties() {
        return [
            { id: 'fill', name: 'Fill', type: 'checkbox', value: this.fill },
            { id: 'fillColor', name: 'Fill Color', type: 'color', value: this.fillColor },
            { id: 'stroke', name: 'Stroke', type: 'checkbox', value: this.stroke },
            { id: 'strokeColor', name: 'Stroke Color', type: 'color', value: this.strokeColor },
            { id: 'strokeWidth', name: 'Width', type: 'range', min: 1, max: 50, step: 1, value: this.strokeWidth },
            { id: 'opacity', name: 'Opacity', type: 'range', min: 0, max: 100, step: 1, value: Math.round(this.opacity * 100) }
        ];
    }

    /**
     * Update a property value.
     */
    setProperty(id, value) {
        switch (id) {
            case 'fill':
            case 'stroke':
                this[id] = value;
                break;
            case 'fillColor':
            case 'strokeColor':
                this[id] = value;
                break;
            case 'strokeWidth':
                this.strokeWidth = Number(value);
                break;
            case 'opacity':
                this.opacity = Number(value) / 100;
                break;
        }
    }

    /**
     * Apply fill and stroke styles to context.
     */
    applyStyles(ctx) {
        ctx.globalAlpha = this.opacity;
        if (this.fill) {
            ctx.fillStyle = this.fillColor;
        }
        if (this.stroke) {
            ctx.strokeStyle = this.strokeColor;
            ctx.lineWidth = this.strokeWidth;
        }
    }

    /**
     * Fill and stroke the current path based on shape settings.
     */
    fillAndStroke(ctx) {
        if (this.fill) {
            ctx.fill();
        }
        if (this.stroke) {
            ctx.stroke();
        }
    }

    /**
     * Get SVG style attributes string.
     * @returns {string} SVG style attributes
     */
    getSVGStyleAttrs() {
        const fill = this.fill ? this.fillColor : 'none';
        const stroke = this.stroke ? this.strokeColor : 'none';
        return `fill="${fill}" stroke="${stroke}" stroke-width="${this.strokeWidth}" opacity="${this.opacity}"`;
    }

    /**
     * Convert shape to SVG element string.
     * Must be overridden by subclasses.
     * @returns {string} SVG element
     */
    toSVGElement() {
        throw new Error('toSVGElement() must be implemented by subclass');
    }
}
