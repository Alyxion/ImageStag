/**
 * ActionDispatcher - Routes actions to their handlers.
 *
 * Acts as the central hub for all user interactions across different UI modes.
 * Menu clicks, tool buttons, touch gestures, and keyboard shortcuts all route
 * through this dispatcher to execute the appropriate action.
 */
import { ActionRegistry, getAction } from '../config/ActionRegistry.js';
import { UIConfig } from '../config/UIConfig.js';
import { themeManager } from '../config/ThemeManager.js';

export class ActionDispatcher {
    /**
     * @param {Object} app - The application context
     * @param {Object} vueComponent - The Vue component instance for UI methods
     */
    constructor(app, vueComponent) {
        this.app = app;
        this.vue = vueComponent;
        this.handlers = new Map();
        this.beforeDispatch = [];
        this.afterDispatch = [];

        this.registerDefaultHandlers();
    }

    /**
     * Register all default action handlers.
     */
    registerDefaultHandlers() {
        // Tool selection
        this.handlers.set('selectTool', (params) => {
            if (this.app?.toolManager) {
                this.app.toolManager.select(params.toolId);
                return { success: true };
            }
            return { success: false, error: 'Tool manager not available' };
        });

        // Edit actions
        this.handlers.set('undo', () => {
            if (this.app?.history) {
                this.app.history.undo();
                this.vue?.updateHistory?.();
                this.vue?.updateLayerList?.();
                return { success: true };
            }
            return { success: false, error: 'History not available' };
        });

        this.handlers.set('redo', () => {
            if (this.app?.history) {
                this.app.history.redo();
                this.vue?.updateHistory?.();
                this.vue?.updateLayerList?.();
                return { success: true };
            }
            return { success: false, error: 'History not available' };
        });

        this.handlers.set('cut', () => {
            this.vue?.cut?.();
            return { success: true };
        });

        this.handlers.set('copy', () => {
            this.vue?.copy?.();
            return { success: true };
        });

        this.handlers.set('paste', () => {
            this.vue?.paste?.();
            return { success: true };
        });

        this.handlers.set('pasteInPlace', () => {
            this.vue?.pasteInPlace?.();
            return { success: true };
        });

        this.handlers.set('deleteSelection', () => {
            this.vue?.deleteSelection?.();
            return { success: true };
        });

        this.handlers.set('selectAll', () => {
            this.vue?.selectAll?.();
            return { success: true };
        });

        this.handlers.set('deselect', () => {
            this.vue?.deselect?.();
            return { success: true };
        });

        this.handlers.set('invertSelection', () => {
            this.vue?.invertSelection?.();
            return { success: true };
        });

        // View actions
        this.handlers.set('zoomIn', () => {
            this.vue?.zoomIn?.();
            return { success: true };
        });

        this.handlers.set('zoomOut', () => {
            this.vue?.zoomOut?.();
            return { success: true };
        });

        this.handlers.set('zoom100', () => {
            this.vue?.setZoomPercent?.(100);
            return { success: true };
        });

        this.handlers.set('fitToWindow', () => {
            this.vue?.fitToWindow?.();
            return { success: true };
        });

        this.handlers.set('togglePanel', (params) => {
            const panel = params.panel;
            if (panel === 'navigator') {
                this.vue.showNavigator = !this.vue.showNavigator;
            } else if (panel === 'layers') {
                this.vue.showLayerPanel = !this.vue.showLayerPanel;
            } else if (panel === 'history') {
                this.vue.showHistoryPanel = !this.vue.showHistoryPanel;
            }
            return { success: true };
        });

        // Color actions
        this.handlers.set('swapColors', () => {
            this.vue?.swapColors?.();
            return { success: true };
        });

        this.handlers.set('resetColors', () => {
            this.vue?.resetColors?.();
            return { success: true };
        });

        this.handlers.set('pickColor', (params) => {
            this.vue?.openColorPicker?.(params.target);
            return { success: true };
        });

        // Layer actions
        this.handlers.set('addLayer', () => {
            this.vue?.addLayer?.();
            return { success: true };
        });

        this.handlers.set('duplicateLayer', () => {
            this.vue?.duplicateLayer?.();
            return { success: true };
        });

        this.handlers.set('deleteLayer', () => {
            this.vue?.deleteLayer?.();
            return { success: true };
        });

        this.handlers.set('mergeDown', () => {
            this.vue?.mergeDown?.();
            return { success: true };
        });

        this.handlers.set('flattenImage', () => {
            this.vue?.flattenImage?.();
            return { success: true };
        });

        this.handlers.set('moveLayerUp', () => {
            this.vue?.moveLayerUp?.();
            return { success: true };
        });

        this.handlers.set('moveLayerDown', () => {
            this.vue?.moveLayerDown?.();
            return { success: true };
        });

        this.handlers.set('toggleLayerVisibility', () => {
            this.vue?.toggleLayerVisibility?.();
            return { success: true };
        });

        this.handlers.set('toggleLayerLock', () => {
            this.vue?.toggleLayerLock?.();
            return { success: true };
        });

        // File actions
        this.handlers.set('newDocument', () => {
            this.vue?.newDocument?.();
            return { success: true };
        });

        this.handlers.set('openFile', () => {
            this.vue?.openFile?.();
            return { success: true };
        });

        this.handlers.set('save', () => {
            this.vue?.save?.();
            return { success: true };
        });

        this.handlers.set('exportPng', () => {
            this.vue?.exportPng?.();
            return { success: true };
        });

        this.handlers.set('exportJpg', () => {
            this.vue?.exportJpg?.();
            return { success: true };
        });

        this.handlers.set('closeDocument', () => {
            this.vue?.closeDocument?.();
            return { success: true };
        });

        // Image actions
        this.handlers.set('resizeImage', () => {
            this.vue?.resizeImage?.();
            return { success: true };
        });

        this.handlers.set('canvasSize', () => {
            this.vue?.canvasSize?.();
            return { success: true };
        });

        this.handlers.set('flipHorizontal', () => {
            this.vue?.flipHorizontal?.();
            return { success: true };
        });

        this.handlers.set('flipVertical', () => {
            this.vue?.flipVertical?.();
            return { success: true };
        });

        this.handlers.set('rotate90CW', () => {
            this.vue?.rotate90CW?.();
            return { success: true };
        });

        this.handlers.set('rotate90CCW', () => {
            this.vue?.rotate90CCW?.();
            return { success: true };
        });

        // UI actions
        this.handlers.set('toggleTheme', () => {
            themeManager.toggle();
            return { success: true };
        });

        this.handlers.set('setTheme', (params) => {
            themeManager.setTheme(params.theme);
            return { success: true };
        });

        this.handlers.set('setMode', (params) => {
            UIConfig.setMode(params.mode);
            this.vue?.onModeChange?.(params.mode);
            return { success: true };
        });
    }

