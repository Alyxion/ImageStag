/**
 * FloatingPanel - A flexible, draggable, dockable panel component
 *
 * Features:
 * - Draggable with drag handle
 * - Dockable to edges (left, right, top, bottom)
 * - Collapsible/expandable (implode/explode)
 * - Pin functionality (keeps drawer panels open)
 * - Compact mode when pinned in tablet mode
 * - Remembers position and state in localStorage
 */

export class FloatingPanel {
    constructor(options = {}) {
        this.id = options.id || `panel-${Date.now()}`;
        this.title = options.title || 'Panel';
        this.icon = options.icon || null;

        // Position and size
        this.x = options.x ?? 100;
        this.y = options.y ?? 100;
        this.width = options.width ?? 250;
        this.height = options.height ?? 300;
        this.minWidth = options.minWidth ?? 150;
        this.minHeight = options.minHeight ?? 100;

        // State
        this.isVisible = options.visible ?? true;
        this.isCollapsed = options.collapsed ?? false;
        this.isPinned = options.pinned ?? false;
        this.isCompact = options.compact ?? false;

        // Docking
        this.dockPosition = options.dockPosition ?? null; // 'left', 'right', 'top', 'bottom', or null for floating
        this.dockOrder = options.dockOrder ?? 0; // Order when multiple panels docked to same edge

        // Internal state
        this.isDragging = false;
        this.isResizing = false;
        this.dragOffset = { x: 0, y: 0 };
        this.element = null;
        this.contentElement = null;

        // Callbacks
        this.onStateChange = options.onStateChange || null;
        this.onDock = options.onDock || null;
        this.onClose = options.onClose || null;

        // Storage key for persistence
        this.storageKey = `stagforge-panel-${this.id}`;

        // Load saved state
        this.loadState();
    }

    /**
     * Create the panel DOM element
     * @param {HTMLElement} container - Parent container
     * @returns {HTMLElement}
     */
    createElement(container) {
        this.container = container;

        // Main panel element
        this.element = document.createElement('div');
        this.element.className = 'floating-panel';
        this.element.id = this.id;
        this.element.dataset.panelId = this.id;

        this.updateClasses();
        this.updatePosition();

        // Header with drag handle
        const header = document.createElement('div');
        header.className = 'fp-header';
        header.innerHTML = `
            <div class="fp-drag-handle">
                ${this.icon ? `<span class="fp-icon">${this.icon}</span>` : ''}
                <span class="fp-title">${this.title}</span>
            </div>
            <div class="fp-controls">
                <button class="fp-btn fp-pin-btn" title="Pin panel">
                    <span class="fp-pin-icon"></span>
                </button>
                <button class="fp-btn fp-collapse-btn" title="Collapse">
                    <span class="fp-collapse-icon"></span>
                </button>
                <button class="fp-btn fp-close-btn" title="Close">
                    <span class="fp-close-icon"></span>
                </button>
            </div>
        `;

        // Content area
        this.contentElement = document.createElement('div');
        this.contentElement.className = 'fp-content';

        // Resize handle (bottom-right corner)
        const resizeHandle = document.createElement('div');
        resizeHandle.className = 'fp-resize-handle';

        // Assemble
        this.element.appendChild(header);
        this.element.appendChild(this.contentElement);
        this.element.appendChild(resizeHandle);

        // Bind events
        this.bindEvents(header, resizeHandle);

        container.appendChild(this.element);
        return this.element;
    }

