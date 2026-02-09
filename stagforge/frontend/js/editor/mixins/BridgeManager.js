/**
 * BridgeManager Mixin
 *
 * Handles WebSocket bridge communication with Python backend.
 * Replaces NiceGUI's run_method/run_javascript calls with custom bridge.
 *
 * Features:
 * - Automatic WebSocket connection management
 * - Heartbeat and reconnection handling
 * - Command handler registration for Python-to-JS calls
 * - Event emission for JS-to-Python communication
 *
 * Required component data:
 *   - sessionId: String (from props)
 *   - Various methods from other mixins
 *
 * Required component methods (from other mixins):
 *   - executeToolAction(toolId, action, params)
 *   - executeCommand(command, params)
 *   - pushData(requestId, layerId, documentId, format, bg)
 *   - exportDocument(documentId)
 *   - importDocument(documentData, documentId)
 *   - getConfig(path)
 *   - setConfig(path, value)
 *   - getLayerEffects(layerId, documentId)
 *   - addLayerEffect(layerId, effectType, params, documentId)
 *   - updateLayerEffect(layerId, effectId, params, documentId)
 *   - removeLayerEffect(layerId, effectId, documentId)
 *   - buildStateUpdate()
 */

import { EditorBridgeClient } from '/static/js/bridge/EditorBridgeClient.js';

