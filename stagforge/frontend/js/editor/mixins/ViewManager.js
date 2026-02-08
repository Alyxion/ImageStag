/**
 * ViewManager Mixin
 *
 * Handles panel visibility, theme management, and view state persistence.
 *
 * Required component data:
 *   - showToolPanel: Boolean
 *   - showRibbon: Boolean
 *   - showRightPanel: Boolean
 *   - showNavigator: Boolean
 *   - showLayers: Boolean
 *   - showHistory: Boolean
 *   - showSources: Boolean
 *   - tabletNavPanelOpen: Boolean
 *   - tabletLayersPanelOpen: Boolean
 *   - tabletHistoryPanelOpen: Boolean
 *   - tabletLeftDrawerOpen: Boolean
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateNavigator(): Updates navigator panel
 *   - closeMenu(): Closes active menus
 */
export const ViewManagerMixin = {
    methods: {
        /**
         * Toggle a view option (panel visibility)
         * @param {string} option - Property name to toggle
         */
        toggleViewOption(option) {
            this[option] = !this[option];
            if (option === 'showNavigator' && this[option]) {
                this.$nextTick(() => this.updateNavigator());
            }
            // Persist panel visibility state
            this.savePanelState();
        },

        /**
         * Save panel visibility state to localStorage.
         * Desktop and tablet state are stored under separate keys so
         * mode switches can never corrupt each other's panel settings.
         */
        savePanelState() {
            try {
                const mode = this.currentUIMode || 'desktop';
                if (mode === 'desktop') {
                    localStorage.setItem('stagforge-panels-desktop', JSON.stringify({
                        showToolPanel: this.showToolPanel,
                        showRibbon: this.showRibbon,
                        showRightPanel: this.showRightPanel,
                        showNavigator: this.showNavigator,
                        showLayers: this.showLayers,
                        showHistory: this.showHistory,
                        showSources: this.showSources,
                    }));
                } else if (mode === 'tablet') {
                    localStorage.setItem('stagforge-panels-tablet', JSON.stringify({
                        tabletNavPanelOpen: this.tabletNavPanelOpen,
                        tabletLayersPanelOpen: this.tabletLayersPanelOpen,
                        tabletHistoryPanelOpen: this.tabletHistoryPanelOpen,
                        tabletLeftDrawerOpen: this.tabletLeftDrawerOpen,
                    }));
                }
            } catch (e) {
                // localStorage might be unavailable
            }
        },

        /**
         * Load panel visibility state from localStorage.
         * Each mode loads only its own saved state — desktop panel
         * settings are never affected by tablet/limited mode and vice versa.
         *
         * Config props set via URL/iframe embedding take precedence:
         * if a configShow* prop is false, localStorage cannot override it.
         */
        loadPanelState() {
            // Migrate legacy combined key (one-time)
            try {
                if (localStorage.getItem('stagforge-panel-state')) {
                    localStorage.removeItem('stagforge-panel-state');
                }
            } catch (e) { /* ignore */ }

            // Desktop panels
            try {
                const saved = localStorage.getItem('stagforge-panels-desktop');
                if (saved) {
                    const s = JSON.parse(saved);
                    if (typeof s.showToolPanel === 'boolean' && this.configShowToolbar !== false) {
                        this.showToolPanel = s.showToolPanel;
                    }
                    if (typeof s.showRibbon === 'boolean' && this.configShowToolProperties !== false) {
                        this.showRibbon = s.showRibbon;
                    }
                    if (typeof s.showRightPanel === 'boolean') {
                        this.showRightPanel = s.showRightPanel;
                    }
                    if (typeof s.showNavigator === 'boolean' && this.configShowNavigator !== false) {
                        this.showNavigator = s.showNavigator;
                    }
                    if (typeof s.showLayers === 'boolean' && this.configShowLayers !== false) {
                        this.showLayers = s.showLayers;
                    }
                    if (typeof s.showHistory === 'boolean' && this.configShowHistory !== false) {
                        this.showHistory = s.showHistory;
                    }
                    if (typeof s.showSources === 'boolean') {
                        this.showSources = s.showSources;
                    }
                }
            } catch (e) {
                console.warn('Failed to load desktop panel state:', e);
            }

            // Tablet panels
            try {
                const saved = localStorage.getItem('stagforge-panels-tablet');
                if (saved) {
                    const s = JSON.parse(saved);
                    if (typeof s.tabletNavPanelOpen === 'boolean') this.tabletNavPanelOpen = s.tabletNavPanelOpen;
                    if (typeof s.tabletLayersPanelOpen === 'boolean') this.tabletLayersPanelOpen = s.tabletLayersPanelOpen;
                    if (typeof s.tabletHistoryPanelOpen === 'boolean') this.tabletHistoryPanelOpen = s.tabletHistoryPanelOpen;
                    if (typeof s.tabletLeftDrawerOpen === 'boolean') this.tabletLeftDrawerOpen = s.tabletLeftDrawerOpen;
                }
            } catch (e) {
                console.warn('Failed to load tablet panel state:', e);
            }
        },

        /**
         * Reset panel visibility to defaults
         */
        resetPanelState() {
            // Desktop panels - all visible by default
            this.showToolPanel = true;
            this.showRibbon = true;
            this.showRightPanel = true;
            this.showNavigator = true;
            this.showLayers = true;
            this.showHistory = true;
            this.showSources = false;  // Image sources hidden by default
            // Tablet panels - all closed by default
            this.tabletNavPanelOpen = false;
            this.tabletLayersPanelOpen = false;
            this.tabletHistoryPanelOpen = false;
            this.tabletLeftDrawerOpen = false;
            // Clear saved state for all modes
            try {
                localStorage.removeItem('stagforge-panels-desktop');
                localStorage.removeItem('stagforge-panels-tablet');
            } catch (e) {
                // Ignore
            }
        },

        /**
         * Toggle navigator panel visibility
         */
        toggleNavigator() {
            this.showNavigator = !this.showNavigator;
        },

        /**
         * Set application theme
         * @param {string} theme - Theme name ('light', 'dark', 'system')
         */
        setTheme(theme) {
            const app = this.getState();
            if (app?.themeManager) {
                app.themeManager.setTheme(theme);
            }
            this.closeMenu();
        },

        /**
         * Toggle between light and dark theme
         */
        toggleTheme() {
            const app = this.getState();
            if (app?.themeManager) {
                app.themeManager.toggle();
            }
        },
    },
};

export default ViewManagerMixin;
