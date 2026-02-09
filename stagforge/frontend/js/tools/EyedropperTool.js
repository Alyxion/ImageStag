/**
 * EyedropperTool - Sample color from canvas.
 *
 * Sample sources:
 * - All Layers: composites all visible layers (no checkerboard)
 * - Current Layer: samples raw pixel from the active layer only
 */
import { Tool } from './Tool.js';

export class EyedropperTool extends Tool {
    static id = 'eyedropper';
    static name = 'Eyedropper';
    static icon = 'eyedropper';
    static iconEntity = '&#128167;';  // Eyeglasses
    static group = 'eyedropper';
    static groupShortcut = 'i';
    static priority = 10;
    static cursor = 'crosshair';
    static layerTypes = { raster: true, text: true, svg: true, group: false };

    constructor(app) {
        super(app);
        this.sampleSize = 1; // 1 = single pixel, 3 = 3x3 average, 5 = 5x5 average
        this.sampleSource = 'allLayers'; // 'allLayers' or 'currentLayer'

        // Live preview state
        this.previewColor = null;
        this.previewR = 0;
        this.previewG = 0;
        this.previewB = 0;
        this.previewA = 255;
    }

    onMouseDown(e) {
        // When spring-loaded (activated via Alt key), always set foreground color
        // (don't use altKey, which would set background)
        const setBackground = this._isSpringLoaded ? false : e.altKey;
        this.sampleColor(e.docX, e.docY, setBackground);
    }

    onMouseMove(e) {
        // Live preview on hover (always update preview, not just when dragging)
        const { docX, docY } = e;
        this.updatePreview(docX, docY);

        // Set color while dragging
        if (e.buttons === 1) {
            const setBackground = this._isSpringLoaded ? false : e.altKey;
            this.sampleColor(docX, docY, setBackground);
        }
    }

    /**
     * Sample RGBA from the appropriate source at document coordinates.
     * Returns {r, g, b, a} or null if out of bounds.
     */
    _sampleAt(docX, docY) {
        if (this.sampleSource === 'currentLayer') {
            return this._sampleCurrentLayer(docX, docY);
        }
        return this._sampleAllLayers(docX, docY);
    }

    /**
     * Sample from the layer compositing canvas (all visible layers, no checkerboard).
     */
    _sampleAllLayers(docX, docY) {
        const renderer = this.app.renderer;
        const { layerCanvas, layerCtx } = renderer;
        if (!layerCanvas || !layerCtx) return null;

        const cs = renderer._compositeScale || 1;
        const cw = layerCanvas.width;
        const ch = layerCanvas.height;

        if (this.sampleSize === 1) {
            const px = Math.floor(docX * cs);
            const py = Math.floor(docY * cs);
            if (px < 0 || px >= cw || py < 0 || py >= ch) return null;

            const imageData = layerCtx.getImageData(px, py, 1, 1);
            return {
                r: imageData.data[0],
                g: imageData.data[1],
                b: imageData.data[2],
                a: imageData.data[3]
            };
        }

        // Average over area (in scaled canvas space)
        const half = Math.floor(this.sampleSize / 2);
        const startX = Math.max(0, Math.floor((docX - half) * cs));
        const startY = Math.max(0, Math.floor((docY - half) * cs));
        const endX = Math.min(cw, Math.floor((docX + half + 1) * cs));
        const endY = Math.min(ch, Math.floor((docY + half + 1) * cs));
        const width = endX - startX;
        const height = endY - startY;
        if (width <= 0 || height <= 0) return null;

        const imageData = layerCtx.getImageData(startX, startY, width, height);
        let sumR = 0, sumG = 0, sumB = 0, sumA = 0, count = 0;
        for (let i = 0; i < imageData.data.length; i += 4) {
            sumR += imageData.data[i];
            sumG += imageData.data[i + 1];
            sumB += imageData.data[i + 2];
            sumA += imageData.data[i + 3];
            count++;
        }
        return {
            r: Math.round(sumR / count),
            g: Math.round(sumG / count),
            b: Math.round(sumB / count),
            a: Math.round(sumA / count)
        };
    }