    /**
     * Register a custom handler.
     * @param {string} name - Handler name
     * @param {Function} handler - Handler function (params) => { success, error? }
     */
    registerHandler(name, handler) {
        this.handlers.set(name, handler);
    }

    /**
     * Add a hook to run before dispatch.
     * @param {Function} hook - (actionId, params) => void
     */
    addBeforeDispatch(hook) {
        this.beforeDispatch.push(hook);
    }

    /**
     * Add a hook to run after dispatch.
     * @param {Function} hook - (actionId, params, result) => void
     */
    addAfterDispatch(hook) {
        this.afterDispatch.push(hook);
    }

    /**
     * Dispatch an action by ID.
     * @param {string} actionId - The action ID from ActionRegistry
     * @param {Object} [extraParams] - Additional parameters to merge
     * @returns {{ success: boolean, error?: string }}
     */
    dispatch(actionId, extraParams = {}) {
        const action = getAction(actionId);
        if (!action) {
            console.warn(`Unknown action: ${actionId}`);
            return { success: false, error: `Unknown action: ${actionId}` };
        }

        // Check if action is allowed in current mode
        if (!this.isActionAllowed(actionId)) {
            console.warn(`Action not allowed in current mode: ${actionId}`);
            return { success: false, error: 'Action not allowed in current mode' };
        }

        // Run before hooks
        for (const hook of this.beforeDispatch) {
            try {
                hook(actionId, { ...action.params, ...extraParams });
            } catch (e) {
                console.error('Before dispatch hook error:', e);
            }
        }

        // Find and execute handler
        const handler = this.handlers.get(action.handler);
        if (!handler) {
            console.warn(`No handler registered for: ${action.handler}`);
            return { success: false, error: `No handler for: ${action.handler}` };
        }

        let result;
        try {
            const params = { ...action.params, ...extraParams };
            result = handler(params);
        } catch (e) {
            console.error(`Error executing action ${actionId}:`, e);
            result = { success: false, error: e.message };
        }

        // Run after hooks
        for (const hook of this.afterDispatch) {
            try {
                hook(actionId, { ...action.params, ...extraParams }, result);
            } catch (e) {
                console.error('After dispatch hook error:', e);
            }
        }

        return result || { success: true };
    }

    /**
     * Check if an action is allowed in the current mode.
     * @param {string} actionId
     * @returns {boolean}
     */
    isActionAllowed(actionId) {
        const mode = UIConfig.getMode();

        // All actions allowed in desktop and tablet modes
        if (mode !== 'limited') return true;

        // In limited mode, check restrictions
        const action = getAction(actionId);
        if (!action) return false;

        // Tool actions - check tool whitelist
        if (actionId.startsWith('tool.')) {
            const toolId = action.params?.toolId;
            return toolId ? UIConfig.isToolAllowed(toolId) : false;
        }

        // Feature-specific actions
        if (actionId.startsWith('view.zoom') && !UIConfig.isFeatureAllowed('zoom')) {
            return false;
        }

        if (actionId === 'edit.undo' && !UIConfig.isFeatureAllowed('undo')) {
            return false;
        }

        if (actionId === 'edit.redo' && !UIConfig.isFeatureAllowed('redo')) {
            return false;
        }

        if (actionId.startsWith('layer.') && !UIConfig.isFeatureAllowed('layerSwitch')) {
            // Allow visibility toggle even without layer switch
            if (actionId !== 'layer.toggleVisibility') {
                return false;
            }
        }

        // Color picker
        if (actionId.startsWith('color.pick') && !UIConfig.isFeatureAllowed('colorPicker')) {
            return false;
        }

        // File operations might be restricted
        const settings = UIConfig.getModeSettings();
        if (settings.singleDocument && (actionId === 'file.new' || actionId === 'file.close')) {
            return false;
        }

        return true;
    }

    /**
     * Get list of available actions for the current mode.
     * @returns {Array<{ id: string, action: Object }>}
     */
    getAvailableActions() {
        const result = [];
        for (const [id, action] of Object.entries(ActionRegistry)) {
            if (this.isActionAllowed(id)) {
                result.push({ id, ...action });
            }
        }
        return result;
    }

    /**
     * Get available tool actions for the current mode.
     * @returns {Array<{ id: string, action: Object }>}
     */
    getAvailableToolActions() {
        return this.getAvailableActions().filter(a => a.category === 'tool');
    }
}
