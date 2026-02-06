/**
 * DialogManager Mixin
 *
 * Centralized dialog lifecycle management. Maintains a stack of open dialogs
 * so Escape key and overlay clicks always close the topmost one.
 *
 * Usage in other mixins:
 *   Opening:  this.pushDialog('myDialog', () => { this.myDialogVisible = false; });
 *             this.myDialogVisible = true;
 *
 *   Closing:  this.popDialog('myDialog');
 *             this.myDialogVisible = false;
 *
 *   Or just call the close handler which should do both.
 */
export const DialogManagerMixin = {
    data() {
        return {
            /** @type {Array<{name: string, close: Function}>} */
            _dialogStack: [],
        };
    },

    methods: {
        /**
         * Push a dialog onto the stack. Call when opening a dialog.
         * @param {string} name - Unique dialog identifier
         * @param {Function} closeHandler - Function to call to close/cancel the dialog
         */
        pushDialog(name, closeHandler) {
            // Avoid duplicates — if already on stack, remove first
            this._dialogStack = this._dialogStack.filter(d => d.name !== name);
            this._dialogStack.push({ name, close: closeHandler });
        },

        /**
         * Remove a dialog from the stack. Call when closing a dialog.
         * @param {string} name - Dialog identifier to remove
         */
        popDialog(name) {
            this._dialogStack = this._dialogStack.filter(d => d.name !== name);
        },

        /**
         * Close the topmost dialog. Called by Escape key and overlay clicks.
         * @returns {boolean} true if a dialog was closed, false if stack was empty
         */
        closeTopmostDialog() {
            if (this._dialogStack.length === 0) return false;
            const top = this._dialogStack.pop();
            top.close();
            return true;
        },

        /**
         * Check if any dialog is currently open.
         * @returns {boolean}
         */
        hasOpenDialog() {
            return this._dialogStack.length > 0;
        },
    },
};
