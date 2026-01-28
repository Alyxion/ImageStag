/**
 * Slopstag Image Editor - Main Application
 */
import { EventBus } from './utils/EventBus.js';
import { LayerStack } from './core/LayerStack.js';
import { Renderer } from './core/Renderer.js';
import { History } from './core/History.js';
import { ToolManager } from './tools/ToolManager.js';
import { PluginManager } from './plugins/PluginManager.js';
import * as LayerEffects from './core/LayerEffects.js';

// Tools
import { BrushTool } from './tools/BrushTool.js';
import { EraserTool } from './tools/EraserTool.js';
import { ShapeTool } from './tools/ShapeTool.js';
import { FillTool } from './tools/FillTool.js';
import { EyedropperTool } from './tools/EyedropperTool.js';
import { MoveTool } from './tools/MoveTool.js';

// UI
import { Toolbar } from './ui/Toolbar.js';
import { ToolPanel } from './ui/ToolPanel.js';
import { LayerPanel } from './ui/LayerPanel.js';
import { PropertyPanel } from './ui/PropertyPanel.js';
import { ColorPicker } from './ui/ColorPicker.js';
import { StatusBar } from './ui/StatusBar.js';

class EditorApp {
    constructor() {
        this.eventBus = new EventBus();

        // Default document size
        this.canvasWidth = 800;
        this.canvasHeight = 600;

        // Default colors
        this.foregroundColor = '#000000';
        this.backgroundColor = '#FFFFFF';

        // Get display canvas
        this.displayCanvas = document.getElementById('main-canvas');

        // Initialize core systems
        this.layerStack = new LayerStack(this.canvasWidth, this.canvasHeight, this.eventBus);
        this.renderer = new Renderer(this.displayCanvas, this.layerStack);
        this.history = new History(this);
        this.toolManager = new ToolManager(this);
        this.pluginManager = new PluginManager(this);

        // Register tools
        this.registerTools();

        // Bind events
        this.bindEvents();

        // Initialize
        this.init();
    }

    registerTools() {
        this.toolManager.register(MoveTool);
        this.toolManager.register(BrushTool);
        this.toolManager.register(EraserTool);
        this.toolManager.register(ShapeTool);
        this.toolManager.register(FillTool);
        this.toolManager.register(EyedropperTool);
    }

    async init() {
        // Resize display canvas
        this.resizeDisplayCanvas();

        // Set up renderer
        this.renderer.resize(this.canvasWidth, this.canvasHeight);

        // Create initial background layer
        const bgLayer = this.layerStack.addLayer({ name: 'Background' });
        bgLayer.fill('#FFFFFF');

        // Initialize plugin system (connect to backend)
        await this.pluginManager.initialize();

        // Initialize UI components
        this.toolbar = new Toolbar(this);
        this.toolPanel = new ToolPanel(this);
        this.colorPicker = new ColorPicker(this);
        this.layerPanel = new LayerPanel(this);
        this.propertyPanel = new PropertyPanel(this);
        this.statusBar = new StatusBar(this);

        // Select default tool
        this.toolManager.select('brush');

        // Center and render
        this.renderer.fitToViewport();

        this.statusBar.setStatus('Ready');
        console.log('Slopstag Image Editor initialized');
    }

