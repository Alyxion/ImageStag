/**
 * KeyboardEvents Mixin
 *
 * Handles keyboard shortcuts and window resize events.
 *
 * Required component data:
 *   - currentUIMode: String
 *   - limitedSettings: Object { enableKeyboardShortcuts, allowUndo }
 *   - _springLoadedPrevTool: String|null - Previous tool ID for spring-loaded tools
 *   - _springLoadedKey: String|null - Which key triggered spring-loaded mode
 *   - _uiHidden: Boolean - Whether UI is hidden via Tab
 *   - _savedPanelState: Object - Saved panel visibility state
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
 *   - reselect(): Restore previous selection
 *   - invertSelection(): Invert current selection
 *   - deleteSelection(): Delete selected area
 *   - fillSelectionWithColor(color): Fill selection with color
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
         * Activate spring-loaded tool (temporary tool switch)
         * @param {string} toolId - Tool to temporarily switch to
         * @param {string} key - The key that triggered this (for keyup matching)
         */
        activateSpringLoadedTool(toolId, key) {
            const app = this.getState();
            if (!app?.toolManager) return false;

            // Already in spring-loaded mode for this key
            if (this._springLoadedKey === key) return false;

            // Store previous tool
            const currentToolId = app.toolManager.currentTool?.constructor?.id;
            if (currentToolId && currentToolId !== toolId) {
                this._springLoadedPrevTool = currentToolId;
                this._springLoadedKey = key;
                app.toolManager.select(toolId);
                // Mark the new tool as spring-loaded so it can adjust behavior
                const newTool = app.toolManager.currentTool;
                if (newTool) {
                    newTool._isSpringLoaded = true;
                }
                return true;
            }
            return false;
        },

        /**
         * Deactivate spring-loaded tool and restore previous
         * @param {string} key - The key that was released
         */
        deactivateSpringLoadedTool(key) {
            const app = this.getState();
            if (!app?.toolManager) return;

            // Only restore if this is the key that activated spring-loaded mode
            if (this._springLoadedKey === key && this._springLoadedPrevTool) {
                app.toolManager.select(this._springLoadedPrevTool);
                this._springLoadedPrevTool = null;
                this._springLoadedKey = null;
            }
        },

        /**
         * Toggle UI visibility (Tab key)
         */
        toggleUIVisibility() {
            if (this._uiHidden) {
                // Restore panels
                if (this._savedPanelState) {
                    this.showMenuBar = this._savedPanelState.showMenuBar;
                    this.showToolPanel = this._savedPanelState.showToolPanel;
                    this.showRightPanel = this._savedPanelState.showRightPanel;
                    this.showBottomBar = this._savedPanelState.showBottomBar;
                    this.showDocumentTabs = this._savedPanelState.showDocumentTabs;
                }
                this._uiHidden = false;
            } else {
                // Save and hide panels
                this._savedPanelState = {
                    showMenuBar: this.showMenuBar,
                    showToolPanel: this.showToolPanel,
                    showRightPanel: this.showRightPanel,
                    showBottomBar: this.showBottomBar,
                    showDocumentTabs: this.showDocumentTabs,
                };
                this.showMenuBar = false;
                this.showToolPanel = false;
                this.showRightPanel = false;
                this.showBottomBar = false;
                this.showDocumentTabs = false;
                this._uiHidden = true;
            }
        },

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

            // Tab key toggles UI visibility
            if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey) {
                e.preventDefault();
                this.toggleUIVisibility();
                return;
            }

            // Space key for spring-loaded Hand/Pan tool
            if (e.key === ' ' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.repeat) {
                e.preventDefault();
                this.activateSpringLoadedTool('hand', 'Space');
                return;
            }

            // Alt key for spring-loaded Eyedropper tool (only on alt alone, not alt+other key)
            // Skip if current tool uses Alt (like Clone Stamp for setting source)
            if (e.key === 'Alt' && !e.ctrlKey && !e.metaKey && !e.repeat) {
                const currentToolId = app.toolManager?.currentTool?.constructor?.id;
                const toolsUsingAlt = ['clonestamp'];  // Tools that use Alt+click
                if (!toolsUsingAlt.includes(currentToolId)) {
                    // Don't prevent default - allow Alt+Backspace etc to work
                    this.activateSpringLoadedTool('eyedropper', 'Alt');
                }
                return;
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
                        if (e.shiftKey) {
                            this.reselect();
                        } else {
                            this.deselect();
                        }
                        return;
                    case 'i':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.invertSelection();
                            return;
                        }
                        break;
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
                // Delete to clear selection (no modifiers)
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    e.preventDefault();
                    this.deleteSelection();
                    return;
                }
            }

            // Alt+Backspace: Fill with FG color
            if (e.altKey && !e.ctrlKey && !e.metaKey && e.key === 'Backspace') {
                e.preventDefault();
                const fgColor = app.foregroundColor || '#000000';
                this.fillSelectionWithColor(fgColor);
                return;
            }

            // Ctrl+Backspace: Fill with BG color
            if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key === 'Backspace') {
                e.preventDefault();
                const bgColor = app.backgroundColor || '#FFFFFF';
                this.fillSelectionWithColor(bgColor);
                return;
            }

            // Tool shortcuts (no modifiers) - continued
            if (!e.ctrlKey && !e.metaKey && !e.altKey) {
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

            // Restore from spring-loaded Space (Hand tool)
            if (e.key === ' ') {
                this.deactivateSpringLoadedTool('Space');
            }

            // Restore from spring-loaded Alt (Eyedropper tool)
            if (e.key === 'Alt') {
                this.deactivateSpringLoadedTool('Alt');
            }

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
