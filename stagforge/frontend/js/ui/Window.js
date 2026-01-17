/**
 * Window.js - Draggable, collapsible window/panel component
 *
 * Features:
 * - Draggable by title bar
 * - Collapsible content
 * - Close button (optional)
 * - Resize handle (optional)
 * - Z-index management for focus
 */

export class Window {
    static zIndexCounter = 100;
    static windows = new Map();

    constructor(options = {}) {
        this.id = options.id || `window-${Date.now()}`;
        this.title = options.title || 'Window';
        this.closable = options.closable !== false;
        this.collapsible = options.collapsible !== false;
        this.resizable = options.resizable || false;
        this.minWidth = options.minWidth || 150;
        this.minHeight = options.minHeight || 100;
        this.width = options.width || 220;
        this.height = options.height || 'auto';
        this.x = options.x ?? 100;
        this.y = options.y ?? 100;
        this.docked = options.docked ?? true;
        this.visible = options.visible !== false;
        this.collapsed = options.collapsed || false;
        this.onClose = options.onClose || null;
        this.onCollapse = options.onCollapse || null;
        this.content = options.content || null;

        this.element = null;
        this.titleBar = null;
        this.contentEl = null;
        this.isDragging = false;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;

        Window.windows.set(this.id, this);
    }

    /**
     * Create the DOM structure for the window
     */
    createElement() {
        this.element = document.createElement('div');
        this.element.className = 'panel-window';
        this.element.id = this.id;
        this.element.style.width = typeof this.width === 'number' ? `${this.width}px` : this.width;
        if (this.height !== 'auto') {
            this.element.style.height = typeof this.height === 'number' ? `${this.height}px` : this.height;
        }

        if (!this.docked) {
            this.element.classList.add('floating');
            this.element.style.left = `${this.x}px`;
            this.element.style.top = `${this.y}px`;
            this.element.style.zIndex = Window.zIndexCounter++;
        }

        if (!this.visible) {
            this.element.style.display = 'none';
        }

        // Title bar
        this.titleBar = document.createElement('div');
        this.titleBar.className = 'panel-window-titlebar';

        const titleText = document.createElement('span');
        titleText.className = 'panel-window-title';
        titleText.textContent = this.title;
        this.titleBar.appendChild(titleText);

        const buttons = document.createElement('div');
        buttons.className = 'panel-window-buttons';

        if (this.collapsible) {
            const collapseBtn = document.createElement('button');
            collapseBtn.className = 'panel-window-btn collapse-btn';
            collapseBtn.innerHTML = this.collapsed ? '&#9654;' : '&#9660;';
            collapseBtn.title = 'Collapse';
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleCollapse();
            });
            buttons.appendChild(collapseBtn);
        }

        if (this.closable) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'panel-window-btn close-btn';
            closeBtn.innerHTML = '&times;';
            closeBtn.title = 'Close';
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.close();
            });
            buttons.appendChild(closeBtn);
        }

        this.titleBar.appendChild(buttons);
        this.element.appendChild(this.titleBar);

        // Content area
        this.contentEl = document.createElement('div');
        this.contentEl.className = 'panel-window-content';
        if (this.collapsed) {
            this.contentEl.style.display = 'none';
        }
        this.element.appendChild(this.contentEl);

        // Resize handle
        if (this.resizable && !this.docked) {
            const resizeHandle = document.createElement('div');
            resizeHandle.className = 'panel-window-resize';
            this.element.appendChild(resizeHandle);
            this.setupResize(resizeHandle);
        }

        // Setup drag behavior
        this.setupDrag();

        // Focus on click
        this.element.addEventListener('mousedown', () => this.bringToFront());

        return this.element;
    }

    /**
     * Setup drag behavior for title bar
     */
    setupDrag() {
        this.titleBar.addEventListener('mousedown', (e) => {
            if (e.target.closest('.panel-window-btn')) return;
            if (this.docked) return;

            this.isDragging = true;
            this.dragOffsetX = e.clientX - this.element.offsetLeft;
            this.dragOffsetY = e.clientY - this.element.offsetTop;
            this.element.classList.add('dragging');

            const onMouseMove = (e) => {
                if (!this.isDragging) return;
                const x = e.clientX - this.dragOffsetX;
                const y = e.clientY - this.dragOffsetY;
                this.element.style.left = `${Math.max(0, x)}px`;
                this.element.style.top = `${Math.max(0, y)}px`;
                this.x = x;
                this.y = y;
            };

            const onMouseUp = () => {
                this.isDragging = false;
                this.element.classList.remove('dragging');
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    /**
     * Setup resize behavior
     */
    setupResize(handle) {
        handle.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            const startX = e.clientX;
            const startY = e.clientY;
            const startWidth = this.element.offsetWidth;
            const startHeight = this.element.offsetHeight;

            const onMouseMove = (e) => {
                const newWidth = Math.max(this.minWidth, startWidth + e.clientX - startX);
                const newHeight = Math.max(this.minHeight, startHeight + e.clientY - startY);
                this.element.style.width = `${newWidth}px`;
                this.element.style.height = `${newHeight}px`;
                this.width = newWidth;
                this.height = newHeight;
            };

            const onMouseUp = () => {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    /**
     * Bring window to front (highest z-index)
     */
    bringToFront() {
        if (!this.docked && this.element) {
            this.element.style.zIndex = Window.zIndexCounter++;
        }
    }

    /**
     * Toggle collapsed state
     */
    toggleCollapse() {
        this.collapsed = !this.collapsed;
        if (this.contentEl) {
            this.contentEl.style.display = this.collapsed ? 'none' : '';
        }
        const collapseBtn = this.titleBar.querySelector('.collapse-btn');
        if (collapseBtn) {
            collapseBtn.innerHTML = this.collapsed ? '&#9654;' : '&#9660;';
        }
        this.element.classList.toggle('collapsed', this.collapsed);
        if (this.onCollapse) {
            this.onCollapse(this.collapsed);
        }
    }

    /**
     * Show window
     */
    show() {
        this.visible = true;
        if (this.element) {
            this.element.style.display = '';
            this.bringToFront();
        }
    }

    /**
     * Hide window
     */
    hide() {
        this.visible = false;
        if (this.element) {
            this.element.style.display = 'none';
        }
    }

    /**
     * Close window
     */
    close() {
        this.hide();
        if (this.onClose) {
            this.onClose();
        }
    }

    /**
     * Toggle visibility
     */
    toggle() {
        if (this.visible) {
            this.hide();
        } else {
            this.show();
        }
    }

    /**
     * Set content element or HTML
     */
    setContent(content) {
        if (!this.contentEl) return;
        if (typeof content === 'string') {
            this.contentEl.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            this.contentEl.innerHTML = '';
            this.contentEl.appendChild(content);
        }
    }

    /**
     * Get the content element for direct manipulation
     */
    getContentElement() {
        return this.contentEl;
    }

    /**
     * Undock window (make floating)
     */
    undock() {
        if (!this.docked) return;
        this.docked = false;
        this.element.classList.add('floating');
        this.element.style.position = 'fixed';
        this.element.style.left = `${this.x}px`;
        this.element.style.top = `${this.y}px`;
        this.element.style.zIndex = Window.zIndexCounter++;
    }

    /**
     * Dock window back to container
     */
    dock() {
        if (this.docked) return;
        this.docked = true;
        this.element.classList.remove('floating');
        this.element.style.position = '';
        this.element.style.left = '';
        this.element.style.top = '';
        this.element.style.zIndex = '';
    }

    /**
     * Static method to get window by ID
     */
    static getById(id) {
        return Window.windows.get(id);
    }
}
