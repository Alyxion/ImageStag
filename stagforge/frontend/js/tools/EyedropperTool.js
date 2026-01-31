/**
 * EyedropperTool - Sample color from canvas.
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

    constructor(app) {
        super(app);
        this.sampleSize = 1; // 1 = single pixel, 3 = 3x3 average, 5 = 5x5 average

        // Live preview state
        this.previewColor = null;
        this.previewR = 0;
        this.previewG = 0;
        this.previewB = 0;
        this.previewA = 255;
    }

    onMouseDown(e, x, y) {
        // When spring-loaded (activated via Alt key), always set foreground color
        // (don't use altKey, which would set background)
        const setBackground = this._isSpringLoaded ? false : e.altKey;
        this.sampleColor(x, y, setBackground);
    }

    onMouseMove(e, x, y, coords) {
        // Live preview on hover (always update preview, not just when dragging)
        const docX = coords?.docX ?? x;
        const docY = coords?.docY ?? y;
        this.updatePreview(docX, docY);

        // Set color while dragging
        if (e.buttons === 1) {
            const setBackground = this._isSpringLoaded ? false : e.altKey;
            this.sampleColor(docX, docY, setBackground);
        }
    }

    /**
     * Update the live color preview without setting the color.
     */
    updatePreview(x, y) {
        const { compositeCanvas, compositeCtx } = this.app.renderer;
        if (!compositeCanvas || !compositeCtx) return;

        x = Math.floor(x);
        y = Math.floor(y);

        // Check bounds
        if (x < 0 || x >= compositeCanvas.width || y < 0 || y >= compositeCanvas.height) {
            return;
        }

        let r, g, b, a;

        if (this.sampleSize === 1) {
            const imageData = compositeCtx.getImageData(x, y, 1, 1);
            r = imageData.data[0];
            g = imageData.data[1];
            b = imageData.data[2];
            a = imageData.data[3];
        } else {
            const half = Math.floor(this.sampleSize / 2);
            const startX = Math.max(0, x - half);
            const startY = Math.max(0, y - half);
            const endX = Math.min(compositeCanvas.width, x + half + 1);
            const endY = Math.min(compositeCanvas.height, y + half + 1);
            const width = endX - startX;
            const height = endY - startY;

            const imageData = compositeCtx.getImageData(startX, startY, width, height);
            let sumR = 0, sumG = 0, sumB = 0, sumA = 0, count = 0;

            for (let i = 0; i < imageData.data.length; i += 4) {
                sumR += imageData.data[i];
                sumG += imageData.data[i + 1];
                sumB += imageData.data[i + 2];
                sumA += imageData.data[i + 3];
                count++;
            }

            r = Math.round(sumR / count);
            g = Math.round(sumG / count);
            b = Math.round(sumB / count);
            a = Math.round(sumA / count);
        }

        this.previewR = r;
        this.previewG = g;
        this.previewB = b;
        this.previewA = a;
        this.previewColor = this._rgbToHex(r, g, b);

        // Emit event for UI update
        this.app.eventBus?.emit('eyedropper:preview', {
            hex: this.previewColor,
            r, g, b, a,
            hsv: this._rgbToHsv(r, g, b)
        });
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
        // Force a render to ensure composite canvas is up to date
        // This is important for SVG/Vector layers which render asynchronously
        this.app.renderer.render();

        // Sample from composite (rendered) canvas
        const { compositeCanvas, compositeCtx } = this.app.renderer;

        x = Math.floor(x);
        y = Math.floor(y);

        // Check bounds
        if (x < 0 || x >= compositeCanvas.width || y < 0 || y >= compositeCanvas.height) return;

        let r, g, b;

        if (this.sampleSize === 1) {
            // Single pixel
            const imageData = compositeCtx.getImageData(x, y, 1, 1);
            r = imageData.data[0];
            g = imageData.data[1];
            b = imageData.data[2];
        } else {
            // Average over area
            const half = Math.floor(this.sampleSize / 2);
            const startX = Math.max(0, x - half);
            const startY = Math.max(0, y - half);
            const endX = Math.min(compositeCanvas.width, x + half + 1);
            const endY = Math.min(compositeCanvas.height, y + half + 1);
            const width = endX - startX;
            const height = endY - startY;

            const imageData = compositeCtx.getImageData(startX, startY, width, height);
            let sumR = 0, sumG = 0, sumB = 0, count = 0;

            for (let i = 0; i < imageData.data.length; i += 4) {
                sumR += imageData.data[i];
                sumG += imageData.data[i + 1];
                sumB += imageData.data[i + 2];
                count++;
            }

            r = Math.round(sumR / count);
            g = Math.round(sumG / count);
            b = Math.round(sumB / count);
        }

        // Convert to hex
        const hex = '#' +
            r.toString(16).padStart(2, '0') +
            g.toString(16).padStart(2, '0') +
            b.toString(16).padStart(2, '0');

        // Set color
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
                id: 'sampleSize', name: 'Sample Size', type: 'select',
                options: [
                    { value: 1, label: 'Point' },
                    { value: 3, label: '3x3 Average' },
                    { value: 5, label: '5x5 Average' }
                ],
                value: this.sampleSize
            }
        ];

        // Add live color preview if we have one
        if (this.previewColor) {
            props.push({
                id: 'colorPreview',
                name: 'Preview',
                type: 'colorPreview',
                value: {
                    hex: this.previewColor,
                    r: this.previewR,
                    g: this.previewG,
                    b: this.previewB,
                    a: this.previewA,
                    hsv: this._rgbToHsv(this.previewR, this.previewG, this.previewB)
                }
            });
        }

        return props;
    }

    onPropertyChanged(id, value) {
        if (id === 'sampleSize') {
            this.sampleSize = parseInt(value, 10);
        }
    }

    getHint() {
        if (this.previewColor) {
            const hsv = this._rgbToHsv(this.previewR, this.previewG, this.previewB);
            return `${this.previewColor.toUpperCase()} | R:${this.previewR} G:${this.previewG} B:${this.previewB} | H:${hsv.h}° S:${hsv.s}% V:${hsv.v}%`;
        }
        return 'Click to sample color, Alt+click for background';
    }
}
