/**
 * BlendModes - Maps blend mode names to Canvas2D globalCompositeOperation values.
 */
export const BlendModes = {
    // Blend mode identifiers
    NORMAL: 'normal',
    MULTIPLY: 'multiply',
    SCREEN: 'screen',
    OVERLAY: 'overlay',
    DARKEN: 'darken',
    LIGHTEN: 'lighten',
    COLOR_DODGE: 'color-dodge',
    COLOR_BURN: 'color-burn',
    HARD_LIGHT: 'hard-light',
    SOFT_LIGHT: 'soft-light',
    DIFFERENCE: 'difference',
    EXCLUSION: 'exclusion',
    HUE: 'hue',
    SATURATION: 'saturation',
    COLOR: 'color',
    LUMINOSITY: 'luminosity',

    /**
     * Get all blend modes for UI display.
     * @returns {Array<{id: string, name: string, group: string}>}
     */
    getAllModes() {
        return [
            { id: 'normal', name: 'Normal', group: 'basic' },
            { id: 'multiply', name: 'Multiply', group: 'darken' },
            { id: 'screen', name: 'Screen', group: 'lighten' },
            { id: 'overlay', name: 'Overlay', group: 'contrast' },
            { id: 'darken', name: 'Darken', group: 'darken' },
            { id: 'lighten', name: 'Lighten', group: 'lighten' },
            { id: 'color-dodge', name: 'Color Dodge', group: 'lighten' },
            { id: 'color-burn', name: 'Color Burn', group: 'darken' },
            { id: 'hard-light', name: 'Hard Light', group: 'contrast' },
            { id: 'soft-light', name: 'Soft Light', group: 'contrast' },
            { id: 'difference', name: 'Difference', group: 'inversion' },
            { id: 'exclusion', name: 'Exclusion', group: 'inversion' },
            { id: 'hue', name: 'Hue', group: 'component' },
            { id: 'saturation', name: 'Saturation', group: 'component' },
            { id: 'color', name: 'Color', group: 'component' },
            { id: 'luminosity', name: 'Luminosity', group: 'component' }
        ];
    },

    /**
     * Convert blend mode name to Canvas2D composite operation.
     * @param {string} blendMode
     * @returns {string}
     */
    toCompositeOperation(blendMode) {
        const mapping = {
            'normal': 'source-over',
            'multiply': 'multiply',
            'screen': 'screen',
            'overlay': 'overlay',
            'darken': 'darken',
            'lighten': 'lighten',
            'color-dodge': 'color-dodge',
            'color-burn': 'color-burn',
            'hard-light': 'hard-light',
            'soft-light': 'soft-light',
            'difference': 'difference',
            'exclusion': 'exclusion',
            'hue': 'hue',
            'saturation': 'saturation',
            'color': 'color',
            'luminosity': 'luminosity'
        };
        return mapping[blendMode] || 'source-over';
    }
};
