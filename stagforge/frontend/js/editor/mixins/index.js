/**
 * Editor Mixins Index
 *
 * Exports all Vue mixins for the canvas editor component.
 * These mixins can be imported individually or as a group.
 *
 * Usage:
 *   import { ColorManagementMixin, LayerOperationsMixin } from './mixins';
 *
 * Or import all:
 *   import * as EditorMixins from './mixins';
 */

// Core layer and color mixins
import { ColorManagementMixin } from './ColorManagement.js';
import { LayerOperationsMixin } from './LayerOperations.js';
import { LayerDragDropMixin } from './LayerDragDrop.js';

// History, zoom, and navigation mixins
import { HistoryManagerMixin } from './HistoryManager.js';
import { ZoomManagerMixin } from './ZoomManager.js';
import { NavigatorManagerMixin } from './NavigatorManager.js';

// Tool management mixins
import { ToolManagerMixin } from './ToolManager.js';
import { ColorPickerMixin } from './ColorPicker.js';

// Event handling mixins
import { CanvasEventsMixin } from './CanvasEvents.js';
import { KeyboardEventsMixin } from './KeyboardEvents.js';

// Menu and UI mixins
import { MenuManagerMixin } from './MenuManager.js';
import { PopupMenuMixin } from './PopupMenu.js';
import { ViewManagerMixin } from './ViewManager.js';

// Clipboard and selection mixins
import { ClipboardManagerMixin } from './ClipboardManager.js';

// Effects management
import { EffectsManagerMixin } from './EffectsManager.js';

// File operations
import { FileManagerMixin } from './FileManager.js';

// Session API
import { SessionAPIManagerMixin } from './SessionAPIManager.js';

// Tablet UI
import { TabletUIManagerMixin } from './TabletUIManager.js';

// Brush cursor and presets
import { BrushCursorManagerMixin } from './BrushCursorManager.js';

// Filter and preferences dialogs
import { FilterDialogManagerMixin } from './FilterDialogManager.js';

// Document UI, tabs, layer list, image sources
import { DocumentUIManagerMixin } from './DocumentUIManager.js';

// Named exports
export { ColorManagementMixin } from './ColorManagement.js';
export { LayerOperationsMixin } from './LayerOperations.js';
export { LayerDragDropMixin } from './LayerDragDrop.js';
export { HistoryManagerMixin } from './HistoryManager.js';
export { ZoomManagerMixin } from './ZoomManager.js';
export { NavigatorManagerMixin } from './NavigatorManager.js';
export { ToolManagerMixin } from './ToolManager.js';
export { ColorPickerMixin } from './ColorPicker.js';
export { CanvasEventsMixin } from './CanvasEvents.js';
export { KeyboardEventsMixin } from './KeyboardEvents.js';
export { MenuManagerMixin } from './MenuManager.js';
export { PopupMenuMixin } from './PopupMenu.js';
export { ViewManagerMixin } from './ViewManager.js';
export { ClipboardManagerMixin } from './ClipboardManager.js';
export { EffectsManagerMixin } from './EffectsManager.js';
export { FileManagerMixin } from './FileManager.js';
export { SessionAPIManagerMixin } from './SessionAPIManager.js';
export { TabletUIManagerMixin } from './TabletUIManager.js';
export { BrushCursorManagerMixin } from './BrushCursorManager.js';
export { FilterDialogManagerMixin } from './FilterDialogManager.js';
export { DocumentUIManagerMixin } from './DocumentUIManager.js';

/**
 * Array of all available mixins
 */
export const allMixins = [
    ColorManagementMixin,
    LayerOperationsMixin,
    LayerDragDropMixin,
    HistoryManagerMixin,
    ZoomManagerMixin,
    NavigatorManagerMixin,
    ToolManagerMixin,
    ColorPickerMixin,
    CanvasEventsMixin,
    KeyboardEventsMixin,
    MenuManagerMixin,
    PopupMenuMixin,
    ViewManagerMixin,
    ClipboardManagerMixin,
    EffectsManagerMixin,
    FileManagerMixin,
    SessionAPIManagerMixin,
    TabletUIManagerMixin,
    BrushCursorManagerMixin,
    FilterDialogManagerMixin,
    DocumentUIManagerMixin,
];

/**
 * Helper to merge all mixins into a single object
 * @returns {Object} Combined mixin with all methods
 */
export function createEditorMixin() {
    const combined = {
        data() {
            let result = {};
            for (const mixin of allMixins) {
                if (mixin.data) {
                    const mixinData = typeof mixin.data === 'function' ? mixin.data() : mixin.data;
                    result = { ...result, ...mixinData };
                }
            }
            return result;
        },
        methods: {},
        computed: {},
    };

    for (const mixin of allMixins) {
        if (mixin.methods) {
            Object.assign(combined.methods, mixin.methods);
        }
        if (mixin.computed) {
            Object.assign(combined.computed, mixin.computed);
        }
    }

    return combined;
}

// Default export is the array of all mixins
export default allMixins;