    bindEvents() {
        // Canvas mouse events
        this.displayCanvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.displayCanvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.displayCanvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.displayCanvas.addEventListener('mouseleave', (e) => this.handleMouseLeave(e));
        this.displayCanvas.addEventListener('wheel', (e) => this.handleWheel(e));

        // Keyboard events
        window.addEventListener('keydown', (e) => this.handleKeyDown(e));
        window.addEventListener('keyup', (e) => this.handleKeyUp(e));

        // Window resize
        window.addEventListener('resize', () => this.resizeDisplayCanvas());

        // Prevent context menu on canvas
        this.displayCanvas.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    /**
     * Get coordinates in both document space and active layer's local space.
     * @param {number} docX - X in document space
     * @param {number} docY - Y in document space
     * @returns {{ docX: number, docY: number, layerX: number, layerY: number }}
     */
    getCoordinates(docX, docY) {
        const layer = this.layerStack.getActiveLayer();
        let layerX = docX;
        let layerY = docY;

        if (layer && layer.docToLayer) {
            const layerCoords = layer.docToLayer(docX, docY);
            layerX = layerCoords.x;
            layerY = layerCoords.y;
        } else if (layer) {
            // Fallback for layers without docToLayer (simple offset)
            layerX = docX - (layer.offsetX || 0);
            layerY = docY - (layer.offsetY || 0);
        }

        return { docX, docY, layerX, layerY };
    }

    handleMouseDown(e) {
        const rect = this.displayCanvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const { x, y } = this.renderer.screenToCanvas(screenX, screenY);

        // Middle mouse for panning
        if (e.button === 1) {
            this.isPanning = true;
            this.lastPanX = e.clientX;
            this.lastPanY = e.clientY;
            return;
        }

        const coords = this.getCoordinates(x, y);
        this.toolManager.currentTool?.onMouseDown(e, coords.layerX, coords.layerY, coords);
    }

    handleMouseMove(e) {
        const rect = this.displayCanvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const { x, y } = this.renderer.screenToCanvas(screenX, screenY);

        // Handle panning
        if (this.isPanning) {
            const dx = e.clientX - this.lastPanX;
            const dy = e.clientY - this.lastPanY;
            this.renderer.pan(dx, dy);
            this.lastPanX = e.clientX;
            this.lastPanY = e.clientY;
            return;
        }

        const coords = this.getCoordinates(x, y);
        this.toolManager.currentTool?.onMouseMove(e, coords.layerX, coords.layerY, coords);

        // Update status bar coordinates (show document coords)
        this.statusBar?.setCoordinates(Math.round(x), Math.round(y));
    }

    handleMouseUp(e) {
        if (this.isPanning) {
            this.isPanning = false;
            return;
        }

        const rect = this.displayCanvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const { x, y } = this.renderer.screenToCanvas(screenX, screenY);

        const coords = this.getCoordinates(x, y);
        this.toolManager.currentTool?.onMouseUp(e, coords.layerX, coords.layerY, coords);
    }

    handleMouseLeave(e) {
        this.isPanning = false;
        this.toolManager.currentTool?.onMouseLeave(e);
    }

    handleWheel(e) {
        e.preventDefault();

        const rect = this.displayCanvas.getBoundingClientRect();
        const centerX = e.clientX - rect.left;
        const centerY = e.clientY - rect.top;

        // Zoom with scroll
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        this.renderer.zoomAt(factor, centerX, centerY);
        this.toolbar?.updateZoomDisplay();
    }

    handleKeyDown(e) {
        // Undo/Redo shortcuts
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                this.history.undo();
                return;
            } else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') {
                e.preventDefault();
                this.history.redo();
                return;
            }
        }

        // Tool shortcuts
        if (!e.ctrlKey && !e.metaKey && !e.altKey) {
            // Color shortcuts
            if (e.key === 'x' || e.key === 'X') {
                const temp = this.foregroundColor;
                this.foregroundColor = this.backgroundColor;
                this.backgroundColor = temp;
                this.eventBus.emit('color:foreground-changed', { color: this.foregroundColor });
                this.eventBus.emit('color:background-changed', { color: this.backgroundColor });
                return;
            }
            if (e.key === 'd' || e.key === 'D') {
                this.foregroundColor = '#000000';
                this.backgroundColor = '#FFFFFF';
                this.eventBus.emit('color:foreground-changed', { color: '#000000' });
                this.eventBus.emit('color:background-changed', { color: '#FFFFFF' });
                return;
            }

            // Tool shortcuts
            if (this.toolManager.handleShortcut(e.key)) {
                return;
            }
        }

        // Space for temporary pan
        if (e.key === ' ' && !this.isSpacePanning) {
            this.isSpacePanning = true;
            this.displayCanvas.style.cursor = 'grab';
        }

        this.toolManager.currentTool?.onKeyDown(e);
    }

    handleKeyUp(e) {
        if (e.key === ' ') {
            this.isSpacePanning = false;
            const tool = this.toolManager.currentTool;
            if (tool) {
                this.displayCanvas.style.cursor = tool.constructor.cursor;
            }
        }

        this.toolManager.currentTool?.onKeyUp(e);
    }

    resizeDisplayCanvas() {
        const container = this.displayCanvas.parentElement;
        this.displayCanvas.width = container.clientWidth;
        this.displayCanvas.height = container.clientHeight;
        this.renderer.centerCanvas();
    }

    /**
     * Create a new document.
     * @param {number} width
     * @param {number} height
     */
    newDocument(width, height) {
        this.canvasWidth = width;
        this.canvasHeight = height;

        // Reset layer stack
        this.layerStack = new LayerStack(width, height, this.eventBus);
        this.renderer.layerStack = this.layerStack;
        this.renderer.resize(width, height);

        // Create initial layer with white background
        const bgLayer = this.layerStack.addLayer({ name: 'Background' });
        bgLayer.fill('#FFFFFF');

        // Clear history
        this.history.clear();

        // Update UI
        this.resizeDisplayCanvas();
        this.layerPanel?.update();
        this.statusBar?.updateSize();

        this.eventBus.emit('document:new', { width, height });
    }
}

// Wait for NiceGUI/Vue to mount elements
function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }

        const observer = new MutationObserver((mutations, obs) => {
            const el = document.querySelector(selector);
            if (el) {
                obs.disconnect();
                resolve(el);
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });

        setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Element ${selector} not found within ${timeout}ms`));
        }, timeout);
    });
}

// Initialize when canvas element is available
waitForElement('#main-canvas').then(() => {
    console.log('Canvas element found, initializing Slopstag...');
    window.app = new EditorApp();
    window.LayerEffects = LayerEffects;  // Export for testing and plugins
}).catch(err => {
    console.error('Failed to initialize:', err);
});
