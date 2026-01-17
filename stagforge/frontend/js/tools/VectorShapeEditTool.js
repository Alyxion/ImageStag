/**
 * VectorShapeEditTool - Select and edit vector shapes.
 *
 * Features:
 * - Click to select shapes
 * - Shift+click to add to selection
 * - Drag shapes to move them
 * - Drag control points to resize/reshape
 * - Drag bezier handles to adjust curves
 * - Double-click to enter point editing mode
 * - Delete/Backspace to delete selected shapes
 */
import { Tool } from './Tool.js';
import { VectorLayer } from '../core/VectorLayer.js';

export class VectorShapeEditTool extends Tool {
    static id = 'select';
    static name = 'Select';
    static icon = 'cursor';
    static shortcut = 'v';
    static cursor = 'default';

    constructor(app) {
        super(app);

        // Interaction state
        this.isDragging = false;
        this.dragMode = null;  // 'move', 'control', 'handle'
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.lastX = 0;
        this.lastY = 0;

        // What we're dragging
        this.draggedShape = null;
        this.draggedControl = null;

        // Cursor states
        this.cursorOverControl = false;
    }

    activate() {
        super.activate();
        // Show selection handles on active vector layer
        this.refreshSelection();
    }

    deactivate() {
        super.deactivate();
        // Clear selection when leaving the select tool
        const layer = this.getVectorLayer();
        if (layer && layer.selectedShapeIds.size > 0) {
            layer.clearSelection();
            this.app.renderer.requestRender();
        }
    }

    /**
     * Get the current vector layer if any.
     */
    getVectorLayer() {
        const layer = this.app.layerStack.getActiveLayer();
        if (layer && layer.isVector && layer.isVector()) {
            return layer;
        }
        return null;
    }

    refreshSelection() {
        // Selection handles are now drawn by the Renderer as an overlay,
        // so we only need to request a renderer update (not a layer re-render)
        this.app.renderer.requestRender();
    }

    onMouseDown(e, x, y) {
        const layer = this.getVectorLayer();
        if (!layer || layer.locked) return;

        this.dragStartX = x;
        this.dragStartY = y;
        this.lastX = x;
        this.lastY = y;

        // Check for control point hit first
        const controlHit = layer.getControlPointAt(x, y);
        if (controlHit) {
            this.isDragging = true;
            this.dragMode = controlHit.control.type === 'handle' ? 'handle' : 'control';
            this.draggedShape = controlHit.shape;
            this.draggedControl = controlHit.control;

            // Start editing mode for fast Canvas 2D preview during drag
            layer.startEditing();

            // Save state for undo
            this.app.history.saveState('Edit Shape');
            return;
        }

        // Check for shape hit
        const shape = layer.getShapeAt(x, y);
        if (shape) {
            // Select or add to selection
            if (e.shiftKey) {
                // Toggle selection
                if (layer.selectedShapeIds.has(shape.id)) {
                    layer.deselectShape(shape.id);
                } else {
                    layer.selectShape(shape.id, true);
                }
            } else {
                // Select this shape (clearing others unless already selected)
                if (!layer.selectedShapeIds.has(shape.id)) {
                    layer.selectShape(shape.id, false);
                }
            }

            // Start dragging to move
            this.isDragging = true;
            this.dragMode = 'move';
            this.draggedShape = shape;

            // Start editing mode for fast Canvas 2D preview during drag
            layer.startEditing();

            // Save state for undo
            this.app.history.saveState('Move Shape');
        } else {
            // Clicked empty area - clear selection
            if (!e.shiftKey) {
                layer.clearSelection();
            }
        }

        this.app.renderer.requestRender();
    }

    onMouseMove(e, x, y) {
        const layer = this.getVectorLayer();
        if (!layer) return;

        if (this.isDragging) {
            const dx = x - this.lastX;
            const dy = y - this.lastY;

            if (this.dragMode === 'move') {
                // Move all selected shapes
                for (const shape of layer.getSelectedShapes()) {
                    shape.moveBy(dx, dy);
                }
            } else if (this.dragMode === 'control' || this.dragMode === 'handle') {
                // Move control point
                this.draggedShape.setControlPoint(this.draggedControl.id, x, y);
            }

            this.lastX = x;
            this.lastY = y;

            layer.render();
            this.app.renderer.requestRender();
        } else {
            // Update cursor based on what we're hovering over
            const controlHit = layer.getControlPointAt(x, y);
            if (controlHit) {
                this.app.displayCanvas.style.cursor = 'move';
                this.cursorOverControl = true;
            } else if (layer.getShapeAt(x, y)) {
                this.app.displayCanvas.style.cursor = 'move';
                this.cursorOverControl = false;
            } else {
                this.app.displayCanvas.style.cursor = 'default';
                this.cursorOverControl = false;
            }
        }
    }

    onMouseUp(e, x, y) {
        if (this.isDragging) {
            // End editing mode - triggers SVG render
            const layer = this.getVectorLayer();
            if (layer) {
                layer.endEditing();
            }

            this.isDragging = false;
            this.dragMode = null;
            this.draggedShape = null;
            this.draggedControl = null;

            // Finish undo state
            this.app.history.finishState();

            // Request renderer update for selection handles overlay
            this.app.renderer.requestRender();
        }
    }