    /**
     * Bind all event listeners
     */
    bindEvents(header, resizeHandle) {
        const dragHandle = header.querySelector('.fp-drag-handle');

        // Drag events
        dragHandle.addEventListener('mousedown', (e) => this.startDrag(e));
        dragHandle.addEventListener('touchstart', (e) => this.startDrag(e), { passive: false });

        // Resize events
        resizeHandle.addEventListener('mousedown', (e) => this.startResize(e));
        resizeHandle.addEventListener('touchstart', (e) => this.startResize(e), { passive: false });

        // Control buttons
        header.querySelector('.fp-pin-btn').addEventListener('click', () => this.togglePin());
        header.querySelector('.fp-collapse-btn').addEventListener('click', () => this.toggleCollapse());
        header.querySelector('.fp-close-btn').addEventListener('click', () => this.close());

        // Double-click header to collapse
        dragHandle.addEventListener('dblclick', () => this.toggleCollapse());

        // Global move/end events
        document.addEventListener('mousemove', (e) => this.onMouseMove(e));
        document.addEventListener('mouseup', () => this.endDragOrResize());
        document.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
        document.addEventListener('touchend', () => this.endDragOrResize());

        // Prevent text selection during drag
        this.element.addEventListener('selectstart', (e) => {
            if (this.isDragging || this.isResizing) e.preventDefault();
        });
    }

    /**
     * Start dragging the panel
     */
    startDrag(e) {
        if (this.dockPosition && this.isPinned) return; // Can't drag pinned docked panels

        e.preventDefault();
        this.isDragging = true;
        this.element.classList.add('dragging');

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;

        const rect = this.element.getBoundingClientRect();
        this.dragOffset.x = clientX - rect.left;
        this.dragOffset.y = clientY - rect.top;

        // Undock if dragging a docked panel
        if (this.dockPosition) {
            this.undock();
        }
    }

    /**
     * Start resizing the panel
     */
    startResize(e) {
        if (this.isCollapsed) return;

        e.preventDefault();
        e.stopPropagation();
        this.isResizing = true;
        this.element.classList.add('resizing');
    }

    /**
     * Handle mouse move for drag/resize
     */
    onMouseMove(e) {
        if (this.isDragging) {
            this.doDrag(e.clientX, e.clientY);
        } else if (this.isResizing) {
            this.doResize(e.clientX, e.clientY);
        }
    }

    /**
     * Handle touch move for drag/resize
     */
    onTouchMove(e) {
        if (!this.isDragging && !this.isResizing) return;
        e.preventDefault();

        const touch = e.touches[0];
        if (this.isDragging) {
            this.doDrag(touch.clientX, touch.clientY);
        } else if (this.isResizing) {
            this.doResize(touch.clientX, touch.clientY);
        }
    }

    /**
     * Perform drag movement
     */
    doDrag(clientX, clientY) {
        if (!this.isDragging || !this.container) return;

        const containerRect = this.container.getBoundingClientRect();
        let newX = clientX - containerRect.left - this.dragOffset.x;
        let newY = clientY - containerRect.top - this.dragOffset.y;

        // Constrain to container bounds
        newX = Math.max(0, Math.min(newX, containerRect.width - this.element.offsetWidth));
        newY = Math.max(0, Math.min(newY, containerRect.height - this.element.offsetHeight));

        this.x = newX;
        this.y = newY;
        this.updatePosition();

        // Check for dock zones
        this.checkDockZones(clientX, clientY, containerRect);
    }

    /**
     * Perform resize
     */
    doResize(clientX, clientY) {
        if (!this.isResizing) return;

        const rect = this.element.getBoundingClientRect();
        let newWidth = clientX - rect.left;
        let newHeight = clientY - rect.top;

        // Apply constraints
        newWidth = Math.max(this.minWidth, newWidth);
        newHeight = Math.max(this.minHeight, newHeight);

        this.width = newWidth;
        this.height = newHeight;
        this.updateSize();
    }

    /**
     * End drag or resize operation
     */
    endDragOrResize() {
        if (this.isDragging) {
            this.isDragging = false;
            this.element.classList.remove('dragging');

            // Finalize docking if in dock zone
            if (this.pendingDock) {
                this.dock(this.pendingDock);
                this.pendingDock = null;
            }

            this.saveState();
        }

        if (this.isResizing) {
            this.isResizing = false;
            this.element.classList.remove('resizing');
            this.saveState();
        }

        this.element.classList.remove('dock-preview-left', 'dock-preview-right',
                                       'dock-preview-top', 'dock-preview-bottom');
    }

