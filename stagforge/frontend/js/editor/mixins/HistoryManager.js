/**
 * HistoryManager Mixin
 *
 * Handles undo/redo operations, history state display,
 * and jumping to specific history points.
 *
 * Required component data:
 *   - historyList: Array
 *   - historyIndex: Number
 *   - canUndo: Boolean
 *   - canRedo: Boolean
 *   - memoryUsedMB: Number
 *   - memoryMaxMB: Number
 *   - memoryPercent: Number
 *   - lastUndoAction: String
 *   - lastRedoAction: String
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 */
export const HistoryManagerMixin = {
    methods: {
        /**
         * Update the history state from the app's History instance
         * Refreshes the history list, undo/redo availability, and memory usage
         */
        updateHistoryState() {
            try {
                const app = this.getState();
                if (!app?.history) return;

                const entries = app.history.getEntries() || [];
                this.historyList = entries.map(entry => ({
                    name: entry.name || 'Action',
                    icon: this.getHistoryIcon(entry.type),
                    isCurrent: entry.isCurrent || false,
                    isFuture: entry.isFuture || false
                }));
                this.historyIndex = app.history.getCurrentIndex();
                this.canUndo = app.history.canUndo();
                this.canRedo = app.history.canRedo();

                // Update memory usage
                const memInfo = app.history.getMemoryUsage();
                this.memoryUsedMB = memInfo.usedMB;
                this.memoryMaxMB = memInfo.maxMB;
                this.memoryPercent = Math.min(100, memInfo.percentage);

                // Get action names for tooltips
                const undoEntry = app.history.getUndoEntry();
                const redoEntry = app.history.getRedoEntry();
                this.lastUndoAction = undoEntry?.name || '';
                this.lastRedoAction = redoEntry?.name || '';
            } catch (e) {
                console.error('[HistoryManager] Error updating history state:', e);
            }
        },

        /**
         * Get the icon for a history entry type
         * @param {string} type - History entry type
         * @returns {string} HTML entity for the icon
         */
        getHistoryIcon(type) {
            const icons = {
                'current': '&#9654;',    // ▶
                'brush': '&#128396;',    // 🖌
                'erase': '&#9986;',      // ✂
                'fill': '&#128276;',     // 🔔
                'layer': '&#128193;',    // 📁
                'transform': '&#8689;',  // ⇱
                'filter': '&#9881;',     // ⚙
                'selection': '&#9633;',  // □
                'document': '&#128196;', // 📄
            };
            return icons[type] || '&#9679;'; // ●
        },

        /**
         * Undo the last action
         */
        undo() {
            const app = this.getState();
            if (app?.history?.canUndo()) {
                app.history.undo();
                this.updateHistoryState();
            }
        },

        /**
         * Redo the last undone action
         */
        redo() {
            const app = this.getState();
            if (app?.history?.canRedo()) {
                app.history.redo();
                this.updateHistoryState();
            }
        },

        /**
         * Jump to a specific point in history
         * @param {number} index - Target history index
         */
        jumpToHistory(index) {
            const app = this.getState();
            if (!app?.history) return;

            const currentIndex = app.history.getCurrentIndex();
            // Entries are: [undoStack entries] [current state] [redoStack entries]
            // Current state is at index = undoStack.length = currentIndex

            if (index < currentIndex) {
                // Go back (undo) to reach this state
                const steps = currentIndex - index;
                for (let i = 0; i < steps; i++) {
                    app.history.undo();
                }
            } else if (index > currentIndex) {
                // Go forward (redo) to reach this state
                const steps = index - currentIndex;
                for (let i = 0; i < steps; i++) {
                    app.history.redo();
                }
            }
            // If index === currentIndex, we're already there

            this.updateHistoryState();
        },
    },
};

export default HistoryManagerMixin;
