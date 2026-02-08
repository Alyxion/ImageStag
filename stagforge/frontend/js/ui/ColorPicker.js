/**
 * ColorPicker - Foreground/background color selection.
 */
export class ColorPicker {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;
        this.container = document.getElementById('tool-panel');
        this.render();
        this.bindEvents();
    }

    render() {
        // Add color picker to tool panel
        const colorSection = document.createElement('div');
        colorSection.className = 'color-picker-section';
        colorSection.innerHTML = `
            <div class="color-swatches">
                <div class="color-swatch-container">
                    <input type="color" id="foreground-color" class="color-input"
                           value="${this.app.foregroundColor || '#000000'}">
                    <div class="color-swatch foreground" id="fg-swatch"></div>
                </div>
                <div class="color-swatch-container">
                    <input type="color" id="background-color" class="color-input"
                           value="${this.app.backgroundColor || '#FFFFFF'}">
                    <div class="color-swatch background" id="bg-swatch"></div>
                </div>
                <button class="color-swap" id="swap-colors" title="Swap Colors (X)">⇄</button>
                <button class="color-reset" id="reset-colors" title="Reset to Black/White (D)">◐</button>
            </div>
        `;
        this.container.appendChild(colorSection);
        this.updateSwatches();
    }

    bindEvents() {
        // Foreground color
        const fgInput = document.getElementById('foreground-color');
        const fgSwatch = document.getElementById('fg-swatch');

        fgInput?.addEventListener('input', (e) => {
            this.app.foregroundColor = e.target.value;
            this.updateSwatches();
            this.app.eventBus.emit('color:foreground-changed', { color: e.target.value });
        });

        fgSwatch?.addEventListener('click', () => fgInput?.click());

        // Background color
        const bgInput = document.getElementById('background-color');
        const bgSwatch = document.getElementById('bg-swatch');

        bgInput?.addEventListener('input', (e) => {
            this.app.backgroundColor = e.target.value;
            this.updateSwatches();
            this.app.eventBus.emit('color:background-changed', { color: e.target.value });
        });

        bgSwatch?.addEventListener('click', () => bgInput?.click());

        // Swap colors
        document.getElementById('swap-colors')?.addEventListener('click', () => {
            this.swapColors();
        });


        // Listen for color changes from other sources
        this.app.eventBus.on('color:foreground-changed', () => this.updateSwatches());
        this.app.eventBus.on('color:background-changed', () => this.updateSwatches());
    }

    swapColors() {
        const temp = this.app.foregroundColor;
        this.app.foregroundColor = this.app.backgroundColor;
        this.app.backgroundColor = temp;
        this.updateSwatches();
        this.app.eventBus.emit('color:foreground-changed', { color: this.app.foregroundColor });
        this.app.eventBus.emit('color:background-changed', { color: this.app.backgroundColor });
    }


    updateSwatches() {
        const fgInput = document.getElementById('foreground-color');
        const bgInput = document.getElementById('background-color');
        const fgSwatch = document.getElementById('fg-swatch');
        const bgSwatch = document.getElementById('bg-swatch');

        if (fgInput) fgInput.value = this.app.foregroundColor || '#000000';
        if (bgInput) bgInput.value = this.app.backgroundColor || '#FFFFFF';
        if (fgSwatch) fgSwatch.style.backgroundColor = this.app.foregroundColor || '#000000';
        if (bgSwatch) bgSwatch.style.backgroundColor = this.app.backgroundColor || '#FFFFFF';
    }
}