    /**
     * Check if panel is in a dock zone
     */
    checkDockZones(clientX, clientY, containerRect) {
        const dockThreshold = 40; // pixels from edge to trigger dock

        this.pendingDock = null;
        this.element.classList.remove('dock-preview-left', 'dock-preview-right',
                                       'dock-preview-top', 'dock-preview-bottom');

        if (clientX - containerRect.left < dockThreshold) {
            this.pendingDock = 'left';
            this.element.classList.add('dock-preview-left');
        } else if (containerRect.right - clientX < dockThreshold) {
            this.pendingDock = 'right';
            this.element.classList.add('dock-preview-right');
        } else if (clientY - containerRect.top < dockThreshold) {
            this.pendingDock = 'top';
            this.element.classList.add('dock-preview-top');
        } else if (containerRect.bottom - clientY < dockThreshold) {
            this.pendingDock = 'bottom';
            this.element.classList.add('dock-preview-bottom');
        }
    }

    /**
     * Dock panel to an edge
     */
    dock(position) {
        this.dockPosition = position;
        this.updateClasses();
        this.saveState();

        if (this.onDock) {
            this.onDock(this, position);
        }
    }

    /**
     * Undock panel (make it floating)
     */
    undock() {
        this.dockPosition = null;
        this.isPinned = false;
        this.updateClasses();
        this.saveState();
    }

    /**
     * Toggle pin state
     */
    togglePin() {
        this.isPinned = !this.isPinned;
        this.updateClasses();
        this.saveState();
        this.notifyStateChange();
    }

    /**
     * Toggle collapsed state
     */
    toggleCollapse() {
        this.isCollapsed = !this.isCollapsed;
        this.updateClasses();
        this.saveState();
        this.notifyStateChange();
    }

    /**
     * Expand panel (opposite of collapse)
     */
    expand() {
        if (this.isCollapsed) {
            this.isCollapsed = false;
            this.updateClasses();
            this.saveState();
            this.notifyStateChange();
        }
    }

    /**
     * Collapse panel
     */
    collapse() {
        if (!this.isCollapsed) {
            this.isCollapsed = true;
            this.updateClasses();
            this.saveState();
            this.notifyStateChange();
        }
    }

    /**
     * Show the panel
     */
    show() {
        this.isVisible = true;
        this.updateClasses();
        this.saveState();
        this.notifyStateChange();
    }

    /**
     * Hide the panel
     */
    hide() {
        this.isVisible = false;
        this.updateClasses();
        this.saveState();
        this.notifyStateChange();
    }

    /**
     * Close the panel (hide with callback)
     */
    close() {
        this.hide();
        if (this.onClose) {
            this.onClose(this);
        }
    }

    /**
     * Set compact mode (for pinned panels in tablet mode)
     */
    setCompact(compact) {
        this.isCompact = compact;
        this.updateClasses();
    }

    /**
     * Update CSS classes based on state
     */
    updateClasses() {
        if (!this.element) return;

        const classes = ['floating-panel'];

        if (!this.isVisible) classes.push('hidden');
        if (this.isCollapsed) classes.push('collapsed');
        if (this.isPinned) classes.push('pinned');
        if (this.isCompact) classes.push('compact');
        if (this.dockPosition) {
            classes.push('docked', `docked-${this.dockPosition}`);
        } else {
            classes.push('floating');
        }

        this.element.className = classes.join(' ');
    }

    /**
     * Update panel position
     */
    updatePosition() {
        if (!this.element || this.dockPosition) return;

        this.element.style.left = `${this.x}px`;
        this.element.style.top = `${this.y}px`;
    }

    /**
     * Update panel size
     */
    updateSize() {
        if (!this.element) return;

        this.element.style.width = `${this.width}px`;
        if (!this.isCollapsed) {
            this.element.style.height = `${this.height}px`;
        }
    }

    /**
     * Set panel content
     */
    setContent(content) {
        if (!this.contentElement) return;

        if (typeof content === 'string') {
            this.contentElement.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            this.contentElement.innerHTML = '';
            this.contentElement.appendChild(content);
        }
    }

