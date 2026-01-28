/**
 * ExportConfig - Defines supported export formats and their options.
 *
 * Each format entry describes:
 *   - id: unique key (used as value in select)
 *   - label: display name
 *   - mimeType: MIME type for canvas.toBlob()
 *   - extension: file extension
 *   - supportsTransparency: whether alpha channel is preserved
 *   - options: array of configurable options (quality, bit depth, etc.)
 *
 * Option types:
 *   - range: numeric slider (min, max, step, default)
 *   - select: dropdown (choices: [{value, label}], default)
 *   - checkbox: boolean toggle (default)
 */

export const EXPORT_FORMATS = [
    {
        id: 'png',
        label: 'PNG',
        mimeType: 'image/png',
        extension: 'png',
        supportsTransparency: true,
        options: [
            {
                id: 'bitDepth',
                label: 'Color Depth',
                type: 'select',
                choices: [
                    { value: 8, label: '8-bit (24/32-bit color)' },
                ],
                default: 8,
            },
        ],
    },
    {
        id: 'jpeg',
        label: 'JPEG',
        mimeType: 'image/jpeg',
        extension: 'jpg',
        supportsTransparency: false,
        options: [
            {
                id: 'quality',
                label: 'Quality',
                type: 'range',
                min: 1,
                max: 100,
                step: 1,
                default: 92,
                unit: '%',
            },
        ],
    },
    {
        id: 'webp',
        label: 'WebP',
        mimeType: 'image/webp',
        extension: 'webp',
        supportsTransparency: true,
        options: [
            {
                id: 'quality',
                label: 'Quality',
                type: 'range',
                min: 1,
                max: 100,
                step: 1,
                default: 90,
                unit: '%',
            },
            {
                id: 'lossless',
                label: 'Lossless',
                type: 'checkbox',
                default: false,
            },
        ],
    },
    {
        id: 'avif',
        label: 'AVIF',
        mimeType: 'image/avif',
        extension: 'avif',
        supportsTransparency: true,
        options: [
            {
                id: 'quality',
                label: 'Quality',
                type: 'range',
                min: 1,
                max: 100,
                step: 1,
                default: 80,
                unit: '%',
            },
        ],
    },
    {
        id: 'bmp',
        label: 'BMP',
        mimeType: 'image/bmp',
        extension: 'bmp',
        supportsTransparency: false,
        options: [],
    },
    {
        id: 'svg',
        label: 'SVG (vector layers only)',
        mimeType: 'image/svg+xml',
        extension: 'svg',
        supportsTransparency: true,
        vectorOnly: true,
        options: [],
    },
];

/**
 * Accepted file extensions for opening images.
 * Used by the file open dialog.
 */
export const OPEN_IMAGE_ACCEPT = {
    'image/*': [
        '.png', '.jpg', '.jpeg', '.gif', '.bmp',
        '.webp', '.avif', '.svg', '.ico', '.tiff', '.tif',
    ],
    'application/zip': ['.sfr'],
};

/**
 * Accept string for fallback <input type="file"> element.
 */
export const OPEN_IMAGE_ACCEPT_STRING =
    '.sfr,.png,.jpg,.jpeg,.gif,.bmp,.webp,.avif,.svg,.ico,.tiff,.tif';

/**
 * Image file extensions (not .sfr) for detecting image files vs documents.
 */
export const IMAGE_EXTENSIONS = new Set([
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'avif', 'svg', 'ico', 'tiff', 'tif',
]);

/**
 * Get a format config by id.
 * @param {string} id
 * @returns {Object|undefined}
 */
export function getFormatById(id) {
    return EXPORT_FORMATS.find(f => f.id === id);
}

/**
 * Build default export options for a format.
 * @param {string} formatId
 * @returns {Object} key-value of option defaults
 */
export function getDefaultOptions(formatId) {
    const fmt = getFormatById(formatId);
    if (!fmt) return {};
    const opts = {};
    for (const opt of fmt.options) {
        opts[opt.id] = opt.default;
    }
    return opts;
}
