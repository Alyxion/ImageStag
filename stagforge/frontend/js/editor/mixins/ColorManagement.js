/**
 * ColorManagement Mixin
 *
 * Handles foreground/background color management, recent colors,
 * and color swapping/resetting operations.
 *
 * Required component data:
 *   - fgColor: String
 *   - bgColor: String
 *   - hexInput: String
 *   - recentColors: Array
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - emitStateUpdate(): Emits state change to parent
 *   - setPickerColor(color): Sets the color picker value
 */
export const ColorManagementMixin = {
    methods: {
        /**
         * Set the foreground (primary) color
         * @param {string} color - Hex color value (#RRGGBB)
         */
        setForegroundColor(color) {
            this.fgColor = color;
            this.hexInput = color;
            this.addRecentColor(color);
            const app = this.getState();
            if (app) {
                app.foregroundColor = color;
                app.eventBus.emit('color:foreground-changed', { color });
            }
            this.emitStateUpdate();
        },

        /**
         * Set the background (secondary) color
         * @param {string} color - Hex color value (#RRGGBB)
         */
        setBackgroundColor(color) {
            this.bgColor = color;
            this.addRecentColor(color);
            const app = this.getState();
            if (app) {
                app.backgroundColor = color;
                app.eventBus.emit('color:background-changed', { color });
            }
            this.emitStateUpdate();
        },

        /**
         * Add a color to the recent colors list
         * Maintains a max of 12 recent colors, with most recent first
         * @param {string} color - Hex color value
         */
        addRecentColor(color) {
            // Don't add if it's already the most recent
            if (this.recentColors[0] === color) return;
            // Remove if already in list
            const idx = this.recentColors.indexOf(color);
            if (idx !== -1) {
                this.recentColors.splice(idx, 1);
            }
            // Add to front
            this.recentColors.unshift(color);
            // Keep max 12
            if (this.recentColors.length > 12) {
                this.recentColors.pop();
            }
        },

        /**
         * Apply hex color from manual input field
         * Validates format and applies to picker
         */
        applyHexColor() {
            let hex = this.hexInput.trim();
            if (!hex.startsWith('#')) hex = '#' + hex;
            if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
                this.setPickerColor(hex);
            }
        },

        /**
         * Swap foreground and background colors
         * Keyboard shortcut: X
         */
        swapColors() {
            const temp = this.fgColor;
            this.setForegroundColor(this.bgColor);
            this.setBackgroundColor(temp);
        },

    },
};

export default ColorManagementMixin;
