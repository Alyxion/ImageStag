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
         * Save panel visibility state to localStorage
         */
        savePanelState() {
            const state = {
                // Desktop panels
                showToolPanel: this.showToolPanel,
                showRibbon: this.showRibbon,
                showRightPanel: this.showRightPanel,
                showNavigator: this.showNavigator,
                showLayers: this.showLayers,
                showHistory: this.showHistory,
                showSources: this.showSources,
                // Tablet panels
                tabletNavPanelOpen: this.tabletNavPanelOpen,
                tabletLayersPanelOpen: this.tabletLayersPanelOpen,
                tabletHistoryPanelOpen: this.tabletHistoryPanelOpen,
                tabletLeftDrawerOpen: this.tabletLeftDrawerOpen,
            };
            try {
                localStorage.setItem('stagforge-panel-state', JSON.stringify(state));
            } catch (e) {
                // localStorage might be unavailable
            }
        },

        /**
         * Load panel visibility state from localStorage
         */
        loadPanelState() {
            try {
                const saved = localStorage.getItem('stagforge-panel-state');
                if (saved) {
                    const state = JSON.parse(saved);
                    // Desktop panels
                    if (typeof state.showToolPanel === 'boolean') this.showToolPanel = state.showToolPanel;
                    if (typeof state.showRibbon === 'boolean') this.showRibbon = state.showRibbon;
                    if (typeof state.showRightPanel === 'boolean') this.showRightPanel = state.showRightPanel;
                    if (typeof state.showNavigator === 'boolean') this.showNavigator = state.showNavigator;
                    if (typeof state.showLayers === 'boolean') this.showLayers = state.showLayers;
                    if (typeof state.showHistory === 'boolean') this.showHistory = state.showHistory;
                    if (typeof state.showSources === 'boolean') this.showSources = state.showSources;
                    // Tablet panels
                    if (typeof state.tabletNavPanelOpen === 'boolean') this.tabletNavPanelOpen = state.tabletNavPanelOpen;
                    if (typeof state.tabletLayersPanelOpen === 'boolean') this.tabletLayersPanelOpen = state.tabletLayersPanelOpen;
                    if (typeof state.tabletHistoryPanelOpen === 'boolean') this.tabletHistoryPanelOpen = state.tabletHistoryPanelOpen;
                    if (typeof state.tabletLeftDrawerOpen === 'boolean') this.tabletLeftDrawerOpen = state.tabletLeftDrawerOpen;
                }
            } catch (e) {
                // localStorage might be unavailable or corrupted
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
