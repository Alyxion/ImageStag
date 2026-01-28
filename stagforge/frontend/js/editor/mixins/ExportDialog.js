/**
 * ExportDialog Mixin
 *
 * Handles the Export As dialog and Export Again (re-export with last settings).
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 */
import { EXPORT_FORMATS, getFormatById, getDefaultOptions } from '../../config/ExportConfig.js';

export const ExportDialogMixin = {
    data() {
        return {
            exportDialogVisible: false,
            exportFormat: 'png',
            exportOptions: {},
            exportTransparent: true,
            exportFilename: 'export',
            // Remembers last export settings for "Export Again"
            _lastExportSettings: null,
        };
    },
    computed: {
        exportFormats() {
            return EXPORT_FORMATS.filter(f => !f.vectorOnly);
        },
        currentExportFormat() {
            return getFormatById(this.exportFormat);
        },
        hasLastExport() {
            return !!this._lastExportSettings;
        },
    },
    methods: {
        /**
         * Show the export dialog.
         */
        showExportDialog() {
            const app = this.getState();
            const doc = app?.documentManager?.getActiveDocument();
            this.exportFilename = doc?.name || 'export';

            // Restore last settings or defaults
            if (this._lastExportSettings) {
                this.exportFormat = this._lastExportSettings.format;
                this.exportOptions = { ...this._lastExportSettings.options };
                this.exportTransparent = this._lastExportSettings.transparent;
            } else {
                this.exportFormat = 'png';
                this.exportOptions = getDefaultOptions('png');
                this.exportTransparent = true;
            }
            this.exportDialogVisible = true;
        },

        /**
         * Called when the format dropdown changes — reset options to defaults for new format.
         */
        onExportFormatChange() {
            this.exportOptions = getDefaultOptions(this.exportFormat);
            const fmt = getFormatById(this.exportFormat);
            if (fmt && !fmt.supportsTransparency) {
                this.exportTransparent = false;
            }
        },

        /**
         * Execute the export with current dialog settings.
         */
        async doExport() {
            const settings = {
                format: this.exportFormat,
                options: { ...this.exportOptions },
                transparent: this.exportTransparent,
                filename: this.exportFilename,
            };

            this._lastExportSettings = settings;
            this.exportDialogVisible = false;
            await this._executeExport(settings);
        },

        /**
         * Re-export with the last used settings (Export Again).
         */
        async exportAgain() {
            if (!this._lastExportSettings) {
                this.showExportDialog();
                return;
            }
            // Update filename from current document
            const app = this.getState();
            const doc = app?.documentManager?.getActiveDocument();
            const settings = {
                ...this._lastExportSettings,
                filename: doc?.name || this._lastExportSettings.filename,
            };
            await this._executeExport(settings);
        },

        /**
         * Flatten the document to a canvas, then export.
         * @param {Object} settings - Export settings
         */
        async _executeExport(settings) {
            const app = this.getState();
            if (!app?.layerStack) return;

            const fmt = getFormatById(settings.format);
            if (!fmt) return;

            const w = app.layerStack.width;
            const h = app.layerStack.height;
            const flatCanvas = document.createElement('canvas');
            flatCanvas.width = w;
            flatCanvas.height = h;
            const ctx = flatCanvas.getContext('2d');

            // Background
            if (!settings.transparent || !fmt.supportsTransparency) {
                ctx.fillStyle = '#FFFFFF';
                ctx.fillRect(0, 0, w, h);
            }

            // Composite visible layers (bottom to top)
            for (let i = app.layerStack.layers.length - 1; i >= 0; i--) {
                const layer = app.layerStack.layers[i];
                if (!layer.visible || layer.isGroup?.()) continue;

                // Layer effects
                if (layer.hasEffects?.() && window.effectRenderer) {
                    const rendered = window.effectRenderer.getRenderedLayer(layer);
                    if (rendered) {
                        if (rendered.behindCanvas) {
                            ctx.globalAlpha = layer.opacity;
                            ctx.drawImage(rendered.behindCanvas, rendered.offsetX, rendered.offsetY);
                        }
                        ctx.globalAlpha = layer.opacity;
                        ctx.drawImage(rendered.contentCanvas, rendered.offsetX, rendered.offsetY);
                    } else {
                        ctx.globalAlpha = layer.opacity;
                        ctx.drawImage(layer.canvas, layer.offsetX || 0, layer.offsetY || 0);
                    }
                } else {
                    ctx.globalAlpha = layer.opacity;
                    ctx.drawImage(layer.canvas, layer.offsetX || 0, layer.offsetY || 0);
                }
            }
            ctx.globalAlpha = 1.0;

            // Determine quality parameter
            let quality = undefined;
            if (settings.options.quality !== undefined) {
                quality = settings.options.quality / 100;
            }
            // WebP lossless: quality 1.0 signals lossless in Chrome
            if (settings.format === 'webp' && settings.options.lossless) {
                quality = 1.0;
            }

            const mimeType = fmt.mimeType;

            let blob;
            if (settings.format === 'bmp') {
                blob = this._canvasToBMP(flatCanvas);
            } else {
                blob = await new Promise(resolve => {
                    flatCanvas.toBlob(resolve, mimeType, quality);
                });
                if (!blob) {
                    blob = await new Promise(resolve => {
                        flatCanvas.toBlob(resolve, 'image/png');
                    });
                }
            }

            if (!blob) return;

            // Download
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.download = `${settings.filename}.${fmt.extension}`;
            link.href = url;
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 5000);
        },

        /**
         * Convert a canvas to a BMP Blob (uncompressed 24-bit).
         * @param {HTMLCanvasElement} canvas
         * @returns {Blob}
         */
        _canvasToBMP(canvas) {
            const w = canvas.width;
            const h = canvas.height;
            const ctx = canvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, w, h);
            const pixels = imageData.data;

            const rowSize = Math.ceil((w * 3) / 4) * 4; // Rows padded to 4-byte boundary
            const pixelDataSize = rowSize * h;
            const fileSize = 54 + pixelDataSize;
            const buf = new ArrayBuffer(fileSize);
            const view = new DataView(buf);

            // BMP file header (14 bytes)
            view.setUint8(0, 0x42); // 'B'
            view.setUint8(1, 0x4D); // 'M'
            view.setUint32(2, fileSize, true);
            view.setUint32(6, 0, true);
            view.setUint32(10, 54, true);

            // DIB header (40 bytes - BITMAPINFOHEADER)
            view.setUint32(14, 40, true);
            view.setInt32(18, w, true);
            view.setInt32(22, h, true);
            view.setUint16(26, 1, true); // planes
            view.setUint16(28, 24, true); // bits per pixel
            view.setUint32(30, 0, true); // compression (none)
            view.setUint32(34, pixelDataSize, true);
            view.setUint32(38, 2835, true); // h-res (72 DPI)
            view.setUint32(42, 2835, true); // v-res
            view.setUint32(46, 0, true);
            view.setUint32(50, 0, true);

            // Pixel data (bottom-up, BGR)
            let offset = 54;
            for (let y = h - 1; y >= 0; y--) {
                for (let x = 0; x < w; x++) {
                    const i = (y * w + x) * 4;
                    view.setUint8(offset++, pixels[i + 2]); // B
                    view.setUint8(offset++, pixels[i + 1]); // G
                    view.setUint8(offset++, pixels[i]);     // R
                }
                // Pad row to 4-byte boundary
                while (offset % 4 !== 0) {
                    view.setUint8(offset++, 0);
                }
            }

            return new Blob([buf], { type: 'image/bmp' });
        },
    },
};

export default ExportDialogMixin;
