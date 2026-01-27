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
    }

    onMouseDown(e, x, y) {
        this.sampleColor(x, y, e.altKey);
    }

    onMouseMove(e, x, y) {
        // Live preview while dragging
        if (e.buttons === 1) {
            this.sampleColor(x, y, e.altKey);
        }
    }

    sampleColor(x, y, setBackground) {
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
        return [
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
    }
}
