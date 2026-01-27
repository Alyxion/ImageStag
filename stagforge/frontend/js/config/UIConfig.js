/**
 * UIConfig - Configuration for UI modes and settings.
 *
 * Manages:
 * - Current UI mode (desktop, tablet, limited)
 * - Mode-specific settings
 * - Persistence of preferences
 */

/**
 * Default configuration values
 */
const DEFAULTS = {
    mode: 'desktop',

    // Filter execution settings
    filters: {
        executionMode: 'js',            // 'js' (WASM in browser, default) or 'server' (Python backend)
    },

    // Rendering settings (applies to all modes)
    rendering: {
        // Vector layer rendering
        vectorSVGRendering: true,       // Render vector layers via SVG (true) or Canvas 2D (false)
        vectorSupersampleLevel: 3,      // Supersampling multiplier (1 = off, 2-4 recommended)
        vectorAntialiasing: false,      // Use geometricPrecision (true) or crispEdges (false)
                                        // Note: crispEdges gives exact cross-platform parity
    },

    // Desktop mode settings (full interface)
    desktopMode: {
        showMenuBar: true,
        showDocumentTabs: true,
        showRibbon: true,
        showToolPanel: true,
        showRightPanel: true,
        showStatusBar: true,
        showColorPalette: true,
        showNavigator: true,
        showLayerPanel: true,
        showHistoryPanel: true
    },

    // Tablet mode settings (touch-optimized)
    tabletMode: {
        buttonSize: 56,          // Touch target size in px (minimum 48px recommended)
        showToolLabels: false,   // Icons only
        gestureZoom: true,       // Pinch to zoom
        gesturePan: true,        // Two-finger pan
        showBottomBar: true,     // Tool properties at bottom
        swipeToolSwitch: false   // Swipe to switch tools
    },

    // Tablet mode visibility settings
    tabletModeUI: {
        showTopBar: true,                           // Icon toolbar at top
        showToolStrip: true,                        // Tool icons on left
        showBottomBar: true,                        // Properties bar at bottom
        showStatusBar: true,                        // Status bar at bottom
        showNavigatorPanel: true,                   // Navigator floating panel
        showLayersPanel: true,                      // Layers floating panel
        showHistoryPanel: true,                     // History floating panel
    },

    // Limited mode settings (minimal UI, configurable)
    limitedMode: {
        // Tool restrictions
        allowedTools: ['brush', 'eraser'],          // Whitelist of tool IDs
        fixedBrushSize: null,                       // null = adjustable, number = fixed size
        fixedEraserSize: null,                      // null = adjustable, number = fixed size
        fixedBrushColor: null,                      // null = user can choose, string = fixed color

        // Feature flags
        allowZoom: false,
        allowPan: true,
        allowUndo: true,
        allowRedo: false,
        allowColorPicker: true,
        allowLayerSwitch: false,                    // Can user switch between layers?
        allowSizeAdjust: true,                      // Can user adjust brush/eraser size?

        // Keyboard shortcuts - disable all by default in limited mode
        enableKeyboardShortcuts: false,

        // Background layer support (for kids drawing app scenario)
        // When set, these layers are visible but cannot be edited
        lockedLayerIds: [],                         // Array of layer IDs that are locked
        backgroundImageUrl: null,                   // Optional: load this as background
        editableLayerIndex: -1,                     // Which layer is editable (-1 = topmost)

        // UI visibility - all optional floating elements
        showMenuBar: false,                         // Never show menu in limited mode
        showHeader: false,                          // Never show header/toolbar in limited mode
        showDocumentTabs: false,                    // No document tabs
        showStatusBar: false,                       // No status bar
        showNavigator: false,                       // Only show when zoomed (and allowZoom is true)
        showFloatingToolbar: true,                  // The floating tool buttons
        showFloatingColorPicker: true,              // Color picker panel
        showFloatingUndo: true,                     // Undo button (if allowUndo)
        showFloatingSizeSlider: true,               // Size adjustment (if allowSizeAdjust)
        floatingToolbarPosition: 'top',             // 'top', 'bottom', 'left', 'right'

        // Document settings
        singleDocument: true,                       // Disable multiple documents
        fixedCanvasSize: null,                      // null or {width, height}
        canvasBackgroundColor: '#FFFFFF'
    }
};

