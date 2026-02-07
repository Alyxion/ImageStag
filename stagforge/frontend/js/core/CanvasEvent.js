/**
 * CanvasEvent - Unified event object for canvas tool interactions.
 *
 * Replaces the old 4-parameter signature (e, x, y, coords) with a single
 * event that encapsulates all three coordinate spaces and forwards common
 * DOM MouseEvent properties directly (no nesting required).
 *
 * Coordinate spaces:
 *   - screenX/screenY: Relative to canvas element (for UI positioning)
 *   - docX/docY: Document space (stable across zoom/pan, used for overlays)
 *   - layerX/layerY: Layer-local (after offset + rotation/scale)
 */
export class CanvasEvent {
    /**
     * @param {MouseEvent|Object} domEvent - Original DOM MouseEvent (or fake for synthetic events)
     * @param {{ screenX: number, screenY: number, docX: number, docY: number, layerX: number, layerY: number }} coords
     */
    constructor(domEvent, { screenX, screenY, docX, docY, layerX, layerY }) {
        // Canvas coordinate spaces
        this.screenX = screenX;
        this.screenY = screenY;
        this.docX = docX;
        this.docY = docY;
        this.layerX = layerX;
        this.layerY = layerY;

        // Forward common DOM MouseEvent properties directly
        this.clientX  = domEvent.clientX  ?? 0;
        this.clientY  = domEvent.clientY  ?? 0;
        this.pageX    = domEvent.pageX    ?? 0;
        this.pageY    = domEvent.pageY    ?? 0;
        this.offsetX  = domEvent.offsetX  ?? 0;
        this.offsetY  = domEvent.offsetY  ?? 0;
        this.altKey   = domEvent.altKey   ?? false;
        this.ctrlKey  = domEvent.ctrlKey  ?? false;
        this.shiftKey = domEvent.shiftKey ?? false;
        this.metaKey  = domEvent.metaKey  ?? false;
        this.button   = domEvent.button   ?? 0;
        this.buttons  = domEvent.buttons  ?? 0;
        this.target   = domEvent.target   ?? null;

        // Escape hatch for rare cases needing the full DOM event
        this.domEvent = domEvent;
    }

    /** Delegate preventDefault to the underlying DOM event. */
    preventDefault() { this.domEvent.preventDefault?.(); }

    /** Delegate stopPropagation to the underlying DOM event. */
    stopPropagation() { this.domEvent.stopPropagation?.(); }

    /**
     * Factory for API/synthetic events (no real DOM event, coords in layer space).
     * Used by SessionAPIManager for programmatic tool execution.
     *
     * @param {number} x - Layer-local X
     * @param {number} y - Layer-local Y
     * @param {Object} [layer] - Layer for offset conversion
     * @returns {CanvasEvent}
     */
    static fromLayerCoords(x, y, layer) {
        let docX, docY;
        if (layer?.layerToDoc) {
            const doc = layer.layerToDoc(x, y);
            docX = doc.x;
            docY = doc.y;
        } else {
            docX = x + (layer?.offsetX || 0);
            docY = y + (layer?.offsetY || 0);
        }
        const fake = {
            clientX: 0, clientY: 0, pageX: 0, pageY: 0, offsetX: 0, offsetY: 0,
            altKey: false, ctrlKey: false, shiftKey: false, metaKey: false,
            button: 0, buttons: 0, target: null,
        };
        return new CanvasEvent(fake, {
            screenX: 0, screenY: 0,
            docX, docY,
            layerX: x, layerY: y,
        });
    }
}