    /**
     * Get content element for external manipulation
     */
    getContentElement() {
        return this.contentElement;
    }

    /**
     * Save panel state to localStorage
     */
    saveState() {
        try {
            const state = {
                x: this.x,
                y: this.y,
                width: this.width,
                height: this.height,
                isVisible: this.isVisible,
                isCollapsed: this.isCollapsed,
                isPinned: this.isPinned,
                dockPosition: this.dockPosition,
                dockOrder: this.dockOrder
            };
            localStorage.setItem(this.storageKey, JSON.stringify(state));
        } catch (e) {
            console.warn('Could not save panel state:', e);
        }
    }

    /**
     * Load panel state from localStorage
     */
    loadState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const state = JSON.parse(saved);
                Object.assign(this, state);
            }
        } catch (e) {
            console.warn('Could not load panel state:', e);
        }
    }

    /**
     * Notify state change callback
     */
    notifyStateChange() {
        if (this.onStateChange) {
            this.onStateChange(this);
        }
    }

    /**
     * Destroy the panel and clean up
     */
    destroy() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        this.element = null;
        this.contentElement = null;
    }
}

/**
 * PanelManager - Manages multiple FloatingPanel instances
 */
export class PanelManager {
    constructor(container) {
        this.container = container;
        this.panels = new Map();
        this.dockGroups = {
            left: [],
            right: [],
            top: [],
            bottom: []
        };
    }

    /**
     * Create and register a new panel
     */
    createPanel(options) {
        const panel = new FloatingPanel({
            ...options,
            onDock: (p, position) => this.handleDock(p, position),
            onStateChange: (p) => this.handleStateChange(p)
        });

        panel.createElement(this.container);
        this.panels.set(panel.id, panel);

        if (panel.dockPosition) {
            this.addToDockGroup(panel);
        }

        return panel;
    }

    /**
     * Get a panel by ID
     */
    getPanel(id) {
        return this.panels.get(id);
    }

    /**
     * Handle panel dock event
     */
    handleDock(panel, position) {
        // Remove from old dock group
        this.removeFromDockGroups(panel);

        // Add to new dock group
        this.addToDockGroup(panel);

        // Reflow docked panels
        this.reflowDockGroup(position);
    }

    /**
     * Handle panel state change
     */
    handleStateChange(panel) {
        if (panel.dockPosition) {
            this.reflowDockGroup(panel.dockPosition);
        }
    }

    /**
     * Add panel to dock group
     */
    addToDockGroup(panel) {
        if (!panel.dockPosition) return;

        const group = this.dockGroups[panel.dockPosition];
        if (group && !group.includes(panel)) {
            group.push(panel);
            group.sort((a, b) => a.dockOrder - b.dockOrder);
        }
    }

    /**
     * Remove panel from all dock groups
     */
    removeFromDockGroups(panel) {
        for (const group of Object.values(this.dockGroups)) {
            const idx = group.indexOf(panel);
            if (idx !== -1) {
                group.splice(idx, 1);
            }
        }
    }

    /**
     * Reflow panels in a dock group
     */
    reflowDockGroup(position) {
        const group = this.dockGroups[position];
        if (!group) return;

        let offset = 0;
        for (const panel of group) {
            if (!panel.isVisible) continue;

            if (position === 'left' || position === 'right') {
                panel.element.style.top = `${offset}px`;
                offset += panel.isCollapsed ? 40 : panel.height;
            } else {
                panel.element.style.left = `${offset}px`;
                offset += panel.isCollapsed ? 40 : panel.width;
            }
        }
    }

    /**
     * Set compact mode for all panels
     */
    setAllCompact(compact) {
        for (const panel of this.panels.values()) {
            panel.setCompact(compact);
        }
    }

    /**
     * Destroy all panels
     */
    destroyAll() {
        for (const panel of this.panels.values()) {
            panel.destroy();
        }
        this.panels.clear();
    }
}

export default FloatingPanel;