export const BridgeManagerMixin = {
    data() {
        return {
            // Bridge connection state
            bridgeConnected: false,
            bridgeState: 'disconnected',
        };
    },

    methods: {
        /**
         * Initialize the WebSocket bridge client.
         * Called during component mount.
         */
        initBridge() {
            // In 'off' mode, skip bridge entirely
            if (this.backendMode === 'off') {
                console.log('[BridgeManager] Backend mode is "off", bridge not initialized');
                this.bridgeConnected = false;
                this.bridgeState = 'disabled';
                return;
            }

            const sessionId = this.$props.sessionId;
            if (!sessionId) {
                console.warn('[BridgeManager] No sessionId provided, bridge not initialized');
                return;
            }

            // Determine WebSocket URL (ws:// or wss:// based on page protocol)
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/api/ws/editor`;

            this._bridge = new EditorBridgeClient({
                url: wsUrl,
                sessionId: sessionId,
                heartbeatInterval: 1000,
                reconnectDelay: 1000,
                maxReconnectAttempts: 10,
                responseTimeout: 30000,
            });

            // Register handlers for Python commands
            this._registerBridgeHandlers();

            // Handle connection state changes
            this._bridge.addEventListener('connected', () => {
                console.log('[BridgeManager] Connected');
                this.bridgeConnected = true;
                this.bridgeState = 'connected';
                // Send initial state update
                this.emitStateUpdate();
            });

            this._bridge.addEventListener('disconnected', () => {
                console.log('[BridgeManager] Disconnected');
                this.bridgeConnected = false;
                this.bridgeState = 'disconnected';
            });

            this._bridge.addEventListener('reconnecting', () => {
                console.log('[BridgeManager] Reconnecting...');
                this.bridgeState = 'reconnecting';
            });

            this._bridge.addEventListener('error', (e) => {
                console.error('[BridgeManager] Error:', e.detail);
            });
        },

        /**
         * Register all command handlers for Python-to-JS communication.
         * @private
         */
        _registerBridgeHandlers() {
            if (!this._bridge) return;

            // Tool execution
            this._bridge.registerHandler('executeToolAction', async (params) => {
                return this.executeToolAction(params.toolId, params.action, params.params);
            });

            // Command execution
            this._bridge.registerHandler('executeCommand', async (params) => {
                return this.executeCommand(params.command, params.params);
            });

            // Data push (for image/layer retrieval)
            this._bridge.registerHandler('pushData', async (params) => {
                return await this.pushData(
                    params.requestId,
                    params.layerId,
                    params.documentId,
                    params.format,
                    params.bg
                );
            });

            // Document export
            this._bridge.registerHandler('exportDocument', async (params) => {
                return await this.exportDocument(params.documentId);
            });

            // Document import
            this._bridge.registerHandler('importDocument', async (params) => {
                return await this.importDocument(params.documentData, params.documentId);
            });

            // Config get
            this._bridge.registerHandler('getConfig', (params) => {
                return this.getConfig(params.path);
            });

            // Config set
            this._bridge.registerHandler('setConfig', (params) => {
                return this.setConfig(params.path, params.value);
            });

            // Layer effects API
            this._bridge.registerHandler('getLayerEffects', (params) => {
                return this.getLayerEffects(params.layerId, params.documentId);
            });

            this._bridge.registerHandler('addLayerEffect', (params) => {
                return this.addLayerEffect(
                    params.layerId,
                    params.effectType,
                    params.params,
                    params.documentId
                );
            });

            this._bridge.registerHandler('updateLayerEffect', (params) => {
                return this.updateLayerEffect(
                    params.layerId,
                    params.effectId,
                    params.params,
                    params.documentId
                );
            });

            this._bridge.registerHandler('removeLayerEffect', (params) => {
                return this.removeLayerEffect(
                    params.layerId,
                    params.effectId,
                    params.documentId
                );
            });

            // Browser storage (OPFS) methods
            this._bridge.registerHandler('listStoredDocuments', async () => {
                return await this.listStoredDocuments();
            });

            this._bridge.registerHandler('clearStoredDocuments', async () => {
                return await this.clearStoredDocuments();
            });

            this._bridge.registerHandler('deleteStoredDocument', async (params) => {
                return await this.deleteStoredDocument(params.documentId);
            });

            // Editor actions (from canvas_editor.py)
            this._bridge.registerHandler('newDocument', (params) => {
                this.newDocument(params.width, params.height);
                return { success: true };
            });

            this._bridge.registerHandler('undo', () => {
                this.undo();
                return { success: true };
            });

            this._bridge.registerHandler('redo', () => {
                this.redo();
                return { success: true };
            });

            this._bridge.registerHandler('selectTool', (params) => {
                this.selectTool(params.toolId);
                return { success: true };
            });

            this._bridge.registerHandler('applyFilter', (params) => {
                this.applyFilter(params.filterId, params.params);
                return { success: true };
            });
        },

        /**
         * Connect to the bridge server.
         * @returns {Promise<void>}
         */
        async connectBridge() {
            if (!this._bridge) {
                this.initBridge();
            }

            if (this._bridge) {
                try {
                    await this._bridge.connect();
                } catch (e) {
                    console.error('[BridgeManager] Failed to connect:', e);
                }
            }
        },

        /**
         * Disconnect from the bridge server.
         */
        disconnectBridge() {
            if (this._bridge) {
                this._bridge.disconnect();
            }
        },

        /**
         * Emit state update to Python via bridge.
         * This replaces the Vue $emit('state-update') call.
         */
        emitStateUpdateViaBridge() {
            if (!this._bridge?.isConnected) {
                return;
            }

            // Build state update data
            const stateData = this.buildStateUpdate();

            // Send via bridge
            this._bridge.emit('state-update', stateData);
        },

        /**
         * Build the state update object for Python.
         * @returns {Object} State update data
         */
        buildStateUpdate() {
            const app = this.getState();
            if (!app?.documentManager) return {};

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
                    fillOpacity: layer.fillOpacity ?? 1,
                    blendMode: layer.blendMode,
                    width: layer.width || 0,
                    height: layer.height || 0,
                    offsetX: layer.offsetX || 0,
                    offsetY: layer.offsetY || 0,
                    parentId: layer.parentId || null,
                    // Transform properties
                    rotation: layer.rotation || 0,
                    scaleX: layer.scaleX ?? 1,
                    scaleY: layer.scaleY ?? 1,
                })) || [],
            }));

            const activeDoc = app.documentManager.getActiveDocument();

            return {
                active_document_id: activeDoc?.id || null,
                documents: documents,
                active_tool: this.currentToolId,
                tool_properties: this.toolProperties.reduce((acc, p) => { acc[p.id] = p.value; return acc; }, {}),
                foreground_color: this.fgColor,
                background_color: this.bgColor,
                zoom: this.zoom,
                recent_colors: this.recentColors,
            };
        },
    },

    mounted() {
        // Initialize and connect bridge after component is mounted
        this.$nextTick(() => {
            this.connectBridge();
        });
    },

    beforeUnmount() {
        // Clean up bridge connection
        this.disconnectBridge();
    },
};

export default BridgeManagerMixin;
