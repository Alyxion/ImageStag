/**
 * KeyboardEvents Mixin
 *
 * Handles keyboard shortcuts and window resize events.
 *
 * Required component data:
 *   - currentUIMode: String
 *   - limitedSettings: Object { enableKeyboardShortcuts, allowUndo }
 *
 * Required component refs:
 *   - canvasContainer: HTMLElement
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - undo(): Undo last action
 *   - redo(): Redo last undone action
 *   - clipboardCopy(): Copy selection
 *   - clipboardCopyMerged(): Copy merged visible
 *   - clipboardCut(): Cut selection
 *   - clipboardPaste(): Paste content
 *   - clipboardPasteInPlace(): Paste in original position
 *   - selectAll(): Select entire canvas
 *   - deselect(): Clear selection
 *   - deleteSelection(): Delete selected area
 *   - swapColors(): Swap FG/BG colors
 *   - resetColors(): Reset to black/white
 *   - fileSave(): Save document
 *   - fileSaveAs(): Save document as
 *   - fileOpen(): Open document
 *   - createGroup(): Create layer group
 *   - ungroupSelectedLayers(): Ungroup selected layers
 *   - cycleToolInGroup(shortcut): Cycle through tool group
 */
export const KeyboardEventsMixin = {
    methods: {
        /**
         * Handle key down events for shortcuts
         * @param {KeyboardEvent} e - The keyboard event
         */
        handleKeyDown(e) {
            const app = this.getState();
            if (!app) return;

            // Don't intercept keys when an input/textarea/select is focused
            const tag = document.activeElement?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
                return;
            }

            // In limited mode, block most keyboard shortcuts
            if (this.currentUIMode === 'limited' && !this.limitedSettings.enableKeyboardShortcuts) {
                // Only allow Ctrl+Z for undo if enabled
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && this.limitedSettings.allowUndo) {
                    e.preventDefault();
                    this.undo();
                }
                return; // Block all other shortcuts in limited mode
            }

            // Ctrl/Cmd shortcuts
            if (e.ctrlKey || e.metaKey) {
                switch (e.key.toLowerCase()) {
                    case 'z':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.redo();
                        } else {
                            this.undo();
                        }
                        return;
                    case 'y':
                        e.preventDefault();
                        this.redo();
                        return;
                    case 'c':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.clipboardCopyMerged();
                        } else {
                            this.clipboardCopy();
                        }
                        return;
                    case 'x':
                        e.preventDefault();
                        this.clipboardCut();
                        return;
                    case 'v':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.clipboardPasteInPlace();
                        } else {
                            this.clipboardPaste();
                        }
                        return;
                    case 'a':
                        e.preventDefault();
                        this.selectAll();
                        return;
                    case 'd':
                        e.preventDefault();
                        this.deselect();
                        return;
                    case 's':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.fileSaveAs();
                        } else {
                            this.fileSave();
                        }
                        return;
                    case 'o':
                        e.preventDefault();
                        this.fileOpen();
                        return;
                    case 'g':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.ungroupSelectedLayers();
                        } else {
                            this.createGroup();
                        }
                        return;
                }
            }

            // Tool shortcuts (no modifiers)
            if (!e.ctrlKey && !e.metaKey && !e.altKey) {
                if (e.key === 'x' || e.key === 'X') {
                    this.swapColors();
                    return;
                }
                if (e.key === 'd' || e.key === 'D') {
                    this.resetColors();
                    return;
                }
                // Escape to deselect
                if (e.key === 'Escape') {
                    this.deselect();
                    return;
                }
                // Delete to clear selection
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    e.preventDefault();
                    this.deleteSelection();
                    return;
                }

                // Shift+key cycles through tools in the same group
                if (e.shiftKey) {
                    const lowerKey = e.key.toLowerCase();
                    if (this.cycleToolInGroup(lowerKey)) {
                        return;
                    }
                }

                // Regular tool shortcuts
                if (app.toolManager.handleShortcut(e.key)) {
                    return;
                }
            }

            app.toolManager.currentTool?.onKeyDown(e);
        },

        /**
         * Handle key up events
         * @param {KeyboardEvent} e - The keyboard event
         */
        handleKeyUp(e) {
            const app = this.getState();
            app?.toolManager?.currentTool?.onKeyUp(e);
        },

        /**
         * Handle window resize
         */
        handleResize() {
            const app = this.getState();
            if (!app?.renderer) return;

            const container = this.$refs.canvasContainer;
            if (!container) return;

            // Use resizeDisplay for proper HiDPI support
            const displayWidth = container.clientWidth || app.renderer.displayWidth;
            const displayHeight = container.clientHeight || app.renderer.displayHeight;
            app.renderer.resizeDisplay(displayWidth, displayHeight);
            app.renderer.centerCanvas();
        },
    },
};

export default KeyboardEventsMixin;
