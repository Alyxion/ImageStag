/**
 * BrushPresets - Predefined brush configurations.
 */
export const BrushPresets = [
    { id: 'hard-round-sm', name: 'Hard Round Small', size: 5, hardness: 100, opacity: 100, flow: 100 },
    { id: 'hard-round-md', name: 'Hard Round Medium', size: 20, hardness: 100, opacity: 100, flow: 100 },
    { id: 'hard-round-lg', name: 'Hard Round Large', size: 50, hardness: 100, opacity: 100, flow: 100 },
    { id: 'soft-round-sm', name: 'Soft Round Small', size: 10, hardness: 0, opacity: 100, flow: 100 },
    { id: 'soft-round-md', name: 'Soft Round Medium', size: 30, hardness: 0, opacity: 100, flow: 100 },
    { id: 'soft-round-lg', name: 'Soft Round Large', size: 60, hardness: 0, opacity: 100, flow: 100 },
    { id: 'airbrush', name: 'Airbrush', size: 40, hardness: 0, opacity: 50, flow: 30 },
    { id: 'pencil', name: 'Pencil', size: 2, hardness: 100, opacity: 100, flow: 100 },
    { id: 'marker', name: 'Marker', size: 15, hardness: 80, opacity: 80, flow: 100 },
    { id: 'chalk', name: 'Chalk', size: 25, hardness: 50, opacity: 70, flow: 60 },
];

export const DEFAULT_PRESET = 'hard-round-md';

/**
 * Get a preset by ID.
 */
export function getPreset(id) {
    return BrushPresets.find(p => p.id === id);
}

/**
 * Get the default preset.
 */
export function getDefaultPreset() {
    return getPreset(DEFAULT_PRESET);
}