    /**
     * Sample from the current (active) layer's canvas directly.
     * Ignores layer opacity/blend mode — returns the raw pixel color.
     */
    _sampleCurrentLayer(docX, docY) {
        const layer = this.app.layerStack?.getActiveLayer();
        if (!layer || layer.isGroup?.()) return null;

        // Get the layer's 2d context — raster layers use .ctx, SVG layers use ._ctx
        const ctx = layer.ctx || layer._ctx;
        if (!ctx) return null;

        // Convert document coords to layer-local coords
        const local = layer.docToCanvas(docX, docY);
        const lx = Math.floor(local.x);
        const ly = Math.floor(local.y);

        if (lx < 0 || lx >= layer.width || ly < 0 || ly >= layer.height) return null;

        if (this.sampleSize === 1) {
            const imageData = ctx.getImageData(lx, ly, 1, 1);
            return {
                r: imageData.data[0],
                g: imageData.data[1],
                b: imageData.data[2],
                a: imageData.data[3]
            };
        }

        const half = Math.floor(this.sampleSize / 2);
        const startX = Math.max(0, lx - half);
        const startY = Math.max(0, ly - half);
        const endX = Math.min(layer.width, lx + half + 1);
        const endY = Math.min(layer.height, ly + half + 1);
        const width = endX - startX;
        const height = endY - startY;
        if (width <= 0 || height <= 0) return null;

        const imageData = ctx.getImageData(startX, startY, width, height);
        let sumR = 0, sumG = 0, sumB = 0, sumA = 0, count = 0;
        for (let i = 0; i < imageData.data.length; i += 4) {
            sumR += imageData.data[i];
            sumG += imageData.data[i + 1];
            sumB += imageData.data[i + 2];
            sumA += imageData.data[i + 3];
            count++;
        }
        return {
            r: Math.round(sumR / count),
            g: Math.round(sumG / count),
            b: Math.round(sumB / count),
            a: Math.round(sumA / count)
        };
    }

    /**
     * Update the live color preview without setting the color.
     */
    updatePreview(x, y) {
        // Force render to ensure layer canvas is current
        this.app.renderer.render();

        const sample = this._sampleAt(x, y);
        const hasColor = sample && sample.a > 0;
        const changed = hasColor !== !!this.previewColor;

        if (hasColor) {
            this.previewR = sample.r;
            this.previewG = sample.g;
            this.previewB = sample.b;
            this.previewA = sample.a;
            this.previewColor = this._rgbToHex(sample.r, sample.g, sample.b);
        } else if (this.previewColor) {
            this.previewColor = null;
        }

        // Trigger toolbar refresh when preview appears, disappears, or changes
        if (changed || hasColor) {
            this.app.eventBus?.emit('tool:properties-changed');
        }
    }

    /**
     * Convert RGB to hex string.
     */
    _rgbToHex(r, g, b) {
        return '#' +
            r.toString(16).padStart(2, '0') +
            g.toString(16).padStart(2, '0') +
            b.toString(16).padStart(2, '0');
    }

    /**
     * Convert RGB to HSV.
     */
    _rgbToHsv(r, g, b) {
        r /= 255;
        g /= 255;
        b /= 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const d = max - min;

        let h = 0;
        const s = max === 0 ? 0 : d / max;
        const v = max;

        if (max !== min) {
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }

        return {
            h: Math.round(h * 360),
            s: Math.round(s * 100),
            v: Math.round(v * 100)
        };
    }

    sampleColor(x, y, setBackground) {
        // Force a render to ensure layer canvas is up to date
        this.app.renderer.render();

        const sample = this._sampleAt(x, y);
        if (!sample) return;

        const hex = this._rgbToHex(sample.r, sample.g, sample.b);

        // Set color (always opaque RGB — alpha is not part of fg/bg color)
        if (setBackground) {
            this.app.backgroundColor = hex;
            this.app.eventBus.emit('color:background-changed', { color: hex });
        } else {
            this.app.foregroundColor = hex;
            this.app.eventBus.emit('color:foreground-changed', { color: hex });
        }
    }

    getProperties() {
        const props = [
            {
                id: 'sampleSource', name: 'Sample', type: 'select',
                options: [
                    { value: 'allLayers', label: 'All Layers' },
                    { value: 'currentLayer', label: 'Current Layer' }
                ],
                value: this.sampleSource
            },
            {
                id: 'sampleSize', name: 'Size', type: 'select',
                options: [
                    { value: 1, label: 'Point' },
                    { value: 3, label: '3x3' },
                    { value: 5, label: '5x5' }
                ],
                value: this.sampleSize
            }
        ];

        // Live color preview with round swatch + RGB/A + HSV
        if (this.previewColor) {
            const hsv = this._rgbToHsv(this.previewR, this.previewG, this.previewB);
            props.push({
                id: 'eyedropperPreview',
                name: '',
                type: 'eyedropperPreview',
                value: {
                    hex: this.previewColor,
                    r: this.previewR,
                    g: this.previewG,
                    b: this.previewB,
                    a: this.previewA,
                    h: hsv.h,
                    s: hsv.s,
                    v: hsv.v
                }
            });
        }

        return props;
    }

    onPropertyChanged(id, value) {
        if (id === 'sampleSize') {
            this.sampleSize = parseInt(value, 10);
        } else if (id === 'sampleSource') {
            this.sampleSource = value;
        }
    }

    getHint() {
        return 'Click to sample color, Alt+click for background';
    }
}