/**
 * UIConfig class - singleton configuration manager
 */
class UIConfigClass {
    constructor() {
        this.storageKey = 'stagforge-ui-config';
        this.listeners = [];
        this.config = this.deepClone(DEFAULTS);
    }

    /**
     * Initialize configuration by loading saved preferences.
     */
    init() {
        this.loadSavedConfig();
    }

    /**
     * Deep clone an object.
     * @param {Object} obj
     * @returns {Object}
     */
    deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    /**
     * Get current UI mode.
     * @returns {string} 'desktop', 'tablet', or 'limited'
     */
    getMode() {
        return this.config.mode;
    }

    /**
     * Set UI mode.
     * @param {string} mode - 'desktop', 'tablet', or 'limited'
     */
    setMode(mode) {
        if (!['desktop', 'tablet', 'limited'].includes(mode)) {
            console.warn(`Invalid mode: ${mode}. Using 'desktop'.`);
            mode = 'desktop';
        }

        const previousMode = this.config.mode;
        this.config.mode = mode;
        this.saveConfig();

        if (previousMode !== mode) {
            this.notifyListeners('mode', mode, previousMode);
        }
    }

    /**
     * Get mode-specific settings.
     * @param {string} [mode] - Mode to get settings for (defaults to current)
     * @returns {Object}
     */
    getModeSettings(mode = null) {
        mode = mode || this.config.mode;
        switch (mode) {
            case 'desktop':
                return { ...this.config.desktopMode };
            case 'tablet':
                return { ...this.config.tabletMode };
            case 'limited':
                return { ...this.config.limitedMode };
            default:
                return {};
        }
    }

    /**
     * Update mode-specific settings.
     * @param {string} mode - 'desktop', 'tablet', or 'limited'
     * @param {Object} settings - Settings to merge
     */
    updateModeSettings(mode, settings) {
        const key = `${mode}Mode`;
        if (this.config[key]) {
            Object.assign(this.config[key], settings);
            this.saveConfig();
            this.notifyListeners(`${mode}Settings`, this.config[key]);
        }
    }

    /**
     * Get a specific setting value.
     * @param {string} path - Dot-separated path (e.g., 'limitedMode.allowZoom')
     * @returns {*}
     */
    get(path) {
        const parts = path.split('.');
        let value = this.config;
        for (const part of parts) {
            if (value === undefined || value === null) return undefined;
            value = value[part];
        }
        return value;
    }

    /**
     * Set a specific setting value.
     * @param {string} path - Dot-separated path
     * @param {*} value
     */
    set(path, value) {
        const parts = path.split('.');
        let obj = this.config;
        for (let i = 0; i < parts.length - 1; i++) {
            if (obj[parts[i]] === undefined) {
                obj[parts[i]] = {};
            }
            obj = obj[parts[i]];
        }
        const lastKey = parts[parts.length - 1];
        const previousValue = obj[lastKey];
        obj[lastKey] = value;
        this.saveConfig();

        if (previousValue !== value) {
            this.notifyListeners(path, value, previousValue);
        }
    }

    /**
     * Check if a tool is allowed in the current mode.
     * @param {string} toolId
     * @returns {boolean}
     */
    isToolAllowed(toolId) {
        if (this.config.mode !== 'limited') return true;
        return this.config.limitedMode.allowedTools.includes(toolId);
    }

    /**
     * Check if a feature is allowed in the current mode.
     * @param {string} feature - 'zoom', 'pan', 'undo', 'redo', 'colorPicker', 'layerSwitch'
     * @returns {boolean}
     */
    isFeatureAllowed(feature) {
        if (this.config.mode !== 'limited') return true;

        const featureMap = {
            zoom: 'allowZoom',
            pan: 'allowPan',
            undo: 'allowUndo',
            redo: 'allowRedo',
            colorPicker: 'allowColorPicker',
            layerSwitch: 'allowLayerSwitch'
        };

        const key = featureMap[feature];
        return key ? this.config.limitedMode[key] !== false : true;
    }

    /**
     * Check if a layer is locked (non-editable).
     * @param {string} layerId
     * @returns {boolean}
     */
    isLayerLocked(layerId) {
        if (this.config.mode !== 'limited') return false;
        return this.config.limitedMode.lockedLayerIds.includes(layerId);
    }

