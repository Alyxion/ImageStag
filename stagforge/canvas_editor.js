/**
 * Slopstag Canvas Editor - NiceGUI Vue Component
 *
 * This Vue component provides the UI shell for the image editor.
 * It imports the core modules and initializes the editor in mounted().
 */

// Import all editor mixins (using absolute path for NiceGUI static serving)
import { allMixins } from '/static/js/editor/mixins/index.js';

// Store editor state outside Vue's reactivity (like Three.js pattern)
const editorState = new WeakMap();

export default {
    template: `
        <div class="editor-root" ref="root" :data-theme="currentTheme" :data-mode="currentUIMode"
            @dragover.prevent="onFileDragOver"
            @dragleave="onFileDragLeave"
            @drop.prevent="onFileDrop">

            <!-- ==================== TABLET MODE UI ==================== -->
            <template v-if="currentUIMode === 'tablet'">
                <!-- Tablet Top Bar - Icon buttons with labels -->
                <div class="tablet-top-bar">
                    <!-- Tools button -->
                    <button class="tablet-icon-btn" @click="tabletLeftDrawerOpen = !tabletLeftDrawerOpen; savePanelState()"
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
                    <div class="tablet-dock-panel tablet-tool-dock" v-if="tabletLeftDrawerOpen">
                        <div class="tablet-panel-content tablet-tool-panel-content">
                            <div class="tablet-tool-groups">
                                <div class="tablet-tool-group" v-for="group in filteredToolGroups" :key="group.id">
                                    <button
                                        class="tablet-tool-group-btn"
                                        :class="{ active: isToolGroupActive(group) }"
                                        @click="selectToolFromGroup(group)"
                                        @pointerdown="startToolLongPress($event, group)"
                                        @pointerup="cancelToolLongPress"
                                        @pointerleave="cancelToolLongPress"
                                        :title="getActiveToolInGroup(group).name">
                                        <span class="tablet-tool-icon" v-html="getToolIcon(getActiveToolInGroup(group).icon)"></span>
                                        <span class="tablet-tool-group-indicator" v-if="group.tools.length > 1">&#9662;</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <button class="tablet-dock-icon" v-if="!tabletLeftDrawerOpen" @click="tabletLeftDrawerOpen = true; savePanelState()">
                        <span v-html="getToolIcon('tools')"></span>
                    </button>
                </div>

                <!-- Tool group flyout (fixed position, outside scroll container) -->
                <div class="tablet-tool-flyout" v-if="tabletExpandedToolGroup"
                    :style="{ top: tabletFlyoutPos.y + 'px', left: tabletFlyoutPos.x + 'px' }"
                    @click.stop>
                    <button v-for="tool in tabletExpandedToolGroupData.tools" :key="tool.id"
                        class="tablet-flyout-btn"
                        :class="{ active: currentToolId === tool.id }"
                        @click="selectToolFromFlyout(tabletExpandedToolGroupData, tool); tabletExpandedToolGroup = null">
                        <span class="tablet-flyout-icon" v-html="getToolIcon(tool.icon)"></span>
                        <span class="tablet-flyout-name">{{ tool.name }}</span>
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
                                    <div class="tablet-layer-icon" v-if="layer.isGroup" v-html="getToolIcon('folder-group')"></div>
                                    <canvas v-else class="tablet-layer-thumb" :ref="'layerThumb_' + layer.id" width="40" height="40"></canvas>
                                    <div class="tablet-layer-info">
                                        <div class="tablet-layer-name">{{ layer.name }}</div>
                                        <div class="tablet-layer-opacity">{{ Math.round(layer.opacity * 100) }}%</div>
                                    </div>
                                    <button class="tablet-layer-visibility" :class="{ visible: layer.visible }"
                                        @click.stop="toggleLayerVisibility(layer.id)"
                                        v-html="getToolIcon(layer.visible ? 'eye' : 'eye-off')">
                                    </button>
                                    <button class="tablet-layer-menu-btn" @click.stop="showLayerContextMenuTouch($event, layer)"
                                        v-html="getToolIcon('dots-vertical')">
                                    </button>
                                </div>
                            </div>
                            <div class="tablet-layer-actions">
                                <button class="tablet-btn tablet-btn-primary" @click.stop="showAddLayerMenuPopup($event)">+ New</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="duplicateLayer">Dup</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="deleteLayer">Del</button>
                                <button class="tablet-btn tablet-btn-secondary" @click="mergeDown">Merge</button>
                            </div>

                            <!-- Add Layer Menu (Tablet) -->
                            <div v-if="showAddLayerMenu" class="add-layer-menu context-menu"
                                 :style="addLayerMenuPosition"
                                 @click.stop>
                                <div class="menu-item" @click="addPixelLayer">New Pixel Layer</div>
                                <div class="menu-item" @click="addVectorLayer">New Vector Layer</div>
                                <div class="menu-separator"></div>
                                <div class="menu-item" @click="showLibraryDialog">
                                    From Library...
                                </div>
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
                                <div class="tablet-filter-name">{{ f.name }} <span class="filter-source-icon" :title="f.source === 'wasm' ? 'Runs locally' : 'Requires server'">{{ f.source === 'wasm' ? '⚡' : '☁' }}</span></div>
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
                    <button class="tablet-menu-item" @click="tabletMenuAction('new_from_clipboard')">New from Clipboard</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('open')">Open... (Ctrl+O)</button>
                    <div class="tablet-menu-divider"></div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('save')">Save (Ctrl+S)</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('saveAs')">Save As... (Ctrl+Shift+S)</button>
                    <div class="tablet-menu-divider"></div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('export_as')">Export As...</button>
                    <button class="tablet-menu-item" :disabled="!hasLastExport" @click="tabletMenuAction('export_again')">Export Again</button>
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
                    <div class="tablet-menu-subheader">Size</div>
                    <button class="tablet-menu-item" @click="tabletMenuAction('resize')">Resize...</button>
                    <button class="tablet-menu-item" @click="tabletMenuAction('canvas_size')">Canvas Size...</button>
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
                        <div class="toolbar-menu" v-if="showMenuBar">
                            <button class="toolbar-menu-btn" @click="showFileMenu"><span class="menu-btn-icon" v-html="getToolIcon('file')"></span> File</button>
                            <button class="toolbar-menu-btn" @click="showEditMenu"><span class="menu-btn-icon" v-html="getToolIcon('edit')"></span> Edit</button>
                            <button class="toolbar-menu-btn" @click="showViewMenu"><span class="menu-btn-icon" v-html="getToolIcon('view')"></span> View</button>
                            <button class="toolbar-menu-btn" @click="showFilterMenu"><span class="menu-btn-icon" v-html="getToolIcon('filter')"></span> Filter</button>
                            <button class="toolbar-menu-btn" @click="showSelectMenu"><span class="menu-btn-icon" v-html="getToolIcon('selection')"></span> Select</button>
                            <button class="toolbar-menu-btn" @click="showImageMenu"><span class="menu-btn-icon" v-html="getToolIcon('image')"></span> Image</button>
                            <button class="toolbar-menu-btn" @click="showLayerMenu"><span class="menu-btn-icon" v-html="getToolIcon('layers')"></span> Layer</button>
                        </div>
                    </div>
                    <div class="toolbar-center">
                        <!-- Spacer for layout balance -->
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
                        <template v-else-if="prop.type === 'toggle'">
                            <button class="toggle-btn" :class="{ active: prop.value }"
                                    :title="prop.hint || prop.name"
                                    @click="updateToolProperty(prop.id, !prop.value)">
                                <span v-if="prop.icon === 'link'" class="toggle-icon">&#128279;</span>
                                <span v-else class="toggle-icon">&#9679;</span>
                            </button>
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
                        <div class="tool-group" v-for="group in filteredToolGroups" :key="group.id"
                            @mouseenter="showToolFlyout($event, group)"
                            @mouseleave="scheduleCloseFlyout">
                            <button
                                class="tool-button"
                                :class="{ active: isToolGroupActive(group) }"
                                :title="getActiveToolInGroup(group).name + (group.shortcut ? ' (' + group.shortcut.toUpperCase() + ', Shift+' + group.shortcut.toUpperCase() + ' to cycle)' : '')"
                                @click="selectToolFromGroup(group)">
                                <span class="tool-icon" v-html="getToolIcon(getActiveToolInGroup(group).icon)"></span>
                            </button>
                            <span class="tool-group-indicator" v-if="group.tools.length > 1">&#9662;</span>
                        </div>
                        <!-- Desktop tool group flyout (fixed, outside overflow context) -->
                        <div class="tool-flyout" v-if="activeToolFlyout"
                            :style="{ top: desktopFlyoutPos.y + 'px', left: desktopFlyoutPos.x + 'px' }"
                            @mouseenter="cancelCloseFlyout"
                            @mouseleave="scheduleCloseFlyout">
                            <button
                                v-for="tool in desktopFlyoutTools"
                                :key="tool.id"
                                class="flyout-tool-btn"
                                :class="{ active: currentToolId === tool.id }"
                                :title="tool.name"
                                @click="selectToolFromFlyout(desktopFlyoutGroup, tool)">
                                <span class="flyout-icon" v-html="getToolIcon(tool.icon)"></span>
                                <span class="flyout-name">{{ tool.name }}</span>
                            </button>
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
                <div class="right-panel" v-show="currentUIMode === 'desktop' && shouldShowRightPanel">
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
                                    v-html="getToolIcon(layer.visible ? 'eye' : 'eye-off')">
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
                                <div class="layer-group-icon" v-else title="Layer Group" v-html="getToolIcon('folder-group')">
                                </div>
                                <div class="layer-info">
                                    <span class="layer-name">{{ layer.name }}</span>
                                    <span class="layer-meta">
                                        <span class="layer-type-icon group" v-if="layer.isGroup" title="Group">G</span>
                                        <span class="layer-type-icon text" v-else-if="layer.isText" title="Text Layer">T</span>
                                        <span class="layer-type-icon svg" v-else-if="layer.isSVG" title="SVG Layer">S</span>
                                        <span class="layer-type-icon vector" v-else-if="layer.isVector" title="Vector Layer">V</span>
                                        <span class="layer-type-icon raster" v-else title="Pixel Layer">P</span>
                                        <span v-if="layer.locked" class="layer-locked" v-html="getToolIcon('lock-closed')"></span>
                                    </span>
                                </div>
                                <button class="layer-menu-btn" @click.stop="showLayerContextMenuTouch($event, layer)" title="Layer menu"
                                    v-html="getToolIcon('dots-vertical')">
                                </button>
                            </div>
                        </div>
                        <div class="layer-buttons">
                            <button @click.stop="showAddLayerMenuPopup($event)" title="Add layer" v-html="getToolIcon('plus')"></button>
                            <button @click="createGroup" title="Create group (Ctrl+G)" v-html="getToolIcon('folder-group')"></button>
                            <button @click="deleteLayer" title="Delete layer" v-html="getToolIcon('trash')"></button>
                        </div>

                        <!-- Add Layer Menu -->
                        <div v-if="showAddLayerMenu" class="add-layer-menu context-menu"
                             :style="addLayerMenuPosition"
                             @click.stop>
                            <div class="menu-item" @click="addPixelLayer">New Pixel Layer</div>
                            <div class="menu-item" @click="addVectorLayer">New Vector Layer</div>
                            <div class="menu-separator"></div>
                            <div class="menu-item" @click="showLibraryDialog">
                                From Library...
                            </div>
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
            <div class="status-bar" v-show="currentUIMode === 'desktop' && showBottomBar">
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
                    <span class="status-backend"
                          :class="backendStatusClass"
                          style="cursor:pointer"
                          @contextmenu.prevent.stop="showBackendMenu($event)">
                        {{ backendStatusText }}
                    </span>
                </span>
            </div>

            <!-- Backend mode context menu -->
            <div v-if="showBackendContextMenu" class="backend-context-menu"
                 :style="{ left: backendMenuX + 'px', top: backendMenuY + 'px' }">
                <div v-for="m in backendModes" :key="m.id"
                     class="backend-menu-item"
                     :class="{ active: m.id === currentBackendMode }"
                     @click.stop="switchBackendMode(m.id)">
                    <span class="backend-menu-check">{{ m.id === currentBackendMode ? '\u2713' : '' }}</span>
                    <span>{{ m.label }}</span>
                    <span class="backend-menu-desc">{{ m.desc }}</span>
                </div>
            </div>

            <!-- Dropdown menus -->
            <div v-if="activeMenu" class="toolbar-dropdown" :style="menuPosition" @click.stop>
                <template v-if="activeMenu === 'file'">
                    <div class="menu-item" @click="menuAction('new')"><span class="menu-icon" v-html="getToolIcon('plus')"></span> New...</div>
                    <div class="menu-item" @click="menuAction('new_from_clipboard')"><span class="menu-icon" v-html="getToolIcon('paste')"></span> New from Clipboard</div>
                    <div class="menu-item" @click="menuAction('open')"><span class="menu-icon" v-html="getToolIcon('open')"></span> Open... (Ctrl+O)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('save')"><span class="menu-icon" v-html="getToolIcon('save')"></span> Save (Ctrl+S)</div>
                    <div class="menu-item" @click="menuAction('saveAs')"><span class="menu-icon" v-html="getToolIcon('save')"></span> Save As... (Ctrl+Shift+S)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('export_as')"><span class="menu-icon" v-html="getToolIcon('export')"></span> Export As...</div>
                    <div class="menu-item" :class="{ disabled: !hasLastExport }" @click="hasLastExport && menuAction('export_again')"><span class="menu-icon" v-html="getToolIcon('export')"></span> Export Again</div>
                </template>
                <template v-else-if="activeMenu === 'edit'">
                    <div class="menu-item" :class="{ disabled: !canUndo }" @click="canUndo && menuAction('undo')">
                        <span class="menu-icon" v-html="getToolIcon('undo')"></span> Undo{{ lastUndoAction ? ' ' + lastUndoAction : '' }} (Ctrl+Z)
                    </div>
                    <div class="menu-item" :class="{ disabled: !canRedo }" @click="canRedo && menuAction('redo')">
                        <span class="menu-icon" v-html="getToolIcon('redo')"></span> Redo{{ lastRedoAction ? ' ' + lastRedoAction : '' }} (Ctrl+Y)
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('cut')"><span class="menu-icon" v-html="getToolIcon('cut')"></span> Cut (Ctrl+X)</div>
                    <div class="menu-item" @click="menuAction('copy')"><span class="menu-icon" v-html="getToolIcon('copy')"></span> Copy (Ctrl+C)</div>
                    <div class="menu-item" @click="menuAction('copy_merged')"><span class="menu-icon" v-html="getToolIcon('copy')"></span> Copy Merged (Ctrl+Shift+C)</div>
                    <div class="menu-item" @click="menuAction('paste')"><span class="menu-icon" v-html="getToolIcon('paste')"></span> Paste (Ctrl+V)</div>
                    <div class="menu-item" @click="menuAction('paste_in_place')"><span class="menu-icon" v-html="getToolIcon('paste')"></span> Paste in Place (Ctrl+Shift+V)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('select_all')"><span class="menu-icon" v-html="getToolIcon('selection')"></span> Select All (Ctrl+A)</div>
                    <div class="menu-item" @click="menuAction('deselect')"><span class="menu-icon" v-html="getToolIcon('deselect')"></span> Deselect (Ctrl+D)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="showPreferencesDialog"><span class="menu-icon" v-html="getToolIcon('settings')"></span> Preferences...</div>
                </template>
                <template v-else-if="activeMenu === 'view'">
                    <div class="menu-header">Panels</div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showToolPanel')">
                        <span class="menu-check" v-html="showToolPanel ? getToolIcon('check') : ''"></span>
                        Tools
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showRibbon')">
                        <span class="menu-check" v-html="showRibbon ? getToolIcon('check') : ''"></span>
                        Tool Options (Ribbon)
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showRightPanel')">
                        <span class="menu-check" v-html="showRightPanel ? getToolIcon('check') : ''"></span>
                        Right Panel
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showNavigator')">
                        <span class="menu-check" v-html="showNavigator ? getToolIcon('check') : ''"></span>
                        Navigator
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showLayers')">
                        <span class="menu-check" v-html="showLayers ? getToolIcon('check') : ''"></span>
                        Layers
                    </div>
                    <div class="menu-item menu-checkbox" @click="toggleViewOption('showHistory')">
                        <span class="menu-check" v-html="showHistory ? getToolIcon('check') : ''"></span>
                        History
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">Theme</div>
                    <div class="menu-item menu-checkbox" @click="setTheme('dark')">
                        <span class="menu-check" v-html="currentTheme === 'dark' ? getToolIcon('check') : ''"></span>
                        Dark Theme
                    </div>
                    <div class="menu-item menu-checkbox" @click="setTheme('light')">
                        <span class="menu-check" v-html="currentTheme === 'light' ? getToolIcon('check') : ''"></span>
                        Light Theme
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">UI Mode</div>
                    <div class="menu-item menu-checkbox" @click="setUIMode('desktop')">
                        <span class="menu-check" v-html="currentUIMode === 'desktop' ? getToolIcon('check') : ''"></span>
                        Desktop Mode
                    </div>
                    <div class="menu-item menu-checkbox" @click="setUIMode('tablet')">
                        <span class="menu-check" v-html="currentUIMode === 'tablet' ? getToolIcon('check') : ''"></span>
                        Tablet Mode
                    </div>
                    <div class="menu-item menu-checkbox" @click="setUIMode('limited')">
                        <span class="menu-check" v-html="currentUIMode === 'limited' ? getToolIcon('check') : ''"></span>
                        Limited Mode
                    </div>
                    <div class="menu-separator"></div>
                    <div class="menu-header">Zoom</div>
                    <div class="menu-item" @click="menuAction('zoom_in')"><span class="menu-icon" v-html="getToolIcon('zoom-in')"></span> Zoom In (Ctrl++)</div>
                    <div class="menu-item" @click="menuAction('zoom_out')"><span class="menu-icon" v-html="getToolIcon('zoom-out')"></span> Zoom Out (Ctrl+-)</div>
                    <div class="menu-item" @click="menuAction('zoom_fit')"><span class="menu-icon" v-html="getToolIcon('view')"></span> Fit to Window</div>
                    <div class="menu-item" @click="menuAction('zoom_100')"><span class="menu-icon" v-html="getToolIcon('view')"></span> Actual Pixels (100%)</div>
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
                <template v-else-if="activeMenu === 'select'">
                    <div class="menu-item" @click="menuAction('select_all')"><span class="menu-icon" v-html="getToolIcon('selection')"></span> Select All (Ctrl+A)</div>
                    <div class="menu-item" :class="{ disabled: !hasSelection }" @click="hasSelection && menuAction('deselect')"><span class="menu-icon" v-html="getToolIcon('deselect')"></span> Deselect (Ctrl+D)</div>
                    <div class="menu-item" :class="{ disabled: !hasPreviousSelection }" @click="hasPreviousSelection && menuAction('reselect')"><span class="menu-icon" v-html="getToolIcon('selection')"></span> Reselect (Ctrl+Shift+D)</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('invert_selection')"><span class="menu-icon" v-html="getToolIcon('invert')"></span> Inverse (Ctrl+Shift+I)</div>
                </template>
                <template v-else-if="activeMenu === 'image'">
                    <div class="menu-item" @click="menuAction('resize')"><span class="menu-icon" v-html="getToolIcon('resize')"></span> Resize...</div>
                    <div class="menu-item" @click="menuAction('canvas_size')"><span class="menu-icon" v-html="getToolIcon('crop')"></span> Canvas Size...</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="menuAction('flatten')"><span class="menu-icon" v-html="getToolIcon('layers')"></span> Flatten Image</div>
                </template>
                <template v-else-if="activeMenu === 'layer'">
                    <div class="menu-item" @click="menuAction('transform')"><span class="menu-icon" v-html="getToolIcon('resize')"></span> Transform...</div>
                    <div class="menu-item" @click="menuAction('reset_transform')"><span class="menu-icon" v-html="getToolIcon('undo')"></span> Reset Transform</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="duplicateLayer()"><span class="menu-icon" v-html="getToolIcon('copy')"></span> Duplicate Layer</div>
                    <div class="menu-item" @click="deleteLayer()"><span class="menu-icon" v-html="getToolIcon('trash')"></span> Delete Layer</div>
                    <div class="menu-separator"></div>
                    <div class="menu-item" @click="mergeDown()"><span class="menu-icon" v-html="getToolIcon('merge')"></span> Merge Down</div>
                    <div class="menu-item" @click="rasterizeActiveLayer()"><span class="menu-icon" v-html="getToolIcon('grid')"></span> Rasterize</div>
                </template>
            </div>

            <!-- Filter submenu -->
            <div v-if="activeSubmenu" class="toolbar-dropdown filter-submenu" :style="submenuPosition"
                 @mouseenter="cancelSubmenuClose" @mouseleave="closeSubmenuDelayed" @click.stop>
                <div class="menu-item" v-for="f in filtersByCategory[activeSubmenu]" :key="f.id"
                     @click="openFilterDialog(f)">
                    {{ f.name }}
                    <span v-if="f.params && f.params.length > 0" class="has-params">...</span>
                    <span class="filter-source-icon" :title="f.source === 'wasm' ? 'Runs locally' : 'Requires server'">{{ f.source === 'wasm' ? '⚡' : '☁' }}</span>
                </div>
            </div>

            <!-- Filter Dialog -->
            <div v-if="filterDialogVisible" class="filter-dialog-overlay filter-dialog-overlay--transparent">
                <div class="filter-dialog filter-dialog--corner" @click.stop>
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
                        <div class="pref-section">
                            <h4>Filter Execution</h4>
                            <div class="pref-row">
                                <label>Run filters via:</label>
                                <select v-model="prefFilterExecMode">
                                    <option value="js">Browser (local)</option>
                                    <option value="server">Server (Python)</option>
                                </select>
                                <span class="pref-hint">Browser runs filters locally; Server requires backend connection</span>
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

            <!-- Library Dialog -->
            <div v-if="libraryDialogOpen" class="filter-dialog-overlay" @click="closeLibraryDialog">
                <div class="library-dialog" @click.stop>
                    <div class="library-dialog-header">
                        <span class="library-dialog-title">Insert from Library</span>
                        <button class="filter-dialog-close" @click="closeLibraryDialog">&times;</button>
                    </div>
                    <div class="library-dialog-body">
                        <div v-if="libraryLoading" class="library-dialog-loading">
                            Loading library...
                        </div>
                        <template v-else-if="libraryItems.length === 0">
                            <div class="library-dialog-empty">No items available</div>
                        </template>
                        <template v-else>
                            <div class="library-dialog-categories">
                                <div v-for="category in libraryCategories" :key="category"
                                     class="library-category-item"
                                     :class="{ active: category === librarySelectedCategory }"
                                     @click="selectLibraryCategory(category)">
                                    {{ category }}
                                </div>
                            </div>
                            <div class="library-dialog-items">
                                <div v-for="item in filteredLibraryItems" :key="item.id"
                                     class="library-dialog-item"
                                     @click="addLayerFromLibrary(item)">
                                    <div class="library-item-icon">
                                        <span v-if="item.type === 'svg'">&#128444;</span>
                                        <span v-else>&#128247;</span>
                                    </div>
                                    <div class="library-item-name">{{ item.name }}</div>
                                </div>
                            </div>
                        </template>
                    </div>
                    <div class="library-dialog-footer">
                        <button class="btn-cancel" @click="closeLibraryDialog">Cancel</button>
                    </div>
                </div>
            </div>

            <!-- New Document Dialog -->
            <div v-if="newDocDialogVisible" class="filter-dialog-overlay" @click="newDocDialogVisible = false">
                <div class="filter-dialog new-doc-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">New Document</span>
                        <button class="filter-dialog-close" @click="newDocDialogVisible = false">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <!-- Preset dropdown -->
                        <div class="new-doc-field">
                            <label>Preset</label>
                            <select v-model="newDocPreset" @change="applyNewDocPreset(newDocPreset)" class="new-doc-select">
                                <option value="vga">VGA (640×480)</option>
                                <option value="hd">HD 720p (1280×720)</option>
                                <option value="fhd">Full HD 1080p (1920×1080)</option>
                                <option value="qhd">QHD 1440p (2560×1440)</option>
                                <option value="4k">4K UHD (3840×2160)</option>
                                <option value="a4_72">A4 @72 DPI (595×842)</option>
                                <option value="a4_150">A4 @150 DPI (1240×1754)</option>
                                <option value="a4_300">A4 @300 DPI (2480×3508)</option>
                                <option value="letter_300">US Letter @300 DPI (2550×3300)</option>
                                <option value="custom">Custom</option>
                            </select>
                        </div>

                        <!-- Width/Height/DPI inputs in a row -->
                        <div class="new-doc-dimensions">
                            <div class="new-doc-field">
                                <label>Width</label>
                                <div class="new-doc-input-row">
                                    <input type="number" v-model.number="newDocWidth" min="1" max="8000" @input="onNewDocDimensionChange" class="param-number-input">
                                    <span class="new-doc-unit">px</span>
                                </div>
                            </div>
                            <div class="new-doc-field">
                                <label>Height</label>
                                <div class="new-doc-input-row">
                                    <input type="number" v-model.number="newDocHeight" min="1" max="8000" @input="onNewDocDimensionChange" class="param-number-input">
                                    <span class="new-doc-unit">px</span>
                                </div>
                            </div>
                            <div class="new-doc-field">
                                <label>DPI</label>
                                <div class="new-doc-input-row">
                                    <input type="number" v-model.number="newDocDpi" min="1" max="1200" @input="onNewDocDimensionChange" class="param-number-input new-doc-dpi-input">
                                </div>
                            </div>
                        </div>

                        <!-- Real size preview -->
                        <div class="new-doc-size-preview">
                            Print size: {{ getNewDocSizeInMeters().width }} × {{ getNewDocSizeInMeters().height }}
                        </div>

                        <!-- Background options with preview -->
                        <div class="new-doc-field new-doc-bg-field">
                            <label>Background</label>
                            <div class="new-doc-bg-row">
                                <!-- Clickable color preview on the left -->
                                <div class="new-doc-bg-preview-box"
                                     :class="{ 'bg-checkerboard': newDocBackground === 'none' }"
                                     :style="newDocBackground !== 'none' ? { background: getNewDocBgPreviewColor() } : {}"
                                     @click="openNewDocColorPicker"
                                     title="Click to pick custom color"></div>
                                <div class="new-doc-bg-options">
                                    <button class="new-doc-bg-btn" :class="{ active: newDocBackground === 'none' }" @click="newDocBackground = 'none'" title="Transparent">
                                        <span class="bg-preview bg-checkerboard"></span>
                                    </button>
                                    <button class="new-doc-bg-btn" :class="{ active: newDocBackground === 'white' }" @click="newDocBackground = 'white'" title="White">
                                        <span class="bg-preview" style="background: #fff"></span>
                                    </button>
                                    <button class="new-doc-bg-btn" :class="{ active: newDocBackground === 'black' }" @click="newDocBackground = 'black'" title="Black">
                                        <span class="bg-preview" style="background: #000"></span>
                                    </button>
                                    <button class="new-doc-bg-btn" :class="{ active: newDocBackground === 'gray' }" @click="newDocBackground = 'gray'" title="Gray">
                                        <span class="bg-preview" style="background: #808080"></span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="filter-dialog-footer">
                        <div></div>
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="newDocDialogVisible = false">Cancel</button>
                            <button class="btn-apply" @click="createNewDocument">Create</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Color Picker Popup (top-level overlay) -->
            <div v-if="newDocColorPickerOpen" class="new-doc-color-picker-overlay" @click="closeNewDocColorPicker">
                <div class="new-doc-color-picker-popup" @click.stop>
                    <input type="color" :value="getNewDocBgInputColor()" @input="onNewDocBgColorChange" class="new-doc-color-input">
                    <button class="new-doc-color-picker-close" @click="closeNewDocColorPicker">&times;</button>
                </div>
            </div>

            <!-- Resize Dialog -->
            <div v-if="resizeDialogVisible" class="filter-dialog-overlay" @click="resizeDialogVisible = false">
                <div class="filter-dialog resize-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">Resize Image</span>
                        <button class="filter-dialog-close" @click="resizeDialogVisible = false">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <div class="resize-fields">
                            <div class="resize-field">
                                <label>Width</label>
                                <input type="number" min="1" max="8000" v-model.number="resizeWidth" @input="onResizeWidthChange" class="param-number-input resize-input">
                                <span class="resize-unit">px</span>
                            </div>
                            <div class="resize-lock-row">
                                <button class="resize-lock-btn" :class="{ active: resizeLockAspect }" @click="resizeLockAspect = !resizeLockAspect" :title="resizeLockAspect ? 'Unlock aspect ratio' : 'Lock aspect ratio'">
                                    <span v-if="resizeLockAspect">&#x1F512;</span>
                                    <span v-else>&#x1F513;</span>
                                </button>
                            </div>
                            <div class="resize-field">
                                <label>Height</label>
                                <input type="number" min="1" max="8000" v-model.number="resizeHeight" @input="onResizeHeightChange" class="param-number-input resize-input">
                                <span class="resize-unit">px</span>
                            </div>
                        </div>
                    </div>
                    <div class="filter-dialog-footer">
                        <div></div>
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="resizeDialogVisible = false">Cancel</button>
                            <button class="btn-apply" @click="applyResize">Apply</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Export Dialog -->
            <div v-if="exportDialogVisible" class="filter-dialog-overlay" @click="exportDialogVisible = false">
                <div class="filter-dialog export-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">Export As</span>
                        <button class="filter-dialog-close" @click="exportDialogVisible = false">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <div class="export-field">
                            <label>Filename</label>
                            <input type="text" v-model="exportFilename" class="export-text-input">
                        </div>
                        <div class="export-field">
                            <label>Format</label>
                            <select v-model="exportFormat" @change="onExportFormatChange" class="export-select">
                                <option v-for="fmt in exportFormats" :key="fmt.id" :value="fmt.id">{{ fmt.label }} (.{{ fmt.extension }})</option>
                            </select>
                        </div>
                        <div class="export-field" v-if="currentExportFormat && currentExportFormat.supportsTransparency">
                            <label class="export-checkbox">
                                <input type="checkbox" v-model="exportTransparent">
                                Transparent background
                            </label>
                        </div>
                        <template v-if="currentExportFormat">
                            <div class="export-field" v-for="opt in currentExportFormat.options" :key="opt.id">
                                <template v-if="opt.type === 'range'">
                                    <label>{{ opt.label }}</label>
                                    <div class="param-range-row">
                                        <input type="range" :min="opt.min" :max="opt.max" :step="opt.step"
                                            v-model.number="exportOptions[opt.id]">
                                        <input type="number" class="param-number-input"
                                            :min="opt.min" :max="opt.max" :step="opt.step"
                                            v-model.number="exportOptions[opt.id]">
                                        <span v-if="opt.unit" class="resize-unit">{{ opt.unit }}</span>
                                    </div>
                                </template>
                                <template v-else-if="opt.type === 'select'">
                                    <label>{{ opt.label }}</label>
                                    <select v-model="exportOptions[opt.id]" class="export-select">
                                        <option v-for="ch in opt.choices" :key="ch.value" :value="ch.value">{{ ch.label }}</option>
                                    </select>
                                </template>
                                <template v-else-if="opt.type === 'checkbox'">
                                    <label class="export-checkbox">
                                        <input type="checkbox" v-model="exportOptions[opt.id]">
                                        {{ opt.label }}
                                    </label>
                                </template>
                            </div>
                        </template>
                    </div>
                    <div class="filter-dialog-footer">
                        <div></div>
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="exportDialogVisible = false">Cancel</button>
                            <button class="btn-apply" @click="doExport">Export</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Canvas Size Dialog -->
            <div v-if="canvasSizeDialogVisible" class="filter-dialog-overlay" @click="canvasSizeDialogVisible = false">
                <div class="filter-dialog canvas-size-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">Canvas Size</span>
                        <button class="filter-dialog-close" @click="canvasSizeDialogVisible = false">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <div class="resize-fields">
                            <div class="resize-field">
                                <label>Width</label>
                                <input type="number" min="1" max="8000" v-model.number="canvasNewWidth" class="param-number-input resize-input">
                                <span class="resize-unit">px</span>
                            </div>
                            <div class="resize-field">
                                <label>Height</label>
                                <input type="number" min="1" max="8000" v-model.number="canvasNewHeight" class="param-number-input resize-input">
                                <span class="resize-unit">px</span>
                            </div>
                        </div>
                        <div class="anchor-section">
                            <label class="anchor-label">Anchor</label>
                            <div class="anchor-grid">
                                <button v-for="i in 9" :key="i - 1"
                                    class="anchor-cell"
                                    :class="{ active: canvasAnchor === (i - 1) }"
                                    @click="canvasAnchor = i - 1"
                                    :title="['Top Left','Top Center','Top Right','Middle Left','Center','Middle Right','Bottom Left','Bottom Center','Bottom Right'][i - 1]">
                                    <span class="anchor-dot"></span>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="filter-dialog-footer">
                        <div></div>
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="canvasSizeDialogVisible = false">Cancel</button>
                            <button class="btn-apply" @click="applyCanvasSize">Apply</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Layer Transform Dialog -->
            <div v-if="transformDialogVisible" class="filter-dialog-overlay" @click="transformDialogVisible = false">
                <div class="filter-dialog transform-dialog" @click.stop>
                    <div class="filter-dialog-header">
                        <span class="filter-dialog-title">Layer Transform</span>
                        <button class="filter-dialog-close" @click="transformDialogVisible = false">&times;</button>
                    </div>
                    <div class="filter-dialog-body">
                        <div class="transform-fields">
                            <div class="transform-field">
                                <label>Rotation</label>
                                <div class="transform-input-row">
                                    <input type="range" min="-180" max="180" step="1" v-model.number="transformRotation" class="transform-slider">
                                    <input type="number" min="-360" max="360" step="1" v-model.number="transformRotation" class="param-number-input transform-input">
                                    <span class="resize-unit">°</span>
                                </div>
                            </div>
                            <div class="transform-field">
                                <label>Scale X</label>
                                <div class="transform-input-row">
                                    <input type="range" min="10" max="200" step="1" v-model.number="transformScaleX" @input="onTransformScaleXChange" class="transform-slider">
                                    <input type="number" min="1" max="1000" step="1" v-model.number="transformScaleX" @input="onTransformScaleXChange" class="param-number-input transform-input">
                                    <span class="resize-unit">%</span>
                                </div>
                            </div>
                            <div class="transform-lock-row">
                                <button class="resize-lock-btn" :class="{ active: transformLockAspect }" @click="transformLockAspect = !transformLockAspect" :title="transformLockAspect ? 'Unlock aspect ratio' : 'Lock aspect ratio'">
                                    <span v-if="transformLockAspect">&#x1F512;</span>
                                    <span v-else>&#x1F513;</span>
                                </button>
                            </div>
                            <div class="transform-field">
                                <label>Scale Y</label>
                                <div class="transform-input-row">
                                    <input type="range" min="10" max="200" step="1" v-model.number="transformScaleY" @input="onTransformScaleYChange" class="transform-slider">
                                    <input type="number" min="1" max="1000" step="1" v-model.number="transformScaleY" @input="onTransformScaleYChange" class="param-number-input transform-input">
                                    <span class="resize-unit">%</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="filter-dialog-footer">
                        <button class="btn-reset" @click="transformRotation = 0; transformScaleX = 100; transformScaleY = 100;">Reset</button>
                        <div class="filter-dialog-buttons">
                            <button class="btn-cancel" @click="transformDialogVisible = false">Cancel</button>
                            <button class="btn-apply" @click="applyTransform">Apply</button>
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
        isolated: { type: Boolean, default: false },
        empty: { type: Boolean, default: false },
        // UI visibility config - these are initial values, internal state can be toggled
        configShowMenu: { type: Boolean, default: true },
        configShowNavigator: { type: Boolean, default: true },
        configShowLayers: { type: Boolean, default: true },
        configShowToolProperties: { type: Boolean, default: true },
        configShowBottomBar: { type: Boolean, default: true },
        configShowHistory: { type: Boolean, default: true },
        configShowToolbar: { type: Boolean, default: true },
        configShowDocumentTabs: { type: Boolean, default: true },
        // Tool category filtering - array of group IDs to show (null = all)
        // Groups: selection, freeform, quicksel, move, crop, hand, brush, eraser,
        //         stamp, retouch, dodge, pen, shapes, fill, text, eyedropper, misc
        visibleToolGroups: { type: Array, default: null },
        // Tool category filtering - array of group IDs to hide
        hiddenToolGroups: { type: Array, default: () => [] },
        backendMode: { type: String, default: 'on' },
    },

    mixins: allMixins,

    created() {
        // Initialize view options from config props
        console.log('[Stagforge] created() - configShowNavigator:', this.configShowNavigator);
        console.log('[Stagforge] created() - configShowLayers:', this.configShowLayers);
        console.log('[Stagforge] created() - configShowHistory:', this.configShowHistory);
        console.log('[Stagforge] created() - configShowToolProperties:', this.configShowToolProperties);

        this.showMenuBar = this.configShowMenu;
        this.showNavigator = this.configShowNavigator;
        this.showLayers = this.configShowLayers;
        this.showRibbon = this.configShowToolProperties;  // Tool properties = ribbon
        this.showBottomBar = this.configShowBottomBar;
        this.showHistory = this.configShowHistory;
        this.showToolPanel = this.configShowToolbar;  // Toolbar = tool panel
        this.showDocumentTabs = this.configShowDocumentTabs;
        this.currentBackendMode = this.backendMode || 'on';

        console.log('[Stagforge] created() - after assignment:');
        console.log('[Stagforge]   showNavigator:', this.showNavigator);
        console.log('[Stagforge]   showLayers:', this.showLayers);
        console.log('[Stagforge]   showHistory:', this.showHistory);
        console.log('[Stagforge]   showRibbon:', this.showRibbon);
    },

    computed: {
        /**
         * Whether the right panel should be visible.
         * Only show if at least one child panel is visible.
         */
        shouldShowRightPanel() {
            return this.showRightPanel && (this.showNavigator || this.showLayers || this.showHistory);
        },

        backendStatusText() {
            if (this.currentBackendMode === 'off') return 'Disabled';
            if (this.currentBackendMode === 'offline') return 'Offline';
            return this.backendConnected ? 'Backend' : 'Offline';
        },

        backendStatusClass() {
            if (this.currentBackendMode === 'off') return 'disabled';
            if (this.currentBackendMode === 'offline') return 'disconnected';
            return this.backendConnected ? 'connected' : 'disconnected';
        },

        /**
         * Filter tool groups based on visibility props
         */
        filteredToolGroups() {
            if (!this.toolGroups) return [];
            return this.toolGroups.filter(group => {
                // If visibleToolGroups is set, only show those groups
                if (this.visibleToolGroups !== null) {
                    return this.visibleToolGroups.includes(group.id);
                }
                // Otherwise, hide groups in hiddenToolGroups
                return !this.hiddenToolGroups.includes(group.id);
            });
        },
        tabletExpandedToolGroupData() {
            if (!this.tabletExpandedToolGroup || !this.toolGroups) return { tools: [] };
            return this.toolGroups.find(g => g.id === this.tabletExpandedToolGroup) || { tools: [] };
        },
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
        groupedLibraryItems() {
            // Group library items by category for the add layer menu
            const grouped = {};
            for (const item of this.libraryItems) {
                if (!grouped[item.category]) {
                    grouped[item.category] = [];
                }
                grouped[item.category].push(item);
            }
            return grouped;
        },
        libraryCategories() {
            // Get unique categories from library items
            return [...new Set(this.libraryItems.map(i => i.category))];
        },
        filteredLibraryItems() {
            // Filter library items by selected category
            if (!this.librarySelectedCategory) return [];
            return this.libraryItems.filter(i => i.category === this.librarySelectedCategory);
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
            tabletLeftDrawerOpen: true,      // Tools panel open
            tabletExpandedToolGroup: null,  // Currently expanded tool group in tablet panel
            tabletFlyoutPos: { x: 0, y: 0 }, // Fixed position for tool flyout
            desktopFlyoutPos: { x: 0, y: 0 }, // Fixed position for desktop tool flyout
            desktopFlyoutGroup: null, // Current desktop flyout group object
            desktopFlyoutTools: [], // Tools in current desktop flyout group

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
            tabletAllTools: [],              // Populated from tools/index.js in initEditor()

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

            // View options (can be initialized from configShow* props)
            showMenuBar: true,
            showToolPanel: true,
            showToolbar: true,
            showRibbon: true,
            showRightPanel: true,
            showNavigator: true,
            showLayers: true,
            showHistory: true,
            showSources: false,
            showBottomBar: true,

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

            // Selection
            hasSelection: false,
            hasPreviousSelection: false,

            // Add layer menu
            showAddLayerMenu: false,
            addLayerMenuPosition: { left: '0px', bottom: '0px' },
            showLibrarySubmenu: false,  // Deprecated, kept for compatibility
            libraryItems: [],
            libraryLoading: false,
            // Library dialog
            libraryDialogOpen: false,
            librarySelectedCategory: null,

            // Status
            coordsX: 0,
            coordsY: 0,
            isPointerActive: false,  // True when pointer (mouse/touch) is over canvas
            statusMessage: 'Ready',
            backendConnected: false,
            currentBackendMode: 'on',
            showBackendContextMenu: false,
            backendMenuX: 0,
            backendMenuY: 0,
            backendModes: [
                { id: 'on', label: 'Connected', desc: 'Full backend' },
                { id: 'offline', label: 'Offline', desc: 'No server filters' },
                { id: 'off', label: 'Disabled', desc: 'No connection' },
            ],
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
            prefFilterExecMode: 'js',

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

        // Start heartbeat to keep session alive (every 5 seconds)
        // Session will be cleaned up if no heartbeat received for 6 seconds
        this._heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, 5000);
    },

    beforeUnmount() {
        // Stop heartbeat when component unmounts
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }

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

        showBackendMenu(e) {
            this.backendMenuX = e.clientX;
            this.backendMenuY = e.clientY;
            this.showBackendContextMenu = true;
            // Position above the click point after render
            this.$nextTick(() => {
                const menu = this.$el.querySelector('.backend-context-menu');
                if (menu) {
                    const rect = menu.getBoundingClientRect();
                    // Move above and left so it doesn't go off-screen
                    let x = e.clientX - rect.width;
                    let y = e.clientY - rect.height;
                    if (x < 0) x = e.clientX;
                    if (y < 0) y = e.clientY;
                    this.backendMenuX = x;
                    this.backendMenuY = y;
                }
            });
            // Dismiss on next click anywhere
            const dismiss = (ev) => {
                if (!ev.target.closest('.backend-context-menu')) {
                    this.showBackendContextMenu = false;
                }
                document.removeEventListener('mousedown', dismiss);
            };
            setTimeout(() => document.addEventListener('mousedown', dismiss), 0);
        },

        switchBackendMode(newMode) {
            this.showBackendContextMenu = false;
            const oldMode = this.currentBackendMode;
            if (newMode === oldMode) return;

            this.currentBackendMode = newMode;
            const app = this.getState();
            if (app) app.backendMode = newMode;

            console.log(`[Editor] Backend mode: ${oldMode} -> ${newMode}`);

            if (newMode === 'off' || newMode === 'offline') {
                // Clear backend filters and connector
                if (app?.pluginManager) {
                    app.pluginManager.backendFilters.clear();
                    app.pluginManager.imageSources.clear();
                    app.pluginManager.backendConnector = null;
                }
                this.backendConnected = false;
                this.filters = this.filters.filter(f => f.source === 'javascript' || f.source === 'wasm');
                if (app?.eventBus) {
                    app.eventBus.emit('backend:disconnected', { mode: newMode });
                }
            } else {
                // 'on' — reconnect
                if (app?.pluginManager) {
                    app.pluginManager.initialize().then(() => {
                        this.loadBackendData();
                    });
                }
            }
        },

        /**
         * Send heartbeat to keep session alive.
         * Sessions are cleaned up after 6 seconds without heartbeat.
         */
        sendHeartbeat() {
            const sessionId = this.$props.sessionId;
            if (!sessionId) return;

            fetch(`/api/sessions/${sessionId}/heartbeat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).then(response => {
                if (response.status === 404 && !this._sessionLostWarned) {
                    // Session lost (server restarted) - show reconnection message once
                    this._sessionLostWarned = true;
                    console.warn('Session lost - server may have restarted. Please reload the page.');
                    this.statusMessage = 'Session lost - reload page to reconnect';
                } else if (response.ok) {
                    // Session recovered (e.g., after re-registration)
                    this._sessionLostWarned = false;
                }
            }).catch(() => {
                // Network error - ignore (will retry on next heartbeat)
            });
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
            // Import core modules and tools
            const [
                { EventBus },
                { LayerStack },
                { Renderer },
                { History },
                { Clipboard },
                { ToolManager },
                { themeManager },
                { UIConfig },
                { registerAllTools, toolGroups: importedToolGroups, toolMetadata, getToolIcon: getToolIconFn },
                { BackendConnector },
                { PluginManager },
                { DocumentManager },
                { AutoSave },
                { TextLayer },
                { VectorLayer },
                { SVGLayer },
                { createShape },
                LayerEffectsModule,
                { FileManager },
                { SelectionManager },
            ] = await Promise.all([
                import('/static/js/utils/EventBus.js'),
                import('/static/js/core/LayerStack.js'),
                import('/static/js/core/Renderer.js'),
                import('/static/js/core/History.js'),
                import('/static/js/core/Clipboard.js'),
                import('/static/js/tools/ToolManager.js'),
                import('/static/js/config/ThemeManager.js'),
                import('/static/js/config/UIConfig.js'),
                import('/static/js/tools/index.js'),
                import('/static/js/plugins/BackendConnector.js'),
                import('/static/js/plugins/PluginManager.js'),
                import('/static/js/core/DocumentManager.js'),
                import('/static/js/core/AutoSave.js'),
                import('/static/js/core/TextLayer.js'),
                import('/static/js/core/VectorLayer.js'),
                import('/static/js/core/SVGLayer.js'),
                import('/static/js/core/VectorShape.js'),
                import('/static/js/core/LayerEffects.js'),
                import('/static/js/core/FileManager.js'),
                import('/static/js/core/SelectionManager.js'),
            ]);

            // Expose layer classes and shape factory to window for testing
            window.TextLayer = TextLayer;
            window.VectorLayer = VectorLayer;
            window.SVGLayer = SVGLayer;
            window.createVectorShape = createShape;
            window.createShape = createShape;  // Alias for testing
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
                selectionManager: null,
                toolManager: null,
                pluginManager: null,
                documentManager: null,
                fileManager: null,
                backendMode: this.backendMode,
            };

            // Initialize document manager first (but don't create documents yet)
            app.documentManager = new DocumentManager(app);

            // Create initial empty layer stack (will be replaced when document is created)
            app.layerStack = new LayerStack(this.docWidth, this.docHeight, eventBus);
            app.renderer = new Renderer(canvas, app.layerStack);
            app.renderer.resizeDisplay(displayWidth, displayHeight);  // Set up HiDPI canvas
            app.renderer.setApp(app);  // Enable tool overlay rendering
            app.renderer.setOnRender(() => this.markNavigatorDirty());  // Debounced navigator update on render
            app.history = new History(app);
            app.clipboard = new Clipboard(app);
            app.selectionManager = new SelectionManager(app);
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

            // Register all tools from tools/index.js
            registerAllTools(app.toolManager);

            // Set tool groups and metadata from auto-discovery
            this.toolGroups = importedToolGroups;
            this.tabletAllTools = toolMetadata;
            this._getToolIconFn = getToolIconFn;

            // Store state
            editorState.set(this, app);

            // Expose for testing (accessible via window.__stagforge_app__)
            window.__stagforge_app__ = app;
            window.sessionId = this.sessionId;  // Expose for testing

            // Initialize theme and UI configuration
            themeManager.init();
            UIConfig.init();
            this.currentTheme = themeManager.getTheme();
            // Sync UIConfig's stored mode with the active mode so setMode()
            // dedup check doesn't suppress future mode switches
            if (!window.__stagforgeUrlMode) {
                // No URL override — use UIConfig's saved mode
                const savedMode = UIConfig.get('mode');
                if (savedMode && savedMode !== this.currentUIMode) {
                    this.currentUIMode = savedMode;
                }
            }
            // Ensure UIConfig agrees with our current mode
            UIConfig.config.mode = this.currentUIMode;

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
            // In isolated mode, auto-save is disabled to prevent cross-session interference
            const isIsolated = this.isolated || window.__stagforge_config__?.isolated || false;
            app.autoSave = new AutoSave(app, {
                interval: 5000,
                disabled: isIsolated,
            });
            await app.autoSave.initialize();

            // Try to restore documents from previous session
            const restored = await app.autoSave.restoreDocuments();

            if (!restored) {
                // No documents restored, create initial document through DocumentManager
                // Check empty mode from props or config
                const isEmpty = this.empty || window.__stagforge_config__?.empty || false;
                app.documentManager.createDocument({
                    width: this.docWidth,
                    height: this.docHeight,
                    name: 'Untitled',
                    activate: true,
                    empty: isEmpty,
                });
            }

            // Update document tabs
            this.updateDocumentTabs();

            // Emit ready event for iframe embedding
            window.dispatchEvent(new CustomEvent('stagforge:ready', {
                detail: { sessionId: this.sessionId }
            }));

            // Connect to backend and load filters
            await app.pluginManager.initialize();

            // Populate filter list from all available sources (JS, WASM, backend)
            const allFilters = app.pluginManager.getAllFilters();
            if (allFilters.length > 0) {
                this.filters = allFilters;
            }

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

            // Tool change handler
            eventBus.on('tool:changed', (data) => {
                this.currentToolId = data.tool?.constructor.id || '';
                this.currentToolName = data.tool?.constructor.name || '';
                this.updateToolProperties(); this.updateToolHint(); this.updateBrushCursor();
                app.renderer.showLayerBounds = (this.currentToolId === 'move');
                app.renderer.requestRender();
                if (this.currentToolId === 'brush' && !this.brushPresetThumbnailsGenerated) this.generateBrushPresetThumbnails();
                if (this.currentUIMode === 'tablet') this.syncTabletToolProperties();
            });

            // Common layer update handler
            const onLayerChange = (render = true, nav = true) => {
                this.updateLayerList();
                // Use debounced preview updates instead of direct calls
                if (nav) this.markPreviewsDirty();  // Marks all layers + navigator dirty
                if (render) app.renderer.requestRender();
                this.emitStateUpdate();
            };

            // Layer events
            ['layer:added', 'layer:removed', 'layer:updated', 'layer:duplicated',
             'layer:merged', 'layer:flattened', 'layers:changed'].forEach(e => eventBus.on(e, () => onLayerChange()));
            eventBus.on('layer:moved', () => onLayerChange(true, false));
            eventBus.on('layers:restored', () => { onLayerChange(false, true); this.syncDocDimensions(); });
            eventBus.on('layer:selected', (data) => {
                this.activeLayerId = data.layer?.id;
                this.updateLayerControls();
                this.emitStateUpdate();
            });

            // Update history state when history changes
            eventBus.on('history:changed', (data) => {
                this.updateHistoryState();
                this.syncDocDimensions();
                this.emitStateUpdate();
                // Use debounced preview updates - marks active layer and navigator dirty
                // If data has affectedLayerId, only mark that layer; otherwise mark active layer
                const affectedLayerId = data?.affectedLayerId || app.layerStack?.getActiveLayer()?.id;
                this.markPreviewsDirty(affectedLayerId);
                // Invalidate layer image cache so auto-save captures current state
                if (app.layerStack) {
                    for (const layer of app.layerStack.layers) {
                        if (layer.invalidateImageCache) {
                            layer.invalidateImageCache();
                        }
                    }
                }
                // Hide "Saved" indicator when document is modified
                if (this.autoSaveStatus === 'saved') {
                    this.autoSaveStatus = 'idle';
                }
            });

            // Viewport and color events - use debounced navigator update
            eventBus.on('viewport:changed', () => this.markNavigatorDirty());
            eventBus.on('color:foreground-changed', (data) => { this.fgColor = data.color; });
            eventBus.on('color:background-changed', (data) => { this.bgColor = data.color; });

            // Selection events
            eventBus.on('selection:changed', (data) => {
                this.hasSelection = data.hasSelection;
                // Check if there's a previous selection available for Reselect
                this.hasPreviousSelection = !!(app.selectionManager?._previousMask);
            });
            eventBus.on('selection:cleared', () => {
                this.hasSelection = false;
                this.hasPreviousSelection = !!(app.selectionManager?._previousMask);
            });

            // Initial navigator update after mount
            setTimeout(() => this.forceUpdateNavigator(), 500);

            // Backend connection events
            eventBus.on('backend:connected', () => { this.backendConnected = true; this.loadBackendData(); });
            eventBus.on('backend:disconnected', () => { this.backendConnected = false; });

            // When WASM filters become available, add them to the filter list
            eventBus.on('wasm:ready', ({ filters }) => {
                const wasmList = Array.from(filters.values());
                // Merge: add WASM filters that aren't already present
                const existingIds = new Set(this.filters.map(f => f.id));
                for (const f of wasmList) {
                    if (!existingIds.has(f.id)) {
                        this.filters.push(f);
                    }
                }
            });

            // Auto-save events
            eventBus.on('autosave:saving', () => { this.autoSaveStatus = 'saving'; });
            eventBus.on('autosave:saved', (data) => {
                this.autoSaveStatus = 'saved';
                this.lastAutoSaveTime = data.timestamp;
                this.justSaved = true;
                setTimeout(() => { this.justSaved = false; }, 600);
            });

            // Document events
            ['documents:changed', 'document:modified'].forEach(e => eventBus.on(e, () => this.updateDocumentTabs()));
            eventBus.on('document:activated', () => {
                this.updateDocumentTabs(); this.updateLayerList(); this.updateHistoryState();
                // Force immediate updates on document switch (not debounced)
                this.forceUpdateNavigator(); this.forceUpdateAllThumbnails();
                this.zoom = app.renderer.zoom;
                this.syncDocDimensions();
            });
            eventBus.on('document:close-requested', (data) => this.showCloseDocumentDialog(data.document, data.callback));
            eventBus.on('documents:restored', (data) => {
                console.log(`[Editor] Restored ${data.count} document(s)`);
                this.updateDocumentTabs(); this.updateLayerList(); this.updateHistoryState();
                // Force immediate updates after restore (not debounced)
                this.forceUpdateNavigator(); this.forceUpdateAllThumbnails();
                this.zoom = app.renderer.zoom;
                this.syncDocDimensions();
                this.statusMessage = `Restored ${data.count} document(s)`;
            });

            // Load backend data after init (skip if backend disabled)
            if (this.currentBackendMode === 'on') {
                setTimeout(() => {
                    if (!this.backendConnected) this.loadBackendData().then(() => {
                        if (this.filters.length > 0) this.backendConnected = true;
                    });
                }, 1000);
            }

            this.statusMessage = 'Ready';
            this.updateHistoryState();

            // Emit initial state to Python
            this.emitStateUpdate();
        },

        // All other methods are provided by mixins - see mixins/index.js for full list
    },
};
