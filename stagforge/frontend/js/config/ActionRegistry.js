/**
 * ActionRegistry - Central registry of all available actions.
 *
 * Each action defines:
 * - handler: The method name to call on ActionDispatcher
 * - params: Default parameters for the action
 * - icon: Icon identifier for UI display
 * - label: Human-readable label
 * - shortcut: Keyboard shortcut (optional)
 * - category: Grouping category for menus
 */

export const ActionRegistry = {
    // ============================================================
    // TOOL SELECTION
    // ============================================================
    'tool.selection': {
        handler: 'selectTool',
        params: { toolId: 'selection' },
        icon: 'pointer',
        label: 'Selection',
        shortcut: 'M',
        category: 'tool'
    },
    'tool.move': {
        handler: 'selectTool',
        params: { toolId: 'move' },
        icon: 'move',
        label: 'Move',
        shortcut: 'V',
        category: 'tool'
    },
    'tool.hand': {
        handler: 'selectTool',
        params: { toolId: 'hand' },
        icon: 'hand',
        label: 'Hand',
        shortcut: 'H',
        category: 'tool'
    },
    'tool.brush': {
        handler: 'selectTool',
        params: { toolId: 'brush' },
        icon: 'brush',
        label: 'Brush',
        shortcut: 'B',
        category: 'tool'
    },
    'tool.pencil': {
        handler: 'selectTool',
        params: { toolId: 'pencil' },
        icon: 'pencil',
        label: 'Pencil',
        shortcut: 'N',
        category: 'tool'
    },
    'tool.eraser': {
        handler: 'selectTool',
        params: { toolId: 'eraser' },
        icon: 'eraser',
        label: 'Eraser',
        shortcut: 'E',
        category: 'tool'
    },
    'tool.fill': {
        handler: 'selectTool',
        params: { toolId: 'fill' },
        icon: 'fill',
        label: 'Fill',
        shortcut: 'G',
        category: 'tool'
    },
    'tool.gradient': {
        handler: 'selectTool',
        params: { toolId: 'gradient' },
        icon: 'gradient',
        label: 'Gradient',
        shortcut: 'G',
        category: 'tool'
    },
    'tool.eyedropper': {
        handler: 'selectTool',
        params: { toolId: 'eyedropper' },
        icon: 'eyedropper',
        label: 'Eyedropper',
        shortcut: 'I',
        category: 'tool'
    },
    'tool.line': {
        handler: 'selectTool',
        params: { toolId: 'line' },
        icon: 'line',
        label: 'Line',
        shortcut: 'L',
        category: 'tool'
    },
    'tool.rect': {
        handler: 'selectTool',
        params: { toolId: 'rect' },
        icon: 'square',
        label: 'Rectangle',
        shortcut: 'R',
        category: 'tool'
    },
    'tool.circle': {
        handler: 'selectTool',
        params: { toolId: 'circle' },
        icon: 'circle',
        label: 'Ellipse',
        shortcut: 'C',
        category: 'tool'
    },
    'tool.polygon': {
        handler: 'selectTool',
        params: { toolId: 'polygon' },
        icon: 'polygon',
        label: 'Polygon',
        shortcut: 'P',
        category: 'tool'
    },
    'tool.text': {
        handler: 'selectTool',
        params: { toolId: 'text' },
        icon: 'text',
        label: 'Text',
        shortcut: 'T',
        category: 'tool'
    },
    'tool.crop': {
        handler: 'selectTool',
        params: { toolId: 'crop' },
        icon: 'crop',
        label: 'Crop',
        shortcut: '',
        category: 'tool'
    },
    'tool.lasso': {
        handler: 'selectTool',
        params: { toolId: 'lasso' },
        icon: 'lasso',
        label: 'Lasso',
        shortcut: '',
        category: 'tool'
    },
    'tool.magicwand': {
        handler: 'selectTool',
        params: { toolId: 'magicwand' },
        icon: 'wand',
        label: 'Magic Wand',
        shortcut: 'W',
        category: 'tool'
    },
    'tool.pen': {
        handler: 'selectTool',
        params: { toolId: 'pen' },
        icon: 'pen',
        label: 'Pen',
        shortcut: '',
        category: 'tool'
    },
    'tool.shape': {
        handler: 'selectTool',
        params: { toolId: 'shape' },
        icon: 'shapes',
        label: 'Shape',
        shortcut: 'U',
        category: 'tool'
    },
    'tool.vectorshapeedit': {
        handler: 'selectTool',
        params: { toolId: 'vectorshapeedit' },
        icon: 'node',
        label: 'Edit Vector',
        shortcut: '',
        category: 'tool'
    },
    'tool.blur': {
        handler: 'selectTool',
        params: { toolId: 'blur' },
        icon: 'blur',
        label: 'Blur',
        shortcut: '',
        category: 'tool'
    },
    'tool.sharpen': {
        handler: 'selectTool',
        params: { toolId: 'sharpen' },
        icon: 'sharpen',
        label: 'Sharpen',
        shortcut: '',
        category: 'tool'
    },
    'tool.smudge': {
        handler: 'selectTool',
        params: { toolId: 'smudge' },
        icon: 'smudge',
        label: 'Smudge',
        shortcut: '',
        category: 'tool'
    },
    'tool.dodge': {
        handler: 'selectTool',
        params: { toolId: 'dodge' },
        icon: 'dodge',
        label: 'Dodge',
        shortcut: 'O',
        category: 'tool'
    },
    'tool.burn': {
        handler: 'selectTool',
        params: { toolId: 'burn' },
        icon: 'burn',
        label: 'Burn',
        shortcut: '',
        category: 'tool'
    },
    'tool.sponge': {
        handler: 'selectTool',
        params: { toolId: 'sponge' },
        icon: 'sponge',
        label: 'Sponge',
        shortcut: '',
        category: 'tool'
    },
    'tool.spray': {
        handler: 'selectTool',
        params: { toolId: 'spray' },
        icon: 'spray',
        label: 'Spray',
        shortcut: 'A',
        category: 'tool'
    },
    'tool.clonestamp': {
        handler: 'selectTool',
        params: { toolId: 'clonestamp' },
        icon: 'stamp',
        label: 'Clone Stamp',
        shortcut: 'S',
        category: 'tool'
    },

    // ============================================================
    // EDIT ACTIONS
    // ============================================================
    'edit.undo': {
        handler: 'undo',
        icon: 'undo',
        label: 'Undo',
        shortcut: 'Ctrl+Z',
        category: 'edit'
    },
    'edit.redo': {
        handler: 'redo',
        icon: 'redo',
        label: 'Redo',
        shortcut: 'Ctrl+Y',
        category: 'edit'
    },
    'edit.cut': {
        handler: 'cut',
        icon: 'cut',
        label: 'Cut',
        shortcut: 'Ctrl+X',
        category: 'edit'
    },
    'edit.copy': {
        handler: 'copy',
        icon: 'copy',
        label: 'Copy',
        shortcut: 'Ctrl+C',
        category: 'edit'
    },
    'edit.paste': {
        handler: 'paste',
        icon: 'paste',
        label: 'Paste',
        shortcut: 'Ctrl+V',
        category: 'edit'
    },
    'edit.pasteInPlace': {
        handler: 'pasteInPlace',
        icon: 'paste',
        label: 'Paste in Place',
        shortcut: 'Ctrl+Shift+V',
        category: 'edit'
    },
    'edit.delete': {
        handler: 'deleteSelection',
        icon: 'delete',
        label: 'Delete',
        shortcut: 'Delete',
        category: 'edit'
    },
    'edit.selectAll': {
        handler: 'selectAll',
        icon: 'select-all',
        label: 'Select All',
        shortcut: 'Ctrl+A',
        category: 'edit'
    },
    'edit.deselect': {
        handler: 'deselect',
        icon: 'deselect',
        label: 'Deselect',
        shortcut: 'Ctrl+D',
        category: 'edit'
    },
    'edit.invertSelection': {
        handler: 'invertSelection',
        icon: 'invert',
        label: 'Invert Selection',
        shortcut: 'Ctrl+Shift+I',
        category: 'edit'
    },

    // ============================================================
    // VIEW ACTIONS
    // ============================================================
    'view.zoomIn': {
        handler: 'zoomIn',
        icon: 'zoom-in',
        label: 'Zoom In',
        shortcut: 'Ctrl++',
        category: 'view'
    },
    'view.zoomOut': {
        handler: 'zoomOut',
        icon: 'zoom-out',
        label: 'Zoom Out',
        shortcut: 'Ctrl+-',
        category: 'view'
    },
    'view.zoom100': {
        handler: 'zoom100',
        icon: 'zoom-100',
        label: 'Actual Pixels',
        shortcut: 'Ctrl+1',
        category: 'view'
    },
    'view.fitToWindow': {
        handler: 'fitToWindow',
        icon: 'fit',
        label: 'Fit to Window',
        shortcut: 'Ctrl+0',
        category: 'view'
    },
    'view.toggleNavigator': {
        handler: 'togglePanel',
        params: { panel: 'navigator' },
        icon: 'navigator',
        label: 'Navigator',
        shortcut: '',
        category: 'view'
    },
    'view.toggleLayers': {
        handler: 'togglePanel',
        params: { panel: 'layers' },
        icon: 'layers',
        label: 'Layers',
        shortcut: 'F7',
        category: 'view'
    },
    'view.toggleHistory': {
        handler: 'togglePanel',
        params: { panel: 'history' },
        icon: 'history',
        label: 'History',
        shortcut: '',
        category: 'view'
    },

    // ============================================================
    // COLOR ACTIONS
    // ============================================================
    'color.swapFgBg': {
        handler: 'swapColors',
        icon: 'swap',
        label: 'Swap Colors',
        shortcut: 'X',
        category: 'color'
    },
    'color.pickForeground': {
        handler: 'pickColor',
        params: { target: 'foreground' },
        icon: 'color-fg',
        label: 'Foreground Color',
        shortcut: '',
        category: 'color'
    },
    'color.pickBackground': {
        handler: 'pickColor',
        params: { target: 'background' },
        icon: 'color-bg',
        label: 'Background Color',
        shortcut: '',
        category: 'color'
    },

    // ============================================================
    // LAYER ACTIONS
    // ============================================================
    'layer.add': {
        handler: 'addLayer',
        icon: 'layer-add',
        label: 'New Layer',
        shortcut: 'Ctrl+Shift+N',
        category: 'layer'
    },
    'layer.duplicate': {
        handler: 'duplicateLayer',
        icon: 'layer-duplicate',
        label: 'Duplicate Layer',
        shortcut: 'Ctrl+J',
        category: 'layer'
    },
    'layer.delete': {
        handler: 'deleteLayer',
        icon: 'layer-delete',
        label: 'Delete Layer',
        shortcut: '',
        category: 'layer'
    },
    'layer.mergeDown': {
        handler: 'mergeDown',
        icon: 'layer-merge',
        label: 'Merge Down',
        shortcut: 'Ctrl+E',
        category: 'layer'
    },
    'layer.flatten': {
        handler: 'flattenImage',
        icon: 'flatten',
        label: 'Flatten Image',
        shortcut: 'Ctrl+Shift+E',
        category: 'layer'
    },
    'layer.moveUp': {
        handler: 'moveLayerUp',
        icon: 'arrow-up',
        label: 'Move Up',
        shortcut: 'Ctrl+]',
        category: 'layer'
    },
    'layer.moveDown': {
        handler: 'moveLayerDown',
        icon: 'arrow-down',
        label: 'Move Down',
        shortcut: 'Ctrl+[',
        category: 'layer'
    },
    'layer.toggleVisibility': {
        handler: 'toggleLayerVisibility',
        icon: 'eye',
        label: 'Toggle Visibility',
        shortcut: '',
        category: 'layer'
    },
    'layer.toggleLock': {
        handler: 'toggleLayerLock',
        icon: 'lock',
        label: 'Toggle Lock',
        shortcut: '',
        category: 'layer'
    },

    // ============================================================
    // FILE ACTIONS
    // ============================================================
    'file.new': {
        handler: 'newDocument',
        icon: 'file-new',
        label: 'New',
        shortcut: 'Ctrl+N',
        category: 'file'
    },
    'file.open': {
        handler: 'openFile',
        icon: 'folder-open',
        label: 'Open',
        shortcut: 'Ctrl+O',
        category: 'file'
    },
    'file.save': {
        handler: 'save',
        icon: 'save',
        label: 'Save',
        shortcut: 'Ctrl+S',
        category: 'file'
    },
    'file.exportPng': {
        handler: 'exportPng',
        icon: 'export',
        label: 'Export PNG',
        shortcut: 'Ctrl+Shift+S',
        category: 'file'
    },
    'file.exportJpg': {
        handler: 'exportJpg',
        icon: 'export',
        label: 'Export JPEG',
        shortcut: '',
        category: 'file'
    },
    'file.close': {
        handler: 'closeDocument',
        icon: 'close',
        label: 'Close',
        shortcut: 'Ctrl+W',
        category: 'file'
    },

    // ============================================================
    // IMAGE ACTIONS
    // ============================================================
    'image.resize': {
        handler: 'resizeImage',
        icon: 'resize',
        label: 'Resize Image',
        shortcut: '',
        category: 'image'
    },
    'image.canvasSize': {
        handler: 'canvasSize',
        icon: 'canvas',
        label: 'Canvas Size',
        shortcut: '',
        category: 'image'
    },
    'image.flipHorizontal': {
        handler: 'flipHorizontal',
        icon: 'flip-h',
        label: 'Flip Horizontal',
        shortcut: '',
        category: 'image'
    },
    'image.flipVertical': {
        handler: 'flipVertical',
        icon: 'flip-v',
        label: 'Flip Vertical',
        shortcut: '',
        category: 'image'
    },
    'image.rotate90cw': {
        handler: 'rotate90CW',
        icon: 'rotate-cw',
        label: 'Rotate 90° CW',
        shortcut: '',
        category: 'image'
    },
    'image.rotate90ccw': {
        handler: 'rotate90CCW',
        icon: 'rotate-ccw',
        label: 'Rotate 90° CCW',
        shortcut: '',
        category: 'image'
    },

    // ============================================================
    // UI ACTIONS
    // ============================================================
    'ui.toggleTheme': {
        handler: 'toggleTheme',
        icon: 'theme',
        label: 'Toggle Theme',
        shortcut: '',
        category: 'ui'
    },
    'ui.setDarkTheme': {
        handler: 'setTheme',
        params: { theme: 'dark' },
        icon: 'moon',
        label: 'Dark Theme',
        shortcut: '',
        category: 'ui'
    },
    'ui.setLightTheme': {
        handler: 'setTheme',
        params: { theme: 'light' },
        icon: 'sun',
        label: 'Light Theme',
        shortcut: '',
        category: 'ui'
    },
    'ui.setDesktopMode': {
        handler: 'setMode',
        params: { mode: 'desktop' },
        icon: 'desktop',
        label: 'Desktop Mode',
        shortcut: '',
        category: 'ui'
    },
    'ui.setTabletMode': {
        handler: 'setMode',
        params: { mode: 'tablet' },
        icon: 'tablet',
        label: 'Tablet Mode',
        shortcut: '',
        category: 'ui'
    },
    'ui.setLimitedMode': {
        handler: 'setMode',
        params: { mode: 'limited' },
        icon: 'minimize',
        label: 'Limited Mode',
        shortcut: '',
        category: 'ui'
    }
};

/**
 * Get actions by category.
 * @param {string} category
 * @returns {Object} Map of action ID to action config
 */
export function getActionsByCategory(category) {
    const result = {};
    for (const [id, action] of Object.entries(ActionRegistry)) {
        if (action.category === category) {
            result[id] = action;
        }
    }
    return result;
}

/**
 * Get all tool actions.
 * @returns {Object}
 */
export function getToolActions() {
    return getActionsByCategory('tool');
}

/**
 * Get action by ID.
 * @param {string} actionId
 * @returns {Object|null}
 */
export function getAction(actionId) {
    return ActionRegistry[actionId] || null;
}

/**
 * Find action by shortcut.
 * @param {string} shortcut - e.g., 'Ctrl+Z', 'B', 'Delete'
 * @returns {Object|null} { id, action } or null
 */
export function findActionByShortcut(shortcut) {
    for (const [id, action] of Object.entries(ActionRegistry)) {
        if (action.shortcut === shortcut) {
            return { id, action };
        }
    }
    return null;
}