    /**
     * Get the index of the editable layer in limited mode.
     * @returns {number} -1 for topmost, or specific index
     */
    getEditableLayerIndex() {
        if (this.config.mode !== 'limited') return -1;
        return this.config.limitedMode.editableLayerIndex;
    }

    /**
     * Save configuration to localStorage.
     */
    saveConfig() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.config));
        } catch (e) {
            console.warn('Could not save UI config:', e);
        }
    }

    /**
     * Load configuration from localStorage.
     */
    loadSavedConfig() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const parsed = JSON.parse(saved);
                // Deep merge with defaults to ensure all keys exist
                this.config = this.mergeDeep(this.deepClone(DEFAULTS), parsed);
            }
        } catch (e) {
            console.warn('Could not load UI config:', e);
        }
    }

    /**
     * Deep merge two objects.
     * @param {Object} target
     * @param {Object} source
     * @returns {Object}
     */
    mergeDeep(target, source) {
        for (const key of Object.keys(source)) {
            if (source[key] instanceof Object && key in target && target[key] instanceof Object) {
                this.mergeDeep(target[key], source[key]);
            } else {
                target[key] = source[key];
            }
        }
        return target;
    }

    /**
     * Reset configuration to defaults.
     */
    reset() {
        this.config = this.deepClone(DEFAULTS);
        this.saveConfig();
        this.notifyListeners('reset', this.config);
    }

    /**
     * Add a listener for config changes.
     * @param {Function} callback - Called with (key, newValue, previousValue)
     */
    addListener(callback) {
        this.listeners.push(callback);
    }

    /**
     * Remove a config change listener.
     * @param {Function} callback
     */
    removeListener(callback) {
        const idx = this.listeners.indexOf(callback);
        if (idx !== -1) {
            this.listeners.splice(idx, 1);
        }
    }

    /**
     * Notify all listeners of a config change.
     */
    notifyListeners(key, newValue, previousValue) {
        for (const listener of this.listeners) {
            try {
                listener(key, newValue, previousValue);
            } catch (e) {
                console.error('Config listener error:', e);
            }
        }
    }

    /**
     * Create a limited mode preset for a kids drawing app.
     * @param {Object} options
     * @returns {Object} Limited mode configuration
     */
    static createKidsDrawingPreset(options = {}) {
        return {
            allowedTools: options.tools || ['brush', 'eraser'],
            fixedBrushSize: options.brushSize || 30,
            fixedEraserSize: options.eraserSize || 40,
            fixedBrushColor: options.brushColor || null,
            allowZoom: false,
            allowPan: false,
            allowUndo: true,
            allowRedo: false,
            allowColorPicker: true,
            allowLayerSwitch: false,
            lockedLayerIds: options.lockedLayerIds || [],
            backgroundImageUrl: options.backgroundImage || null,
            editableLayerIndex: -1,  // Topmost layer
            showNavigator: false,
            showFloatingToolbar: true,
            showFloatingColorPicker: true,
            floatingToolbarPosition: 'top',
            singleDocument: true,
            fixedCanvasSize: options.canvasSize || null,
            canvasBackgroundColor: options.backgroundColor || '#FFFFFF'
        };
    }

    /**
     * Create a limited mode preset for annotation/markup.
     * @param {Object} options
     * @returns {Object} Limited mode configuration
     */
    static createAnnotationPreset(options = {}) {
        return {
            allowedTools: options.tools || ['brush', 'eraser', 'line', 'rect', 'text'],
            fixedBrushSize: null,
            fixedEraserSize: null,
            fixedBrushColor: null,
            allowZoom: true,
            allowPan: true,
            allowUndo: true,
            allowRedo: true,
            allowColorPicker: true,
            allowLayerSwitch: false,
            lockedLayerIds: options.lockedLayerIds || [],
            backgroundImageUrl: options.backgroundImage || null,
            editableLayerIndex: -1,
            showNavigator: true,
            showFloatingToolbar: true,
            showFloatingColorPicker: true,
            floatingToolbarPosition: 'top',
            singleDocument: true,
            fixedCanvasSize: null,
            canvasBackgroundColor: '#FFFFFF'
        };
    }
}

// Singleton instance
export const UIConfig = new UIConfigClass();

// Also export the class for creating custom instances
export { UIConfigClass };
