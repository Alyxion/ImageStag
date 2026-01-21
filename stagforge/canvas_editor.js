/**
 * Slopstag Canvas Editor - NiceGUI Vue Component
 *
 * This Vue component provides the UI shell for the image editor.
 * It imports the core modules and initializes the editor in mounted().
 */

// Import editor mixins (using absolute path for NiceGUI static serving)
import {
    ColorManagementMixin,
    LayerOperationsMixin,
    LayerDragDropMixin,
    HistoryManagerMixin,
    ZoomManagerMixin,
    NavigatorManagerMixin,
    ToolManagerMixin,
    ColorPickerMixin,
    CanvasEventsMixin,
    KeyboardEventsMixin,
    MenuManagerMixin,
    PopupMenuMixin,
    ViewManagerMixin,
    ClipboardManagerMixin,
} from '/static/js/editor/mixins/index.js';

// Store editor state outside Vue's reactivity (like Three.js pattern)
const editorState = new WeakMap();

export default {
    template: `
        <div class="editor-root" ref="root" :data-theme="currentTheme" :data-mode="currentUIMode">

            <!-- ==================== TABLET MODE UI ==================== -->
            <template v-if="currentUIMode === 'tablet'">
                <!-- Tablet Top Bar - Icon buttons with labels -->
                <div class="tablet-top-bar">
                    <!-- Tools button -->
                    <button class="tablet-icon-btn" @click="tabletLeftDrawerOpen = !tabletLeftDrawerOpen"
                        :class="{ active: tabletLeftDrawerOpen }">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('tools')"></span>
                        <span class="tablet-icon-btn-label">Tools</span>
                    </button>

                    <!-- File menu -->
                    <button class="tablet-icon-btn" @click="toggleTabletPopup('file')"
                        :class="{ active: tabletFileMenuOpen }">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('file')"></span>
                        <span class="tablet-icon-btn-label">File</span>
                    </button>

                    <!-- Edit menu -->
                    <button class="tablet-icon-btn" @click="toggleTabletPopup('edit')"
                        :class="{ active: tabletEditMenuOpen }">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('edit')"></span>
                        <span class="tablet-icon-btn-label">Edit</span>
                    </button>

                    <!-- View menu -->
                    <button class="tablet-icon-btn" @click="toggleTabletPopup('view')"
                        :class="{ active: tabletViewMenuOpen }">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('view')"></span>
                        <span class="tablet-icon-btn-label">View</span>
                    </button>

                    <!-- Filters panel button -->
                    <button class="tablet-icon-btn" @click="toggleTabletPopup('filter')"
                        :class="{ active: tabletFilterPanelOpen }">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('filter')"></span>
                        <span class="tablet-icon-btn-label">Filter</span>
                    </button>

                    <!-- Image menu -->
                    <button class="tablet-icon-btn" @click="toggleTabletPopup('image')"
                        :class="{ active: tabletImageMenuOpen }">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('image')"></span>
                        <span class="tablet-icon-btn-label">Image</span>
                    </button>

                    <!-- Title (flexible space) -->
                    <span class="tablet-title-spacer"></span>

                    <!-- Undo/Redo -->
                    <button class="tablet-icon-btn" @click="undo" :disabled="!canUndo">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('undo')"></span>
                        <span class="tablet-icon-btn-label">Undo</span>
                    </button>
                    <button class="tablet-icon-btn" @click="redo" :disabled="!canRedo">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('redo')"></span>
                        <span class="tablet-icon-btn-label">Redo</span>
                    </button>

                    <!-- Deselect (only show if selection exists) -->
                    <button class="tablet-icon-btn" v-if="hasSelection" @click="tabletMenuAction('deselect')">
                        <span class="tablet-icon-btn-icon" v-html="getToolIcon('deselect')"></span>
                        <span class="tablet-icon-btn-label">Deselect</span>
                    </button>

                    <!-- Zoom -->
                    <button class="tablet-icon-btn" @click="toggleTabletPopup('zoom')">
                        <span class="tablet-icon-btn-icon">{{ Math.round(zoom * 100) }}%</span>
                        <span class="tablet-icon-btn-label">Zoom</span>
                    </button>
                </div>

                <!-- ==================== LEFT DOCK (Tools) ==================== -->
                <div class="tablet-dock-stack left">
                    <div class="tablet-dock-panel" v-if="tabletLeftDrawerOpen">
                        <div class="tablet-panel-header">
                            <button class="tablet-panel-icon-close" @click="tabletLeftDrawerOpen = false">
                                <span v-html="getToolIcon('tools')"></span>
                            </button>
                            <span class="tablet-panel-title">Tools</span>
                        </div>
                        <div class="tablet-panel-content">
                            <div class="tablet-tool-grid">
                                <button v-for="(tool, index) in tabletAllTools" :key="tool.id"
                                    class="tablet-tool-btn-large"
                                    :class="{ active: currentToolId === tool.id, 'drag-over': toolDragOverIndex === index }"
                                    :title="tool.name"
                                    draggable="true"
                                    @click="selectTool(tool.id)"
                                    @dragstart="onToolDragStart(index, $event)"
                                    @dragover.prevent="onToolDragOver(index, $event)"
                                    @dragleave="onToolDragLeave"
                                    @drop.prevent="onToolDrop(index)"
                                    @dragend="onToolDragEnd">
                                    <span class="tablet-tool-icon" v-html="getToolIcon(tool.icon)"></span>
                                    <span class="tablet-tool-label">{{ tool.name }}</span>
                                </button>
                            </div>
                        </div>
                    </div>
                    <button class="tablet-dock-icon" v-if="!tabletLeftDrawerOpen" @click="tabletLeftDrawerOpen = true">
                        <span v-html="getToolIcon('tools')"></span>
                    </button>
                </div>

                <!-- ==================== RIGHT DOCK (Nav, Layers, History) ==================== -->
                <div class="tablet-dock-stack right">
                    <!-- Navigator: Panel or Icon -->
                    <div class="tablet-dock-panel" v-if="tabletNavPanelOpen" ref="sidePanelNav">
                        <div class="tablet-panel-header">
                            <button class="tablet-panel-icon-close" @click="toggleSidePanel('nav')">
                                <span v-html="getToolIcon('navigator')"></span>
                            </button>
                            <span class="tablet-panel-title">Navigator</span>
                        </div>
                        <div class="tablet-panel-content">
                            <canvas ref="tabletNavigatorCanvas" class="tablet-navigator-canvas"
                                @mousedown="navigatorMouseDown" @mousemove="navigatorMouseMove"
                                @mouseup="navigatorMouseUp" @mouseleave="navigatorMouseUp"
                                @touchstart.prevent="navigatorTouchStart" @touchmove.prevent="navigatorTouchMove"
                                @touchend.prevent="navigatorMouseUp"></canvas>
                            <div class="tablet-zoom-controls">
                                <button class="tablet-btn tablet-btn-secondary" @click="zoomOut">−</button>
                                <span class="tablet-zoom-display">{{ Math.round(zoom * 100) }}%</span>
                                <button class="tablet-btn tablet-btn-secondary" @click="zoomIn">+</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="setZoomPercent(100)">1:1</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="fitToWindow">Fit</button>
                            </div>
                        </div>
                    </div>
                    <button class="tablet-dock-icon" v-if="!tabletNavPanelOpen" @click="toggleSidePanel('nav')">
                        <span v-html="getToolIcon('navigator')"></span>
                    </button>

                    <!-- Layers: Panel or Icon -->
                    <div class="tablet-dock-panel" v-if="tabletLayersPanelOpen" ref="sidePanelLayers">
                        <div class="tablet-panel-header">
                            <button class="tablet-panel-icon-close" @click="toggleSidePanel('layers')">
                                <span v-html="getToolIcon('layers')"></span>
                            </button>
                            <span class="tablet-panel-title">Layers</span>
                        </div>
                        <div class="tablet-panel-content">
                            <div class="tablet-layers-list">
                                <div v-for="(layer, idx) in visibleLayers" :key="layer.id" class="tablet-layer-item"
                                    :class="{
                                        active: layer.id === activeLayerId,
                                        'layer-group': layer.isGroup,
                                        'child-layer': layer.indentLevel > 0,
                                        'child-layer-2': layer.indentLevel > 1,
                                        'drag-over-top': layerDragOverIndex === idx && layerDragOverPosition === 'top',
                                        'drag-over-bottom': layerDragOverIndex === idx && layerDragOverPosition === 'bottom',
                                        'drag-over-into': layerDragOverGroup === layer.id && layerDragOverPosition === 'into',
                                        'dragging': layerDragIndex === idx
                                    }"
                                    draggable="true"
                                    @click="selectLayer(layer.id)"
                                    @dragstart="onLayerDragStart(idx, layer, $event)"
                                    @dragover.prevent="onLayerDragOver(idx, layer, $event)"
                                    @dragleave="onLayerDragLeave($event)"
                                    @drop.prevent="onLayerDrop(idx, layer)"
                                    @dragend="onLayerDragEnd">
                                    <button v-if="layer.isGroup" class="tablet-layer-expand"
                                        :class="{ expanded: layer.expanded }"
                                        @click.stop="toggleGroupExpanded(layer.id)">
                                        ▶
                                    </button>
                                    <div class="tablet-layer-icon" v-if="layer.isGroup">📁</div>
                                    <canvas v-else class="tablet-layer-thumb" :ref="'tabletLayerThumb_' + layer.id"></canvas>
                                    <div class="tablet-layer-info">
                                        <div class="tablet-layer-name">{{ layer.name }}</div>
                                        <div class="tablet-layer-opacity">{{ Math.round(layer.opacity * 100) }}%</div>
                                    </div>
                                    <button class="tablet-layer-visibility" :class="{ visible: layer.visible }"
                                        @click.stop="toggleLayerVisibility(layer.id)">
                                        {{ layer.visible ? '👁' : '○' }}
                                    </button>
                                    <button class="tablet-layer-menu-btn" @click.stop="showLayerContextMenuTouch($event, layer)">
                                        ☰
                                    </button>
                                </div>
                            </div>
                            <div class="tablet-layer-actions">
                                <button class="tablet-btn tablet-btn-primary" @click="addLayer">+ New</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="duplicateLayer">Dup</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="deleteLayer">Del</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="mergeDown">Merge</button>
                            </div>
                            <div class="tablet-layer-props" v-if="activeLayerId">
                                <div class="tablet-prop-row">
                                    <label>Opacity</label>
                                    <input type="range" min="0" max="100" :value="activeLayerOpacity"
                                        @input="updateLayerOpacity(Number($event.target.value))">
                                    <span>{{ activeLayerOpacity }}%</span>
                                </div>
                                <div class="tablet-prop-row">
                                    <label>Blend</label>
                                    <select class="tablet-select" v-model="activeLayerBlendMode" @change="updateLayerBlendMode">
                                        <option v-for="mode in blendModes" :key="mode" :value="mode">{{ mode }}</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                    <button class="tablet-dock-icon" v-if="!tabletLayersPanelOpen" @click="toggleSidePanel('layers')">
                        <span v-html="getToolIcon('layers')"></span>
                    </button>

                    <!-- History: Panel or Icon -->
                    <div class="tablet-dock-panel" v-if="tabletHistoryPanelOpen" ref="sidePanelHistory">
                        <div class="tablet-panel-header">
                            <button class="tablet-panel-icon-close" @click="toggleSidePanel('history')">
                                <span v-html="getToolIcon('history')"></span>
                            </button>
                            <span class="tablet-panel-title">History</span>
                        </div>
                        <div class="tablet-panel-content">
                            <div class="tablet-history-list">
                                <div v-for="(item, idx) in historyList" :key="idx" class="tablet-history-item"
                                    :class="{ active: idx === historyIndex, future: idx > historyIndex }"
                                    @click="jumpToHistory(idx)">
                                    <span class="tablet-history-icon">{{ idx > historyIndex ? '○' : '●' }}</span>
                                    <span class="tablet-history-name">{{ item.name }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <button class="tablet-dock-icon" v-if="!tabletHistoryPanelOpen" @click="toggleSidePanel('history')">
                        <span v-html="getToolIcon('history')"></span>
                    </button>
                </div>

                <!-- ==================== FILTERS PANEL (Special tabbed panel with previews) ==================== -->
                <div class="tablet-floating-panel filters-panel" :class="{ open: tabletFilterPanelOpen }"
                    style="left: 50%; top: 70px; transform: translateX(-50%); width: 500px; max-height: 80vh;">
                    <div class="tablet-panel-header">
                        <span class="tablet-panel-title">Filters</span>
                        <div class="tablet-panel-controls">
                            <button class="tablet-panel-close" @click="tabletFilterPanelOpen = false">&times;</button>
                        </div>
                    </div>
                    <!-- Filter category tabs -->
                    <div class="tablet-filter-tabs">
                        <button v-for="cat in filterCategories" :key="cat"
                            class="tablet-filter-tab" :class="{ active: tabletFilterTab === cat }"
                            @click="switchFilterTab(cat)">
                            {{ formatCategory(cat) }}
                        </button>
                    </div>
                    <!-- Filter grid with previews -->
                    <div class="tablet-panel-content tablet-filter-grid-container">
                        <div class="tablet-filter-grid">
                            <div v-for="f in filtersInCurrentTab" :key="f.id"
                                class="tablet-filter-card" @click="openFilterDialog(f); tabletFilterPanelOpen = false">
                                <div class="tablet-filter-preview">
                                    <img v-if="filterPreviews[f.id]" :src="filterPreviews[f.id]" class="tablet-filter-preview-img">
                                    <div v-else-if="filterPreviewsLoading[f.id]" class="tablet-filter-loading">Loading...</div>
                                    <div v-else class="tablet-filter-placeholder" @click.stop="loadFilterPreview(f.id)">
                                        <span v-html="getToolIcon('filter')"></span>
                                    </div>
                                </div>
                                <div class="tablet-filter-name">{{ f.name }}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Drawer Overlay (tap to close non-pinned elements) -->
                <div class="tablet-drawer-overlay"
                    :class="{ visible: hasOpenUnpinnedPopup }"
                    @click="closeAllTabletPopups"></div>

                <!-- ==================== INDIVIDUAL MENU POPUPS ==================== -->

                <!-- File Menu Popup -->
                <div v-if="tabletFileMenuOpen" class="tablet-menu-popup file-menu" @click.stop>
                    <button class="tablet-menu-item" @click="tabletMenuAction('new')">New Document...</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('open')">Open... (Ctrl+O)</button>
                    <div class="tablet-menu-divider"></div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('save')">Save (Ctrl+S)</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('saveAs')">Save As... (Ctrl+Shift+S)</button>
                    <div class="tablet-menu-divider"></div>
                    <div class="tablet-menu-subheader">Load Sample Image</div>
                    <button class="tablet-menu-item" v-for="img in sampleImages" :key="img.id"
                        @click="tabletMenuAction('loadSample', img)">{{ img.name }}</button>
                    <div class="tablet-menu-divider"></div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('export')">Export PNG</button>
                </div>

                <!-- Edit Menu Popup -->
                <div v-if="tabletEditMenuOpen" class="tablet-menu-popup edit-menu" @click.stop>
                    <button class="tablet-menu-item" @click="tabletMenuAction('undo')" :disabled="!canUndo">
                        Undo{{ lastUndoAction ? ' ' + lastUndoAction : '' }}
                    </button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('redo')" :disabled="!canRedo">
                        Redo{{ lastRedoAction ? ' ' + lastRedoAction : '' }}
                    </button>
                    <div class="tablet-menu-divider"></div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('cut')">Cut</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('copy')">Copy</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('paste')">Paste</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('pasteInPlace')">Paste in Place</button>
                    <div class="tablet-menu-divider"></div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('selectAll')">Select All</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('deselect')">Deselect</button>
                </div>

                <!-- View Menu Popup -->
                <div v-if="tabletViewMenuOpen" class="tablet-menu-popup view-menu" @click.stop>
                    <div class="tablet-menu-subheader">Panels</div>
                    <button class="tablet-menu-item tablet-menu-toggle" @click="tabletLeftDrawerOpen = !tabletLeftDrawerOpen">
                        <span class="tablet-menu-check">{{ tabletLeftDrawerOpen ? '✓' : '' }}</span>
                        Tools Drawer
                    </button>
                    <button class="tablet-menu-item tablet-menu-toggle" @click="tabletFilterPanelOpen = !tabletFilterPanelOpen">
                        <span class="tablet-menu-check">{{ tabletFilterPanelOpen ? '✓' : '' }}</span>
                        Filters Panel
                    </button>
                    <div class="tablet-menu-divider"></div>
                    <div class="tablet-menu-subheader">Theme</div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('toggleTheme')">
                        {{ currentTheme === 'dark' ? 'Switch to Light' : 'Switch to Dark' }}
                    </button>
                    <div class="tablet-menu-divider"></div>
                    <div class="tablet-menu-subheader">Mode</div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('desktop')">Desktop Mode</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('limited')">Limited Mode</button>
                </div>

                <!-- Image Menu Popup -->
                <div v-if="tabletImageMenuOpen" class="tablet-menu-popup image-menu" @click.stop>
                    <div class="tablet-menu-subheader">Transform</div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('flipH')">Flip Horizontal</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('flipV')">Flip Vertical</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('rotate90')">Rotate 90° CW</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('rotate-90')">Rotate 90° CCW</button>
                    <div class="tablet-menu-divider"></div>
                    <div class="tablet-menu-subheader">Layers</div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('flatten')">Flatten Image</button>
                </div>

                <!-- Zoom Menu Popup -->
                <div v-if="tabletZoomMenuOpen" class="tablet-zoom-popup" @click.stop>
                    <button class="tablet-menu-item" @click="setZoomPercent(25); tabletZoomMenuOpen = false">25%</button>
                    <button class="tablet-menu-item" @click="setZoomPercent(50); tabletZoomMenuOpen = false">50%</button>
                    <button class="tablet-menu-item" @click="setZoomPercent(100); tabletZoomMenuOpen = false">100%</button>
                    <button class="tablet-menu-item" @click="setZoomPercent(200); tabletZoomMenuOpen = false">200%</button>
                    <button class="tablet-menu-item" @click="setZoomPercent(400); tabletZoomMenuOpen = false">400%</button>
                    <button class="tablet-menu-item" @click="fitToWindow(); tabletZoomMenuOpen = false">Fit to Window</button>
                </div>

                <!-- Tablet Color Picker Popup -->
                <div v-if="tabletColorPickerOpen" class="tablet-color-picker-popup" @click.stop>
                    <div class="tablet-color-picker-header">
                        <span>{{ tabletColorPickerTarget === 'fg' ? 'Foreground' : 'Background' }} Color</span>
                        <button class="tablet-color-picker-close" @click="tabletColorPickerOpen = false">&times;</button>
                    </div>
                    <div class="tablet-color-picker-body">
                        <!-- Current color preview with native picker -->
                        <div class="tablet-color-current">
                            <div class="tablet-color-preview"
                                :style="{ backgroundColor: tabletColorPickerTarget === 'fg' ? fgColor : bgColor }">
                                <input type="color"
                                    :value="tabletColorPickerTarget === 'fg' ? fgColor : bgColor"
                                    @input="setTabletPickerColor($event.target.value)"
                                    class="tablet-color-native-input">
                            </div>
                            <div class="tablet-color-hex-input">
                                <input type="text" v-model="hexInput" @keyup.enter="applyTabletHexColor" placeholder="#RRGGBB">
                                <button @click="applyTabletHexColor">Set</button>
                            </div>
                        </div>

                        <!-- Recent colors -->
                        <div class="tablet-color-section" v-if="recentColors.length > 0">
                            <div class="tablet-color-section-label">Recent</div>
                            <div class="tablet-color-grid">
                                <div v-for="(color, idx) in recentColors" :key="'recent-'+idx"
                                    class="tablet-color-cell"
                                    :style="{ backgroundColor: color }"
                                    @click="setTabletPickerColor(color)"></div>
                            </div>
                        </div>

                        <!-- Common colors (large touch-friendly swatches) -->
                        <div class="tablet-color-section">
                            <div class="tablet-color-section-label">Common</div>
                            <div class="tablet-color-grid">
                                <div v-for="(color, idx) in commonColors" :key="'common-'+idx"
                                    class="tablet-color-cell"
                                    :style="{ backgroundColor: color }"
                                    @click="setTabletPickerColor(color)"></div>
                            </div>
                        </div>

                        <!-- Extended palette -->
                        <div class="tablet-color-section">
                            <div class="tablet-color-section-label">Palette</div>
                            <div class="tablet-color-grid extended">
                                <div v-for="(color, idx) in extendedColors" :key="'ext-'+idx"
                                    class="tablet-color-cell small"
                                    :style="{ backgroundColor: color }"
                                    @click="setTabletPickerColor(color)"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </template>

            <!-- ==================== LIMITED MODE UI ==================== -->
            <template v-if="currentUIMode === 'limited'">
                <!-- Floating Tool Toolbar -->
                <div v-if="limitedSettings.showFloatingToolbar" class="limited-floating-toolbar"
                    :class="limitedSettings.floatingToolbarPosition">
                    <button v-for="toolId in limitedSettings.allowedTools" :key="toolId"
                        class="limited-tool-btn" :class="{ active: currentToolId === toolId }"
                        @click="selectTool(toolId)" :title="getToolName(toolId)">
                        <span v-html="getToolIcon(getToolIconId(toolId))"></span>
                    </button>
                </div>

                <!-- Floating Color Picker (if allowed) -->
                <div v-if="limitedSettings.showFloatingColorPicker && limitedSettings.allowColorPicker"
                    class="limited-color-picker">
                    <div class="limited-color-swatch" :style="{ backgroundColor: fgColor }"
                        @click="openLimitedColorPicker" title="Current Color"></div>
                    <div class="limited-color-grid">
                        <div v-for="color in limitedQuickColors" :key="color" class="limited-color-cell"
                            :style="{ backgroundColor: color }" @click="setForegroundColor(color)"></div>
                    </div>
                </div>

                <!-- Floating Undo Button (if allowed) -->
                <div v-if="limitedSettings.showFloatingUndo && limitedSettings.allowUndo" class="limited-action-group">
                    <button class="limited-action-btn" @click="undo" :disabled="!canUndo" title="Undo">
                        <span v-html="getToolIcon('undo')"></span>
                    </button>
                </div>

                <!-- Floating Navigator (if zoomed and allowed) -->
                <div v-if="limitedSettings.showNavigator && limitedSettings.allowZoom && zoom !== 1.0"
                    class="limited-floating-navigator">
                    <canvas ref="limitedNavigatorCanvas" class="limited-navigator-canvas"
                        @mousedown="navigatorMouseDown" @mousemove="navigatorMouseMove" @mouseup="navigatorMouseUp"
                        @touchstart.prevent="navigatorTouchStart" @touchmove.prevent="navigatorTouchMove" @touchend.prevent="navigatorMouseUp"></canvas>
                </div>
            </template>

            <!-- ==================== DESKTOP MODE UI ==================== -->
            <!-- Top toolbar (Desktop only) -->
            <div class="toolbar-container" v-if="currentUIMode === 'desktop'">
                <div class="toolbar" ref="toolbar">
                    <div class="toolbar-left">
                        <div class="toolbar-menu">
                            <button class="toolbar-menu-btn" @click="showFileMenu">File</button>
                            <button class="toolbar-menu-btn" @click="showEditMenu">Edit</button>
                            <button class="toolbar-menu-btn" @click="showViewMenu">View</button>
                            <button class="toolbar-menu-btn" @click="showFilterMenu">Filter</button>
                            <button class="toolbar-menu-btn" @click="showImageMenu">Image</button>
                        </div>
                    </div>
                    <div class="toolbar-center">
                        <span class="toolbar-title">Slopstag</span>
                    </div>
                    <div class="toolbar-right">
                        <span class="toolbar-zoom">{{ Math.round(zoom * 100) }}%</span>
                    </div>
                </div>
            </div>

            <!-- Document Tabs (Desktop only) -->
            <div class="document-tabs" v-if="currentUIMode === 'desktop' && (documentTabs.length > 1 || showDocumentTabs)">
                <div class="document-tabs-scroll">
                    <div
                        v-for="doc in documentTabs"
                        :key="doc.id"
                        class="document-tab"
                        :class="{ active: doc.isActive, modified: doc.modified }"
                        @click="activateDocument(doc.id)"
                        @mousedown.middle="closeDocument(doc.id)"
                        :title="doc.name + ' (' + doc.width + 'x' + doc.height + ')'"
                    >
                        <span class="document-tab-name">{{ doc.displayName }}</span>
                        <button class="document-tab-close" @click.stop="closeDocument(doc.id)" title="Close">&times;</button>
                    </div>
                    <button class="document-tab-new" @click="showNewDocumentDialog" title="New Document">+</button>
                </div>
            </div>

            <!-- Tool Settings Ribbon -->
            <div class="ribbon-bar" v-show="currentUIMode === 'desktop' && showRibbon">
                <div class="ribbon-tool-name">{{ currentToolName }}</div>

                <!-- Color controls in ribbon -->
                <div class="color-swatches-container">
                    <div class="color-swatches" @click="swapColors" title="Click to swap (X)">
                        <div class="color-swatch bg" :style="{ backgroundColor: bgColor }" @click.stop="openColorPicker('bg', $event)" title="Background color (click to edit)"></div>
                        <div class="color-swatch fg" :style="{ backgroundColor: fgColor }" @click.stop="openColorPicker('fg', $event)" title="Foreground color (click to edit)"></div>
                        <div class="color-swap-icon" title="Swap colors (X)">&#8633;</div>
                    </div>
                    <button class="color-reset-btn" @click="resetColors" title="Reset to black/white (D)">
                        <span class="reset-swatch black"></span>
                        <span class="reset-swatch white"></span>
                    </button>
                </div>

                <div class="ribbon-separator"></div>


                <!-- Tool properties -->
                <div class="ribbon-properties" v-if="toolProperties.length > 0" style="overflow: visible;">
                    <div class="ribbon-prop" v-for="prop in toolProperties" :key="prop.id" :style="prop.id === 'preset' ? 'position: relative; overflow: visible;' : ''">
                        <label v-if="prop.id !== 'preset'">{{ prop.name }}</label>
                        <template v-if="prop.type === 'range'">
                            <input
                                type="range"
                                :min="prop.min"
                                :max="prop.max"
                                :step="prop.step || 1"
                                :value="prop.value"
                                @input="updateToolProperty(prop.id, $event.target.value)">
                            <span class="ribbon-value">{{ prop.value }}</span>
                        </template>
                        <template v-else-if="prop.type === 'select' && prop.id === 'preset'">
                            <!-- Special brush preset dropdown with thumbnails -->
                            <div class="brush-preset-dropdown" @click.stop.prevent="toggleBrushPresetMenu($event)">
                                <img v-if="brushPresetThumbnails[prop.value]" :src="brushPresetThumbnails[prop.value]" class="dropdown-thumb">
                                <span class="dropdown-arrow">&#9662;</span>
                            </div>
                            <div class="brush-preset-menu" v-if="showBrushPresetMenu" @click.stop>
                                <div class="brush-preset-grid">
                                    <div class="brush-preset-option"
                                         v-for="opt in prop.options"
                                         :key="opt.value"
                                         :class="{ selected: opt.value === prop.value }"
                                         @click="selectBrushPreset(opt.value)"
                                         :title="opt.label">
                                        <img :src="brushPresetThumbnails[opt.value]" class="preset-thumb">
                                        <span v-if="!brushPresetThumbnails[opt.value]" class="preset-fallback">{{ opt.label }}</span>
                                    </div>
                                </div>
                            </div>
                        </template>
                        <template v-else-if="prop.type === 'select'">
                            <select :value="prop.value" @change="updateToolProperty(prop.id, $event.target.value)">
                                <option v-for="opt in prop.options" :key="opt.value !== undefined ? opt.value : opt" :value="opt.value !== undefined ? opt.value : opt">{{ opt.label || opt }}</option>
                            </select>
                        </template>
                        <template v-else-if="prop.type === 'checkbox'">
                            <input type="checkbox" :checked="prop.value" @change="updateToolProperty(prop.id, $event.target.checked)">
                        </template>
                        <template v-else-if="prop.type === 'color'">
                            <input type="color" :value="prop.value" @input="updateToolProperty(prop.id, $event.target.value)">
                        </template>
                    </div>
                </div>

            </div>

            <!-- Color Picker Popup -->
            <div v-if="colorPickerVisible" class="color-picker-popup" :style="colorPickerPosition" @click.stop>
                <div class="color-picker-header">
                    <span>{{ colorPickerTarget === 'fg' ? 'Foreground' : 'Background' }} Color</span>
                    <button @click="closeColorPicker">&times;</button>
                </div>
                <div class="color-picker-body">
                    <input type="color" class="color-picker-large" :value="colorPickerTarget === 'fg' ? fgColor : bgColor"
                        @input="setPickerColor($event.target.value)">
                    <div class="color-picker-hex">
                        <input type="text" v-model="hexInput" @keyup.enter="applyHexColor" placeholder="#RRGGBB">
                        <button @click="applyHexColor">Set</button>
                    </div>
                    <div class="color-picker-section" v-if="recentColors.length > 0">
                        <div class="section-label">Recent</div>
                        <div class="color-grid">
                            <div v-for="(color, idx) in recentColors" :key="'recent-'+idx"
                                class="color-cell" :style="{ backgroundColor: color }"
                                @click="setPickerColor(color)"></div>
                        </div>
                    </div>
                    <div class="color-picker-section">
                        <div class="section-label">Swatches</div>
                        <div class="color-grid large">
                            <div v-for="(color, idx) in commonColors" :key="'common-'+idx"
                                class="color-cell" :style="{ backgroundColor: color }"
                                @click="setPickerColor(color)"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Main editor area -->
            <div class="editor-main">
                <!-- Left tool panel (Desktop) -->
                <div class="tool-panel" v-show="currentUIMode === 'desktop' && showToolPanel">
                    <div class="tool-buttons-section">
                        <!-- Tool Groups -->
                        <div class="tool-group" v-for="group in toolGroups" :key="group.id"
                            @mouseenter="showToolFlyout(group)"
                            @mouseleave="scheduleCloseFlyout">
                            <button
                                class="tool-button"
                                :class="{ active: isToolGroupActive(group) }"
                                :title="getActiveToolInGroup(group).name + (group.shortcut ? ' (' + group.shortcut.toUpperCase() + ', Shift+' + group.shortcut.toUpperCase() + ' to cycle)' : '')"
                                @click="selectToolFromGroup(group)">
                                <span class="tool-icon" v-html="getToolIcon(getActiveToolInGroup(group).icon)"></span>
                            </button>
                            <span class="tool-group-indicator" v-if="group.tools.length > 1">&#9662;</span>
                            <!-- Tool group flyout (shown on hover) -->
                            <div class="tool-flyout" v-if="activeToolFlyout === group.id"
                                @mouseenter="cancelCloseFlyout"
                                @mouseleave="scheduleCloseFlyout">
                                <button
                                    v-for="tool in group.tools"
                                    :key="tool.id"
                                    class="flyout-tool-btn"
                                    :class="{ active: currentToolId === tool.id }"
                                    :title="tool.name"
                                    @click="selectToolFromFlyout(group, tool)">
                                    <span class="flyout-icon" v-html="getToolIcon(tool.icon)"></span>
                                    <span class="flyout-name">{{ tool.name }}</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tablet Tool Strip - hidden, using drawer instead -->
                <!-- <div class="tablet-tool-strip" v-show="currentUIMode === 'tablet'">
                    <button v-for="tool in tabletAllTools" :key="tool.id"
                        class="tablet-tool-btn"
                        :class="{ active: currentToolId === tool.id }"
                        :title="tool.name"
                        @click="selectTool(tool.id)">
                        <span v-html="getToolIcon(tool.icon)"></span>
                    </button>
                </div> -->

                <!-- Canvas container -->
                <div class="canvas-container" ref="canvasContainer"
                    :class="canvasContainerClasses">
                    <canvas
                        id="main-canvas"
                        ref="mainCanvas"
                        tabindex="0"
                        :style="{ cursor: canvasCursor }"
                        @mousedown="handleMouseDown"
                        @mousemove="handleMouseMove"
                        @mouseup="handleMouseUp"
                        @mouseleave="handleMouseLeave"
                        @mouseenter="handleMouseEnter"
                        @dblclick="handleDoubleClick"
                        @wheel.prevent="handleWheel"
                        @contextmenu.prevent
                    ></canvas>
                    <!-- Cursor overlay for large brush sizes (no browser limit) -->
                    <!-- Hidden when non-pinned drawer is open (drawer would capture cursor) -->
                    <canvas
                        v-show="showCursorOverlay && !drawerOverlapsCanvas"
                        ref="cursorOverlay"
                        class="cursor-overlay"
                        :style="{
                            left: (cursorOverlayX - cursorOverlaySize/2) + 'px',
                            top: (cursorOverlayY - cursorOverlaySize/2) + 'px',
                            width: cursorOverlaySize + 'px',
                            height: cursorOverlaySize + 'px'
                        }"
                    ></canvas>
                </div>

                <!-- Right panel -->
                <div class="right-panel" v-show="currentUIMode === 'desktop' && showRightPanel">
                    <!-- Navigator panel -->
                    <div class="navigator-panel" v-show="showNavigator">
                        <div class="panel-header" @mousedown="startPanelDrag('navigator', $event)">
                            Navigator
                            <button class="panel-collapse-btn" @click="toggleNavigator">&#9660;</button>
                        </div>
                        <div class="navigator-content">
                            <canvas ref="navigatorCanvas" class="navigator-canvas"
                                @mousedown="navigatorMouseDown"
                                @mousemove="navigatorMouseMove"
                                @mouseup="navigatorMouseUp"></canvas>
                            <div class="navigator-zoom">
                                <button class="nav-zoom-btn" @click="setZoomPercent(100)" title="Reset to 100%">1:1</button>
                                <button class="nav-zoom-btn" @click="fitToWindow" title="Fit to window">Fit</button>
                                <input type="range" min="10" max="800" :value="Math.round(zoom * 100)"
                                    @input="setZoomPercent($event.target.value)">
                                <input type="number" class="zoom-input" :value="Math.round(zoom * 100)"
                                    @change="setZoomPercent($event.target.value)" min="10" max="800">
                                <span>%</span>
                            </div>
                        </div>
                    </div>

                    <!-- Layer panel -->
                    <div class="layer-panel" v-show="showLayers">
                        <div class="panel-header">Layers</div>
                        <div class="layer-controls">
                            <select class="layer-blend-mode" v-model="activeLayerBlendMode" @change="updateLayerBlendMode">
                                <option v-for="mode in blendModes" :key="mode" :value="mode">{{ mode }}</option>
                            </select>
                            <div class="layer-opacity-row">
                                <span>Opacity:</span>
                                <input type="range" min="0" max="100" v-model.number="activeLayerOpacity" @input="updateLayerOpacity">
                                <span class="property-value">{{ activeLayerOpacity }}%</span>
                            </div>
                        </div>
                        <div class="layer-list">
                            <div
                                v-for="(layer, idx) in visibleLayers"
                                :key="layer.id"
                                class="layer-item"
                                :class="{
                                    active: layer.id === activeLayerId,
                                    'layer-group': layer.isGroup,
                                    'drag-over-top': layerDragOverIndex === idx && layerDragOverPosition === 'top',
                                    'drag-over-bottom': layerDragOverIndex === idx && layerDragOverPosition === 'bottom',
                                    'drag-over-into': layerDragOverGroup === layer.id && layerDragOverPosition === 'into',
                                    'dragging': layerDragIndex === idx
                                }"
                                :style="{ paddingLeft: (8 + layer.indentLevel * 16) + 'px' }"
                                draggable="true"
                                @click="selectLayer(layer.id)"
                                @contextmenu.prevent="showLayerContextMenu($event, layer)"
                                @dragstart="onLayerDragStart(idx, layer, $event)"
                                @dragover.prevent="onLayerDragOver(idx, layer, $event)"
                                @dragleave="onLayerDragLeave($event)"
                                @drop.prevent="onLayerDrop(idx, layer)"
                                @dragend="onLayerDragEnd">
                                <button
                                    v-if="layer.isGroup"
                                    class="layer-expand"
                                    @click.stop="toggleGroupExpanded(layer.id)"
                                    :title="layer.expanded ? 'Collapse group' : 'Expand group'">
                                    {{ layer.expanded ? '▼' : '▶' }}
                                </button>
                                <button
                                    class="layer-visibility"
                                    :class="{ visible: layer.visible }"
                                    @click.stop="toggleLayerVisibility(layer.id)"
                                    v-html="layer.visible ? '&#128065;' : '&#128064;'">
                                </button>
                                <div class="layer-thumbnails" v-if="!layer.isGroup">
                                    <canvas
                                        class="layer-thumbnail"
                                        :ref="'layerThumb_' + layer.id"
                                        width="40"
                                        height="40"
                                        :title="layer.name">
                                    </canvas>
                                    <canvas
                                        class="layer-thumbnail alpha"
                                        width="40"
                                        height="40"
                                        style="display: none;"
                                        title="Alpha channel">
                                    </canvas>
                                </div>
                                <div class="layer-group-icon" v-else title="Layer Group">
                                    &#128193;
                                </div>
                                <div class="layer-info">
                                    <span class="layer-name">{{ layer.name }}</span>
                                    <span class="layer-meta">
                                        <span class="layer-type-icon group" v-if="layer.isGroup" title="Group">G</span>
                                        <span class="layer-type-icon text" v-else-if="layer.isText" title="Text Layer">T</span>
                                        <span class="layer-type-icon" v-else-if="layer.isVector" title="Vector Layer">&#9674;</span>
                                        <span class="layer-type-icon raster" v-else title="Pixel Layer">&#9632;</span>
                                        <span v-if="layer.locked" class="layer-locked" v-html="'&#128274;'"></span>
                                    </span>
                                </div>
                                <button class="layer-menu-btn" @click.stop="showLayerContextMenuTouch($event, layer)" title="Layer menu">
                                    ⋮
                                </button>
                            </div>
                        </div>
                        <div class="layer-buttons">
                            <button @click="addLayer" title="Add layer">+</button>
                            <button @click="createGroup" title="Create group (Ctrl+G)">&#128193;</button>
                        </div>
                    </div>

                    <!-- History panel -->
                    <div class="history-panel" v-show="showHistory">
                        <div class="panel-header">History</div>
                        <div class="history-list">
                            <div
                                v-for="entry in displayHistoryList"
                                :key="entry.originalIndex"
                                class="history-item"
                                :class="{ future: entry.isFuture, undoable: !entry.isFuture }"
                                @click="jumpToHistory(entry.originalIndex)">
                                <span class="history-icon" v-html="entry.icon || '&#9679;'"></span>
                                <span class="history-name">{{ entry.name }}</span>
                            </div>
                            <div class="panel-empty" v-if="displayHistoryList.length === 0">No history</div>
                        </div>
                        <div class="history-buttons">
                            <button @click="undo" :disabled="!canUndo" :title="lastUndoAction ? 'Undo: ' + lastUndoAction : 'Undo'">
                                &#8630; Undo
                            </button>
                            <button @click="redo" :disabled="!canRedo" :title="lastRedoAction ? 'Redo: ' + lastRedoAction : 'Redo'">
                                Redo &#8631;
                            </button>
                        </div>
                    </div>

                    <!-- Image Sources panel -->
                    <div class="sources-panel" v-show="showSources">
                        <div class="panel-header">Image Sources</div>
                        <div class="sources-list">
                            <div class="source-category" v-for="(images, source) in imageSources" :key="source">
                                <div class="source-header" @click="toggleSourceCategory(source)">
                                    <span>{{ formatSourceName(source) }}</span>
                                    <span class="source-count">({{ images.length }})</span>
                                </div>
                                <div class="source-images" v-if="expandedSources[source]">
                                    <div
                                        v-for="img in images"
                                        :key="img.id"
                                        class="source-image"
                                        @click="loadSourceImage(source, img)"
                                        :title="img.name">
                                        {{ img.name }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tablet Bottom Bar (tool properties and color) -->
            <div class="tablet-bottom-bar" v-show="currentUIMode === 'tablet'">
                <div class="tablet-current-tool">
                    <span class="tablet-tool-indicator" v-html="getToolIcon(getToolIconId(currentToolId))"></span>
                    <span class="tablet-tool-name">{{ currentToolName }}</span>
                </div>
                <div class="tablet-bottom-divider"></div>
                <!-- Coordinates (always visible, shows values when pointer active) -->
                <div class="tablet-coords">
                    <span class="tablet-coords-value" :class="{ active: isPointerActive }">{{ isPointerActive ? coordsX + ', ' + coordsY : '\u00A0' }}</span>
                </div>
                <div class="tablet-bottom-divider"></div>
                <div class="tablet-prop" v-if="tabletShowSize">
                    <label>Size</label>
                    <input type="range" min="1" max="200" :value="tabletBrushSize" @input="updateTabletBrushSize($event.target.value)">
                    <span class="tablet-prop-value">{{ tabletBrushSize }}px</span>
                </div>
                <div class="tablet-prop" v-if="tabletShowOpacity">
                    <label>Opacity</label>
                    <input type="range" min="0" max="100" :value="tabletOpacity" @input="updateTabletOpacity($event.target.value)">
                    <span class="tablet-prop-value">{{ tabletOpacity }}%</span>
                </div>
                <div class="tablet-prop" v-if="tabletShowHardness">
                    <label>Hardness</label>
                    <input type="range" min="0" max="100" :value="tabletHardness" @input="updateTabletHardness($event.target.value)">
                    <span class="tablet-prop-value">{{ tabletHardness }}%</span>
                </div>
                <!-- Text tool properties -->
                <template v-if="tabletShowTextProps">
                    <div class="tablet-prop">
                        <label>Size</label>
                        <input type="range" min="8" max="120" :value="tabletFontSize" @input="updateTabletFontSize($event.target.value)">
                        <span class="tablet-prop-value">{{ tabletFontSize }}px</span>
                    </div>
                    <div class="tablet-prop">
                        <label>Font</label>
                        <select :value="tabletFontFamily" @change="updateTabletFontFamily($event.target.value)" class="tablet-select">
                            <option v-for="font in tabletFontOptions" :key="font" :value="font">{{ font }}</option>
                        </select>
                    </div>
                    <div class="tablet-prop">
                        <button class="tablet-toggle-btn" :class="{ active: tabletFontWeight === 'bold' }"
                            @click="toggleTabletFontWeight" title="Bold">B</button>
                        <button class="tablet-toggle-btn italic" :class="{ active: tabletFontStyle === 'italic' }"
                            @click="toggleTabletFontStyle" title="Italic">I</button>
                    </div>
                </template>
                <div style="flex: 1;"></div>
                <div class="tablet-color-controls">
                    <div class="tablet-color-swatches">
                        <div class="tablet-color-btn fg" :style="{ backgroundColor: fgColor }"
                            @click.stop="openTabletColorPicker('fg')" title="Foreground Color"></div>
                        <div class="tablet-color-btn bg" :style="{ backgroundColor: bgColor }"
                            @click.stop="openTabletColorPicker('bg')" title="Background Color"></div>
                    </div>
                    <button class="tablet-icon-btn" @click="swapColors" title="Swap Colors (X)">&#8633;</button>
                    <button class="tablet-icon-btn" @click="resetColors" title="Reset Colors (D)">
                        <span style="font-size: 12px;">B/W</span>
                    </button>
                </div>
            </div>

            <!-- Status bar (desktop mode only) -->
            <div class="status-bar" v-show="currentUIMode === 'desktop'">
                <span class="status-coords">{{ coordsX }}, {{ coordsY }}</span>
                <span class="status-separator">|</span>
                <span class="status-size">{{ docWidth }} x {{ docHeight }}</span>
                <span class="status-separator">|</span>
                <span class="status-tool">{{ currentToolName }}</span>
                <span v-if="toolHint" class="status-separator">|</span>
                <span v-if="toolHint" class="status-hint">{{ toolHint }}</span>
                <span v-if="statusMessage" class="status-separator">|</span>
                <span v-if="statusMessage" class="status-message">{{ statusMessage }}</span>
                <span class="status-right">
                    <span class="status-autosave" :class="[autoSaveStatus, { 'just-saved': justSaved }]">
                        <span v-if="autoSaveStatus === 'saving'">Saving...</span>
                        <span v-else-if="autoSaveStatus === 'saved'">Saved {{ formatAutoSaveTime(lastAutoSaveTime) }}</span>
                    </span>
                    <span v-if="autoSaveStatus !== 'idle'" class="status-separator">|</span>
                    <span class="status-memory" :title="'History: ' + memoryUsedMB.toFixed(1) + '/' + memoryMaxMB + ' MB'">
                        <span class="memory-bar">
                            <span class="memory-fill" :style="{ width: memoryPercent + '%' }" :class="{ warning: memoryPercent > 75 }"></span>
                        </span>
                        <span class="memory-text">{{ memoryUsedMB.toFixed(1) }}MB</span>
                    </span>
                    <span class="status-separator">|</span>
                    <span class="status-backend" :class="{ connected: backendConnected, disconnected: !backendConnected }">
                        {{ backendConnected ? 'Backend' : 'Offline' }}
                    </span>
                </span>
            </div>

            <!-- Dropdown menus -->
            <div v-if="activeMenu" class="toolbar-dropdown" :style="menuPosition" @click.stop>
                <template v-if="activeMenu === 'file'">
                    <div class="menu-item" @click="menuAction('new')">New...</div>
                    <div class="menu-item" @click="menuAction('open')">Open... (Ctrl+O)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('save')">Save (Ctrl+S)</div>
                    <div class="menu-item" @click="menuAction('saveAs')">Save As... (Ctrl+Shift+S)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">Load Sample Image</div>
                    <div class="menu-item" v-for="img in sampleImages" :key="img.id" @click="menuAction('load', img)">
                        {{ img.name }}
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('export')">Export PNG</div>
                </template>
                <template v-else-if="activeMenu === 'edit'">
                    <div class="menu-item" :class="{ disabled: !canUndo }" @click="canUndo && menuAction('undo')">
                        Undo{{ lastUndoAction ? ' ' + lastUndoAction : '' }} (Ctrl+Z)
                    </div>
                    <div class="menu-item" :class="{ disabled: !canRedo }" @click="canRedo && menuAction('redo')">
                        Redo{{ lastRedoAction ? ' ' + lastRedoAction : '' }} (Ctrl+Y)
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('cut')">Cut (Ctrl+X)</div>
                    <div class="menu-item" @click="menuAction('copy')">Copy (Ctrl+C)</div>
                    <div class="menu-item" @click="menuAction('paste')">Paste (Ctrl+V)</div>
                    <div class="menu-item" @click="menuAction('paste_in_place')">Paste in Place (Ctrl+Shift+V)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('select_all')">Select All (Ctrl+A)</div>
                    <div class="menu-item" @click="menuAction('deselect')">Deselect (Ctrl+D)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="showPreferencesDialog">Preferences...</div>
                </template>
                <template v-else-if="activeMenu === 'view'">
                    <div class="menu-header">Panels</div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showToolPanel')">
                        <span class="menu-check" v-html="showToolPanel ? '&#10003;' : ''"></span>
                        Tools
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showRibbon')">
                        <span class="menu-check" v-html="showRibbon ? '&#10003;' : ''"></span>
                        Tool Options (Ribbon)
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showRightPanel')">
                        <span class="menu-check" v-html="showRightPanel ? '&#10003;' : ''"></span>
                        Right Panel
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showNavigator')">
                        <span class="menu-check" v-html="showNavigator ? '&#10003;' : ''"></span>
                        Navigator
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showLayers')">
                        <span class="menu-check" v-html="showLayers ? '&#10003;' : ''"></span>
                        Layers
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showHistory')">
                        <span class="menu-check" v-html="showHistory ? '&#10003;' : ''"></span>
                        History
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showSources')">
                        <span class="menu-check" v-html="showSources ? '&#10003;' : ''"></span>
                        Image Sources
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">Theme</div>
                    <div class="menu-item menu-checkbox" @click="setTheme('dark')">
                        <span class="menu-check" v-html="currentTheme === 'dark' ? '&#10003;' : ''"></span>
                        Dark Theme
                    </div>
                    <div class="menu-item menu-checkbox" @click="setTheme('light')">
                        <span class="menu-check" v-html="currentTheme === 'light' ? '&#10003;' : ''"></span>
                        Light Theme
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">UI Mode</div>
                    <div class="menu-item menu-checkbox" @click="setUIMode('desktop')">
                        <span class="menu-check" v-html="currentUIMode === 'desktop' ? '&#10003;' : ''"></span>
                        Desktop Mode
                    </div>
                    <div class="menu-item menu-checkbox" @click="setUIMode('tablet')">
                        <span class="menu-check" v-html="currentUIMode === 'tablet' ? '&#10003;' : ''"></span>
                        Tablet Mode
                    </div>
                    <div class="menu-item menu-checkbox" @click="setUIMode('limited')">
                        <span class="menu-check" v-html="currentUIMode === 'limited' ? '&#10003;' : ''"></span>
                        Limited Mode
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">Zoom</div>
                    <div class="menu-item" @click="menuAction('zoom_in')">Zoom In (Ctrl++)</div>
                    <div class="menu-item" @click="menuAction('zoom_out')">Zoom Out (Ctrl+-)</div>
                    <div class="menu-item" @click="menuAction('zoom_fit')">Fit to Window</div>
                    <div class="menu-item" @click="menuAction('zoom_100')">Actual Pixels (100%)</div>
                </template>
                <template v-else-if="activeMenu === 'filter'">
                    <div class="menu-item disabled" v-if="filters.length === 0">No filters available</div>
                    <template v-for="(categoryFilters, category) in filtersByCategory" :key="category">
                        <div class="menu-submenu" @mouseenter="openSubmenu(category, $event)" @mouseleave="closeSubmenuDelayed">
                            <span>{{ formatCategory(category) }}</span>
                            <span class="submenu-arrow">▶</span>
                        </div>
                    </template>
                </template>
                <template v-else-if="activeMenu === 'image'">
                    <div class="menu-item" @click="menuAction('flatten')">Flatten Image</div>
                </template>
            </div>

            <!-- Filter submenu -->
            <div v-if="activeSubmenu" class="toolbar-dropdown filter-submenu" :style="submenuPosition"
                 @mouseenter="cancelSubmenuClose" @mouseleave="closeSubmenuDelayed" @click.stop>
                <div class="menu-item" v-for="f in filtersByCategory[activeSubmenu]" :key="f.id"
                     @click="openFilterDialog(f)">
                    {{ f.name }}
                    <span v-if="f.params && f.params.length > 0" class="has-params">...</span>
                </div>
            </div>

            <!-- Filter Dialog -->
            <div v-if="filterDialogVisible" class="filter-dialog-overlay" @click="cancelFilterDialog">
                <div class="filter-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">{{ currentFilter?.name }}</span>
                        <button class="filter-dialog-close" @click="cancelFilterDialog">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <div class="filter-description" v-if="currentFilter?.description">
                            {{ currentFilter.description }}
                        </div>
                        <div class="filter-params" v-if="currentFilter?.params?.length > 0">
                            <div class="filter-param" v-for="param in currentFilter.params" :key="param.id">
                                <label>{{ param.name }}</label>
                                <template v-if="param.type === 'range'">
                                    <div class="param-range-row">
                                        <input type="range"
                                            :min="param.min"
                                            :max="param.max"
                                            :step="param.step || 1"
                                            v-model.number="filterParams[param.id]"
                                            @input="updateFilterPreview">
                                        <input type="number"
                                            class="param-number-input"
                                            :min="param.min"
                                            :max="param.max"
                                            :step="param.step || 1"
                                            v-model.number="filterParams[param.id]"
                                            @change="updateFilterPreview">
                                    </div>
                                </template>
                                <template v-else-if="param.type === 'select'">
                                    <select v-model="filterParams[param.id]" @change="updateFilterPreview">
                                        <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                                    </select>
                                </template>
                                <template v-else-if="param.type === 'checkbox'">
                                    <input type="checkbox" v-model="filterParams[param.id]" @change="updateFilterPreview">
                                </template>
                            </div>
                        </div>
                        <div class="filter-no-params" v-else>
                            This filter has no adjustable parameters.
                        </div>
                    </div>
                    <div class="filter-dialog-footer">
                        <label class="preview-checkbox">
                            <input type="checkbox" v-model="filterPreviewEnabled" @change="toggleFilterPreview">
                            Preview
                        </label>
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="cancelFilterDialog">Cancel</button>
                            <button class="btn-apply" @click="applyFilterConfirm">Apply</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Rasterize Dialog -->
            <div v-if="showRasterizePrompt" class="filter-dialog-overlay" @click="cancelRasterize">
                <div class="filter-dialog rasterize-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">Rasterize Layer?</span>
                        <button class="filter-dialog-close" @click="cancelRasterize">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <p class="rasterize-warning">
                            This layer contains vector shapes. To use pixel tools (brush, eraser, fill),
                            the layer must be rasterized first.
                        </p>
                        <p class="rasterize-info">
                            Rasterizing converts vector shapes to pixels. This action cannot be undone
                            (shapes will no longer be individually editable).
                        </p>
                    </div>
                    <div class="filter-dialog-footer">
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="cancelRasterize">Cancel</button>
                            <button class="btn-apply" @click="confirmRasterize">Rasterize</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Preferences Dialog -->
            <div v-if="preferencesDialogVisible" class="filter-dialog-overlay" @click="closePreferencesDialog">
                <div class="filter-dialog preferences-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">Preferences</span>
                        <button class="filter-dialog-close" @click="closePreferencesDialog">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <div class="pref-section">
                            <h4>Vector Rendering</h4>
                            <div class="pref-row">
                                <label class="pref-checkbox">
                                    <input type="checkbox" v-model="prefRenderingSVG">
                                    Render vector layers via SVG
                                </label>
                                <span class="pref-hint">Uses SVG for accurate cross-platform rendering</span>
                            </div>
                            <div class="pref-row">
                                <label>Supersampling Level:</label>
                                <select v-model.number="prefSupersampleLevel">
                                    <option :value="1">1x (None)</option>
                                    <option :value="2">2x</option>
                                    <option :value="3">3x (Recommended)</option>
                                    <option :value="4">4x</option>
                                </select>
                                <span class="pref-hint">Higher values = smoother edges, slower rendering</span>
                            </div>
                            <div class="pref-row">
                                <label class="pref-checkbox">
                                    <input type="checkbox" v-model="prefAntialiasing">
                                    Enable anti-aliasing
                                </label>
                                <span class="pref-hint">Smoother edges but may differ between platforms</span>
                            </div>
                        </div>
                    </div>
                    <div class="filter-dialog-footer">
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="closePreferencesDialog">Cancel</button>
                            <button class="btn-apply" @click="savePreferences">Save</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,

    props: {
        canvasWidth: { type: Number, default: 800 },
        canvasHeight: { type: Number, default: 600 },
        apiBase: { type: String, default: '/api' },
        sessionId: { type: String, default: '' },
    },

    mixins: [
        ColorManagementMixin,
        LayerOperationsMixin,
        LayerDragDropMixin,
        HistoryManagerMixin,
        ZoomManagerMixin,
        NavigatorManagerMixin,
        ToolManagerMixin,
        ColorPickerMixin,
        CanvasEventsMixin,
        KeyboardEventsMixin,
        MenuManagerMixin,
        PopupMenuMixin,
        ViewManagerMixin,
        ClipboardManagerMixin,
    ],

    computed: {
        filtersByCategory() {
            // Group filters by category
            const categories = {};
            const categoryOrder = ['color', 'blur', 'edge', 'threshold', 'morphology', 'artistic', 'noise', 'sharpen', 'uncategorized'];

            for (const filter of this.filters) {
                const cat = filter.category || 'uncategorized';
                if (!categories[cat]) {
                    categories[cat] = [];
                }
                categories[cat].push(filter);
            }

            // Sort by category order
            const sorted = {};
            for (const cat of categoryOrder) {
                if (categories[cat]) {
                    sorted[cat] = categories[cat];
                }
            }
            // Add any remaining categories
            for (const cat in categories) {
                if (!sorted[cat]) {
                    sorted[cat] = categories[cat];
                }
            }
            return sorted;
        },
        visibleLayers() {
            // Build hierarchical layer list: children appear immediately after their parent
            // Also filter out children of collapsed groups
            // Note: Array is already in visual order (index 0 = top)

            const collapsedGroups = new Set();
            for (const layer of this.layers) {
                if (layer.isGroup && !layer.expanded) {
                    collapsedGroups.add(layer.id);
                }
            }

            // Check if layer is inside a collapsed group (recursively)
            const isInCollapsedGroup = (layer) => {
                let parentId = layer.parentId;
                while (parentId) {
                    if (collapsedGroups.has(parentId)) return true;
                    const parent = this.layers.find(l => l.id === parentId);
                    parentId = parent?.parentId;
                }
                return false;
            };

            // Build hierarchical order: recursively add layer and its children
            const result = [];
            const addLayerWithChildren = (layer) => {
                if (isInCollapsedGroup(layer)) return;
                result.push(layer);
                // If this is a group, add its children immediately after
                if (layer.isGroup) {
                    // Find direct children of this group (already in visual order)
                    const children = this.layers.filter(l => l.parentId === layer.id);
                    for (const child of children) {
                        addLayerWithChildren(child);
                    }
                }
            };

            // Start with root-level layers (parentId is null/undefined)
            const rootLayers = this.layers.filter(l => !l.parentId);
            for (const layer of rootLayers) {
                addLayerWithChildren(layer);
            }

            return result;
        },
        displayHistoryList() {
            // Filter out "Current State" and reverse so newest is at top
            // Keep original index for jump-to functionality
            return this.historyList
                .map((entry, idx) => ({ ...entry, originalIndex: idx }))
                .filter(entry => !entry.isCurrent)
                .reverse();
        },
        hasSelection() {
            // Check if there's an active selection
            const selection = this.getSelection();
            return selection && selection.width > 0 && selection.height > 0;
        },
        canvasContainerClasses() {
            // Classes for canvas container (no longer used for pinned drawers)
            return {};
        },
        drawerOverlapsCanvas() {
            // True when a floating panel overlaps the canvas area
            // Dock panels on edges (left tools, right nav/layers/history) don't overlap
            if (this.currentUIMode !== 'tablet') return false;
            // Only the filter panel floats over the canvas
            return this.tabletFilterPanelOpen;
        },
        filterCategories() {
            // Get unique filter categories in order
            const categoryOrder = ['blur', 'color', 'edge', 'sharpen', 'noise', 'artistic', 'threshold', 'morphology', 'uncategorized'];
            const available = new Set(this.filters.map(f => f.category || 'uncategorized'));
            return categoryOrder.filter(cat => available.has(cat));
        },
        filtersInCurrentTab() {
            // Get filters for the currently selected tab
            return this.filters.filter(f => (f.category || 'uncategorized') === this.tabletFilterTab);
        },
        hasOpenUnpinnedPopup() {
            // Check if any popup or panel is open that needs overlay
            if (this.currentUIMode !== 'tablet') return false;
            return this.tabletFilterPanelOpen ||
                   this.tabletFileMenuOpen ||
                   this.tabletEditMenuOpen ||
                   this.tabletViewMenuOpen ||
                   this.tabletImageMenuOpen ||
                   this.tabletZoomMenuOpen;
        },
        // Track which side panel has focus (for closing unpinned on blur)
        activeSidePanel() {
            return this._activeSidePanel || null;
        },
    },

    data() {
        // Mode is set by inline script (URL param or defaults to desktop)
        let initialMode = window.__stagforgeUrlMode || 'desktop';
        let initialTheme = 'dark';

        // Theme from localStorage
        try {
            const savedTheme = localStorage.getItem('stagforge-theme');
            if (savedTheme) initialTheme = savedTheme;
        } catch (e) {
            // Ignore errors
        }

        return {
            // Theme and UI mode
            currentTheme: initialTheme,
            currentUIMode: initialMode,

            // Tablet mode state
            tabletLeftDrawerOpen: false,     // Tools panel open

            // Independent floating panels (Navigator, Layers, History)
            tabletNavPanelOpen: false,
            tabletLayersPanelOpen: false,
            tabletHistoryPanelOpen: false,
            _activeSidePanel: null,          // Currently focused side panel (for blur handling)

            // Individual menu popups
            tabletFileMenuOpen: false,
            tabletEditMenuOpen: false,
            tabletViewMenuOpen: false,
            tabletFilterPanelOpen: false,    // Filters panel (special tabbed panel)
            tabletFilterTab: 'blur',         // Active filter category tab
            tabletImageMenuOpen: false,
            tabletZoomMenuOpen: false,       // Zoom menu popup open
            tabletColorPickerOpen: false,    // Tablet color picker popup
            tabletColorPickerTarget: 'fg',   // 'fg' or 'bg'

            // Filter preview system
            filterPreviews: {},              // Cache: { filterId: base64ImageData }
            filterPreviewsLoading: {},       // { filterId: boolean }
            filterSampleImageLoaded: false,  // Has the sample image been loaded
            tabletBrushSize: 20,             // Current brush/eraser size for tablet UI
            tabletOpacity: 100,              // Current opacity for tablet UI
            tabletHardness: 100,             // Current hardness for tablet UI
            tabletShowSize: true,            // Whether to show size slider
            tabletShowOpacity: true,         // Whether to show opacity slider
            tabletShowHardness: false,       // Whether to show hardness slider

            // Text tool properties for tablet
            tabletShowTextProps: false,      // Whether to show text tool properties
            tabletFontSize: 24,              // Current font size
            tabletFontFamily: 'Arial',       // Current font family
            tabletFontWeight: 'normal',      // Current font weight
            tabletFontStyle: 'normal',       // Current font style
            tabletFontOptions: ['Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Courier New', 'Verdana', 'Impact'],

            // Tool drag-to-reorder state
            toolDragIndex: null,             // Index of tool being dragged
            toolDragOverIndex: null,         // Index of tool being dragged over
            tabletAllTools: [                // All tools available in tablet mode
                { id: 'selection', name: 'Select', icon: 'selection' },
                { id: 'lasso', name: 'Lasso', icon: 'lasso' },
                { id: 'magicwand', name: 'Magic Wand', icon: 'magicwand' },
                { id: 'move', name: 'Move', icon: 'move' },
                { id: 'brush', name: 'Brush', icon: 'brush' },
                { id: 'pencil', name: 'Pencil', icon: 'pencil' },
                { id: 'spray', name: 'Spray', icon: 'spray' },
                { id: 'eraser', name: 'Eraser', icon: 'eraser' },
                { id: 'fill', name: 'Fill', icon: 'fill' },
                { id: 'gradient', name: 'Gradient', icon: 'gradient' },
                { id: 'eyedropper', name: 'Eyedropper', icon: 'eyedropper' },
                { id: 'line', name: 'Line', icon: 'line' },
                { id: 'rect', name: 'Rectangle', icon: 'rect' },
                { id: 'circle', name: 'Ellipse', icon: 'circle' },
                { id: 'polygon', name: 'Polygon', icon: 'polygon' },
                { id: 'text', name: 'Text', icon: 'text' },
                { id: 'crop', name: 'Crop', icon: 'crop' },
                { id: 'clone', name: 'Clone', icon: 'clone' },
                { id: 'smudge', name: 'Smudge', icon: 'smudge' },
                { id: 'blur', name: 'Blur', icon: 'blur' },
            ],

            // Limited mode state and settings
            limitedSettings: {
                allowedTools: ['brush', 'eraser'],
                allowColorPicker: true,
                allowUndo: true,
                allowZoom: false,
                showFloatingToolbar: true,
                showFloatingColorPicker: true,
                showFloatingUndo: true,
                showNavigator: false,
                floatingToolbarPosition: 'top',
                enableKeyboardShortcuts: false,
            },
            limitedQuickColors: [
                '#000000', '#FFFFFF', '#FF0000', '#00FF00',
                '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
                '#FF8000', '#8000FF', '#00FF80', '#FF0080'
            ],

            // Document state
            docWidth: 800,
            docHeight: 600,
            zoom: 1.0,

            // Canvas cursor
            canvasCursor: 'crosshair',
            // Overlay cursor for brush/eraser/spray (unified, no size limit)
            showCursorOverlay: false,
            cursorOverlayX: 0,
            cursorOverlayY: 0,
            cursorOverlaySize: 0,
            mouseOverCanvas: false,  // Track if mouse is over canvas

            // Colors
            fgColor: '#000000',
            bgColor: '#FFFFFF',
            // Professional color palette
            colorPalette: [
                // Row 1: Grayscale
                '#000000', '#1a1a1a', '#333333', '#4d4d4d', '#666666', '#808080',
                '#999999', '#b3b3b3', '#cccccc', '#e6e6e6', '#f2f2f2', '#ffffff',
                // Row 2: Reds
                '#330000', '#660000', '#990000', '#cc0000', '#ff0000', '#ff3333',
                '#ff6666', '#ff9999', '#ffcccc', '#ff6600', '#ff9933', '#ffcc66',
                // Row 3: Oranges/Yellows
                '#331a00', '#663300', '#994d00', '#cc6600', '#ff8000', '#ffb366',
                '#332600', '#665200', '#997a00', '#cca300', '#ffcc00', '#ffe066',
                // Row 4: Greens
                '#003300', '#006600', '#009900', '#00cc00', '#00ff00', '#33ff33',
                '#66ff66', '#99ff99', '#ccffcc', '#003319', '#006633', '#00994d',
                // Row 5: Cyans
                '#003333', '#006666', '#009999', '#00cccc', '#00ffff', '#33ffff',
                '#66ffff', '#99ffff', '#ccffff', '#001a33', '#003366', '#004d99',
                // Row 6: Blues
                '#000033', '#000066', '#000099', '#0000cc', '#0000ff', '#3333ff',
                '#6666ff', '#9999ff', '#ccccff', '#19004d', '#330099', '#4d00cc',
                // Row 7: Purples/Magentas
                '#330033', '#660066', '#990099', '#cc00cc', '#ff00ff', '#ff33ff',
                '#ff66ff', '#ff99ff', '#ffccff', '#4d0033', '#990066', '#cc0099',
                // Row 8: Skin tones + Browns
                '#ffd5c8', '#f5c4b8', '#e8b298', '#d4a076', '#c68642', '#8d5524',
                '#663d14', '#4a2c0a', '#331f06', '#ffe4c4', '#deb887', '#d2691e',
            ],
            commonColors: [
                '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF', '#FFFF00',
                '#FF00FF', '#00FFFF', '#FF8000', '#8000FF', '#00FF80', '#FF0080',
            ],
            recentColors: [],
            showFullPicker: false,
            hexInput: '#000000',

            // View options
            showToolPanel: true,
            showRibbon: true,
            showRightPanel: true,
            showNavigator: true,
            showLayers: true,
            showHistory: true,
            showSources: false,

            // Color picker popup
            colorPickerVisible: false,
            colorPickerTarget: 'fg',  // 'fg' or 'bg'
            colorPickerPosition: { top: '60px', left: '100px' },

            // Tools
            tools: [],
            toolGroups: [],
            activeGroupTools: {},  // groupId -> selected toolId
            currentToolId: 'brush',
            currentToolName: 'Brush',
            toolHint: null,
            toolProperties: [],
            activeToolFlyout: null,
            toolFlyoutTimeout: null,
            flyoutCloseTimeout: null,

            // Brush presets
            brushPresetThumbnails: {},
            brushPresetThumbnailsGenerated: false,
            showBrushPresetMenu: false,
            currentBrushPreset: 'hard-round-md',
            currentBrushPresetName: 'Hard Round Medium',

            // History
            historyList: [],
            historyIndex: -1,
            canUndo: false,
            canRedo: false,
            lastUndoAction: '',
            lastRedoAction: '',

            // Image sources
            imageSources: {},
            expandedSources: {},

            // Navigator
            navigatorDragging: false,
            navigatorUpdatePending: false,
            navigatorUpdateInterval: null,
            lastNavigatorUpdate: 0,

            // Documents (multi-document support)
            documentTabs: [],
            showDocumentTabs: true,
            documentManager: null,

            // Layers
            layers: [],
            activeLayerId: null,
            activeLayerOpacity: 100,
            activeLayerBlendMode: 'normal',
            blendModes: ['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten', 'color-dodge', 'color-burn', 'hard-light', 'soft-light', 'difference', 'exclusion'],

            // Layer drag-and-drop
            layerDragIndex: null,
            layerDragOverIndex: null,
            layerDragOverPosition: null,  // 'top', 'bottom', or 'into' (for groups)
            layerDragOverGroup: null,  // Group ID when dragging into a group

            // Status
            coordsX: 0,
            coordsY: 0,
            isPointerActive: false,  // True when pointer (mouse/touch) is over canvas
            statusMessage: 'Ready',
            backendConnected: false,
            memoryUsedMB: 0,
            memoryMaxMB: 256,
            memoryPercent: 0,

            // Auto-save status
            autoSaveStatus: 'idle',  // 'idle' | 'saving' | 'saved'
            lastAutoSaveTime: null,  // Timestamp of last save
            justSaved: false,  // True briefly after save for flash animation

            // Menu
            activeMenu: null,
            menuPosition: { top: '0px', left: '0px' },
            activeSubmenu: null,
            submenuPosition: { top: '0px', left: '0px' },
            submenuCloseTimeout: null,

            // Filter dialog state
            filterDialogVisible: false,
            currentFilter: null,
            filterParams: {},
            filterPreviewEnabled: true,
            filterPreviewState: null,
            filterPreviewDebounce: null,

            // Rasterize dialog state
            showRasterizePrompt: false,
            rasterizeLayerId: null,
            rasterizeCallback: null,

            // Preferences dialog state
            preferencesDialogVisible: false,
            prefRenderingSVG: true,
            prefSupersampleLevel: 3,
            prefAntialiasing: false,

            // Backend data
            filters: [],
            sampleImages: [],

            // Internal state
            isPanning: false,
            lastPanX: 0,
            lastPanY: 0,
        };
    },

    watch: {
        zoom() {
            // Update cursor overlay when zoom changes (for size-based tools)
            this.updateBrushCursor();
        }
    },

    mounted() {
        this.docWidth = this.canvasWidth;
        this.docHeight = this.canvasHeight;

        // Load saved tool order for tablet mode
        this.loadToolOrder();

        // Load saved panel visibility state
        this.loadPanelState();

        this.initEditor();

        // Close menu on outside click
        document.addEventListener('click', this.closeMenu);
        document.addEventListener('click', this.handleGlobalClick);
        window.addEventListener('keydown', this.handleKeyDown);
        window.addEventListener('keyup', this.handleKeyUp);
        window.addEventListener('resize', this.handleResize);
    },

    beforeUnmount() {
        document.removeEventListener('click', this.closeMenu);
        document.removeEventListener('click', this.handleGlobalClick);
        window.removeEventListener('keydown', this.handleKeyDown);
        window.removeEventListener('keyup', this.handleKeyUp);
        window.removeEventListener('resize', this.handleResize);

        const state = this.getState();
        if (state?.renderer) {
            state.renderer.stopRenderLoop();
        }
    },

    methods: {
        getState() {
            return editorState.get(this);
        },

        /**
         * Format auto-save timestamp for display.
         * @param {number} timestamp - Timestamp in milliseconds
         * @returns {string} - Formatted time string
         */
        formatAutoSaveTime(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },

        async initEditor() {
            // Import core modules dynamically
            const [
                { EventBus },
                { LayerStack },
                { Renderer },
                { History },
                { Clipboard },
                { ToolManager },
                { themeManager },
                { UIConfig },
                { BrushTool },
                { PencilTool },
                { CloneStampTool },
                { SmudgeTool },
                { BlurTool },
                { SharpenTool },
                { DodgeTool },
                { BurnTool },
                { SpongeTool },
                { EraserTool },
                { ShapeTool },
                { FillTool },
                { EyedropperTool },
                { MoveTool },
                { LineTool },
                { RectTool },
                { CircleTool },
                { SelectionTool },
                { SprayTool },
                { TextTool },
                { GradientTool },
                { PolygonTool },
                { MagicWandTool },
                { LassoTool },
                { CropTool },
                { HandTool },
                { VectorShapeEditTool },
                { PenTool },
                { BackendConnector },
                { PluginManager },
                { DocumentManager },
                { AutoSave },
                { TextLayer },
                { VectorLayer },
                { createShape },
                LayerEffectsModule,
                { FileManager },
            ] = await Promise.all([
                import('/static/js/utils/EventBus.js'),
                import('/static/js/core/LayerStack.js'),
                import('/static/js/core/Renderer.js'),
                import('/static/js/core/History.js'),
                import('/static/js/core/Clipboard.js'),
                import('/static/js/tools/ToolManager.js'),
                import('/static/js/config/ThemeManager.js'),
                import('/static/js/config/UIConfig.js'),
                import('/static/js/tools/BrushTool.js'),
                import('/static/js/tools/PencilTool.js'),
                import('/static/js/tools/CloneStampTool.js'),
                import('/static/js/tools/SmudgeTool.js'),
                import('/static/js/tools/BlurTool.js'),
                import('/static/js/tools/SharpenTool.js'),
                import('/static/js/tools/DodgeTool.js'),
                import('/static/js/tools/BurnTool.js'),
                import('/static/js/tools/SpongeTool.js'),
                import('/static/js/tools/EraserTool.js'),
                import('/static/js/tools/ShapeTool.js'),
                import('/static/js/tools/FillTool.js'),
                import('/static/js/tools/EyedropperTool.js'),
                import('/static/js/tools/MoveTool.js'),
                import('/static/js/tools/LineTool.js'),
                import('/static/js/tools/RectTool.js'),
                import('/static/js/tools/CircleTool.js'),
                import('/static/js/tools/SelectionTool.js'),
                import('/static/js/tools/SprayTool.js'),
                import('/static/js/tools/TextTool.js'),
                import('/static/js/tools/GradientTool.js'),
                import('/static/js/tools/PolygonTool.js'),
                import('/static/js/tools/MagicWandTool.js'),
                import('/static/js/tools/LassoTool.js'),
                import('/static/js/tools/CropTool.js'),
                import('/static/js/tools/HandTool.js'),
                import('/static/js/tools/VectorShapeEditTool.js'),
                import('/static/js/tools/PenTool.js'),
                import('/static/js/plugins/BackendConnector.js'),
                import('/static/js/plugins/PluginManager.js'),
                import('/static/js/core/DocumentManager.js'),
                import('/static/js/core/AutoSave.js'),
                import('/static/js/core/TextLayer.js'),
                import('/static/js/core/VectorLayer.js'),
                import('/static/js/core/VectorShape.js'),
                import('/static/js/core/LayerEffects.js'),
                import('/static/js/core/FileManager.js'),
            ]);

            // Expose layer classes and shape factory to window for testing
            window.TextLayer = TextLayer;
            window.VectorLayer = VectorLayer;
            window.createVectorShape = createShape;
            window.LayerEffects = LayerEffectsModule;

            // Set up canvas
            const canvas = this.$refs.mainCanvas;
            const container = this.$refs.canvasContainer;
            if (!canvas || !container) {
                console.error('Canvas refs not available, retrying...');
                await new Promise(r => setTimeout(r, 100));
                return this.initEditor();  // Retry
            }
            // Store logical display dimensions
            const displayWidth = container.clientWidth || 800;
            const displayHeight = container.clientHeight || 600;

            // Create app-like context object
            const eventBus = new EventBus();
            const app = {
                eventBus,
                canvasWidth: this.docWidth,
                canvasHeight: this.docHeight,
                foregroundColor: this.fgColor,
                backgroundColor: this.bgColor,
                displayCanvas: canvas,
                layerStack: null,
                renderer: null,
                history: null,
                clipboard: null,
                toolManager: null,
                pluginManager: null,
                documentManager: null,
                fileManager: null,
            };

            // Initialize document manager first (but don't create documents yet)
            app.documentManager = new DocumentManager(app);

            // Create initial empty layer stack (will be replaced when document is created)
            app.layerStack = new LayerStack(this.docWidth, this.docHeight, eventBus);
            app.renderer = new Renderer(canvas, app.layerStack);
            app.renderer.resizeDisplay(displayWidth, displayHeight);  // Set up HiDPI canvas
            app.renderer.setApp(app);  // Enable tool overlay rendering
            app.renderer.setOnRender(() => this.throttledNavigatorUpdate());  // Update navigator on render
            app.history = new History(app);
            app.clipboard = new Clipboard(app);
            app.toolManager = new ToolManager(app);
            app.pluginManager = new PluginManager(app);
            app.fileManager = new FileManager(app);

            // Add utility methods to app
            app.showRasterizeDialog = (layer, callback) => {
                // Store callback reference for the dialog
                this.rasterizeLayerId = layer.id;
                this.rasterizeCallback = callback;
                this.showRasterizePrompt = true;
            };

            // Set the width/height so tools can access them
            app.width = this.docWidth;
            app.height = this.docHeight;

            // Register tools
            app.toolManager.register(SelectionTool);
            app.toolManager.register(LassoTool);
            app.toolManager.register(MagicWandTool);
            app.toolManager.register(MoveTool);
            app.toolManager.register(BrushTool);
            app.toolManager.register(PencilTool);
            app.toolManager.register(CloneStampTool);
            app.toolManager.register(SmudgeTool);
            app.toolManager.register(BlurTool);
            app.toolManager.register(SharpenTool);
            app.toolManager.register(DodgeTool);
            app.toolManager.register(BurnTool);
            app.toolManager.register(SpongeTool);
            app.toolManager.register(SprayTool);
            app.toolManager.register(EraserTool);
            app.toolManager.register(LineTool);
            app.toolManager.register(RectTool);
            app.toolManager.register(CircleTool);
            app.toolManager.register(PolygonTool);
            app.toolManager.register(ShapeTool);
            app.toolManager.register(FillTool);
            app.toolManager.register(GradientTool);
            app.toolManager.register(TextTool);
            app.toolManager.register(EyedropperTool);
            app.toolManager.register(CropTool);
            app.toolManager.register(HandTool);
            app.toolManager.register(VectorShapeEditTool);
            app.toolManager.register(PenTool);

            // Store state
            editorState.set(this, app);

            // Expose for testing (accessible via window.__stagforge_app__)
            window.__stagforge_app__ = app;
            window.sessionId = this.sessionId;  // Expose for testing

            // Initialize theme and UI configuration
            themeManager.init();
            UIConfig.init();
            this.currentTheme = themeManager.getTheme();
            // Keep URL-specified mode (set in data()), don't override from localStorage
            // this.currentUIMode is already set from window.__stagforgeUrlMode in data()

            // Store references for easy access
            app.themeManager = themeManager;
            app.uiConfig = UIConfig;

            // Listen for theme changes
            themeManager.addListener((newTheme) => {
                this.currentTheme = newTheme;
            });

            // Listen for mode changes
            UIConfig.addListener((key, newValue) => {
                if (key === 'mode') {
                    this.currentUIMode = newValue;
                    this.onModeChange(newValue);
                }
            });

            // Initialize auto-save and try to restore documents
            app.autoSave = new AutoSave(app, { interval: 5000 });  // 5 second interval
            await app.autoSave.initialize();

            // Try to restore documents from previous session
            const restored = await app.autoSave.restoreDocuments();

            if (!restored) {
                // No documents restored, create initial document through DocumentManager
                app.documentManager.createDocument({
                    width: this.docWidth,
                    height: this.docHeight,
                    name: 'Untitled',
                    activate: true
                });
            }

            // Update document tabs
            this.updateDocumentTabs();

            // Connect to backend
            await app.pluginManager.initialize();

            // Update UI from state
            this.updateToolList();
            this.updateLayerList();
            app.toolManager.select('brush');
            this.currentToolId = 'brush';
            this.updateToolProperties();

            // Wait for layout to complete before fitting to viewport
            this.$nextTick(() => {
                // Use our improved fitToWindow method which properly fills the available space
                this.fitToWindow();
            });

            // Generate brush preset thumbnails on initial load (brush is default tool)
            this.generateBrushPresetThumbnails();

            // Update cursor for initial tool
            this.updateBrushCursor();

            // Set up event listeners
            eventBus.on('tool:changed', (data) => {
                this.currentToolId = data.tool?.constructor.id || '';
                this.currentToolName = data.tool?.constructor.name || '';
                this.updateToolProperties();
                this.updateToolHint();
                // Only show layer bounds in move tool
                app.renderer.showLayerBounds = (this.currentToolId === 'move');
                app.renderer.requestRender();

                // Generate brush preset thumbnails when brush tool is selected
                if (this.currentToolId === 'brush' && !this.brushPresetThumbnailsGenerated) {
                    this.generateBrushPresetThumbnails();
                }

                // Update cursor for the new tool
                this.updateBrushCursor();

                // Sync tablet UI with tool properties
                if (this.currentUIMode === 'tablet') {
                    this.syncTabletToolProperties();
                }
            });

            eventBus.on('layer:added', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layer:removed', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layer:selected', (data) => {
                this.activeLayerId = data.layer?.id;
                this.updateLayerControls();
                this.emitStateUpdate();
            });
            eventBus.on('layer:updated', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layer:duplicated', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layer:merged', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layer:flattened', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layer:moved', () => {
                this.updateLayerList();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });
            eventBus.on('layers:restored', () => {
                this.updateLayerList();
                this.updateNavigator();
                this.emitStateUpdate();
            });
            eventBus.on('layers:changed', () => {
                this.updateLayerList();
                this.updateNavigator();
                app.renderer.requestRender();
                this.emitStateUpdate();
            });

            // Document events - sync state with Python
            eventBus.on('documents:changed', () => {
                this.updateDocumentTabs();
                this.emitStateUpdate();
            });
            eventBus.on('document:created', () => {
                this.updateDocumentTabs();
                this.emitStateUpdate();
            });
            eventBus.on('document:activated', () => {
                this.updateDocumentTabs();
                this.updateLayerList();
                this.emitStateUpdate();
            });
            eventBus.on('document:closed', () => {
                this.updateDocumentTabs();
                this.emitStateUpdate();
            });

            // Update history state when history changes
            eventBus.on('history:changed', () => {
                this.updateHistoryState();
                this.emitStateUpdate();
            });

            // Update navigator when viewport changes
            eventBus.on('viewport:changed', () => {
                this.updateNavigator();
            });

            // Initialize navigator after a short delay to ensure canvas is ready
            setTimeout(() => {
                this.updateNavigator();
            }, 500);

            eventBus.on('color:foreground-changed', (data) => {
                this.fgColor = data.color;
            });
            eventBus.on('color:background-changed', (data) => {
                this.bgColor = data.color;
            });

            eventBus.on('backend:connected', () => {
                this.backendConnected = true;
                this.loadBackendData();
            });
            eventBus.on('backend:disconnected', () => {
                this.backendConnected = false;
            });

            // Auto-save status events
            eventBus.on('autosave:saving', () => {
                this.autoSaveStatus = 'saving';
            });
            eventBus.on('autosave:saved', (data) => {
                this.autoSaveStatus = 'saved';
                this.lastAutoSaveTime = data.timestamp;
                // Trigger flash animation
                this.justSaved = true;
                setTimeout(() => {
                    this.justSaved = false;
                }, 600);
            });

            // Document management events
            eventBus.on('documents:changed', () => {
                this.updateDocumentTabs();
            });
            eventBus.on('document:modified', () => {
                // Update tabs to show modified indicator
                this.updateDocumentTabs();
            });
            eventBus.on('document:activated', (data) => {
                this.updateDocumentTabs();
                this.updateLayerList();
                this.updateHistoryState();
                this.updateNavigator();
                this.zoom = app.renderer.zoom;
            });
            eventBus.on('document:close-requested', (data) => {
                this.showCloseDocumentDialog(data.document, data.callback);
            });
            eventBus.on('documents:restored', (data) => {
                console.log(`[Editor] Restored ${data.count} document(s) from auto-save`);
                this.updateDocumentTabs();
                this.updateLayerList();
                this.updateHistoryState();
                this.updateNavigator();
                this.zoom = app.renderer.zoom;
                this.statusMessage = `Restored ${data.count} document(s)`;
            });

            // Also try to load backend data directly after initialization
            // (in case the event was missed)
            setTimeout(() => {
                if (!this.backendConnected) {
                    this.loadBackendData().then(() => {
                        if (this.filters.length > 0) {
                            this.backendConnected = true;
                        }
                    });
                }
            }, 1000);

            this.statusMessage = 'Ready';
            this.updateHistoryState();

            // Emit initial state to Python
            this.emitStateUpdate();
        },

        async loadBackendData() {
            const app = this.getState();
            if (!app?.pluginManager) return;

            try {
                const filtersResponse = await fetch(`${this.apiBase}/filters`);
                if (filtersResponse.ok) {
                    const data = await filtersResponse.json();
                    this.filters = data.filters || [];
                }

                const sourcesResponse = await fetch(`${this.apiBase}/images/sources`);
                if (sourcesResponse.ok) {
                    const sourcesData = await sourcesResponse.json();
                    const sources = sourcesData.sources || [];
                    // Load images from all sources
                    for (const source of sources) {
                        const imagesResponse = await fetch(`${this.apiBase}/images/${source.id}`);
                        if (imagesResponse.ok) {
                            const imagesData = await imagesResponse.json();
                            const images = imagesData.images || [];
                            // Store for File menu (first source only)
                            if (!this.sampleImages.length) {
                                this.sampleImages = images.map(img => ({
                                    id: img.id,
                                    name: img.name,
                                    source: source.id,
                                }));
                            }
                            // Store for Sources panel
                            this.imageSources[source.id] = images.map(img => ({
                                id: img.id,
                                name: img.name,
                            }));
                            // Expand first source by default
                            if (!Object.keys(this.expandedSources).length) {
                                this.expandedSources[source.id] = true;
                            }
                        }
                    }
                }
            } catch (e) {
                console.error('Failed to load backend data:', e);
            }
        },

        // Tool methods moved to ToolManagerMixin
        // History methods moved to HistoryManagerMixin

        // Image sources methods
        async loadImageSources() {
            try {
                const response = await fetch(`${this.apiBase}/images/sources`);
                if (response.ok) {
                    const sources = await response.json();
                    // Load images for each source
                    for (const source of sources) {
                        const imgResponse = await fetch(`${this.apiBase}/images/${source.id}/list`);
                        if (imgResponse.ok) {
                            const images = await imgResponse.json();
                            this.imageSources[source.id] = images;
                            this.expandedSources[source.id] = source.id === 'skimage'; // Expand skimage by default
                        }
                    }
                }
            } catch (e) {
                console.warn('Failed to load image sources:', e);
            }
        },

        toggleSourceCategory(source) {
            this.expandedSources[source] = !this.expandedSources[source];
        },

        formatSourceName(source) {
            const names = {
                'skimage': 'scikit-image Samples',
                'wikimedia': 'Wikimedia Commons',
                'unsplash': 'Unsplash',
            };
            return names[source] || source;
        },

        async loadSourceImage(source, img) {
            try {
                const response = await fetch(`${this.apiBase}/images/${source}/${img.id}`);
                if (response.ok) {
                    const metadata = await response.json();
                    // Load as new layer
                    await this.loadSampleImage({ id: img.id, source, ...metadata });
                    this.statusMessage = `Loaded: ${img.name}`;
                }
            } catch (e) {
                console.error('Failed to load image:', e);
                this.statusMessage = 'Failed to load image';
            }
        },

        // View menu methods
        showViewMenu(e) {
            this.showMenu('view', e);
        },

        // View and theme methods moved to ViewManagerMixin

        setUIMode(mode) {
            const app = this.getState();
            if (app?.uiConfig) {
                app.uiConfig.setMode(mode);
            }
            this.closeMenu();
        },

        onModeChange(mode) {
            // Handle mode-specific UI changes
            console.log('UI mode changed to:', mode);

            // Close any open panels/drawers
            this.tabletPanelOpen = null;
            this.tabletDrawerOpen = null;

            // Load mode-specific settings from UIConfig
            const app = this.getState();
            if (mode === 'limited' && app?.uiConfig) {
                const limitedConfig = app.uiConfig.getModeSettings('limited');
                this.limitedSettings = { ...this.limitedSettings, ...limitedConfig };

                // Ensure we only show allowed tools - switch to first allowed tool if current is not allowed
                if (!this.limitedSettings.allowedTools.includes(this.currentToolId)) {
                    const firstTool = this.limitedSettings.allowedTools[0] || 'brush';
                    this.selectTool(firstTool);
                }
            }

            // Update visibility based on mode
            if (mode === 'desktop') {
                this.showToolPanel = true;
                this.showRibbon = true;
                this.showRightPanel = true;
            } else if (mode === 'tablet') {
                // Tablet mode - CSS handles visibility via data-mode attribute
                this.showToolPanel = false;  // CSS hides desktop panel
                this.showRibbon = false;     // CSS hides ribbon
                this.showRightPanel = false; // CSS hides right panel
            } else if (mode === 'limited') {
                // Limited mode - minimal UI, CSS handles most of it
                this.showToolPanel = false;
                this.showRibbon = false;
                this.showRightPanel = false;
            }

            // Refit canvas to new available space
            this.$nextTick(() => {
                this.fitToWindow();
            });
        },

        // Tablet mode methods

        closeAllPanels() {
            // Close all side panels and drawers
            this.tabletLeftDrawerOpen = false;
            this.tabletNavPanelOpen = false;
            this.tabletLayersPanelOpen = false;
            this.tabletHistoryPanelOpen = false;
            this.tabletFilterPanelOpen = false;
        },

        toggleTabletPopup(which) {
            // Close all other popups first (including color picker)
            const popups = ['file', 'edit', 'view', 'image', 'zoom'];
            for (const p of popups) {
                if (p !== which) {
                    this[`tablet${p.charAt(0).toUpperCase() + p.slice(1)}MenuOpen`] = false;
                }
            }
            this.tabletColorPickerOpen = false;

            // Toggle the requested popup
            switch (which) {
                case 'file':
                    this.tabletFileMenuOpen = !this.tabletFileMenuOpen;
                    break;
                case 'edit':
                    this.tabletEditMenuOpen = !this.tabletEditMenuOpen;
                    break;
                case 'view':
                    this.tabletViewMenuOpen = !this.tabletViewMenuOpen;
                    break;
                case 'filter':
                    this.tabletFilterPanelOpen = !this.tabletFilterPanelOpen;
                    // Load filter previews when opening the panel
                    if (this.tabletFilterPanelOpen) {
                        this.loadAllFilterPreviews();
                    }
                    break;
                case 'image':
                    this.tabletImageMenuOpen = !this.tabletImageMenuOpen;
                    break;
                case 'zoom':
                    this.tabletZoomMenuOpen = !this.tabletZoomMenuOpen;
                    break;
            }
        },

        closeAllTabletPopups() {
            // Close all non-pinned popups and panels
            this.tabletFileMenuOpen = false;
            this.tabletEditMenuOpen = false;
            this.tabletViewMenuOpen = false;
            this.tabletImageMenuOpen = false;
            this.tabletZoomMenuOpen = false;
            this.tabletColorPickerOpen = false;

            // Close non-pinned panels/drawers
            this.closeAllPanels();
        },

        // ==================== SIDE PANEL METHODS (Nav, Layers, History) ====================

        toggleSidePanel(which) {
            // Toggle the requested panel (multiple can be open, they stack)
            const openKey = `tablet${which.charAt(0).toUpperCase() + which.slice(1)}PanelOpen`;
            this[openKey] = !this[openKey];

            // Track active panel for focus handling
            if (this[openKey]) {
                this._activeSidePanel = which;
            } else {
                this._activeSidePanel = null;
            }

            // Persist panel visibility state
            this.savePanelState();
        },

        focusSidePanel(which) {
            // Called when user clicks within a panel
            this._activeSidePanel = which;
        },

        closeSidePanel(which) {
            const openKey = `tablet${which.charAt(0).toUpperCase() + which.slice(1)}PanelOpen`;
            this[openKey] = false;
            if (this._activeSidePanel === which) {
                this._activeSidePanel = null;
            }
        },

        handleGlobalClick(event) {
            // Close side panels when clicking outside - but NOT when clicking canvas (painting)
            if (this.currentUIMode !== 'tablet') return;

            // Check if click was inside any dock stack (using composedPath for detached elements)
            const path = event.composedPath();
            const clickedDock = path.some(el => el.classList && (
                el.classList.contains('tablet-dock-stack') ||
                el.classList.contains('tablet-dock-icon') ||
                el.classList.contains('tablet-dock-panel')
            ));
            if (clickedDock) return; // Don't close if clicking in dock area

            // Don't close panels when clicking on canvas (user is painting/drawing)
            const clickedCanvas = path.some(el =>
                el.classList && el.classList.contains('canvas-container') ||
                el.tagName === 'CANVAS'
            );
            if (clickedCanvas) return;

            // Don't close panels when clicking on floating panels or menus
            const clickedFloating = path.some(el => el.classList && (
                el.classList.contains('tablet-floating-panel') ||
                el.classList.contains('tablet-menu-popup') ||
                el.classList.contains('tablet-top-bar') ||
                el.classList.contains('tablet-bottom-bar')
            ));
            if (clickedFloating) return;

            // Close all dock panels (clicked on overlay or empty space)
            this.tabletLeftDrawerOpen = false;
            this.tabletNavPanelOpen = false;
            this.tabletLayersPanelOpen = false;
            this.tabletHistoryPanelOpen = false;
        },

        async loadFilterPreview(filterId) {
            // Load a single filter preview from the backend
            if (this.filterPreviews[filterId] || this.filterPreviewsLoading[filterId]) {
                return;
            }

            this.filterPreviewsLoading[filterId] = true;

            try {
                const response = await fetch(`/api/filters/${filterId}/preview`);
                if (response.ok) {
                    const data = await response.json();
                    this.filterPreviews[filterId] = data.preview;
                }
            } catch (err) {
                console.warn(`Failed to load filter preview for ${filterId}:`, err);
            } finally {
                this.filterPreviewsLoading[filterId] = false;
            }
        },

        async loadAllFilterPreviews() {
            // Load previews for all filters in the current tab
            for (const filter of this.filtersInCurrentTab) {
                if (!this.filterPreviews[filter.id]) {
                    this.loadFilterPreview(filter.id);
                }
            }
        },

        switchFilterTab(category) {
            this.tabletFilterTab = category;
            // Wait for Vue to update filtersInCurrentTab, then load previews
            this.$nextTick(() => {
                this.loadAllFilterPreviews();
            });
        },

        // Tool drag-to-reorder methods
        onToolDragStart(index, event) {
            this.toolDragIndex = index;
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', index.toString());
            // Add visual feedback
            event.target.classList.add('dragging');
        },

        onToolDragOver(index, event) {
            if (this.toolDragIndex === null || this.toolDragIndex === index) return;
            this.toolDragOverIndex = index;
            event.dataTransfer.dropEffect = 'move';
        },

        onToolDragLeave() {
            this.toolDragOverIndex = null;
        },

        onToolDrop(targetIndex) {
            if (this.toolDragIndex === null || this.toolDragIndex === targetIndex) return;

            // Reorder the tools array
            const tool = this.tabletAllTools.splice(this.toolDragIndex, 1)[0];
            this.tabletAllTools.splice(targetIndex, 0, tool);

            // Save custom order to localStorage
            this.saveToolOrder();

            // Reset drag state
            this.toolDragIndex = null;
            this.toolDragOverIndex = null;
        },

        onToolDragEnd(event) {
            event.target.classList.remove('dragging');
            this.toolDragIndex = null;
            this.toolDragOverIndex = null;
        },

        saveToolOrder() {
            try {
                const order = this.tabletAllTools.map(t => t.id);
                localStorage.setItem('stagforge-tool-order', JSON.stringify(order));
            } catch (e) {
                console.warn('Could not save tool order:', e);
            }
        },

        loadToolOrder() {
            try {
                const saved = localStorage.getItem('stagforge-tool-order');
                if (saved) {
                    const order = JSON.parse(saved);
                    // Reorder tools based on saved order
                    const orderedTools = [];
                    const remainingTools = [...this.tabletAllTools];

                    for (const id of order) {
                        const idx = remainingTools.findIndex(t => t.id === id);
                        if (idx !== -1) {
                            orderedTools.push(remainingTools.splice(idx, 1)[0]);
                        }
                    }
                    // Add any new tools that weren't in saved order
                    this.tabletAllTools = [...orderedTools, ...remainingTools];
                }
            } catch (e) {
                console.warn('Could not load tool order:', e);
            }
        },

        // Note: showTabletMenu() removed - replaced by toggleTabletPopup() with individual menu buttons

        showTabletZoomMenu() {
            // Legacy method for zoom popup - now handled via toggleTabletPopup('zoom')
            this.toggleTabletPopup('zoom');
        },

        tabletMenuAction(action, param) {
            // Close all menu popups
            this.tabletFileMenuOpen = false;
            this.tabletEditMenuOpen = false;
            this.tabletViewMenuOpen = false;
            this.tabletImageMenuOpen = false;
            switch (action) {
                // File actions
                case 'new':
                    this.showNewDocumentDialog();
                    break;
                case 'open':
                    this.fileOpen();
                    break;
                case 'save':
                    this.fileSave();
                    break;
                case 'saveAs':
                    this.fileSaveAs();
                    break;
                case 'loadSample':
                    if (param) this.loadSampleImage(param);
                    break;
                case 'export':
                    this.menuAction('export');
                    break;
                // Edit actions
                case 'undo':
                    this.undo();
                    break;
                case 'redo':
                    this.redo();
                    break;
                case 'cut':
                    this.cutSelection();
                    break;
                case 'copy':
                    this.copySelection();
                    break;
                case 'paste':
                    this.pasteSelection();
                    break;
                case 'pasteInPlace':
                    this.pasteInPlace();
                    break;
                case 'selectAll':
                    this.selectAll();
                    break;
                case 'deselect':
                    this.deselect();
                    break;
                // Image actions
                case 'flipH':
                    this.flipHorizontal();
                    break;
                case 'flipV':
                    this.flipVertical();
                    break;
                case 'rotate90':
                    this.rotate(90);
                    break;
                case 'rotate-90':
                    this.rotate(-90);
                    break;
                case 'flatten':
                    this.menuAction('flatten');
                    break;
                // View actions
                case 'desktop':
                    this.setUIMode('desktop');
                    break;
                case 'limited':
                    this.setUIMode('limited');
                    break;
                case 'toggleTheme':
                    this.toggleTheme();
                    break;
            }
        },

        // zoomIn, zoomOut moved to ZoomManagerMixin

        updateTabletNavigator() {
            const app = this.getState();
            if (!app?.renderer || !app?.layerStack) return;

            const canvas = this.$refs.tabletNavigatorCanvas;
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const maxSize = 240;

            // Calculate scale to fit navigator
            const docWidth = app.renderer.compositeCanvas?.width || this.docWidth;
            const docHeight = app.renderer.compositeCanvas?.height || this.docHeight;
            const scale = Math.min(maxSize / docWidth, maxSize / docHeight);

            canvas.width = Math.round(docWidth * scale);
            canvas.height = Math.round(docHeight * scale);

            // Draw document preview
            ctx.drawImage(app.renderer.compositeCanvas, 0, 0, canvas.width, canvas.height);

            // Draw viewport rectangle using logical display dimensions
            const viewLeft = -app.renderer.panX / app.renderer.zoom;
            const viewTop = -app.renderer.panY / app.renderer.zoom;
            const viewWidth = app.renderer.displayWidth / app.renderer.zoom;
            const viewHeight = app.renderer.displayHeight / app.renderer.zoom;

            ctx.strokeStyle = '#ff3333';
            ctx.lineWidth = 2;
            ctx.strokeRect(
                viewLeft * scale,
                viewTop * scale,
                viewWidth * scale,
                viewHeight * scale
            );
        },

        updateTabletHardness(value) {
            this.tabletHardness = parseInt(value);
            this.updateToolProperty('hardness', this.tabletHardness / 100);
        },

        // Limited mode methods

        getToolName(toolId) {
            const toolNames = {
                brush: 'Brush',
                eraser: 'Eraser',
                pencil: 'Pencil',
                fill: 'Fill',
                line: 'Line',
                rect: 'Rectangle',
                circle: 'Ellipse',
                spray: 'Spray',
                eyedropper: 'Eyedropper'
            };
            return toolNames[toolId] || toolId;
        },

        getToolIconId(toolId) {
            // Map tool IDs to icon IDs (most are the same)
            const iconMap = {
                brush: 'brush',
                eraser: 'eraser',
                pencil: 'pencil',
                fill: 'fill',
                line: 'line',
                rect: 'square',
                circle: 'circle',
                spray: 'spray',
                eyedropper: 'eyedropper'
            };
            return iconMap[toolId] || toolId;
        },

        openLimitedColorPicker() {
            // Open color picker in limited mode
            this.openColorPicker('fg', { target: { getBoundingClientRect: () => ({ left: 16, bottom: 150 }) } });
        },

        // Tablet mode methods

        updateTabletBrushSize(value) {
            this.tabletBrushSize = parseInt(value);
            this.updateToolProperty('size', this.tabletBrushSize);
        },

        updateTabletOpacity(value) {
            this.tabletOpacity = parseInt(value);
            this.updateToolProperty('opacity', this.tabletOpacity / 100);
        },

        updateTabletFontSize(value) {
            this.tabletFontSize = parseInt(value);
            this.updateToolProperty('fontSize', this.tabletFontSize);
        },

        updateTabletFontFamily(value) {
            this.tabletFontFamily = value;
            this.updateToolProperty('fontFamily', value);
        },

        toggleTabletFontWeight() {
            this.tabletFontWeight = this.tabletFontWeight === 'bold' ? 'normal' : 'bold';
            this.updateToolProperty('fontWeight', this.tabletFontWeight);
        },

        toggleTabletFontStyle() {
            this.tabletFontStyle = this.tabletFontStyle === 'italic' ? 'normal' : 'italic';
            this.updateToolProperty('fontStyle', this.tabletFontStyle);
        },

        syncTabletToolProperties() {
            // Sync tablet UI with current tool properties
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (tool) {
                // Size
                if (tool.size !== undefined) {
                    this.tabletBrushSize = tool.size;
                    this.tabletShowSize = true;
                } else {
                    this.tabletShowSize = false;
                }

                // Opacity
                if (tool.opacity !== undefined) {
                    this.tabletOpacity = Math.round(tool.opacity * 100);
                    this.tabletShowOpacity = true;
                } else {
                    this.tabletShowOpacity = false;
                }

                // Hardness
                if (tool.hardness !== undefined) {
                    this.tabletHardness = Math.round(tool.hardness * 100);
                    this.tabletShowHardness = true;
                } else {
                    this.tabletShowHardness = false;
                }

                // Text tool properties
                if (tool.constructor.id === 'text') {
                    this.tabletShowTextProps = true;
                    this.tabletFontSize = tool.fontSize || 24;
                    this.tabletFontFamily = tool.fontFamily || 'Arial';
                    this.tabletFontWeight = tool.fontWeight || 'normal';
                    this.tabletFontStyle = tool.fontStyle || 'normal';
                } else {
                    this.tabletShowTextProps = false;
                }
            }

            // Update tablet navigator if nav panel is open
            if (this.tabletNavPanelOpen) {
                this.$nextTick(() => this.updateTabletNavigator());
            }
        },

        // Navigator methods moved to NavigatorManagerMixin
        // Zoom methods (setZoomPercent, fitToWindow) moved to ZoomManagerMixin

        startPanelDrag(panelId, event) {
            // Placeholder for future panel dragging functionality
        },

        updateToolProperties() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (!tool) {
                this.toolProperties = [];
                return;
            }
            this.toolProperties = tool.getProperties ? tool.getProperties() : [];

            // Sync brush preset state
            if (this.currentToolId === 'brush') {
                const presetProp = this.toolProperties.find(p => p.id === 'preset');
                if (presetProp) {
                    this.currentBrushPreset = presetProp.value;
                    const opt = presetProp.options.find(o => o.value === presetProp.value);
                    this.currentBrushPresetName = opt ? opt.label : presetProp.value;
                }
            }
        },

        updateToolHint() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;
            if (!tool || !tool.getHint) {
                this.toolHint = null;
                return;
            }
            this.toolHint = tool.getHint();
        },

        updateLayerList() {
            const app = this.getState();
            if (!app?.layerStack) return;
            this.layers = app.layerStack.layers.slice().reverse().map(l => {
                const isGroup = l.isGroup ? l.isGroup() : false;
                return {
                    id: l.id,
                    name: l.name,
                    visible: l.visible,
                    locked: l.locked,
                    opacity: l.opacity,
                    blendMode: l.blendMode,
                    isVector: l.isVector ? l.isVector() : false,
                    isText: l.isText ? l.isText() : false,
                    isGroup: isGroup,
                    parentId: l.parentId || null,
                    expanded: l.expanded ?? true,
                    // Layer type for API
                    type: isGroup ? 'group' : (l.isVector?.() ? 'vector' : (l.isText?.() ? 'text' : 'raster')),
                    // Layer dimensions and position (groups don't have dimensions)
                    width: l.width || 0,
                    height: l.height || 0,
                    offsetX: l.offsetX ?? 0,
                    offsetY: l.offsetY ?? 0,
                    // Calculate indent level based on parentId chain
                    indentLevel: this.getLayerIndentLevel(l, app.layerStack),
                };
            });
            this.activeLayerId = app.layerStack.getActiveLayer()?.id;
            this.updateLayerControls();
            // Update thumbnails after Vue has updated the DOM
            this.$nextTick(() => this.updateLayerThumbnails());
        },

        getLayerIndentLevel(layer, layerStack) {
            let level = 0;
            let parentId = layer.parentId;
            while (parentId) {
                level++;
                const parent = layerStack.getLayerById(parentId);
                parentId = parent?.parentId;
            }
            return level;
        },

        updateLayerThumbnails() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const thumbSize = 40;

            for (const layer of app.layerStack.layers) {
                const refKey = 'layerThumb_' + layer.id;
                const thumbCanvas = this.$refs[refKey];
                if (!thumbCanvas || !thumbCanvas[0]) continue;

                const canvas = thumbCanvas[0];
                const ctx = canvas.getContext('2d');

                // Draw transparency grid background
                const gridSize = 5;
                for (let y = 0; y < thumbSize; y += gridSize) {
                    for (let x = 0; x < thumbSize; x += gridSize) {
                        const isLight = ((x / gridSize) + (y / gridSize)) % 2 === 0;
                        ctx.fillStyle = isLight ? '#ffffff' : '#cccccc';
                        ctx.fillRect(x, y, gridSize, gridSize);
                    }
                }

                // Calculate scaling to fit layer in thumbnail
                const layerWidth = layer.width || layer.canvas?.width || thumbSize;
                const layerHeight = layer.height || layer.canvas?.height || thumbSize;
                const scale = Math.min(thumbSize / layerWidth, thumbSize / layerHeight);
                const scaledWidth = layerWidth * scale;
                const scaledHeight = layerHeight * scale;
                const offsetX = (thumbSize - scaledWidth) / 2;
                const offsetY = (thumbSize - scaledHeight) / 2;

                // Draw layer content
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                if (layer.canvas) {
                    ctx.drawImage(layer.canvas, offsetX, offsetY, scaledWidth, scaledHeight);
                }
            }
        },

        updateLayerControls() {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer) {
                // Ensure opacity is a valid number (default to 100 if undefined/NaN)
                const opacity = typeof layer.opacity === 'number' && !isNaN(layer.opacity)
                    ? layer.opacity
                    : 1.0;
                this.activeLayerOpacity = Math.round(opacity * 100);
                this.activeLayerBlendMode = layer.blendMode || 'normal';
            } else {
                // No active layer - reset to defaults
                this.activeLayerOpacity = 100;
                this.activeLayerBlendMode = 'normal';
            }
        },

        // Document management methods
        updateDocumentTabs() {
            const app = this.getState();
            if (!app?.documentManager) return;
            this.documentTabs = app.documentManager.getDocumentList();
        },

        activateDocument(documentId) {
            const app = this.getState();
            if (!app?.documentManager) return;
            app.documentManager.setActiveDocument(documentId);
        },

        closeDocument(documentId) {
            const app = this.getState();
            if (!app?.documentManager) return;
            app.documentManager.closeDocument(documentId);
        },

        showNewDocumentDialog() {
            // For now, create a new document with default settings
            // Could show a dialog for width/height in the future
            const app = this.getState();
            if (!app?.documentManager) return;
            app.documentManager.createDocument({
                width: this.docWidth,
                height: this.docHeight
            });
        },

        showCloseDocumentDialog(document, callback) {
            // Simple confirmation dialog for unsaved changes
            const confirmed = confirm(`"${document.name}" has unsaved changes. Close anyway?`);
            if (callback) callback(confirmed);
        },

        formatCategory(category) {
            // Format category name for display
            const names = {
                'color': 'Color Adjustments',
                'blur': 'Blur & Smooth',
                'edge': 'Edge Detection',
                'threshold': 'Threshold',
                'morphology': 'Morphological',
                'artistic': 'Artistic Effects',
                'noise': 'Noise',
                'sharpen': 'Sharpen',
                'uncategorized': 'Other',
            };
            return names[category] || category.charAt(0).toUpperCase() + category.slice(1);
        },

        // Submenu handling
        openSubmenu(category, event) {
            this.cancelSubmenuClose();
            this.activeSubmenu = category;
            const rect = event.target.getBoundingClientRect();
            this.submenuPosition = {
                top: rect.top + 'px',
                left: (rect.right + 2) + 'px'
            };
        },

        closeSubmenuDelayed() {
            this.submenuCloseTimeout = setTimeout(() => {
                this.activeSubmenu = null;
            }, 150);
        },

        cancelSubmenuClose() {
            if (this.submenuCloseTimeout) {
                clearTimeout(this.submenuCloseTimeout);
                this.submenuCloseTimeout = null;
            }
        },

        // Filter dialog methods
        openFilterDialog(filter) {
            this.activeMenu = null;
            this.activeSubmenu = null;

            // Check if filter has parameters
            const hasParams = filter.params && filter.params.length > 0;

            if (!hasParams) {
                // Apply directly without dialog
                this.applyFilterDirect(filter);
                return;
            }

            // Initialize params with defaults
            this.filterParams = {};
            for (const param of filter.params) {
                this.filterParams[param.id] = param.default !== undefined ? param.default :
                    (param.type === 'range' ? param.min :
                     param.type === 'select' ? param.options[0] :
                     param.type === 'checkbox' ? false : '');
            }

            this.currentFilter = filter;
            this.filterDialogVisible = true;
            this.filterPreviewEnabled = true;
            this.filterPreviewState = null;

            // Save current state for preview/cancel, then apply initial preview
            this.$nextTick(() => {
                this.saveFilterPreviewState();
                // Small delay to ensure state is saved before preview
                setTimeout(() => {
                    this.updateFilterPreview();
                }, 50);
            });
        },

        saveFilterPreviewState() {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer) {
                this.filterPreviewState = layer.ctx.getImageData(0, 0, layer.width, layer.height);
            }
        },

        restoreFilterPreviewState(render = true) {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (layer && this.filterPreviewState) {
                layer.ctx.putImageData(this.filterPreviewState, 0, 0);
                if (render) {
                    app.renderer.requestRender();
                }
            }
        },

        toggleFilterPreview() {
            if (this.filterPreviewEnabled) {
                this.updateFilterPreview();
            } else {
                this.restoreFilterPreviewState();
            }
        },

        async updateFilterPreview() {
            if (!this.filterPreviewEnabled || !this.currentFilter) return;

            // Debounce preview updates
            if (this.filterPreviewDebounce) {
                clearTimeout(this.filterPreviewDebounce);
            }

            this.filterPreviewDebounce = setTimeout(async () => {
                const app = this.getState();
                if (!app || !this.filterPreviewState) return;

                try {
                    // Restore original state first (don't render yet)
                    this.restoreFilterPreviewState(false);

                    // Apply filter with current params and render
                    await this.applyFilterToLayer(this.currentFilter.id, this.filterParams, true);
                } catch (error) {
                    console.error('Preview error:', error);
                    // On error, restore and render original
                    this.restoreFilterPreviewState(true);
                }
            }, 150);
        },

        async applyFilterDirect(filter) {
            const app = this.getState();
            if (!app) return;

            app.history.saveState('Filter: ' + filter.name);
            this.statusMessage = 'Applying ' + filter.name + '...';

            try {
                await this.applyFilterToLayer(filter.id, {}, true);
                app.history.finishState();
                this.statusMessage = filter.name + ' applied';
            } catch (error) {
                console.error('Filter error:', error);
                app.history.abortCapture();
                this.statusMessage = 'Filter failed: ' + error.message;
            }
        },

        async applyFilterConfirm() {
            const app = this.getState();
            if (!app || !this.currentFilter) return;

            // The preview is already applied, just save to history
            app.history.saveState('Filter: ' + this.currentFilter.name);
            app.history.finishState();

            this.statusMessage = this.currentFilter.name + ' applied';
            this.filterDialogVisible = false;
            this.currentFilter = null;
            this.filterPreviewState = null;
        },

        cancelFilterDialog() {
            // Restore original state
            this.restoreFilterPreviewState();

            this.filterDialogVisible = false;
            this.currentFilter = null;
            this.filterPreviewState = null;
            this.statusMessage = 'Filter cancelled';
        },

        // Rasterize dialog methods
        confirmRasterize() {
            const app = this.getState();
            if (!app || !this.rasterizeLayerId) {
                this.cancelRasterize();
                return;
            }

            // Save state before rasterizing
            app.history.saveState('Rasterize Layer');

            // Rasterize the layer
            app.layerStack.rasterizeLayer(this.rasterizeLayerId);
            app.renderer.requestRender();

            app.history.finishState();

            // Update layers display
            this.updateLayerList();

            // Call the callback
            const callback = this.rasterizeCallback;
            this.showRasterizePrompt = false;
            this.rasterizeLayerId = null;
            this.rasterizeCallback = null;

            if (callback) {
                callback(true);
            }
        },

        cancelRasterize() {
            const callback = this.rasterizeCallback;
            this.showRasterizePrompt = false;
            this.rasterizeLayerId = null;
            this.rasterizeCallback = null;

            if (callback) {
                callback(false);
            }
        },

        // Preferences dialog methods
        showPreferencesDialog() {
            this.closeMenu();
            // Load current values from UIConfig
            const app = this.getState();
            if (app?.uiConfig) {
                this.prefRenderingSVG = app.uiConfig.get('rendering.vectorSVGRendering') ?? true;
                this.prefSupersampleLevel = app.uiConfig.get('rendering.vectorSupersampleLevel') ?? 3;
                this.prefAntialiasing = app.uiConfig.get('rendering.vectorAntialiasing') ?? false;
            }
            this.preferencesDialogVisible = true;
        },

        closePreferencesDialog() {
            this.preferencesDialogVisible = false;
        },

        savePreferences() {
            const app = this.getState();
            if (app?.uiConfig) {
                app.uiConfig.set('rendering.vectorSVGRendering', this.prefRenderingSVG);
                app.uiConfig.set('rendering.vectorSupersampleLevel', this.prefSupersampleLevel);
                app.uiConfig.set('rendering.vectorAntialiasing', this.prefAntialiasing);
            }
            this.preferencesDialogVisible = false;

            // Re-render any vector layers with new settings
            this.reRenderVectorLayers();
        },

        async reRenderVectorLayers() {
            const app = this.getState();
            if (!app?.layerStack) return;

            for (const layer of app.layerStack.layers) {
                if (layer.type === 'vector' && layer.renderFinal) {
                    await layer.renderFinal();
                }
            }
            app.renderer?.requestRender();
        },

        async applyFilterToLayer(filterId, params, renderAfter = true) {
            const app = this.getState();
            const layer = app?.layerStack?.getActiveLayer();
            if (!layer) return;

            // Check for active selection to constrain filter
            const selection = this.getSelection();
            let filterX = 0, filterY = 0, filterWidth = layer.width, filterHeight = layer.height;

            if (selection && selection.width > 0 && selection.height > 0) {
                // Convert selection to layer coordinates if needed
                let selX = selection.x, selY = selection.y;
                if (layer.docToCanvas) {
                    const coords = layer.docToCanvas(selection.x, selection.y);
                    selX = coords.x;
                    selY = coords.y;
                }
                // Clamp to layer bounds
                filterX = Math.max(0, Math.floor(selX));
                filterY = Math.max(0, Math.floor(selY));
                filterWidth = Math.min(layer.width - filterX, Math.ceil(selection.width));
                filterHeight = Math.min(layer.height - filterY, Math.ceil(selection.height));

                if (filterWidth <= 0 || filterHeight <= 0) return;
            }

            const imageData = layer.ctx.getImageData(filterX, filterY, filterWidth, filterHeight);

            // Create binary payload
            const metadata = JSON.stringify({
                width: imageData.width,
                height: imageData.height,
                params: params
            });
            const metadataBytes = new TextEncoder().encode(metadata);
            const metadataLength = new Uint32Array([metadataBytes.length]);

            const payload = new Uint8Array(4 + metadataBytes.length + imageData.data.length);
            payload.set(new Uint8Array(metadataLength.buffer), 0);
            payload.set(metadataBytes, 4);
            payload.set(imageData.data, 4 + metadataBytes.length);

            const response = await fetch(`${this.apiBase}/filters/${filterId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/octet-stream' },
                body: payload
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || 'Filter failed');
            }

            const resultBytes = new Uint8Array(await response.arrayBuffer());
            const resultImageData = new ImageData(
                new Uint8ClampedArray(resultBytes),
                imageData.width,
                imageData.height
            );

            // Put result back at the correct position (selection offset)
            layer.ctx.putImageData(resultImageData, filterX, filterY);

            if (renderAfter) {
                app.renderer.requestRender();
            }
        },

        getToolIcon(icon) {
            const icons = {
                // Tool icons
                'selection': '&#9633;',    // White square (selection)
                'lasso': '&#10551;',       // Lasso curve
                'magicwand': '&#10022;',   // Star/wand
                'move': '&#8689;',         // Move arrows
                'cursor': '&#10146;',      // Arrow cursor (shape edit)
                'pen': '&#9998;',          // Pen (bezier path)
                'hand': '&#9995;',         // Hand (pan)
                'brush': '&#128396;',      // Pencil
                'pencil': '&#9999;',       // Pencil
                'spray': '&#9729;',        // Cloud (spray)
                'eraser': '&#9986;',       // Scissors
                'line': '&#9585;',         // Diagonal line
                'rect': '&#9634;',         // Square
                'square': '&#9634;',       // Square (alias)
                'circle': '&#9679;',       // Circle
                'polygon': '&#11039;',     // Pentagon
                'shape': '&#9671;',        // Diamond
                'fill': '&#128276;',       // Bell (bucket)
                'gradient': '&#9698;',     // Gradient triangle
                'text': '&#84;',           // Letter T
                'eyedropper': '&#128083;', // Eyeglasses
                'crop': '&#8862;',         // Crop frame
                'clone': '&#128274;',      // Stamp
                'smudge': '&#9757;',       // Finger pointing
                'blur': '&#128167;',       // Water drop

                // UI/Action icons for tablet mode
                'menu': '&#9776;',         // Hamburger menu
                'tools': '&#128295;',      // Wrench (tools)
                'panels': '&#9881;',       // Gear/panels
                'undo': '&#8630;',         // Undo arrow
                'redo': '&#8631;',         // Redo arrow
                'navigator': '&#9635;',    // Navigation/compass
                'layers': '&#9776;',       // Layers (stacked)
                'history': '&#128337;',    // Clock (history)
                'settings': '&#9881;',     // Gear
                'close': '&#10005;',       // X
                'plus': '&#43;',           // Plus
                'minus': '&#8722;',        // Minus
                'zoom-in': '&#128269;',    // Magnifier
                'zoom-out': '&#128270;',   // Magnifier minus
                'save': '&#128190;',       // Floppy disk
                'export': '&#128228;',     // Export arrow

                // Menu icons for tablet mode
                'file': '&#128196;',       // Document
                'edit': '&#9998;',         // Edit pencil
                'view': '&#128065;',       // Eye (view)
                'filter': '&#128167;',     // Water drop (effects/filter)
                'image': '&#128444;',      // Framed image
                'deselect': '&#10060;',    // X in box (deselect)
            };
            return icons[icon] || '&#9679;';
        },

        // Tool selection methods moved to ToolManagerMixin

        // Brush preset methods
        generateBrushPresetThumbnails() {
            if (this.brushPresetThumbnailsGenerated) return;

            // Preset definitions (must match BrushPresets.js)
            const presets = [
                { id: 'hard-round-sm', size: 5, hardness: 100, opacity: 100, flow: 100 },
                { id: 'hard-round-md', size: 20, hardness: 100, opacity: 100, flow: 100 },
                { id: 'hard-round-lg', size: 50, hardness: 100, opacity: 100, flow: 100 },
                { id: 'soft-round-sm', size: 10, hardness: 0, opacity: 100, flow: 100 },
                { id: 'soft-round-md', size: 30, hardness: 0, opacity: 100, flow: 100 },
                { id: 'soft-round-lg', size: 60, hardness: 0, opacity: 100, flow: 100 },
                { id: 'airbrush', size: 40, hardness: 0, opacity: 50, flow: 30 },
                { id: 'pencil', size: 2, hardness: 100, opacity: 100, flow: 100 },
                { id: 'marker', size: 15, hardness: 80, opacity: 80, flow: 100 },
                { id: 'chalk', size: 25, hardness: 50, opacity: 70, flow: 60 },
            ];

            const newThumbnails = { ...this.brushPresetThumbnails };
            for (const preset of presets) {
                try {
                    newThumbnails[preset.id] = this.generatePresetThumbnail(preset);
                } catch (e) {
                    console.error('Error generating thumbnail for', preset.id, e);
                }
            }

            // Replace with new object to trigger Vue reactivity
            this.brushPresetThumbnails = newThumbnails;
            this.brushPresetThumbnailsGenerated = true;
        },

        generatePresetThumbnail(preset) {
            // Use 2x resolution for crisp rendering
            const width = 64;
            const height = 32;
            const scale = 2;

            const canvas = document.createElement('canvas');
            canvas.width = width * scale;
            canvas.height = height * scale;
            const ctx = canvas.getContext('2d');
            ctx.scale(scale, scale);

            // Enable high-quality rendering
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            // Dark background with subtle gradient
            const bgGrad = ctx.createLinearGradient(0, 0, width, height);
            bgGrad.addColorStop(0, '#1a1a1a');
            bgGrad.addColorStop(1, '#242424');
            ctx.fillStyle = bgGrad;
            ctx.fillRect(0, 0, width, height);

            // Calculate stroke width - scale down large brushes
            const maxStrokeWidth = 10;
            const minStrokeWidth = 1;
            const strokeWidth = Math.max(minStrokeWidth, Math.min(maxStrokeWidth, preset.size * 0.2));

            // Set up stroke style
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.lineWidth = strokeWidth;

            // Calculate alpha from opacity and flow
            const alpha = (preset.opacity / 100) * (preset.flow / 100);

            // Draw bezier curve using native canvas bezierCurveTo for smooth anti-aliased strokes
            ctx.beginPath();
            ctx.moveTo(6, height * 0.65);
            ctx.bezierCurveTo(
                width * 0.3, height * 0.15,   // control point 1
                width * 0.7, height * 0.85,   // control point 2
                width - 6, height * 0.35      // end point
            );

            // Apply hardness via blur/shadow or gradient stroke
            const hardness = preset.hardness / 100;

            if (hardness < 0.5) {
                // Soft brush - use shadow blur for soft edges
                const blur = (1 - hardness) * strokeWidth * 0.8;
                ctx.shadowColor = `rgba(255, 255, 255, ${alpha * 0.7})`;
                ctx.shadowBlur = blur;
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.5})`;
                ctx.stroke();

                // Draw core stroke
                ctx.shadowBlur = blur * 0.3;
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.8})`;
                ctx.lineWidth = strokeWidth * 0.6;
                ctx.stroke();
            } else {
                // Hard brush - solid stroke
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
                ctx.stroke();
            }

            // Reset shadow
            ctx.shadowBlur = 0;
            ctx.shadowColor = 'transparent';

            return canvas.toDataURL('image/png');
        },

        toggleBrushPresetMenu(event) {
            if (event) {
                event.stopPropagation();
                event.preventDefault();
            }
            if (!this.brushPresetThumbnailsGenerated) {
                this.generateBrushPresetThumbnails();
            }
            this.showBrushPresetMenu = !this.showBrushPresetMenu;
        },

        selectBrushPreset(presetId) {
            this.updateToolProperty('preset', presetId);
            this.showBrushPresetMenu = false;
        },

        // Brush cursor methods
        updateBrushCursor() {
            const app = this.getState();
            const tool = app?.toolManager?.currentTool;

            if (!tool) {
                this.canvasCursor = 'default';
                this.showCursorOverlay = false;
                return;
            }

            // Tools that should show a size-based circular cursor overlay
            // These are tools with cursor='none' that have a size property
            const toolCursor = tool.constructor.cursor;
            const hasSize = typeof tool.size === 'number';

            if (toolCursor === 'none' && hasSize) {
                const size = tool.size || 20;
                const zoom = app?.renderer?.zoom || 1;
                const scaledSize = Math.max(4, size * zoom);

                // Always use overlay cursor (unified approach, no size limit)
                this.canvasCursor = 'none';
                this.cursorOverlaySize = Math.ceil(scaledSize) + 4;
                this.drawCursorOverlay(scaledSize);

                // Only show overlay if mouse is over canvas
                this.showCursorOverlay = this.mouseOverCanvas;
            } else {
                // Use the tool's default cursor
                this.showCursorOverlay = false;
                this.canvasCursor = toolCursor || 'crosshair';
            }
        },

        drawCursorOverlay(scaledSize) {
            // Draw the brush cursor on the overlay canvas
            this.$nextTick(() => {
                const canvas = this.$refs.cursorOverlay;
                if (!canvas) return;

                const canvasSize = Math.ceil(scaledSize) + 4;
                canvas.width = canvasSize;
                canvas.height = canvasSize;

                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvasSize, canvasSize);

                const center = canvasSize / 2;
                const radius = scaledSize / 2;

                // Draw outer circle (dark outline)
                ctx.beginPath();
                ctx.arc(center, center, radius, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)';
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Draw inner circle (light outline)
                ctx.beginPath();
                ctx.arc(center, center, radius - 1, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.lineWidth = 1;
                ctx.stroke();

                // Draw center crosshair
                const crossSize = Math.min(8, scaledSize / 4);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(center - crossSize, center);
                ctx.lineTo(center + crossSize, center);
                ctx.moveTo(center, center - crossSize);
                ctx.lineTo(center, center + crossSize);
                ctx.stroke();

                ctx.strokeStyle = 'rgba(0, 0, 0, 0.9)';
                ctx.lineWidth = 0.5;
                ctx.stroke();
            });
        },

        updateCursorOverlayPosition(clientX, clientY) {
            // Update overlay position relative to main canvas (same reference as painting code)
            const canvas = this.$refs.mainCanvas;
            if (!canvas) return;

            const rect = canvas.getBoundingClientRect();
            this.cursorOverlayX = clientX - rect.left;
            this.cursorOverlayY = clientY - rect.top;
        },

        getPresetLabel(presetId) {
            const preset = this.toolProperties.find(p => p.id === 'preset');
            if (preset) {
                const opt = preset.options.find(o => o.value === presetId);
                return opt ? opt.label : presetId;
            }
            return presetId;
        },

        // Layer operations, drag-drop moved to LayerOperationsMixin, LayerDragDropMixin

        // Popup menus moved to PopupMenuMixin

        // Layer effects panel
        showEffectsPanel() {
            const app = this.getState();
            if (!app?.layerStack) return;

            const layer = app.layerStack.getActiveLayer();
            if (!layer) return;

            // Remove existing panels
            document.getElementById('effects-panel')?.remove();
            document.getElementById('effect-editor')?.remove();

            // Capture initial effects state for this layer only (for history diff)
            this._effectsLayerId = layer.id;
            this._effectsBefore = layer.effects ? layer.effects.map(e => e.serialize()) : [];

            // Get available effects from LayerEffects module
            const LayerEffects = window.LayerEffects;
            let availableEffects = [];
            if (LayerEffects?.getAvailableEffects) {
                availableEffects = LayerEffects.getAvailableEffects();
                console.log('Effects from module:', availableEffects.length);
            } else {
                // Fallback list if LayerEffects not yet loaded
                availableEffects = [
                    { type: 'dropShadow', displayName: 'Drop Shadow' },
                    { type: 'innerShadow', displayName: 'Inner Shadow' },
                    { type: 'outerGlow', displayName: 'Outer Glow' },
                    { type: 'innerGlow', displayName: 'Inner Glow' },
                    { type: 'bevelEmboss', displayName: 'Bevel & Emboss' },
                    { type: 'stroke', displayName: 'Stroke' },
                    { type: 'colorOverlay', displayName: 'Color Overlay' }
                ];
                console.log('Using fallback effects:', availableEffects.length);
            }

            // Initialize effects array if needed
            if (!layer.effects) layer.effects = [];

            const panel = document.createElement('div');
            panel.id = 'effects-panel';
            panel.className = 'effects-panel';
            panel.innerHTML = `
                <div class="effects-panel-header">
                    <span>Layer Effects - ${layer.name}</span>
                    <button class="effects-panel-close">&times;</button>
                </div>
                <div class="effects-panel-body">
                    <div class="effects-list-pane">
                        <div class="effects-list" id="effects-list">
                            ${availableEffects.map(e => {
                                const existingEffect = layer.effects.find(eff => eff.type === e.type);
                                const isEnabled = existingEffect?.enabled ?? false;
                                return `
                                    <div class="effect-row ${isEnabled ? 'enabled' : ''}" data-effect-type="${e.type}">
                                        <input type="checkbox" class="effect-checkbox" ${isEnabled ? 'checked' : ''}>
                                        <span class="effect-label">${e.displayName}</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                    <div class="effects-props-pane" id="effects-props">
                        <div class="effects-props-empty">Select an effect to edit properties</div>
                    </div>
                </div>
                <div class="effects-panel-footer">
                    <button class="btn-ok" id="effects-ok">OK</button>
                </div>
            `;

            document.body.appendChild(panel);

            // Center panel
            panel.style.left = ((window.innerWidth - 500) / 2) + 'px';
            panel.style.top = ((window.innerHeight - 450) / 2) + 'px';

            // Make draggable
            this.makePanelDraggable(panel, panel.querySelector('.effects-panel-header'));

            // Store references
            this._effectsLayer = layer;
            this._selectedEffectType = null;

            // Bind checkbox and row click events
            panel.querySelectorAll('.effect-row').forEach(row => {
                const effectType = row.dataset.effectType;
                const checkbox = row.querySelector('.effect-checkbox');

                // Checkbox toggle - add/remove effect
                checkbox.addEventListener('change', (e) => {
                    e.stopPropagation();
                    this.toggleEffect(layer, effectType, checkbox.checked);
                    row.classList.toggle('enabled', checkbox.checked);
                    // Show props if enabling
                    if (checkbox.checked) {
                        this.selectEffectType(effectType);
                    }
                });

                // Row click - select for editing
                row.addEventListener('click', (e) => {
                    if (e.target === checkbox) return;
                    // If not enabled, enable it first
                    if (!checkbox.checked) {
                        checkbox.checked = true;
                        this.toggleEffect(layer, effectType, true);
                        row.classList.add('enabled');
                    }
                    this.selectEffectType(effectType);
                });
            });

            // Close button - commit history if effects changed
            const closePanel = () => {
                this.commitEffectsHistory();
                panel.remove();
            };
            panel.querySelector('.effects-panel-close').addEventListener('click', closePanel);
            panel.querySelector('#effects-ok').addEventListener('click', closePanel);
        },

        /**
         * Commit effects changes to history if there were any changes.
         */
        commitEffectsHistory() {
            const app = this.getState();
            if (!app?.history || !this._effectsLayerId) return;

            const layer = app.layerStack.getLayerById(this._effectsLayerId);
            if (!layer) {
                this._effectsLayerId = null;
                this._effectsBefore = null;
                return;
            }

            // Get current effects state
            const effectsAfter = layer.effects ? layer.effects.map(e => e.serialize()) : [];

            // Compare
            const beforeJson = JSON.stringify(this._effectsBefore);
            const afterJson = JSON.stringify(effectsAfter);

            if (beforeJson !== afterJson) {
                // Create history entry with layer-specific effect snapshot
                app.history.beginCapture('Modify Layer Effects', []);
                app.history.captureEffectsBefore(this._effectsLayerId, this._effectsBefore);
                app.history.commitCapture();

                // Mark document modified for auto-save
                app.documentManager?.getActiveDocument()?.markModified();
            }

            // Clean up
            this._effectsLayerId = null;
            this._effectsBefore = null;
        },

        toggleEffect(layer, effectType, enabled) {
            const LayerEffects = window.LayerEffects;
            console.log('toggleEffect:', effectType, enabled);
            console.log('LayerEffects keys:', LayerEffects ? Object.keys(LayerEffects) : 'none');
            console.log('effectRegistry:', LayerEffects?.effectRegistry);

            if (!layer.effects) layer.effects = [];
            const existingEffect = layer.effects.find(e => e.type === effectType);

            if (enabled && !existingEffect) {
                // Add new effect
                const EffectClass = LayerEffects?.effectRegistry?.[effectType];
                console.log('EffectClass:', effectType, !!EffectClass);
                if (EffectClass) {
                    const effect = new EffectClass();
                    console.log('Created effect:', effect);
                    if (layer.addEffect) {
                        layer.addEffect(effect);
                    } else {
                        // Fallback: manually add to effects array
                        layer.effects.push(effect);
                    }
                    console.log('Layer effects after add:', layer.effects);
                } else {
                    console.warn('No EffectClass for', effectType);
                }
            } else if (!enabled && existingEffect) {
                // Remove effect
                if (layer.removeEffect) {
                    layer.removeEffect(existingEffect.id);
                } else {
                    layer.effects = layer.effects.filter(e => e.id !== existingEffect.id);
                }
            } else if (enabled && existingEffect) {
                // Re-enable existing effect
                existingEffect.enabled = true;
            }

            const app = this.getState();
            app?.renderer?.requestRender();
        },

        selectEffectType(effectType) {
            this._selectedEffectType = effectType;
            const layer = this._effectsLayer;
            console.log('selectEffectType:', effectType, 'layer effects:', layer?.effects);
            const effect = layer?.effects?.find(e => e.type === effectType);
            console.log('Found effect:', effect);

            // Update selection UI
            document.querySelectorAll('.effect-row').forEach(row => {
                row.classList.toggle('selected', row.dataset.effectType === effectType);
            });

            // Render properties
            const propsPane = document.getElementById('effects-props');
            if (!propsPane || !effect) {
                console.log('No effect found, showing empty');
                if (propsPane) {
                    propsPane.innerHTML = '<div class="effects-props-empty">Select an effect to edit properties</div>';
                }
                return;
            }

            const LayerEffects = window.LayerEffects;
            const displayName = LayerEffects?.effectRegistry[effect.type]?.displayName || effect.type;
            const params = effect.getParams ? effect.getParams() : effect;

            propsPane.innerHTML = `
                <div class="effects-props-title">${displayName}</div>
                <div class="effects-props-content">
                    ${this.renderEffectParams(effect, params)}
                </div>
            `;

            // Bind param change events
            const app = this.getState();
            propsPane.querySelectorAll('.effect-param').forEach(input => {
                input.addEventListener('input', () => {
                    this.updateEffectParam(layer, effect, input, app);
                });
            });
        },

        renderEffectsList(layer) {
            const list = document.getElementById('effects-list');
            if (!list) return;

            const LayerEffects = window.LayerEffects;
            if (!layer.effects || layer.effects.length === 0) {
                list.innerHTML = '<div class="effects-empty">No effects applied</div>';
                return;
            }

            list.innerHTML = layer.effects.map((effect) => `
                <div class="effect-item ${effect.enabled ? '' : 'disabled'}" data-effect-id="${effect.id}">
                    <input type="checkbox" class="effect-enabled" ${effect.enabled ? 'checked' : ''}>
                    <span class="effect-name">${LayerEffects?.effectRegistry[effect.type]?.displayName || effect.type}</span>
                    <button class="effect-edit" title="Edit">&#9998;</button>
                    <button class="effect-delete" title="Delete">&times;</button>
                </div>
            `).join('');

            const app = this.getState();

            // Bind events
            list.querySelectorAll('.effect-item').forEach(item => {
                const effectId = item.dataset.effectId;

                item.querySelector('.effect-enabled')?.addEventListener('change', (e) => {
                    const effect = layer.getEffect(effectId);
                    if (effect) {
                        effect.enabled = e.target.checked;
                        item.classList.toggle('disabled', !effect.enabled);
                        app?.renderer?.requestRender();
                    }
                });

                item.querySelector('.effect-edit')?.addEventListener('click', () => {
                    this.showEffectEditor(layer, effectId);
                });

                item.querySelector('.effect-delete')?.addEventListener('click', () => {
                    layer.removeEffect(effectId);
                    this.renderEffectsList(layer);
                    app?.renderer?.requestRender();
                });
            });
        },

        addEffectToLayer(layer, effectType) {
            const LayerEffects = window.LayerEffects;
            const EffectClass = LayerEffects?.effectRegistry[effectType];
            if (!EffectClass) return;

            const effect = new EffectClass();
            layer.addEffect(effect);
            this.renderEffectsList(layer);

            const app = this.getState();
            app?.renderer?.requestRender();

            // Open editor for new effect
            this.showEffectEditor(layer, effect.id);
        },

        showEffectEditor(layer, effectId) {
            const effect = layer.getEffect(effectId);
            if (!effect) return;

            const LayerEffects = window.LayerEffects;

            // Remove existing editor
            document.getElementById('effect-editor')?.remove();

            const editor = document.createElement('div');
            editor.id = 'effect-editor';
            editor.className = 'effect-editor';

            const displayName = LayerEffects?.effectRegistry[effect.type]?.displayName || effect.type;
            const params = effect.getParams ? effect.getParams() : effect;

            editor.innerHTML = `
                <div class="effect-editor-header">
                    <span>${displayName}</span>
                    <button class="effect-editor-close">&times;</button>
                </div>
                <div class="effect-editor-content">
                    ${this.renderEffectParams(effect, params)}
                </div>
            `;

            document.body.appendChild(editor);

            // Position near effects panel
            const panel = document.getElementById('effects-panel');
            if (panel) {
                const rect = panel.getBoundingClientRect();
                editor.style.left = (rect.right + 10) + 'px';
                editor.style.top = rect.top + 'px';
            } else {
                editor.style.left = ((window.innerWidth - 280) / 2 + 200) + 'px';
                editor.style.top = ((window.innerHeight - 300) / 2) + 'px';
            }

            // Make draggable
            this.makePanelDraggable(editor, editor.querySelector('.effect-editor-header'));

            // Close button
            editor.querySelector('.effect-editor-close').addEventListener('click', () => editor.remove());

            // Bind param change events
            const app = this.getState();
            editor.querySelectorAll('.effect-param').forEach(input => {
                input.addEventListener('input', () => {
                    this.updateEffectParam(layer, effect, input, app);
                });
            });
        },

        renderEffectParams(effect, params) {
            const fields = [];

            for (const [key, value] of Object.entries(params)) {
                if (key === 'id' || key === 'type') continue;

                let field = '';
                if (typeof value === 'boolean') {
                    field = `
                        <label class="effect-param-row">
                            <span>${this.formatParamName(key)}</span>
                            <input type="checkbox" class="effect-param" data-param="${key}" ${value ? 'checked' : ''}>
                        </label>
                    `;
                } else if (typeof value === 'number') {
                    const isOpacity = key.toLowerCase().includes('opacity');
                    const min = isOpacity ? 0 : -100;
                    const max = isOpacity ? 1 : 100;
                    const step = isOpacity ? 0.01 : 1;
                    field = `
                        <label class="effect-param-row">
                            <span>${this.formatParamName(key)}</span>
                            <input type="range" class="effect-param" data-param="${key}"
                                   min="${min}" max="${max}" step="${step}" value="${value}">
                            <span class="effect-param-value">${isOpacity ? Math.round(value * 100) + '%' : value}</span>
                        </label>
                    `;
                } else if (typeof value === 'string' && value.startsWith('#')) {
                    field = `
                        <label class="effect-param-row">
                            <span>${this.formatParamName(key)}</span>
                            <input type="color" class="effect-param" data-param="${key}" value="${value}">
                        </label>
                    `;
                } else if (typeof value === 'string') {
                    const options = this.getEffectParamOptions(key);
                    if (options) {
                        field = `
                            <label class="effect-param-row">
                                <span>${this.formatParamName(key)}</span>
                                <select class="effect-param" data-param="${key}">
                                    ${options.map(o => `<option value="${o}" ${o === value ? 'selected' : ''}>${o}</option>`).join('')}
                                </select>
                            </label>
                        `;
                    } else {
                        field = `
                            <label class="effect-param-row">
                                <span>${this.formatParamName(key)}</span>
                                <input type="text" class="effect-param" data-param="${key}" value="${value}">
                            </label>
                        `;
                    }
                }

                if (field) fields.push(field);
            }

            return fields.join('') || '<div class="effects-empty">No parameters</div>';
        },

        getEffectParamOptions(key) {
            const options = {
                position: ['outside', 'inside', 'center'],
                style: ['innerBevel', 'outerBevel', 'emboss', 'pillowEmboss'],
                direction: ['up', 'down'],
                source: ['edge', 'center']
            };
            return options[key];
        },

        formatParamName(name) {
            return name.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
        },

        updateEffectParam(layer, effect, input, app) {
            const param = input.dataset.param;
            let value;

            if (input.type === 'checkbox') {
                value = input.checked;
            } else if (input.type === 'range' || input.type === 'number') {
                value = parseFloat(input.value);
                // Update display value
                const display = input.nextElementSibling;
                if (display?.classList.contains('effect-param-value')) {
                    const isOpacity = param.toLowerCase().includes('opacity');
                    display.textContent = isOpacity ? Math.round(value * 100) + '%' : value;
                }
            } else {
                value = input.value;
            }

            effect[param] = value;
            if (layer._effectCacheVersion !== undefined) {
                layer._effectCacheVersion++;
            }
            app?.renderer?.requestRender();
        },

        makePanelDraggable(element, handle) {
            let offsetX, offsetY;

            handle.style.cursor = 'move';

            handle.addEventListener('mousedown', (e) => {
                offsetX = e.clientX - element.offsetLeft;
                offsetY = e.clientY - element.offsetTop;

                const onMouseMove = (e) => {
                    element.style.left = (e.clientX - offsetX) + 'px';
                    element.style.top = (e.clientY - offsetY) + 'px';
                };

                const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        },

        // Zoom methods moved to ZoomManagerMixin

        // Menus moved to MenuManagerMixin

        // Canvas events and keyboard events moved to CanvasEventsMixin, KeyboardEventsMixin

        // Public methods (callable from Python)
        async newDocument(width, height) {
            const app = this.getState();
            if (!app) return;

            this.docWidth = width;
            this.docHeight = height;
            app.canvasWidth = width;
            app.canvasHeight = height;

            // Reset layer stack (need to import dynamically)
            const { LayerStack } = await import('/static/js/core/LayerStack.js');
            app.layerStack = new LayerStack(width, height, app.eventBus);
            app.renderer.layerStack = app.layerStack;
            app.renderer.resize(width, height);

            // Create initial layer
            const bgLayer = app.layerStack.addLayer({ name: 'Background' });
            bgLayer.fill('#FFFFFF');

            app.history.clear();
            this.updateLayerList();
            this.fitToWindow();
            this.emitStateUpdate();
        },

        // undo/redo methods moved to HistoryManagerMixin

        // ==================== FILE OPERATIONS ====================

        async fileSave() {
            const app = this.getState();
            if (!app?.fileManager) {
                console.warn('FileManager not initialized');
                return;
            }

            this.statusMessage = 'Saving...';
            const result = await app.fileManager.save();
            if (result.success) {
                this.statusMessage = `Saved: ${result.filename}`;
                setTimeout(() => { this.statusMessage = 'Ready'; }, 2000);
            } else if (result.error !== 'cancelled') {
                this.statusMessage = `Save failed: ${result.error}`;
            } else {
                this.statusMessage = 'Ready';
            }
        },

        async fileSaveAs() {
            const app = this.getState();
            if (!app?.fileManager) {
                console.warn('FileManager not initialized');
                return;
            }

            this.statusMessage = 'Saving...';
            const result = await app.fileManager.saveAs();
            if (result.success) {
                this.statusMessage = `Saved: ${result.filename}`;
                setTimeout(() => { this.statusMessage = 'Ready'; }, 2000);
            } else if (result.error !== 'cancelled') {
                this.statusMessage = `Save failed: ${result.error}`;
            } else {
                this.statusMessage = 'Ready';
            }
        },

        async fileOpen() {
            const app = this.getState();
            if (!app?.fileManager) {
                console.warn('FileManager not initialized');
                return;
            }

            this.statusMessage = 'Opening...';
            const result = await app.fileManager.open();
            if (result.success) {
                this.statusMessage = `Opened: ${result.filename}`;
                this.updateLayerList();
                this.fitToWindow();
                setTimeout(() => { this.statusMessage = 'Ready'; }, 2000);
            } else if (result.error !== 'cancelled') {
                this.statusMessage = `Open failed: ${result.error}`;
            } else {
                this.statusMessage = 'Ready';
            }
        },

        async loadSampleImage(img) {
            const app = this.getState();
            if (!app) return;

            this.statusMessage = `Loading ${img.name}...`;
            try {
                const response = await fetch(`${this.apiBase}/images/${img.source}/${img.id}`);
                if (!response.ok) throw new Error('Failed to fetch image');

                // Get metadata from header
                const metadata = JSON.parse(response.headers.get('X-Image-Metadata') || '{}');
                const width = metadata.width || 800;
                const height = metadata.height || 600;

                // Get raw RGBA data
                const buffer = await response.arrayBuffer();
                const rgba = new Uint8ClampedArray(buffer);

                // Create new document with image dimensions
                this.docWidth = width;
                this.docHeight = height;
                app.canvasWidth = width;
                app.canvasHeight = height;

                // Recreate layer stack with new dimensions
                const { LayerStack } = await import('/static/js/core/LayerStack.js');
                app.layerStack = new LayerStack(width, height, app.eventBus);
                app.renderer.layerStack = app.layerStack;
                app.renderer.resize(width, height);

                // Create layer and set image data
                const layer = app.layerStack.addLayer({ name: img.name });
                const imageData = new ImageData(rgba, width, height);
                layer.ctx.putImageData(imageData, 0, 0);

                app.history.clear();
                this.updateLayerList();
                this.fitToWindow();
                this.statusMessage = 'Ready';
            } catch (e) {
                console.error('Failed to load image:', e);
                this.statusMessage = 'Failed to load image';
            }
        },

        async applyFilter(filterId, params) {
            const app = this.getState();
            if (!app?.pluginManager) return;

            this.statusMessage = 'Applying filter...';
            try {
                await app.pluginManager.applyFilter(filterId, app.layerStack.getActiveLayer(), params);
                app.renderer.requestRender();
                this.statusMessage = 'Ready';
            } catch (e) {
                console.error('Failed to apply filter:', e);
                this.statusMessage = 'Filter failed';
            }
        },

        exportPNG() {
            const app = this.getState();
            if (!app?.layerStack) return;

            // Flatten to temp canvas
            const flatCanvas = document.createElement('canvas');
            flatCanvas.width = this.docWidth;
            flatCanvas.height = this.docHeight;
            const ctx = flatCanvas.getContext('2d');

            // White background
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, this.docWidth, this.docHeight);

            // Draw all visible layers
            for (const layer of app.layerStack.layers) {
                if (!layer.visible) continue;
                ctx.globalAlpha = layer.opacity;
                ctx.drawImage(layer.canvas, 0, 0);
            }

            // Export
            const link = document.createElement('a');
            link.download = 'stagforge-export.png';
            link.href = flatCanvas.toDataURL('image/png');
            link.click();
        },

        // Selection and Clipboard methods moved to ClipboardManagerMixin

        // ===== Session API Methods (called from Python) =====

        emitStateUpdate() {
            // Emit state to Python for session tracking (multi-document format)
            const app = this.getState();
            if (!app?.documentManager) return;

            // Build documents array from documentManager
            const documents = app.documentManager.documents.map(doc => ({
                id: doc.id,
                name: doc.name,
                width: doc.width,
                height: doc.height,
                active_layer_id: doc.layerStack?.layers[doc.layerStack.activeLayerIndex]?.id || null,
                is_modified: doc.isModified || false,
                created_at: doc.createdAt?.toISOString() || new Date().toISOString(),
                modified_at: doc.modifiedAt?.toISOString() || new Date().toISOString(),
                layers: doc.layerStack?.layers.map(layer => ({
                    id: layer.id,
                    name: layer.name,
                    type: layer.isGroup?.() ? 'group' : (layer.isVector?.() ? 'vector' : (layer.isText?.() ? 'text' : 'raster')),
                    visible: layer.visible,
                    locked: layer.locked,
                    opacity: layer.opacity,
                    blendMode: layer.blendMode,
                    width: layer.width || 0,
                    height: layer.height || 0,
                    offsetX: layer.offsetX || 0,
                    offsetY: layer.offsetY || 0,
                    parentId: layer.parentId || null,
                })) || [],
            }));

            const activeDoc = app.documentManager.getActiveDocument();

            this.$emit('state-update', {
                active_document_id: activeDoc?.id || null,
                documents: documents,
                active_tool: this.currentToolId,
                tool_properties: this.toolProperties.reduce((acc, p) => { acc[p.id] = p.value; return acc; }, {}),
                foreground_color: this.fgColor,
                background_color: this.bgColor,
                zoom: this.zoom,
                recent_colors: this.recentColors,
            });
        },

        executeCommand(command, params = {}) {
            // Execute editor commands from Python
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                switch (command) {
                    case 'undo':
                        app.history.undo();
                        break;
                    case 'redo':
                        app.history.redo();
                        break;
                    case 'new_layer':
                        this.addLayer();
                        break;
                    case 'delete_layer':
                        this.deleteLayer();
                        break;
                    case 'duplicate_layer':
                        this.duplicateLayer();
                        break;
                    case 'merge_down':
                        this.mergeDown();
                        break;
                    case 'flatten':
                        app.history.saveState('Flatten Image');
                        app.layerStack.flattenAll();
                        app.history.finishState();
                        this.updateLayerList();
                        break;
                    case 'set_foreground_color':
                        if (params.color) this.setForegroundColor(params.color);
                        break;
                    case 'set_background_color':
                        if (params.color) this.setBackgroundColor(params.color);
                        break;
                    case 'select_tool':
                        if (params.tool_id) this.selectTool(params.tool_id);
                        break;
                    case 'apply_filter':
                        if (params.filter_id) this.applyFilter(params.filter_id, params.params || {});
                        break;
                    case 'new_document':
                        if (params.width && params.height) this.newDocument(params.width, params.height);
                        break;
                    // Selection commands
                    case 'select_all':
                        this.selectAll();
                        break;
                    case 'deselect':
                        this.deselect();
                        break;
                    case 'delete_selection':
                        this.deleteSelection();
                        break;
                    // Clipboard commands
                    case 'copy':
                        return { success: this.clipboardCopy() };
                    case 'copy_merged':
                        return { success: this.clipboardCopyMerged() };
                    case 'cut':
                        return { success: this.clipboardCut() };
                    case 'paste':
                        return { success: this.clipboardPaste() };
                    case 'paste_in_place':
                        return { success: this.clipboardPasteInPlace() };
                    default:
                        return { success: false, error: `Unknown command: ${command}` };
                }
                return { success: true };
            } catch (e) {
                return { success: false, error: e.message };
            }
        },

        executeToolAction(toolId, action, params = {}) {
            // Execute tool actions from Python
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            const tool = app.toolManager.tools.get(toolId);
            if (!tool) return { success: false, error: `Tool not found: ${toolId}` };

            try {
                // Select the tool first if not already selected
                if (app.toolManager.currentTool !== tool) {
                    app.toolManager.select(toolId);
                }

                // If the tool has its own executeAction, use it
                if (tool.executeAction) {
                    const result = tool.executeAction(action, params);
                    if (result) {
                        this.emitStateUpdate();
                        return result;
                    }
                }

                // Fallback: Execute the action based on generic patterns
                const layer = app.layerStack.getActiveLayer();
                if (!layer) return { success: false, error: 'No active layer' };

                switch (action) {
                    case 'stroke':
                        // Draw a stroke along points
                        // Note: Tool's onMouseDown/onMouseUp handle history
                        if (!params.points || params.points.length < 2) {
                            return { success: false, error: 'Need at least 2 points for stroke' };
                        }
                        const points = params.points;
                        // Simulate mouse events for the tool
                        tool.onMouseDown({ button: 0 }, points[0][0], points[0][1]);
                        for (let i = 1; i < points.length; i++) {
                            tool.onMouseMove({ button: 0 }, points[i][0], points[i][1]);
                        }
                        tool.onMouseUp({ button: 0 }, points[points.length-1][0], points[points.length-1][1]);
                        app.renderer.requestRender();
                        break;

                    case 'fill':
                        // Flood fill at a point
                        // Note: Tool's onMouseDown handles history
                        if (params.point) {
                            tool.onMouseDown({ button: 0 }, params.point[0], params.point[1]);
                            tool.onMouseUp({ button: 0 }, params.point[0], params.point[1]);
                            app.renderer.requestRender();
                        }
                        break;

                    case 'translate':
                        // Move layer directly (not using tool)
                        if (params.dx !== undefined && params.dy !== undefined) {
                            app.history.saveState('Move');
                            const ctx = layer.ctx;
                            const imageData = ctx.getImageData(0, 0, this.docWidth, this.docHeight);
                            ctx.clearRect(0, 0, this.docWidth, this.docHeight);
                            ctx.putImageData(imageData, params.dx, params.dy);
                            app.history.finishState();
                            app.renderer.requestRender();
                        }
                        break;

                    case 'draw':
                        // Draw shape - fallback for tools without executeAction
                        // Note: Tool's onMouseDown/onMouseUp handle history
                        if (params.start && params.end) {
                            tool.onMouseDown({ button: 0 }, params.start[0], params.start[1]);
                            tool.onMouseMove({ button: 0 }, params.end[0], params.end[1]);
                            tool.onMouseUp({ button: 0 }, params.end[0], params.end[1]);
                            app.renderer.requestRender();
                        }
                        break;

                    default:
                        return { success: false, error: `Unknown action: ${action}` };
                }

                this.emitStateUpdate();
                return { success: true };
            } catch (e) {
                return { success: false, error: e.message };
            }
        },

        getImageData(layerId = null, documentId = null) {
            // Get image data as base64 for Python
            // documentId can be: null (active), "current" (active), index (number), name (string), or UUID
            const app = this.getState();
            if (!app?.documentManager) return { error: 'Editor not initialized' };

            try {
                // Resolve document
                let doc = null;
                if (documentId === null || documentId === undefined || documentId === 'current') {
                    // Use active document
                    doc = app.documentManager.getActiveDocument();
                } else if (typeof documentId === 'number') {
                    // Select by index
                    doc = app.documentManager.documents[documentId];
                } else if (typeof documentId === 'string') {
                    // Try by ID first, then by name
                    doc = app.documentManager.documents.find(d => d.id === documentId);
                    if (!doc) {
                        doc = app.documentManager.documents.find(d => d.name === documentId);
                    }
                }

                if (!doc) {
                    return { error: 'Document not found' };
                }

                const layerStack = doc.layerStack;
                if (!layerStack) {
                    return { error: 'Document has no layer stack' };
                }

                let canvas, width, height, layerInfo = {};
                const docWidth = doc.width;
                const docHeight = doc.height;

                if (layerId) {
                    // Get specific layer - can be ID, index, or name
                    let layer = null;
                    if (typeof layerId === 'number') {
                        layer = layerStack.layers[layerId];
                    } else if (typeof layerId === 'string') {
                        // Try by ID first, then by name
                        layer = layerStack.layers.find(l => l.id === layerId);
                        if (!layer) {
                            layer = layerStack.layers.find(l => l.name === layerId);
                        }
                    }

                    if (!layer) return { error: 'Layer not found' };
                    canvas = layer.canvas;
                    width = canvas.width;
                    height = canvas.height;
                    layerInfo = {
                        name: layer.name,
                        opacity: layer.opacity,
                        blend_mode: layer.blendMode,
                    };
                } else {
                    // Get flattened composite
                    canvas = document.createElement('canvas');
                    canvas.width = docWidth;
                    canvas.height = docHeight;
                    const ctx = canvas.getContext('2d');

                    // White background
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillRect(0, 0, docWidth, docHeight);

                    // Composite all visible layers (bottom to top, so iterate in reverse)
                    for (let i = layerStack.layers.length - 1; i >= 0; i--) {
                        const layer = layerStack.layers[i];
                        if (!layer.visible || layer.isGroup?.()) continue;
                        ctx.globalAlpha = layer.opacity;
                        ctx.drawImage(layer.canvas, layer.offsetX || 0, layer.offsetY || 0);
                    }
                    ctx.globalAlpha = 1.0;
                    width = docWidth;
                    height = docHeight;
                }

                // Get raw pixel data and encode as base64
                const ctx = canvas.getContext('2d');
                const imageData = ctx.getImageData(0, 0, width, height);
                const base64 = this.arrayBufferToBase64(imageData.data.buffer);

                return {
                    data: base64,
                    width: width,
                    height: height,
                    document_id: doc.id,
                    document_name: doc.name,
                    ...layerInfo,
                };
            } catch (e) {
                return { error: e.message };
            }
        },

        arrayBufferToBase64(buffer) {
            let binary = '';
            const bytes = new Uint8Array(buffer);
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        },

        /**
         * Push data to the upload endpoint for a pending request.
         * This is the push-based alternative to getImageData that avoids WebSocket payload limits.
         *
         * @param {string} requestId - Unique request ID for the upload endpoint
         * @param {string|number|null} layerId - Layer selector (ID, name, index, or null for composite)
         * @param {string|number|null} documentId - Document selector (ID, name, index, 'current', or null)
         * @param {string} format - Output format: 'webp', 'avif', 'png', 'svg', 'json'
         * @param {string|null} bg - Background color (e.g., '#FFFFFF') or null for transparent
         */
        async pushData(requestId, layerId = null, documentId = null, format = 'webp', bg = null) {
            const app = this.getState();
            if (!app?.documentManager) {
                console.error('pushData: Editor not initialized');
                return;
            }

            try {
                // Resolve document
                let doc = null;
                if (documentId === null || documentId === undefined || documentId === 'current') {
                    doc = app.documentManager.getActiveDocument();
                } else if (typeof documentId === 'number') {
                    doc = app.documentManager.documents[documentId];
                } else if (typeof documentId === 'string') {
                    doc = app.documentManager.documents.find(d => d.id === documentId);
                    if (!doc) {
                        doc = app.documentManager.documents.find(d => d.name === documentId);
                    }
                }

                if (!doc) {
                    console.error('pushData: Document not found');
                    return;
                }

                const layerStack = doc.layerStack;
                if (!layerStack) {
                    console.error('pushData: Document has no layer stack');
                    return;
                }

                // Resolve layer (if specified)
                let layer = null;
                let layerType = null;
                if (layerId !== null && layerId !== undefined) {
                    if (typeof layerId === 'number') {
                        layer = layerStack.layers[layerId];
                    } else if (typeof layerId === 'string') {
                        layer = layerStack.layers.find(l => l.id === layerId);
                        if (!layer) {
                            layer = layerStack.layers.find(l => l.name === layerId);
                        }
                    }
                    if (!layer) {
                        console.error('pushData: Layer not found');
                        return;
                    }
                    // Determine layer type
                    if (layer.shapes !== undefined) {
                        layerType = 'vector';
                    } else if (layer.runs !== undefined || layer.textContent !== undefined) {
                        layerType = 'text';
                    } else if (layer.isGroup?.()) {
                        layerType = 'group';
                    } else {
                        layerType = 'raster';
                    }
                }

                // Prepare data based on format and layer type
                let blob, contentType, metadata;
                const docWidth = doc.width;
                const docHeight = doc.height;

                if (format === 'json' && layer && layerType === 'vector') {
                    // Export vector layer as JSON
                    const jsonData = JSON.stringify({
                        type: 'vector',
                        shapes: layer.shapes || [],
                        width: layer.canvas?.width || docWidth,
                        height: layer.canvas?.height || docHeight,
                        offsetX: layer.offsetX || 0,
                        offsetY: layer.offsetY || 0,
                    });
                    blob = new Blob([jsonData], { type: 'application/json' });
                    contentType = 'application/json';
                    metadata = {
                        width: layer.canvas?.width || docWidth,
                        height: layer.canvas?.height || docHeight,
                        layerType: 'vector',
                        dataType: 'vector-json',
                    };
                } else if (format === 'svg' && layer && layerType === 'vector') {
                    // Export vector layer as SVG
                    const svgContent = this._layerToSVG(layer, docWidth, docHeight);
                    blob = new Blob([svgContent], { type: 'image/svg+xml' });
                    contentType = 'image/svg+xml';
                    metadata = {
                        width: docWidth,
                        height: docHeight,
                        layerType: 'vector',
                        dataType: 'svg',
                    };
                } else {
                    // Render to canvas and export as image
                    let canvas;
                    if (layer) {
                        // Single layer - render with effects if present
                        if (layer.hasEffects && layer.hasEffects() && window.effectRenderer) {
                            const rendered = window.effectRenderer.getRenderedLayer(layer);
                            if (rendered) {
                                // Create canvas large enough for effects (shadows etc expand bounds)
                                canvas = document.createElement('canvas');
                                canvas.width = rendered.contentCanvas.width;
                                canvas.height = rendered.contentCanvas.height;
                                const ctx = canvas.getContext('2d');

                                // Draw behind effects (shadows, outer glow)
                                if (rendered.behindCanvas) {
                                    ctx.drawImage(rendered.behindCanvas, 0, 0);
                                }
                                // Draw content + stroke
                                ctx.drawImage(rendered.contentCanvas, 0, 0);

                                metadata = {
                                    width: canvas.width,
                                    height: canvas.height,
                                    layerType: layerType,
                                    dataType: 'image',
                                    offsetX: rendered.offsetX,
                                    offsetY: rendered.offsetY,
                                };
                            } else {
                                canvas = layer.canvas;
                                metadata = {
                                    width: canvas.width,
                                    height: canvas.height,
                                    layerType: layerType,
                                    dataType: 'image',
                                };
                            }
                        } else {
                            canvas = layer.canvas;
                            metadata = {
                                width: canvas.width,
                                height: canvas.height,
                                layerType: layerType,
                                dataType: 'image',
                            };
                        }
                    } else {
                        // Composite all visible layers with effects
                        canvas = document.createElement('canvas');
                        canvas.width = docWidth;
                        canvas.height = docHeight;
                        const ctx = canvas.getContext('2d');

                        // Optional background color (transparent by default)
                        if (bg) {
                            ctx.fillStyle = bg;
                            ctx.fillRect(0, 0, docWidth, docHeight);
                        }

                        // Composite all visible layers (bottom to top) with effects
                        for (let i = layerStack.layers.length - 1; i >= 0; i--) {
                            const l = layerStack.layers[i];
                            if (!l.visible || l.isGroup?.()) continue;

                            // Check for layer effects
                            if (l.hasEffects && l.hasEffects() && window.effectRenderer) {
                                const rendered = window.effectRenderer.getRenderedLayer(l);
                                if (rendered) {
                                    // Draw behind effects (shadows, outer glow)
                                    if (rendered.behindCanvas) {
                                        ctx.globalAlpha = l.opacity;
                                        ctx.drawImage(rendered.behindCanvas, rendered.offsetX, rendered.offsetY);
                                    }
                                    // Draw content + stroke
                                    ctx.globalAlpha = l.opacity;
                                    ctx.drawImage(rendered.contentCanvas, rendered.offsetX, rendered.offsetY);
                                } else {
                                    ctx.globalAlpha = l.opacity;
                                    ctx.drawImage(l.canvas, l.offsetX || 0, l.offsetY || 0);
                                }
                            } else {
                                ctx.globalAlpha = l.opacity;
                                ctx.drawImage(l.canvas, l.offsetX || 0, l.offsetY || 0);
                            }
                        }
                        ctx.globalAlpha = 1.0;
                        metadata = {
                            width: docWidth,
                            height: docHeight,
                            layerType: null,
                            dataType: 'image',
                        };
                    }

                    // Convert to requested format
                    const mimeType = format === 'avif' ? 'image/avif' :
                                     format === 'png' ? 'image/png' : 'image/webp';
                    const quality = format === 'png' ? undefined : 0.9;

                    blob = await new Promise(resolve => {
                        canvas.toBlob(resolve, mimeType, quality);
                    });

                    if (!blob) {
                        // Fallback to PNG if format not supported
                        blob = await new Promise(resolve => {
                            canvas.toBlob(resolve, 'image/png');
                        });
                        contentType = 'image/png';
                    } else {
                        contentType = mimeType;
                    }
                }

                // POST to upload endpoint
                const uploadUrl = `${this.$props.apiBase}/upload/${requestId}`;
                const headers = {
                    'Content-Type': contentType,
                    'X-Width': String(metadata.width),
                    'X-Height': String(metadata.height),
                    'X-Document-Id': doc.id,
                    'X-Document-Name': doc.name,
                    'X-Data-Type': metadata.dataType,
                };

                if (layer) {
                    headers['X-Layer-Id'] = layer.id;
                    headers['X-Layer-Name'] = layer.name;
                    headers['X-Layer-Type'] = layerType;
                }

                const response = await fetch(uploadUrl, {
                    method: 'POST',
                    headers: headers,
                    body: blob,
                });

                if (!response.ok) {
                    console.error('pushData: Upload failed', response.status, await response.text());
                }
            } catch (e) {
                console.error('pushData: Error', e);
            }
        },

        /**
         * Convert a vector layer to SVG string.
         * @private
         */
        _layerToSVG(layer, docWidth, docHeight) {
            const shapes = layer.shapes || [];
            let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${docWidth}" height="${docHeight}" viewBox="0 0 ${docWidth} ${docHeight}">`;

            for (const shape of shapes) {
                svgContent += this._shapeToSVGElement(shape);
            }

            svgContent += '</svg>';
            return svgContent;
        },

        /**
         * Convert a shape object to SVG element string.
         * @private
         */
        _shapeToSVGElement(shape) {
            const fill = shape.fill || 'none';
            const stroke = shape.stroke || 'none';
            const strokeWidth = shape.strokeWidth || 1;

            switch (shape.type) {
                case 'rect':
                    return `<rect x="${shape.x}" y="${shape.y}" width="${shape.width}" height="${shape.height}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'ellipse':
                    const cx = shape.cx || (shape.x + shape.width / 2);
                    const cy = shape.cy || (shape.y + shape.height / 2);
                    const rx = shape.rx || (shape.width / 2);
                    const ry = shape.ry || (shape.height / 2);
                    return `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'circle':
                    return `<circle cx="${shape.cx}" cy="${shape.cy}" r="${shape.r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'line':
                    return `<line x1="${shape.x1}" y1="${shape.y1}" x2="${shape.x2}" y2="${shape.y2}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'polygon':
                    const points = (shape.points || []).map(p => `${p.x},${p.y}`).join(' ');
                    return `<polygon points="${points}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'path':
                    return `<path d="${shape.d || ''}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                default:
                    return '';
            }
        },

        async exportDocument() {
            // Export the full document as JSON for cross-platform transfer
            const app = this.getState();
            if (!app) return { error: 'Editor not initialized' };

            try {
                const activeDoc = app.documentManager?.getActiveDocument();
                if (!activeDoc) {
                    return { error: 'No active document' };
                }

                // Serialize the document
                const serialized = await activeDoc.serialize();

                // Add format version
                serialized.version = '1.0';

                return { document: serialized };
            } catch (e) {
                return { error: e.message };
            }
        },

        async importDocument(documentData) {
            // Import a full document from JSON
            const app = this.getState();
            if (!app) return { error: 'Editor not initialized' };

            try {
                if (!documentData || !documentData.layers) {
                    return { error: 'Invalid document format' };
                }

                // Import document using Document.deserialize
                const eventBus = app.eventBus;
                const importedDoc = await Document.deserialize(documentData, eventBus);

                // Add to document manager
                if (app.documentManager) {
                    // Close current document and add imported one
                    const currentDocId = app.documentManager.activeDocumentId;
                    app.documentManager.documents.set(importedDoc.id, importedDoc);
                    app.documentManager.switchToDocument(importedDoc.id);

                    // Update Vue state
                    this.docWidth = importedDoc.width;
                    this.docHeight = importedDoc.height;
                    this.updateDocumentTabs();
                }

                // Update renderer
                app.layerStack = importedDoc.layerStack;
                app.renderer.layerStack = importedDoc.layerStack;
                app.renderer.resize(importedDoc.width, importedDoc.height);
                app.renderer.fitToViewport();
                app.renderer.requestRender();

                // Update layers panel
                this.updateLayerList();

                return { success: true, documentId: importedDoc.id };
            } catch (e) {
                return { error: e.message };
            }
        },

        getConfig(path) {
            // Get UIConfig value(s) for API access
            try {
                if (path) {
                    // Get specific path
                    return UIConfig.get(path);
                } else {
                    // Return full config (deep clone to avoid mutation)
                    return JSON.parse(JSON.stringify(UIConfig.config));
                }
            } catch (e) {
                return { error: e.message };
            }
        },

        setConfig(path, value) {
            // Set UIConfig value for API access
            try {
                UIConfig.set(path, value);

                // Re-render vector layers if rendering settings changed
                if (path.startsWith('rendering.')) {
                    this.reRenderVectorLayers();
                }

                return { success: true, path, value };
            } catch (e) {
                return { error: e.message };
            }
        },

        // Layer Effects API Methods

        getLayerEffects(layerId) {
            // Get all effects for a layer
            const app = this.getState();
            if (!app) return [];

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return [];

                return layer.effects.map(e => e.serialize());
            } catch (e) {
                console.error('getLayerEffects error:', e);
                return [];
            }
        },

        addLayerEffect(layerId, effectType, params = {}) {
            // Add an effect to a layer
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return { success: false, error: 'Layer not found' };

                // Get effect class from registry via window.LayerEffects
                const LayerEffects = window.LayerEffects;
                const EffectClass = LayerEffects?.effectRegistry?.[effectType];
                if (!EffectClass) {
                    return { success: false, error: `Unknown effect type: ${effectType}` };
                }

                // Create effect instance
                const effect = new EffectClass(params);

                // Add to layer
                layer.addEffect(effect);

                // Trigger re-render
                app.renderer.requestRender();
                this.updateLayerList();

                return { success: true, effect_id: effect.id, effect: effect.serialize() };
            } catch (e) {
                console.error('addLayerEffect error:', e);
                return { success: false, error: e.message };
            }
        },

        updateLayerEffect(layerId, effectId, params = {}) {
            // Update an effect's parameters
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return { success: false, error: 'Layer not found' };

                const effect = layer.getEffect(effectId);
                if (!effect) return { success: false, error: 'Effect not found' };

                // Update parameters
                layer.updateEffect(effectId, params);

                // Trigger re-render
                app.renderer.requestRender();

                return { success: true, effect: effect.serialize() };
            } catch (e) {
                console.error('updateLayerEffect error:', e);
                return { success: false, error: e.message };
            }
        },

        removeLayerEffect(layerId, effectId) {
            // Remove an effect from a layer
            const app = this.getState();
            if (!app) return { success: false, error: 'Editor not initialized' };

            try {
                const layer = app.layerStack.layers.find(l => l.id === layerId);
                if (!layer) return { success: false, error: 'Layer not found' };

                const removed = layer.removeEffect(effectId);
                if (!removed) return { success: false, error: 'Effect not found' };

                // Trigger re-render
                app.renderer.requestRender();
                this.updateLayerList();

                return { success: true };
            } catch (e) {
                console.error('removeLayerEffect error:', e);
                return { success: false, error: e.message };
            }
        },
    },
};
