/**
 * ThemeManager - Manages theme switching for the application.
 *
 * Handles:
 * - Setting and getting current theme
 * - Persisting theme preference in localStorage
 * - Notifying listeners of theme changes
 */
export class ThemeManager {
    constructor() {
        this.currentTheme = 'dark';
        this.listeners = [];
        this.storageKey = 'stagforge-theme';
    }

    /**
     * Initialize the theme manager by loading saved preference.
     */
    init() {
        this.loadSavedTheme();
    }

    /**
     * Get the current theme.
     * @returns {string} 'dark' or 'light'
     */
    getTheme() {
        return this.currentTheme;
    }

    /**
     * Set the current theme.
     * @param {string} theme - 'dark' or 'light'
     */
    setTheme(theme) {
        if (theme !== 'dark' && theme !== 'light') {
            console.warn(`Invalid theme: ${theme}. Using 'dark'.`);
            theme = 'dark';
        }

        const previousTheme = this.currentTheme;
        this.currentTheme = theme;

        // Apply to document
        document.documentElement.setAttribute('data-theme', theme);

        // Persist preference
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch (e) {
            console.warn('Could not save theme preference:', e);
        }

        // Notify listeners
        if (previousTheme !== theme) {
            this.notifyListeners(theme, previousTheme);
        }
    }

    /**
     * Toggle between dark and light themes.
     */
    toggle() {
        this.setTheme(this.currentTheme === 'dark' ? 'light' : 'dark');
    }

    /**
     * Load saved theme from localStorage.
     */
    loadSavedTheme() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved === 'dark' || saved === 'light') {
                this.setTheme(saved);
            } else {
                // Default to dark, also check system preference
                const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
                this.setTheme(prefersDark !== false ? 'dark' : 'light');
            }
        } catch (e) {
            // localStorage not available, use default
            this.setTheme('dark');
        }
    }

    /**
     * Add a listener for theme changes.
     * @param {Function} callback - Called with (newTheme, previousTheme)
     */
    addListener(callback) {
        this.listeners.push(callback);
    }

    /**
     * Remove a theme change listener.
     * @param {Function} callback
     */
    removeListener(callback) {
        const idx = this.listeners.indexOf(callback);
        if (idx !== -1) {
            this.listeners.splice(idx, 1);
        }
    }

    /**
     * Notify all listeners of a theme change.
     * @param {string} newTheme
     * @param {string} previousTheme
     */
    notifyListeners(newTheme, previousTheme) {
        for (const listener of this.listeners) {
            try {
                listener(newTheme, previousTheme);
            } catch (e) {
                console.error('Theme listener error:', e);
            }
        }
    }

    /**
     * Get list of available themes.
     * @returns {Array<{id: string, name: string}>}
     */
    getAvailableThemes() {
        return [
            { id: 'dark', name: 'Dark' },
            { id: 'light', name: 'Light' }
        ];
    }
}

// Singleton instance
export const themeManager = new ThemeManager();