    onMouseLeave(e) {
        if (this.isDragging) {
            // End editing mode - triggers SVG render
            const layer = this.getVectorLayer();
            if (layer) {
                layer.endEditing();
            }

            this.isDragging = false;
            this.dragMode = null;
            this.draggedShape = null;
            this.draggedControl = null;
            this.app.history.finishState();

            // Request renderer update for selection handles overlay
            this.app.renderer.requestRender();
        }
    }

    onKeyDown(e) {
        const layer = this.getVectorLayer();
        if (!layer || layer.locked) return;

        if (e.key === 'Delete' || e.key === 'Backspace') {
            // Delete selected shapes
            const selectedIds = [...layer.selectedShapeIds];
            if (selectedIds.length > 0) {
                this.app.history.saveState('Delete Shape');

                for (const id of selectedIds) {
                    layer.removeShape(id);
                }

                this.app.history.finishState();
                this.app.renderer.requestRender();
            }
            e.preventDefault();
        } else if (e.key === 'Escape') {
            // Clear selection
            layer.clearSelection();
            this.app.renderer.requestRender();
        } else if (e.key === 'a' && (e.ctrlKey || e.metaKey)) {
            // Select all shapes
            e.preventDefault();
            for (const shape of layer.shapes) {
                layer.selectShape(shape.id, true);
            }
            this.app.renderer.requestRender();
        } else if (e.key === '[') {
            // Move selected shapes down in z-order
            for (const id of layer.selectedShapeIds) {
                layer.moveShapeInOrder(id, 'down');
            }
            this.app.renderer.requestRender();
        } else if (e.key === ']') {
            // Move selected shapes up in z-order
            for (const id of layer.selectedShapeIds) {
                layer.moveShapeInOrder(id, 'up');
            }
            this.app.renderer.requestRender();
        }
    }

    getProperties() {
        const layer = this.getVectorLayer();
        if (!layer) {
            return [];
        }

        const selected = layer.getSelectedShapes();
        if (selected.length === 1) {
            // Show properties of selected shape
            return selected[0].getProperties();
        } else if (selected.length > 1) {
            // Multiple selection - show common properties only
            return [
                { id: 'info', name: 'Selected', type: 'label', value: `${selected.length} shapes` }
            ];
        }

        return [];
    }

    onPropertyChanged(id, value) {
        const layer = this.getVectorLayer();
        if (!layer) return;

        const selected = layer.getSelectedShapes();
        if (selected.length === 1) {
            this.app.history.saveState('Change Shape Property');
            selected[0].setProperty(id, value);
            layer.render();
            this.app.history.finishState();
            this.app.renderer.requestRender();
        }
    }

    // API execution
    executeAction(action, params) {
        const layer = this.getVectorLayer();
        if (!layer || layer.locked) {
            return { success: false, error: 'No active vector layer or layer is locked' };
        }

        switch (action) {
            case 'select': {
                if (params.shapeId) {
                    layer.selectShape(params.shapeId, params.addToSelection);
                    this.app.renderer.requestRender();
                    return { success: true };
                }
                return { success: false, error: 'shapeId required' };
            }

            case 'deselect': {
                if (params.shapeId) {
                    layer.deselectShape(params.shapeId);
                } else {
                    layer.clearSelection();
                }
                this.app.renderer.requestRender();
                return { success: true };
            }

            case 'move': {
                if (params.shapeId && params.dx !== undefined && params.dy !== undefined) {
                    const shape = layer.getShapeById(params.shapeId);
                    if (shape) {
                        this.app.history.saveState('Move Shape');
                        shape.moveBy(params.dx, params.dy);
                        layer.render();
                        this.app.history.finishState();
                        this.app.renderer.requestRender();
                        return { success: true };
                    }
                    return { success: false, error: 'Shape not found' };
                }
                return { success: false, error: 'shapeId, dx, dy required' };
            }

            case 'delete': {
                const ids = params.shapeIds || [...layer.selectedShapeIds];
                if (ids.length > 0) {
                    this.app.history.saveState('Delete Shape');
                    for (const id of ids) {
                        layer.removeShape(id);
                    }
                    this.app.history.finishState();
                    this.app.renderer.requestRender();
                    return { success: true, deleted: ids.length };
                }
                return { success: false, error: 'No shapes to delete' };
            }

            case 'set_property': {
                if (params.shapeId && params.property && params.value !== undefined) {
                    const shape = layer.getShapeById(params.shapeId);
                    if (shape) {
                        this.app.history.saveState('Change Shape Property');
                        shape.setProperty(params.property, params.value);
                        layer.render();
                        this.app.history.finishState();
                        this.app.renderer.requestRender();
                        return { success: true };
                    }
                    return { success: false, error: 'Shape not found' };
                }
                return { success: false, error: 'shapeId, property, value required' };
            }

            default:
                return { success: false, error: `Unknown action: ${action}` };
        }
    }
}
