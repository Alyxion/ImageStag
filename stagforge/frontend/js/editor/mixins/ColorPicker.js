/**
 * ColorPicker Mixin
 *
 * Handles color picker popup interactions for both desktop and tablet modes.
 *
 * Required component data:
 *   - colorPickerTarget: String ('fg' or 'bg')
 *   - colorPickerVisible: Boolean
 *   - colorPickerPosition: Object
 *   - hexInput: String
 *   - fgColor: String
 *   - bgColor: String
 *   - tabletColorPickerTarget: String
 *   - tabletColorPickerOpen: Boolean
 *   - tabletFileMenuOpen, tabletEditMenuOpen, etc.: Boolean
 *
 * Required component methods:
 *   - setForegroundColor(color): Sets FG color
 *   - setBackgroundColor(color): Sets BG color
 */
export const ColorPickerMixin = {
    methods: {
        /**
         * Open the desktop color picker popup
         * @param {string} target - 'fg' or 'bg'
         * @param {Event} event - Click event for positioning
         */
        openColorPicker(target, event) {
            this.colorPickerTarget = target;
            this.hexInput = target === 'fg' ? this.fgColor : this.bgColor;
            // Position popup below the clicked swatch
            if (event) {
                const rect = event.target.getBoundingClientRect();
                this.colorPickerPosition = {
                    top: (rect.bottom + 5) + 'px',
                    left: rect.left + 'px'
                };
            }
            this.colorPickerVisible = true;
        },

        /**
         * Close the desktop color picker popup
         */
        closeColorPicker() {
            this.colorPickerVisible = false;
        },

        /**
         * Set color from the picker (desktop mode)
         * @param {string} color - Hex color value
         */
        setPickerColor(color) {
            if (this.colorPickerTarget === 'fg') {
                this.setForegroundColor(color);
            } else {
                this.setBackgroundColor(color);
            }
            this.hexInput = color;
        },

        /**
         * Open the tablet color picker popup
         * @param {string} target - 'fg' or 'bg'
         */
        openTabletColorPicker(target) {
            // Close other menus first
            this.tabletFileMenuOpen = false;
            this.tabletEditMenuOpen = false;
            this.tabletViewMenuOpen = false;
            this.tabletImageMenuOpen = false;
            this.tabletZoomMenuOpen = false;

            this.tabletColorPickerTarget = target;
            this.hexInput = target === 'fg' ? this.fgColor : this.bgColor;
            this.tabletColorPickerOpen = true;
        },

        /**
         * Set color from the tablet picker
         * @param {string} color - Hex color value
         */
        setTabletPickerColor(color) {
            if (this.tabletColorPickerTarget === 'fg') {
                this.setForegroundColor(color);
            } else {
                this.setBackgroundColor(color);
            }
            this.hexInput = color;
        },

        /**
         * Apply hex color from tablet input field
         */
        applyTabletHexColor() {
            let hex = this.hexInput.trim();
            if (!hex.startsWith('#')) hex = '#' + hex;
            if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
                this.setTabletPickerColor(hex);
            }
        },

        /**
         * Open color picker in limited mode
         */
        openLimitedColorPicker() {
            // Open color picker in limited mode with fixed position
            this.openColorPicker('fg', {
                target: {
                    getBoundingClientRect: () => ({ left: 16, bottom: 150 })
                }
            });
        },
    },
};

export default ColorPickerMixin;
