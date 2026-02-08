/**
 * Editor Configuration
 *
 * Centralized configuration for the canvas editor.
 * All constants, defaults, and configuration values should be defined here.
 */

export const blendModes = [
    'normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten',
    'color-dodge', 'color-burn', 'hard-light', 'soft-light', 'difference', 'exclusion'
];

export const filterCategories = [
    { id: 'blur', name: 'Blur & Smooth' },
    { id: 'color', name: 'Color Adjustments' },
    { id: 'edge', name: 'Edge Detection' },
    { id: 'sharpen', name: 'Sharpen' },
    { id: 'noise', name: 'Noise' },
    { id: 'artistic', name: 'Artistic Effects' },
    { id: 'morphology', name: 'Morphological' },
    { id: 'uncategorized', name: 'Other' }
];

export const filterCategoryOrder = filterCategories.map(c => c.id);

export const filterCategoryNames = Object.fromEntries(
    filterCategories.map(c => [c.id, c.name])
);

export const fonts = [
    'Arial', 'Helvetica', 'Times New Roman', 'Georgia',
    'Courier New', 'Verdana', 'Impact'
];

export const colors = {
    common: [
        '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF', '#FFFF00',
        '#FF00FF', '#00FFFF', '#FF8000', '#8000FF', '#00FF80', '#FF0080'
    ],
    palette: [
        ['#000000', '#1a1a1a', '#333333', '#4d4d4d', '#666666', '#808080', '#999999', '#b3b3b3', '#cccccc', '#e6e6e6', '#f2f2f2', '#FFFFFF'],
        ['#330000', '#660000', '#990000', '#cc0000', '#ff0000', '#ff3333', '#ff6666', '#ff9999', '#ffcccc', '#ffe6e6', '#fff2f2', '#fffffa'],
        ['#331a00', '#663300', '#994d00', '#cc6600', '#ff8000', '#ff9933', '#ffb366', '#ffcc99', '#ffe6cc', '#fff2e6', '#fffaf2', '#ffffee'],
        ['#003300', '#006600', '#009900', '#00cc00', '#00ff00', '#33ff33', '#66ff66', '#99ff99', '#ccffcc', '#e6ffe6', '#f2fff2', '#f8fff8'],
        ['#003333', '#006666', '#009999', '#00cccc', '#00ffff', '#33ffff', '#66ffff', '#99ffff', '#ccffff', '#e6ffff', '#f2ffff', '#f8ffff'],
        ['#000033', '#000066', '#000099', '#0000cc', '#0000ff', '#3333ff', '#6666ff', '#9999ff', '#ccccff', '#e6e6ff', '#f2f2ff', '#f8f8ff'],
        ['#330033', '#660066', '#990099', '#cc00cc', '#ff00ff', '#ff33ff', '#ff66ff', '#ff99ff', '#ffccff', '#ffe6ff', '#fff2ff', '#fffaff'],
        ['#4a3728', '#6b4423', '#8b5a2b', '#a0522d', '#cd853f', '#deb887', '#f5deb3', '#ffe4c4', '#ffefd5', '#fff8dc', '#fffaf0', '#fffef8']
    ]
};

export const defaults = {
    canvasWidth: 800,
    canvasHeight: 600,
    theme: 'dark',
    uiMode: 'desktop',
    defaultTool: 'brush',
    autoSaveInterval: 5000,
    memoryMax: 256 * 1024 * 1024,  // 256 MB
    memoryWarningPercent: 75
};

export const limitedModeDefaults = {
    allowedTools: ['brush', 'eraser'],
    allowColorPicker: true,
    allowUndo: true,
    allowZoom: false,
    showFloatingToolbar: true,
    showFloatingColorPicker: true,
    showFloatingUndo: true,
    showNavigator: false,
    floatingToolbarPosition: 'top',
    enableKeyboardShortcuts: false
};

/**
 * UI icon mappings (non-tool icons)
 * Tool icons are defined on each tool class via static iconEntity
 */
export const icons = {
    // UI/Action icons
    'menu': '&#9776;',         // Hamburger
    'tools': '&#128295;',      // Wrench
    'panels': '&#9881;',       // Gear
    'undo': '&#8630;',         // Undo arrow
    'redo': '&#8631;',         // Redo arrow
    'navigator': '&#9635;',    // Navigation
    'layers': '&#9776;',       // Stacked
    'history': '&#128337;',    // Clock
    'settings': '&#9881;',     // Gear
    'close': '&#10005;',       // X
    'plus': '&#43;',           // Plus
    'minus': '&#8722;',        // Minus
    'zoom-in': '&#128269;',    // Magnifier
    'zoom-out': '&#128270;',   // Magnifier minus
    'save': '&#128190;',       // Floppy disk
    'export': '&#128228;',     // Export arrow
    'file': '&#128196;',       // Document
    'edit': '&#9998;',         // Edit pencil
    'view': '&#128065;',       // Eye
    'filter': '&#128167;',     // Water drop
    'image': '&#128444;',      // Framed image
    'deselect': '&#10060;',    // X in box
};

/**
 * Get UI icon HTML entity by name
 * For tool icons, use getToolIcon from tools/index.js
 * @param {string} name - Icon name
 * @returns {string} HTML entity or default circle
 */
export function getIcon(name) {
    return icons[name] || '&#9679;';
}

/**
 * Get filter category display name
 * @param {string} categoryId - Category ID
 * @returns {string} Display name
 */
export function getCategoryName(categoryId) {
    return filterCategoryNames[categoryId] ||
           categoryId.charAt(0).toUpperCase() + categoryId.slice(1);
}

// Default export with all config
export default {
    blendModes,
    filterCategories,
    filterCategoryOrder,
    filterCategoryNames,
    fonts,
    colors,
    defaults,
    limitedModeDefaults,
    icons,
    getIcon,
    getCategoryName,
};
