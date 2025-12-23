/**
 * FilterDesigner Vue Component
 *
 * A node-based visual editor for building ImageStag filter pipelines.
 * Wraps the Drawflow library for the graph editor functionality.
 */
export default {
    template: `
        <div class="filter-designer">
            <!-- Left Sidebar: Filter List -->
            <div class="fd-sidebar">
                <div class="fd-sidebar-header">
                    <span class="fd-icon">&#9881;</span>
                    <span>Filters</span>
                </div>
                <input
                    type="text"
                    class="fd-search"
                    placeholder="Search filters..."
                    v-model="searchQuery"
                />
                <div class="fd-filter-list">
                    <div v-for="category in filteredCategories" :key="category.name" class="fd-category">
                        <div class="fd-category-header" @click="toggleCategory(category.name)">
                            <span class="fd-expand-icon">{{ expandedCategories[category.name] ? '▼' : '▶' }}</span>
                            {{ category.name }}
                        </div>
                        <div v-if="expandedCategories[category.name]" class="fd-category-items">
                            <div
                                v-for="filter in category.filters"
                                :key="filter.name"
                                class="fd-filter-item"
                                draggable="true"
                                @dragstart="onDragStart($event, filter)"
                                @click="addFilterNode(filter.name)"
                            >
                                <div class="fd-filter-name">{{ filter.name }}</div>
                                <div class="fd-filter-desc">{{ filter.description }}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="fd-special-nodes">
                    <div class="fd-special-label">Special Nodes</div>
                    <button class="fd-btn fd-btn-source" @click="addSourceNode">Source</button>
                    <button class="fd-btn fd-btn-output" @click="addOutputNode">Output</button>
                    <button class="fd-btn fd-btn-blend" @click="addBlendNode">Blend</button>
                </div>
            </div>

            <!-- Center: Drawflow Canvas -->
            <div class="fd-canvas-container">
                <div class="fd-toolbar">
                    <button class="fd-toolbar-btn" @click="clearGraph" title="Clear all">🗑</button>
                    <button class="fd-toolbar-btn" @click="centerView" title="Center view">⊙</button>
                    <span class="fd-toolbar-hint">Drag filters from sidebar, connect nodes to build pipeline</span>
                    <button class="fd-toolbar-btn fd-btn-run" @click="executeGraph" title="Run">▶</button>
                </div>
                <div
                    ref="drawflowContainer"
                    class="fd-drawflow"
                    @drop="onDrop"
                    @dragover.prevent
                ></div>
            </div>

            <!-- Right Panel: Preview & Parameters -->
            <div class="fd-preview-panel">
                <div class="fd-preview-section">
                    <div class="fd-section-title">Node Preview</div>
                    <div class="fd-preview-scroll">
                        <img
                            v-if="outputImageSrc"
                            :src="outputImageSrc"
                            class="fd-preview-image"
                        />
                        <div v-else class="fd-preview-placeholder">No output</div>
                    </div>
                    <div class="fd-preview-info">{{ outputInfo }}</div>
                </div>
                <div class="fd-params-section">
                    <div class="fd-section-title">Node Parameters</div>
                    <div v-if="selectedNode" class="fd-params-content">
                        <div class="fd-param-header">{{ selectedNode.name }}</div>
                        <!-- Upload option for source nodes -->
                        <div v-if="selectedNode.type === 'source'" class="fd-upload-section">
                            <label class="fd-param-label">Upload Custom Image</label>
                            <input
                                type="file"
                                accept="image/*"
                                @change="handleFileUpload($event)"
                                class="fd-file-input"
                            />
                        </div>
                        <div v-for="param in selectedNode.params" :key="param.name" class="fd-param-row">
                            <label class="fd-param-label">{{ param.name }}</label>
                            <!-- Slider for numeric types -->
                            <template v-if="param.type === 'float' || param.type === 'int'">
                                <input
                                    type="range"
                                    :min="param.min"
                                    :max="param.max"
                                    :step="param.step"
                                    :value="param.value"
                                    @input="updateParam(param.name, $event.target.value)"
                                    class="fd-param-slider"
                                />
                                <span class="fd-param-value">{{ formatValue(param.value, param.type) }}</span>
                            </template>
                            <!-- Text input for string types -->
                            <template v-else-if="param.type === 'str'">
                                <input
                                    type="text"
                                    :value="param.value"
                                    @input="updateParam(param.name, $event.target.value)"
                                    class="fd-param-text"
                                />
                            </template>
                            <!-- Checkbox for boolean types -->
                            <template v-else-if="param.type === 'bool'">
                                <label class="fd-checkbox-label">
                                    <input
                                        type="checkbox"
                                        :checked="param.value"
                                        @change="updateParam(param.name, $event.target.checked)"
                                        class="fd-param-checkbox"
                                    />
                                    {{ param.value ? 'Yes' : 'No' }}
                                </label>
                            </template>
                            <!-- Select for select types -->
                            <template v-else-if="param.type === 'select'">
                                <select
                                    :value="param.value"
                                    @change="updateParam(param.name, $event.target.value)"
                                    class="fd-param-select"
                                >
                                    <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                                </select>
                            </template>
                        </div>
                    </div>
                    <div v-else class="fd-params-placeholder">Select a node to edit parameters</div>
                </div>
            </div>
        </div>
    `,

    props: {
        filters: { type: Array, default: () => [] },
        categories: { type: Array, default: () => [] },
        showSourceNode: { type: Boolean, default: true },
        showOutputNode: { type: Boolean, default: true },
        resource_path: { type: String, default: '' },
        sourceImages: { type: Array, default: () => [] },  // Available source images
        defaultSourceImage: { type: String, default: 'astronaut' },
    },

    data() {
        return {
            editor: null,
            searchQuery: '',
            expandedCategories: {},
            selectedNodeId: null,
            selectedNode: null,
            outputImageSrc: '',
            outputInfo: '',
            nodes: {},  // id -> { type, filterName, params }
            nextPosX: 350,
            nextPosY: 200,
            sourceCounter: 0,  // For unique source names
        };
    },

    computed: {
        filteredCategories() {
            const query = this.searchQuery.toLowerCase();
            if (!query) return this.categories;

            return this.categories.map(cat => ({
                ...cat,
                filters: cat.filters.filter(f =>
                    f.name.toLowerCase().includes(query) ||
                    (f.description && f.description.toLowerCase().includes(query))
                )
            })).filter(cat => cat.filters.length > 0);
        }
    },

    async mounted() {
        // Load CSS files
        this.loadStyles();

        // Initialize Drawflow (async - waits for library to load)
        await this.initDrawflow();

        // Expand first category by default
        if (this.categories.length > 0) {
            this.expandedCategories[this.categories[0].name] = true;
        }

        // Add default nodes after Drawflow is ready
        if (this.editor) {
            if (this.showSourceNode) {
                this.addSourceNode(100, 200);
            }
            if (this.showOutputNode) {
                this.addOutputNode(600, 200);
            }
        }
    },

    unmounted() {
        if (this.editor) {
            // Cleanup if needed
        }
    },

    methods: {
        loadStyles() {
            // Inject CSS directly to avoid file loading issues
            if (document.getElementById('filter-designer-styles')) return;

            const style = document.createElement('style');
            style.id = 'filter-designer-styles';
            style.textContent = `
                /* Drawflow base styles */
                .drawflow,.drawflow .parent-node{position:relative}
                .parent-drawflow{display:flex;overflow:hidden;touch-action:none;outline:0}
                .drawflow{width:100%;height:100%;user-select:none;perspective:0}
                .drawflow .drawflow-node{display:flex;align-items:center;position:absolute;background:#16213e;width:160px;min-height:40px;border-radius:8px;border:2px solid #0f3460;color:#e8e8e8;z-index:2;padding:15px;box-shadow:0 4px 6px rgba(0,0,0,0.3)}
                .drawflow .drawflow-node.selected{border-color:#e94560;box-shadow:0 0 15px rgba(233,69,96,0.4)}
                .drawflow .drawflow-node:hover{cursor:move}
                .drawflow .drawflow-node .inputs,.drawflow .drawflow-node .outputs{width:0}
                .drawflow .drawflow-node .drawflow_content_node{width:100%;display:block}
                .drawflow .drawflow-node .input,.drawflow .drawflow-node .output{position:relative;width:14px;height:14px;border-radius:50%;cursor:crosshair;z-index:1;margin-bottom:5px}
                .drawflow .drawflow-node .input{left:-27px;top:2px;background:#4fc3f7;border:2px solid #0288d1}
                .drawflow .drawflow-node .output{right:-3px;top:2px;background:#ffb74d;border:2px solid #f57c00}
                .drawflow .drawflow-node .input:hover{background:#81d4fa;border-color:#039be5}
                .drawflow .drawflow-node .output:hover{background:#ffcc80;border-color:#ff9800}
                .drawflow svg{z-index:0;position:absolute;overflow:visible!important}
                .drawflow .connection{position:absolute;pointer-events:none;aspect-ratio:1/1}
                .drawflow .connection .main-path{fill:none;stroke-width:3px;stroke:#e94560;pointer-events:all}
                .drawflow .connection .main-path:hover{stroke:#ff6b6b;stroke-width:4px;cursor:pointer}
                .drawflow .connection .main-path.selected{stroke:#43b993}
                .drawflow .connection .point{cursor:move;stroke:#000;stroke-width:2;fill:#fff;pointer-events:all}
                .drawflow-delete{position:absolute;display:block;width:30px;height:30px;background:#e94560;color:#fff;z-index:4;border:2px solid #fff;line-height:30px;font-weight:700;text-align:center;border-radius:50%;cursor:pointer}
                .parent-node .drawflow-delete{right:-15px;top:-15px}

                /* Component layout */
                .filter-designer{display:flex;width:100%;height:100%;background:#1a1a2e;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
                .fd-sidebar{width:220px;background:#f5f5f5;border-right:1px solid #ddd;display:flex;flex-direction:column;flex-shrink:0}
                .fd-sidebar-header{padding:12px 16px;background:white;border-bottom:1px solid #ddd;font-weight:600;font-size:16px;display:flex;align-items:center;gap:8px}
                .fd-icon{color:#2196f3}
                .fd-search{margin:8px;padding:8px 12px;border:1px solid #ddd;border-radius:4px;font-size:14px;outline:none}
                .fd-search:focus{border-color:#2196f3}
                .fd-filter-list{flex:1;overflow-y:auto;padding:8px}
                .fd-category{margin-bottom:4px}
                .fd-category-header{padding:8px 12px;background:white;border-radius:4px;cursor:pointer;font-weight:500;font-size:14px;display:flex;align-items:center;gap:8px}
                .fd-category-header:hover{background:#e3f2fd}
                .fd-expand-icon{font-size:10px;color:#666}
                .fd-category-items{padding-left:8px}
                .fd-filter-item{padding:8px 12px;margin:4px 0;background:white;border-radius:4px;cursor:grab;border-left:3px solid transparent;transition:all 0.15s}
                .fd-filter-item:hover{background:#e3f2fd;border-left-color:#2196f3;transform:translateX(2px)}
                .fd-filter-item:active{cursor:grabbing}
                .fd-filter-name{font-weight:500;font-size:13px;color:#333}
                .fd-filter-desc{font-size:11px;color:#666;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
                .fd-special-nodes{padding:12px;background:white;border-top:1px solid #ddd}
                .fd-special-label{font-size:11px;color:#666;margin-bottom:8px;text-transform:uppercase}
                .fd-btn{padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;font-weight:500;margin-right:4px;margin-bottom:4px}
                .fd-btn-source{background:#c8e6c9;color:#2e7d32}
                .fd-btn-output{background:#e1bee7;color:#7b1fa2}
                .fd-btn-blend{background:#ffe0b2;color:#e65100}
                .fd-btn:hover{opacity:0.85}
                .fd-canvas-container{flex:1;display:flex;flex-direction:column;min-width:0}
                .fd-toolbar{display:flex;align-items:center;padding:8px 12px;background:#16213e;border-bottom:1px solid #0f3460;gap:8px}
                .fd-toolbar-btn{background:transparent;border:none;color:#aaa;cursor:pointer;font-size:18px;padding:4px 8px;border-radius:4px}
                .fd-toolbar-btn:hover{background:rgba(255,255,255,0.1);color:white}
                .fd-btn-run{color:#4caf50}
                .fd-toolbar-hint{flex:1;color:#666;font-size:12px}
                .fd-drawflow{flex:1;background:#1a1a2e;background-image:linear-gradient(rgba(255,255,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px);background-size:20px 20px}
                .fd-preview-panel{width:280px;background:white;border-left:1px solid #ddd;display:flex;flex-direction:column;flex-shrink:0}
                .fd-section-title{font-weight:600;font-size:13px;padding:12px;border-bottom:1px solid #eee}
                .fd-preview-section{border-bottom:1px solid #ddd}
                .fd-preview-scroll{height:200px;overflow:auto;background:#f0f0f0;background-image:linear-gradient(45deg,#e0e0e0 25%,transparent 25%),linear-gradient(-45deg,#e0e0e0 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#e0e0e0 75%),linear-gradient(-45deg,transparent 75%,#e0e0e0 75%);background-size:16px 16px;background-position:0 0,0 8px,8px -8px,-8px 0px}
                .fd-preview-image{display:block}
                .fd-preview-placeholder{height:100%;display:flex;align-items:center;justify-content:center;color:#999;font-size:13px}
                .fd-preview-info{padding:8px 12px;font-size:11px;color:#666}
                .fd-params-section{flex:1;overflow-y:auto}
                .fd-params-content{padding:12px}
                .fd-param-header{font-weight:600;font-size:14px;margin-bottom:12px;color:#333}
                .fd-param-row{margin-bottom:12px}
                .fd-param-label{display:block;font-size:12px;color:#666;margin-bottom:4px}
                .fd-param-slider{width:calc(100% - 50px);vertical-align:middle}
                .fd-param-value{display:inline-block;width:45px;text-align:right;font-size:12px;color:#333;font-family:monospace}
                .fd-param-text{width:100%;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px}
                .fd-param-text:focus{border-color:#2196f3;outline:none}
                .fd-checkbox-label{display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer}
                .fd-param-checkbox{width:16px;height:16px;cursor:pointer}
                .fd-param-select{width:100%;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;background:white}
                .fd-upload-section{margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #eee}
                .fd-file-input{width:100%;padding:8px;border:2px dashed #ddd;border-radius:4px;font-size:11px;cursor:pointer;background:#fafafa}
                .fd-file-input:hover{border-color:#2196f3;background:#f0f7ff}
                .fd-params-placeholder{padding:20px;text-align:center;color:#999;font-size:13px}
                .fd-node-title{padding:8px 12px;font-weight:600;font-size:13px;border-radius:6px 6px 0 0;border-bottom:1px solid rgba(0,0,0,0.2)}
                .fd-node-source{background:#2d6a4f}
                .fd-node-output{background:#7b2cbf}
                .fd-node-filter{background:#0f3460}
                .fd-node-blend{background:#e65100}
                .fd-node-body{padding:8px 12px;font-size:11px;color:#aaa}
                .fd-port-labels{font-size:9px;color:#888;padding:2px 8px}
                .fd-input-labels{text-align:left}
                .fd-output-labels{text-align:right}
            `;
            document.head.appendChild(style);
        },

        loadDrawflow() {
            return new Promise((resolve) => {
                if (window.Drawflow) {
                    resolve();
                    return;
                }
                // Load Drawflow dynamically if not available
                const script = document.createElement('script');
                script.src = `${window.path_prefix || ''}${this.resource_path}/vendor/drawflow.min.js`;
                script.onload = () => resolve();
                script.onerror = () => {
                    console.error('Failed to load Drawflow from', script.src);
                    resolve(); // Continue anyway
                };
                document.head.appendChild(script);
            });
        },

        async initDrawflow() {
            await this.loadDrawflow();
            const container = this.$refs.drawflowContainer;
            console.log('initDrawflow called, container:', container, 'Drawflow:', window.Drawflow);
            if (!container) {
                console.error('Container not found');
                return;
            }
            if (!window.Drawflow) {
                console.error('Drawflow not loaded');
                return;
            }

            this.editor = new window.Drawflow(container);
            this.editor.reroute = true;
            this.editor.start();

            // Event handlers
            this.editor.on('nodeCreated', (id) => {
                this.$emit('node-created', { id: id, node: this.nodes[id] });
            });

            this.editor.on('nodeRemoved', (id) => {
                delete this.nodes[id];
                if (this.selectedNodeId === id) {
                    this.selectedNodeId = null;
                    this.selectedNode = null;
                }
                this.$emit('node-removed', { id: id });
                this.$emit('graph-changed', this.getGraphData());
            });

            this.editor.on('nodeSelected', (id) => {
                this.selectedNodeId = id;
                this.selectedNode = this.nodes[id] || null;
                this.$emit('node-selected', { id: id, node: this.nodes[id] });
            });

            this.editor.on('connectionCreated', (info) => {
                this.$emit('connection-created', info);
                this.$emit('graph-changed', this.getGraphData());
            });

            this.editor.on('connectionRemoved', (info) => {
                this.$emit('connection-removed', info);
                this.$emit('graph-changed', this.getGraphData());
            });
        },

        toggleCategory(name) {
            this.expandedCategories[name] = !this.expandedCategories[name];
        },

        onDragStart(event, filter) {
            event.dataTransfer.setData('filter', JSON.stringify(filter));
            event.dataTransfer.effectAllowed = 'copy';
        },

        onDrop(event) {
            event.preventDefault();
            const filterData = event.dataTransfer.getData('filter');
            if (filterData && this.editor) {
                const filter = JSON.parse(filterData);
                const rect = this.$refs.drawflowContainer.getBoundingClientRect();
                // Convert screen coordinates to Drawflow canvas coordinates
                const x = (event.clientX - rect.left) / this.editor.zoom - this.editor.canvas_x / this.editor.zoom;
                const y = (event.clientY - rect.top) / this.editor.zoom - this.editor.canvas_y / this.editor.zoom;
                this.addFilterNode(filter.name, x, y);
            }
        },

        addSourceNode(x, y, imageName) {
            const posX = x || this.nextPosX;
            const posY = y || this.nextPosY;

            this.sourceCounter++;
            const sourceId = this.sourceCounter === 1 ? 'A' : String.fromCharCode(64 + this.sourceCounter);
            const selectedImage = imageName || this.defaultSourceImage;

            const html = `
                <div class="fd-node-title fd-node-source">Source ${sourceId}</div>
                <div class="fd-node-body fd-source-body">${selectedImage}</div>
            `;

            const id = this.editor.addNode('source', 0, 1, posX, posY, 'source-node', {}, html);
            this.nodes[id] = {
                type: 'source',
                name: `Source ${sourceId}`,
                sourceId: sourceId,
                filterName: null,
                params: [
                    {
                        name: 'image',
                        type: 'select',
                        value: selectedImage,
                        options: this.sourceImages.length > 0 ? this.sourceImages : [selectedImage]
                    }
                ],
                inputPorts: [],
                outputPorts: [{ name: 'output' }]
            };

            this.advancePosition();
            this.$emit('graph-changed', this.getGraphData());
            return id;
        },

        addOutputNode(x, y) {
            const posX = x || this.nextPosX;
            const posY = y || this.nextPosY;

            const html = `
                <div class="fd-node-title fd-node-output">Output</div>
                <div class="fd-node-body">Result</div>
            `;

            const id = this.editor.addNode('output', 1, 0, posX, posY, 'output-node', {}, html);
            this.nodes[id] = {
                type: 'output',
                name: 'Output',
                filterName: null,
                params: [],
                inputPorts: [{ name: 'input' }],
                outputPorts: []
            };

            this.advancePosition();
            this.$emit('graph-changed', this.getGraphData());
            return id;
        },

        addBlendNode(x, y) {
            const posX = x || this.nextPosX;
            const posY = y || this.nextPosY;

            // Get Blend filter info from actual filter metadata
            const blendFilter = this.filters.find(f => f.name === 'Blend');
            const inputPorts = blendFilter?.inputs || [{ name: 'base' }, { name: 'overlay' }];
            const inputLabels = inputPorts.map(p => p.name).join(', ');

            const html = `
                <div class="fd-node-title fd-node-blend">Blend</div>
                <div class="fd-node-body">Combine images</div>
                <div class="fd-port-labels fd-input-labels">← ${inputLabels}</div>
            `;

            const id = this.editor.addNode('blend', inputPorts.length, 1, posX, posY, 'combiner-node', {}, html);

            // Build params from actual filter metadata
            const params = (blendFilter?.params || []).map(p => ({
                name: p.name,
                type: p.type,
                value: p.default,
                min: p.min || 0,
                max: p.max || 1,
                step: p.step || 0.05,
                options: p.options || []
            }));

            this.nodes[id] = {
                type: 'combiner',
                name: 'Blend',
                filterName: 'Blend',
                params: params,
                inputPorts: inputPorts,
                outputPorts: [{ name: 'output' }]
            };

            this.advancePosition();
            this.$emit('graph-changed', this.getGraphData());
        },

        addFilterNode(filterName, x, y) {
            const posX = x || this.nextPosX;
            const posY = y || this.nextPosY;

            // Find filter metadata
            const filter = this.filters.find(f => f.name === filterName);
            const desc = filter?.description?.substring(0, 25) || '';

            // Get port counts from filter metadata
            const inputPorts = filter?.inputs || [{ name: 'input' }];
            const outputPorts = filter?.outputs || [{ name: 'output' }];
            const numInputs = inputPorts.length;
            const numOutputs = outputPorts.length;

            // Build port labels for display
            const inputLabels = numInputs > 1 ? inputPorts.map(p => p.name).join(', ') : '';
            const outputLabels = numOutputs > 1 ? outputPorts.map(p => p.name).join(', ') : '';

            let portsHtml = '';
            if (inputLabels) portsHtml += `<div class="fd-port-labels fd-input-labels">← ${inputLabels}</div>`;
            if (outputLabels) portsHtml += `<div class="fd-port-labels fd-output-labels">${outputLabels} →</div>`;

            const html = `
                <div class="fd-node-title fd-node-filter">${filterName}</div>
                <div class="fd-node-body">${desc}</div>
                ${portsHtml}
            `;

            const id = this.editor.addNode(filterName.toLowerCase(), numInputs, numOutputs, posX, posY, 'filter-node', {}, html);

            // Build params from filter metadata
            const params = (filter?.params || []).map(p => ({
                name: p.name,
                type: p.type,
                value: p.default,
                min: p.min || 0,
                max: p.max || 10,
                step: p.step || (p.type === 'int' ? 1 : 0.1),
                options: p.options || []  // Include options for select types
            }));

            // Detect if this is a multi-input combiner filter
            const isCombiner = numInputs > 1 || ['Blend', 'Composite', 'MaskApply', 'SizeMatcher'].includes(filterName);

            this.nodes[id] = {
                type: isCombiner ? 'combiner' : 'filter',
                name: filterName,
                filterName: filterName,
                params: params,
                inputPorts: inputPorts,
                outputPorts: outputPorts
            };

            this.advancePosition();
            this.$emit('graph-changed', this.getGraphData());
            return id;
        },

        advancePosition() {
            this.nextPosX += 50;
            this.nextPosY += 30;
            if (this.nextPosX > 600) {
                this.nextPosX = 350;
                this.nextPosY = 200;
            }
        },

        updateParam(paramName, value) {
            if (!this.selectedNode) return;

            const param = this.selectedNode.params.find(p => p.name === paramName);
            if (param) {
                // Convert value based on type
                if (param.type === 'int') {
                    param.value = parseInt(value);
                } else if (param.type === 'float') {
                    param.value = parseFloat(value);
                } else if (param.type === 'bool') {
                    param.value = Boolean(value);
                } else {
                    param.value = value;  // string, select, etc.
                }

                // Update source node display when image changes
                if (this.selectedNode.type === 'source' && paramName === 'image') {
                    this.updateSourceNodeDisplay(this.selectedNodeId, value);
                }

                this.$emit('param-changed', {
                    nodeId: this.selectedNodeId,
                    param: paramName,
                    value: param.value
                });
                this.$emit('graph-changed', this.getGraphData());
            }
        },

        updateSourceNodeDisplay(nodeId, imageName) {
            // Update the node's HTML to show the new image name
            const nodeEl = document.querySelector(`#node-${nodeId} .fd-source-body`);
            if (nodeEl) {
                nodeEl.textContent = imageName;
            }
        },

        handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file || !this.selectedNode) return;

            const maxSize = 1024;  // Max dimension for upload

            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    // Resize if too large
                    let width = img.width;
                    let height = img.height;

                    if (width > maxSize || height > maxSize) {
                        if (width > height) {
                            height = Math.round(height * maxSize / width);
                            width = maxSize;
                        } else {
                            width = Math.round(width * maxSize / height);
                            height = maxSize;
                        }
                    }

                    // Draw to canvas and get resized data
                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);

                    const resizedData = canvas.toDataURL('image/jpeg', 0.85);

                    this.$emit('image-uploaded', {
                        nodeId: this.selectedNodeId,
                        fileName: file.name,
                        data: resizedData
                    });
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        },

        // Called from Python after upload is processed
        addUploadedImage(imageName) {
            // Add to source images list
            if (!this.sourceImages.includes(imageName)) {
                this.sourceImages.push(imageName);
            }
            // Update selected source node
            if (this.selectedNode && this.selectedNode.type === 'source') {
                const param = this.selectedNode.params.find(p => p.name === 'image');
                if (param) {
                    param.value = imageName;
                    if (!param.options.includes(imageName)) {
                        param.options.push(imageName);
                    }
                }
                this.updateSourceNodeDisplay(this.selectedNodeId, imageName);
                this.$emit('graph-changed', this.getGraphData());
            }
        },

        formatValue(value, type) {
            if (type === 'int') return Math.round(value);
            if (type === 'float') return value.toFixed(2);
            return value;
        },

        getGraphData() {
            if (!this.editor) return { nodes: {}, connections: [] };

            const exportData = this.editor.export();
            const connections = [];

            // Extract connections from Drawflow export
            if (exportData.drawflow?.Home?.data) {
                Object.entries(exportData.drawflow.Home.data).forEach(([nodeId, node]) => {
                    if (node.outputs) {
                        Object.entries(node.outputs).forEach(([outputKey, output]) => {
                            output.connections.forEach(conn => {
                                const fromOutputIdx = parseInt(outputKey.replace('output_', '')) - 1;
                                const toInputIdx = parseInt(conn.output.replace('input_', '')) - 1;

                                // Get port names from node metadata
                                const fromNode = this.nodes[nodeId];
                                const toNode = this.nodes[conn.node];
                                const fromPortName = fromNode?.outputPorts?.[fromOutputIdx]?.name || 'output';
                                const toPortName = toNode?.inputPorts?.[toInputIdx]?.name || 'input';

                                connections.push({
                                    from_node: nodeId,
                                    from_output: fromOutputIdx,
                                    from_port_name: fromPortName,
                                    to_node: conn.node,
                                    to_input: toInputIdx,
                                    to_port_name: toPortName
                                });
                            });
                        });
                    }
                });
            }

            return {
                nodes: this.nodes,
                connections: connections
            };
        },

        clearGraph() {
            if (this.editor) {
                this.editor.clear();
                this.nodes = {};
                this.selectedNodeId = null;
                this.selectedNode = null;
                this.nextPosX = 350;
                this.nextPosY = 200;
                this.sourceCounter = 0;  // Reset source counter

                // Re-add default nodes
                if (this.showSourceNode) {
                    this.addSourceNode(100, 200);
                }
                if (this.showOutputNode) {
                    this.addOutputNode(600, 200);
                }

                this.$emit('graph-changed', this.getGraphData());
            }
        },

        centerView() {
            if (this.editor) {
                this.editor.zoom_reset();
            }
        },

        executeGraph() {
            this.$emit('execute', this.getGraphData());
        },

        // Methods callable from Python
        setOutputImage(src, info) {
            this.outputImageSrc = src;
            this.outputInfo = info || '';
        },

        getExportData() {
            return this.getGraphData();
        },

        loadPreset(presetData) {
            // Load a preset graph configuration
            if (!this.editor || !presetData) return;

            // Clear current graph
            this.editor.clear();
            this.nodes = {};
            this.selectedNodeId = null;
            this.selectedNode = null;
            this.sourceCounter = 0;

            const nodes = presetData.nodes || {};
            const connections = presetData.connections || [];

            // First pass: create all nodes
            const nodeIdMap = {};  // Map old IDs to new IDs
            for (const [oldId, nodeData] of Object.entries(nodes)) {
                const posX = nodeData.pos_x || 200;
                const posY = nodeData.pos_y || 200;
                const nodeType = nodeData.type;
                const filterName = nodeData.filterName || nodeData.name;

                let newId;
                if (nodeType === 'source') {
                    // Get source image from params
                    const imageParam = nodeData.params?.find(p => p.name === 'image');
                    const imageName = imageParam?.value || 'astronaut';
                    newId = this.addSourceNode(posX, posY, imageName);
                } else if (nodeType === 'output') {
                    newId = this.addOutputNode(posX, posY);
                } else if (nodeType === 'combiner' || nodeType === 'filter') {
                    // Use addFilterNode for both
                    newId = this.addFilterNode(filterName, posX, posY);
                    // Update params
                    if (this.nodes[newId] && nodeData.params) {
                        this.nodes[newId].params = nodeData.params.map(p => ({
                            name: p.name,
                            type: p.type || 'float',
                            value: p.value,
                            min: p.min,
                            max: p.max,
                            step: p.step,
                            options: p.options || []
                        }));
                    }
                }
                nodeIdMap[oldId] = newId;
            }

            // Second pass: create connections
            for (const conn of connections) {
                const fromId = nodeIdMap[conn.from_node];
                const toId = nodeIdMap[conn.to_node];
                if (fromId && toId) {
                    const fromOutput = `output_${(conn.from_output || 0) + 1}`;
                    const toInput = `input_${(conn.to_input || 0) + 1}`;
                    try {
                        this.editor.addConnection(fromId, toId, fromOutput, toInput);
                    } catch (e) {
                        console.warn('Failed to add connection:', e);
                    }
                }
            }

            // Center the view
            this.centerView();

            // Emit graph changed
            this.$emit('graph-changed', this.getGraphData());
        }
    }
};
